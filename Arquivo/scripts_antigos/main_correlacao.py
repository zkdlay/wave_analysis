from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from main__wave import ARQUIVO_DADOS_TRATADOS, PASTA_SAIDA_FIGURAS, carregar_dados_tratados


PASTA_SAIDA_CORRELACAO = PASTA_SAIDA_FIGURAS.parent / "figuras_correlacao"
DPI_FIGURAS = 300
MAX_LAG_HORAS = 48

VARIAVEIS = {
    "temperatura": "Temp",
    "umidade_relativa": "Umid",
    "radiacao_onda_curta": "Rad",
}

PARES_CORRELACAO = [
    ("temperatura", "radiacao_onda_curta"),
    ("umidade_relativa", "radiacao_onda_curta"),
    ("temperatura", "umidade_relativa"),
]


def preparar_dados_correlacao():
    dados = carregar_dados_tratados(ARQUIVO_DADOS_TRATADOS)
    dados = dados[list(VARIAVEIS.keys())].copy()
    dados = dados.apply(pd.to_numeric, errors="coerce")
    dados = dados.interpolate(method="time").bfill().ffill()
    return dados


def salvar_figura(figura, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(caminho, dpi=DPI_FIGURAS)
    plt.close(figura)
    return caminho


def plotar_matriz_correlacao(matriz):
    fig, eixo = plt.subplots(figsize=(6, 5))
    imagem = eixo.imshow(matriz.values, cmap="RdBu_r", vmin=-1, vmax=1)

    eixo.set_xticks(range(len(matriz.columns)))
    eixo.set_yticks(range(len(matriz.index)))
    eixo.set_xticklabels(matriz.columns)
    eixo.set_yticklabels(matriz.index)

    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            valor = matriz.iloc[i, j]
            cor = "white" if abs(valor) > 0.55 else "black"
            eixo.text(j, i, f"{valor:.2f}", ha="center", va="center", color=cor)

    eixo.set_title("Matriz de correlacao")
    barra = fig.colorbar(imagem, ax=eixo, pad=0.02)
    barra.set_label("Correlacao de Pearson")
    fig.tight_layout()
    return fig


def calcular_cross_correlation(dados, variavel_x, variavel_y, max_lag=MAX_LAG_HORAS):
    serie_x = dados[variavel_x]
    serie_y = dados[variavel_y]
    resultados = []

    for lag in range(max_lag + 1):
        correlacao = serie_x.corr(serie_y.shift(lag))
        resultados.append({"lag_horas": lag, "correlacao": correlacao})

    return pd.DataFrame(resultados)


def plotar_cross_correlation(resultado, variavel_x, variavel_y):
    nome_x = VARIAVEIS[variavel_x]
    nome_y = VARIAVEIS[variavel_y]
    indice_maximo = resultado["correlacao"].abs().idxmax()
    lag_maximo = int(resultado.loc[indice_maximo, "lag_horas"])
    correlacao_maxima = resultado.loc[indice_maximo, "correlacao"]

    fig, eixo = plt.subplots(figsize=(8, 4.8))
    eixo.plot(
        resultado["lag_horas"],
        resultado["correlacao"],
        color="black",
        linewidth=1.4,
        marker="o",
        markersize=3,
    )
    eixo.axhline(0, color="#777777", linewidth=0.8)
    eixo.scatter(
        [lag_maximo],
        [correlacao_maxima],
        color="#d73027",
        s=55,
        zorder=3,
        label=f"Max |r|: lag {lag_maximo} h",
    )
    eixo.set_title(f"Cross-correlation: {nome_x} x {nome_y}")
    eixo.set_xlabel("Lag (horas)")
    eixo.set_ylabel("Correlacao")
    eixo.set_xlim(0, MAX_LAG_HORAS)
    eixo.set_ylim(-1, 1)
    eixo.grid(True, alpha=0.25)
    eixo.legend(loc="best", frameon=True)
    fig.tight_layout()
    return fig


def gerar_relatorio(matriz, resultados_lag):
    linhas = [
        "Relatorio de correlacao",
        "=" * 72,
        "",
        "Matriz de correlacao de Pearson",
        "-" * 72,
        matriz.to_string(float_format=lambda valor: f"{valor:.4f}"),
        "",
        "Cross-correlation por lag",
        "-" * 72,
        "Par\tLag_max_abs_horas\tCorrelacao_no_lag\tLag_max_positivo_horas\tCorrelacao_max_positiva",
    ]

    for (variavel_x, variavel_y), resultado in resultados_lag.items():
        nome_par = f"{VARIAVEIS[variavel_x]} x {VARIAVEIS[variavel_y]}"
        indice_abs = resultado["correlacao"].abs().idxmax()
        indice_pos = resultado["correlacao"].idxmax()
        linhas.append(
            f"{nome_par}\t"
            f"{int(resultado.loc[indice_abs, 'lag_horas'])}\t"
            f"{resultado.loc[indice_abs, 'correlacao']:.6f}\t"
            f"{int(resultado.loc[indice_pos, 'lag_horas'])}\t"
            f"{resultado.loc[indice_pos, 'correlacao']:.6f}"
        )

    return "\n".join(linhas) + "\n"


def main():
    PASTA_SAIDA_CORRELACAO.mkdir(parents=True, exist_ok=True)
    dados = preparar_dados_correlacao()
    dados_nomeados = dados.rename(columns=VARIAVEIS)
    matriz = dados_nomeados.corr()

    figura = plotar_matriz_correlacao(matriz)
    caminho_matriz = PASTA_SAIDA_CORRELACAO / "matriz_correlacao.png"
    print(f"Figura salva em: {salvar_figura(figura, caminho_matriz)}")

    resultados_lag = {}
    for variavel_x, variavel_y in PARES_CORRELACAO:
        resultado = calcular_cross_correlation(dados, variavel_x, variavel_y)
        resultados_lag[(variavel_x, variavel_y)] = resultado

        nome_arquivo = f"cross_correlation_{variavel_x}_x_{variavel_y}.png"
        figura = plotar_cross_correlation(resultado, variavel_x, variavel_y)
        caminho_figura = PASTA_SAIDA_CORRELACAO / nome_arquivo
        print(f"Figura salva em: {salvar_figura(figura, caminho_figura)}")

        caminho_csv = (
            PASTA_SAIDA_CORRELACAO
            / f"cross_correlation_{variavel_x}_x_{variavel_y}.csv"
        )
        resultado.to_csv(caminho_csv, index=False)
        print(f"Tabela salva em: {caminho_csv}")

    relatorio = gerar_relatorio(matriz, resultados_lag)
    caminho_relatorio = PASTA_SAIDA_CORRELACAO / "relatorio_correlacao.txt"
    caminho_relatorio.write_text(relatorio, encoding="utf-8")
    print(f"Relatorio salvo em: {caminho_relatorio}")


if __name__ == "__main__":
    main()
