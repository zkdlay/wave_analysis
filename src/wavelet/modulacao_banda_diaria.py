import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analise_wavelet import (
    ARQUIVO_DADOS_TRATADOS,
    PASTA_SAIDA_FIGURAS,
    VARIAVEIS_ANALISAR,
    carregar_dados_tratados,
    caminho_disponivel,
    formatar_periodo,
    preparar_serie,
    salvar_texto,
)
from .comparar_wavelets import calcular_wavelet_por_mae


PASTA_SAIDA_MODULACAO = PASTA_SAIDA_FIGURAS.parent / "figuras_modulacao"
DPI_FIGURAS = 300

WAVELET_MODULACAO = "PAUL"
BANDA_DIARIA_HORAS = (20, 28)
VARIAVEIS_MODULACAO = ["radiacao_onda_curta", "temperatura", "umidade_relativa"]
PARES_MODULACAO = [
    ("radiacao_onda_curta", "temperatura"),
    ("radiacao_onda_curta", "umidade_relativa"),
    ("temperatura", "umidade_relativa"),
]


def salvar_figura(figura, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho_final = caminho_disponivel(caminho)
    figura.savefig(caminho_final, dpi=DPI_FIGURAS)
    plt.close(figura)
    return caminho_final


def calcular_potencia_banda(resultado, periodo_min_dias, periodo_max_dias):
    periodo = resultado["periodo"]
    mascara = (periodo >= periodo_min_dias) & (periodo <= periodo_max_dias)
    if not np.any(mascara):
        centro = (periodo_min_dias + periodo_max_dias) / 2
        mascara[np.argmin(np.abs(periodo - centro))] = True
    return np.nanmean(resultado["espectro_potencia"][mascara, :], axis=0)


def padronizar_0_1(serie):
    minimo = np.nanmin(serie)
    maximo = np.nanmax(serie)
    if maximo == minimo:
        return np.zeros_like(serie)
    return (serie - minimo) / (maximo - minimo)


def calcular_modulacao_diaria(dados):
    periodo_min_dias = BANDA_DIARIA_HORAS[0] / 24
    periodo_max_dias = BANDA_DIARIA_HORAS[1] / 24
    resultados = {}

    for coluna in VARIAVEIS_MODULACAO:
        serie_preparada = preparar_serie(dados, coluna)
        resultado_wavelet = calcular_wavelet_por_mae(serie_preparada, WAVELET_MODULACAO)
        potencia_banda = calcular_potencia_banda(
            resultado_wavelet,
            periodo_min_dias,
            periodo_max_dias,
        )
        resultados[coluna] = {
            "serie_preparada": serie_preparada,
            "resultado_wavelet": resultado_wavelet,
            "potencia_banda": potencia_banda,
            "potencia_banda_norm": padronizar_0_1(potencia_banda),
        }

    return resultados


def plotar_modulacao_par(resultados, variavel_a, variavel_b):
    datas = resultados[variavel_a]["serie_preparada"]["datas"]
    config_a = VARIAVEIS_ANALISAR[variavel_a]
    config_b = VARIAVEIS_ANALISAR[variavel_b]
    potencia_a = resultados[variavel_a]["potencia_banda_norm"]
    potencia_b = resultados[variavel_b]["potencia_banda_norm"]

    correlacao = pd.Series(potencia_a, index=datas).corr(pd.Series(potencia_b, index=datas))

    fig, eixos = plt.subplots(
        3,
        1,
        figsize=(14, 8),
        sharex=True,
        height_ratios=[1, 1, 1.15],
    )

    eixos[0].fill_between(datas, 0, potencia_a, color=config_a["cor"], alpha=0.85)
    eixos[0].set_ylim(0, 1)
    eixos[0].set_ylabel("Pot. norm.")
    eixos[0].set_title(f"{config_a['rotulo']} - potencia na banda diaria")
    eixos[0].grid(True, alpha=0.25)

    eixos[1].fill_between(datas, 0, potencia_b, color=config_b["cor"], alpha=0.85)
    eixos[1].set_ylim(0, 1)
    eixos[1].set_ylabel("Pot. norm.")
    eixos[1].set_title(f"{config_b['rotulo']} - potencia na banda diaria")
    eixos[1].grid(True, alpha=0.25)

    eixos[2].plot(
        datas,
        potencia_a,
        color=config_a["cor"],
        linewidth=1.2,
        label=config_a["rotulo"],
    )
    eixos[2].plot(
        datas,
        potencia_b,
        color=config_b["cor"],
        linewidth=1.2,
        label=config_b["rotulo"],
    )
    eixos[2].set_ylim(0, 1)
    eixos[2].set_ylabel("Potencia normalizada")
    eixos[2].set_xlabel("Data")
    eixos[2].set_title(f"Sobreposicao das potencias diarias | r = {correlacao:.3f}")
    eixos[2].legend(loc="upper right", frameon=True)
    eixos[2].grid(True, alpha=0.25)

    banda = f"{BANDA_DIARIA_HORAS[0]}-{BANDA_DIARIA_HORAS[1]} h"
    fig.suptitle(
        f"Modulacao da banda diaria ({banda}) - Wavelet {WAVELET_MODULACAO.title()}",
        fontsize=15,
    )
    fig.tight_layout()
    return fig, correlacao


def plotar_modulacao_tres_variaveis(resultados):
    datas = resultados[VARIAVEIS_MODULACAO[0]]["serie_preparada"]["datas"]

    fig, eixos = plt.subplots(
        4,
        1,
        figsize=(14, 10),
        sharex=True,
        height_ratios=[1, 1, 1, 1.25],
    )

    for eixo, coluna in zip(eixos[:3], VARIAVEIS_MODULACAO):
        config = VARIAVEIS_ANALISAR[coluna]
        potencia = resultados[coluna]["potencia_banda_norm"]
        eixo.fill_between(datas, 0, potencia, color=config["cor"], alpha=0.85)
        eixo.set_ylim(0, 1)
        eixo.set_ylabel("Pot. norm.")
        eixo.set_title(f"{config['rotulo']} - potencia na banda diaria")
        eixo.grid(True, alpha=0.25)

    for coluna in VARIAVEIS_MODULACAO:
        config = VARIAVEIS_ANALISAR[coluna]
        eixos[3].plot(
            datas,
            resultados[coluna]["potencia_banda_norm"],
            color=config["cor"],
            linewidth=1.1,
            label=config["rotulo"],
        )

    eixos[3].set_ylim(0, 1)
    eixos[3].set_ylabel("Potencia normalizada")
    eixos[3].set_xlabel("Data")
    eixos[3].set_title("Sobreposicao das potencias diarias")
    eixos[3].legend(loc="upper right", frameon=True)
    eixos[3].grid(True, alpha=0.25)

    banda = f"{BANDA_DIARIA_HORAS[0]}-{BANDA_DIARIA_HORAS[1]} h"
    fig.suptitle(
        f"Modulacao da banda diaria ({banda}) - tres variaveis - Wavelet {WAVELET_MODULACAO.title()}",
        fontsize=15,
    )
    fig.tight_layout()
    return fig


def gerar_relatorio_par(resultados, correlacao, variavel_a, variavel_b):
    periodo_min = BANDA_DIARIA_HORAS[0] / 24
    periodo_max = BANDA_DIARIA_HORAS[1] / 24
    linhas = [
        "Relatorio de modulacao da banda diaria",
        "=" * 72,
        f"Wavelet usada: {WAVELET_MODULACAO}",
        f"Banda: {BANDA_DIARIA_HORAS[0]}-{BANDA_DIARIA_HORAS[1]} h",
        f"Banda em dias: {periodo_min:.6f}-{periodo_max:.6f}",
        f"Variaveis comparadas: {VARIAVEIS_ANALISAR[variavel_a]['rotulo']} x {VARIAVEIS_ANALISAR[variavel_b]['rotulo']}",
        "",
        "Potencia media na banda diaria",
        "-" * 72,
    ]

    for coluna in [variavel_a, variavel_b]:
        potencia = resultados[coluna]["potencia_banda"]
        indice_maximo = int(np.nanargmax(potencia))
        instante_maximo = resultados[coluna]["serie_preparada"]["datas"][indice_maximo]
        linhas.extend(
            [
                f"{VARIAVEIS_ANALISAR[coluna]['rotulo']}:",
                f"  Media da potencia: {np.nanmean(potencia):.8g}",
                f"  Desvio padrao da potencia: {np.nanstd(potencia, ddof=1):.8g}",
                f"  Maximo da potencia: {np.nanmax(potencia):.8g}",
                f"  Instante do maximo: {instante_maximo}",
            ]
        )

    linhas.extend(
        [
            "",
            "Relacao entre as duas modulacoes",
            "-" * 72,
            f"Correlacao das potencias normalizadas: {correlacao:.6f}",
        ]
    )

    if correlacao > 0.5:
        interpretacao = "as duas potencias tendem a aumentar e diminuir juntas."
    elif correlacao < -0.5:
        interpretacao = "as duas potencias tendem a variar em sentidos opostos."
    else:
        interpretacao = "nao ha co-variacao linear forte entre as duas potencias."
    linhas.append(f"Leitura direta: {interpretacao}")

    return "\n".join(linhas) + "\n"


def gerar_relatorio_tres_variaveis(resultados):
    linhas = [
        "Relatorio de modulacao da banda diaria - tres variaveis",
        "=" * 72,
        f"Wavelet usada: {WAVELET_MODULACAO}",
        f"Banda: {BANDA_DIARIA_HORAS[0]}-{BANDA_DIARIA_HORAS[1]} h",
        "",
        "Correlacoes entre potencias normalizadas",
        "-" * 72,
    ]

    for variavel_a, variavel_b in PARES_MODULACAO:
        datas = resultados[variavel_a]["serie_preparada"]["datas"]
        potencia_a = resultados[variavel_a]["potencia_banda_norm"]
        potencia_b = resultados[variavel_b]["potencia_banda_norm"]
        correlacao = pd.Series(potencia_a, index=datas).corr(pd.Series(potencia_b, index=datas))
        linhas.append(
            f"{VARIAVEIS_ANALISAR[variavel_a]['rotulo']} x "
            f"{VARIAVEIS_ANALISAR[variavel_b]['rotulo']}: r = {correlacao:.6f}"
        )

    linhas.extend(["", "Resumo por variavel", "-" * 72])
    for coluna in VARIAVEIS_MODULACAO:
        potencia = resultados[coluna]["potencia_banda"]
        indice_maximo = int(np.nanargmax(potencia))
        instante_maximo = resultados[coluna]["serie_preparada"]["datas"][indice_maximo]
        linhas.extend(
            [
                f"{VARIAVEIS_ANALISAR[coluna]['rotulo']}:",
                f"  Media da potencia: {np.nanmean(potencia):.8g}",
                f"  Desvio padrao da potencia: {np.nanstd(potencia, ddof=1):.8g}",
                f"  Maximo da potencia: {np.nanmax(potencia):.8g}",
                f"  Instante do maximo: {instante_maximo}",
            ]
        )

    return "\n".join(linhas) + "\n"


def nome_curto_variavel(coluna):
    return {
        "radiacao_onda_curta": "radiacao",
        "temperatura": "temperatura",
        "umidade_relativa": "umidade",
    }.get(coluna, coluna)


def main():
    PASTA_SAIDA_MODULACAO.mkdir(parents=True, exist_ok=True)
    dados = carregar_dados_tratados(ARQUIVO_DADOS_TRATADOS)
    resultados = calcular_modulacao_diaria(dados)
    sufixo_wavelet = WAVELET_MODULACAO.lower()

    for variavel_a, variavel_b in PARES_MODULACAO:
        figura, correlacao = plotar_modulacao_par(resultados, variavel_a, variavel_b)
        sufixo = f"{nome_curto_variavel(variavel_a)}_{nome_curto_variavel(variavel_b)}"
        caminho_figura = PASTA_SAIDA_MODULACAO / f"modulacao_banda_diaria_{sufixo}_{sufixo_wavelet}.png"
        print(f"Figura salva em: {salvar_figura(figura, caminho_figura)}")

        relatorio = gerar_relatorio_par(resultados, correlacao, variavel_a, variavel_b)
        caminho_relatorio = PASTA_SAIDA_MODULACAO / f"relatorio_modulacao_banda_diaria_{sufixo}_{sufixo_wavelet}.txt"
        print(f"Relatorio salvo em: {salvar_texto(relatorio, caminho_relatorio)}")

    figura_tres = plotar_modulacao_tres_variaveis(resultados)
    caminho_figura_tres = PASTA_SAIDA_MODULACAO / f"modulacao_banda_diaria_tres_variaveis_{sufixo_wavelet}.png"
    print(f"Figura salva em: {salvar_figura(figura_tres, caminho_figura_tres)}")

    relatorio_tres = gerar_relatorio_tres_variaveis(resultados)
    caminho_relatorio_tres = PASTA_SAIDA_MODULACAO / f"relatorio_modulacao_banda_diaria_tres_variaveis_{sufixo_wavelet}.txt"
    print(f"Relatorio salvo em: {salvar_texto(relatorio_tres, caminho_relatorio_tres)}")


if __name__ == "__main__":
    main()
