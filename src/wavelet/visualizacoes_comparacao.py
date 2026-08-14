from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.colors import LogNorm, TwoSlopeNorm

from .analise_wavelet import (
    ARQUIVO_DADOS_TRATADOS,
    FONTE_ANALISE,
    PASTA_SAIDA_FIGURAS,
    QUANTIDADE_PICOS_GLOBAIS,
    VARIAVEIS_ANALISAR,
    carregar_dados_tratados,
    caminho_disponivel,
    detectar_picos_globais,
    formatar_periodo,
    preparar_serie,
)
from .comparar_wavelets import (
    CORES_WAVELETS,
    WAVELETS_COMPARAR,
    calcular_wavelet_por_mae,
)


PASTA_SAIDA_NOVAS_VISUALIZACOES = (
    PASTA_SAIDA_FIGURAS.parent.parent / "figuras_novas_visualizacoes" / FONTE_ANALISE
)
DPI_FIGURAS = 300

BANDAS_TEMPORAIS = {
    "diaria_24h": {
        "rotulo": "Banda diaria (24 h)",
        "periodo_min": 20 / 24,
        "periodo_max": 28 / 24,
    },
    "sinotica_2_8d": {
        "rotulo": "Banda sinotica (2-8 dias)",
        "periodo_min": 2,
        "periodo_max": 8,
    },
    "semanal_7_15d": {
        "rotulo": "Banda semanal (7-15 dias)",
        "periodo_min": 7,
        "periodo_max": 15,
    },
}


def configurar_eixo_periodo(eixo, periodo):
    eixo.set_yscale("log", base=2, subs=None)
    eixo.set_ylim([np.min(periodo), np.max(periodo)])
    eixo.invert_yaxis()
    eixo.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda valor, _: formatar_periodo(valor))
    )


def salvar_figura(figura, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho_final = caminho_disponivel(caminho)
    figura.savefig(caminho_final, dpi=DPI_FIGURAS)
    plt.close(figura)
    return caminho_final


def interpolar_potencia_para_grade(resultado, periodo_referencia):
    potencia = resultado["espectro_potencia"]
    periodo = resultado["periodo"]
    potencia_interpolada = np.empty((len(periodo_referencia), potencia.shape[1]))

    for indice_tempo in range(potencia.shape[1]):
        potencia_interpolada[:, indice_tempo] = np.interp(
            periodo_referencia,
            periodo,
            potencia[:, indice_tempo],
        )

    return potencia_interpolada


def plotar_espectros_globais(coluna, serie_preparada, resultados):
    config = VARIAVEIS_ANALISAR[coluna]
    fig, eixo = plt.subplots(figsize=(8.5, 7.5))

    for wavelet_mae, resultado in resultados.items():
        cor = CORES_WAVELETS.get(wavelet_mae, "black")
        eixo.plot(
            resultado["espectro_wavelet_global"],
            resultado["periodo"],
            color=cor,
            linewidth=1.8,
            label=wavelet_mae.title(),
        )

        picos = detectar_picos_globais(resultado, quantidade=QUANTIDADE_PICOS_GLOBAIS)
        if picos:
            eixo.scatter(
                [pico["potencia"] for pico in picos],
                [pico["periodo"] for pico in picos],
                color=cor,
                s=34,
                zorder=3,
            )

    configurar_eixo_periodo(eixo, next(iter(resultados.values()))["periodo"])
    eixo.set_title(f"Comparacao de espectros globais - {config['rotulo']}")
    eixo.set_xlabel(f"Potencia ({serie_preparada['unidade_potencia']})")
    eixo.set_ylabel("Periodo")
    eixo.grid(True, alpha=0.25)
    eixo.legend(loc="lower right", frameon=True)
    fig.tight_layout()
    return fig


def plotar_heatmap_diferenca(coluna, serie_preparada, resultados, wavelet_a, wavelet_b):
    config = VARIAVEIS_ANALISAR[coluna]
    datas = serie_preparada["datas"]
    resultado_a = resultados[wavelet_a]
    resultado_b = resultados[wavelet_b]
    periodo_referencia = resultado_a["periodo"]
    potencia_a = resultado_a["espectro_potencia"]
    potencia_b = interpolar_potencia_para_grade(resultado_b, periodo_referencia)
    diferenca = potencia_a - potencia_b

    limite = np.nanpercentile(np.abs(diferenca), 98)
    if not np.isfinite(limite) or limite == 0:
        limite = 1.0

    fig, eixo = plt.subplots(figsize=(14, 6))
    imagem = eixo.contourf(
        datas,
        periodo_referencia,
        diferenca,
        levels=np.linspace(-limite, limite, 31),
        cmap="RdBu_r",
        norm=TwoSlopeNorm(vcenter=0, vmin=-limite, vmax=limite),
        extend="both",
    )
    eixo.plot(
        datas,
        resultado_a["cone_influencia"],
        color="black",
        linewidth=1.3,
        label=f"COI {wavelet_a.title()}",
    )
    configurar_eixo_periodo(eixo, periodo_referencia)
    eixo.set_title(
        f"Heatmap da diferenca de potencia - {config['rotulo']}: "
        f"{wavelet_a.title()} - {wavelet_b.title()}"
    )
    eixo.set_xlabel("Data")
    eixo.set_ylabel("Periodo")
    eixo.legend(loc="upper right", frameon=True)
    barra = fig.colorbar(imagem, ax=eixo, pad=0.02)
    barra.set_label(
        f"Diferenca de potencia ({wavelet_a.title()} - {wavelet_b.title()})"
    )
    fig.tight_layout()
    return fig


def plotar_histogramas_potencia(coluna, serie_preparada, resultados):
    config = VARIAVEIS_ANALISAR[coluna]
    fig, eixos = plt.subplots(1, len(resultados), figsize=(16, 4.8), sharey=True)

    for eixo, (wavelet_mae, resultado) in zip(eixos, resultados.items()):
        potencia = resultado["espectro_potencia"].ravel()
        potencia = potencia[np.isfinite(potencia) & (potencia > 0)]
        eixo.hist(
            potencia,
            bins=60,
            color=CORES_WAVELETS.get(wavelet_mae, "black"),
            alpha=0.8,
        )
        eixo.axvline(np.nanmedian(potencia), color="black", linestyle="--", linewidth=1)
        eixo.axvline(np.nanpercentile(potencia, 95), color="#d73027", linewidth=1)
        eixo.set_xscale("log")
        eixo.set_title(wavelet_mae.title())
        eixo.set_xlabel(f"Potencia ({serie_preparada['unidade_potencia']})")
        eixo.grid(True, alpha=0.2)

    eixos[0].set_ylabel("Frequencia")
    fig.suptitle(
        f"Histograma das potencias - {config['rotulo']}\n"
        "Distribuicao concentrada em poucos eventos ou espalhada no tempo-escala",
        fontsize=14,
    )
    fig.tight_layout()
    return fig


def calcular_potencia_banda(resultado, periodo_min, periodo_max):
    periodo = resultado["periodo"]
    mascara = (periodo >= periodo_min) & (periodo <= periodo_max)
    if not np.any(mascara):
        indice = np.argmin(np.abs(periodo - (periodo_min + periodo_max) / 2))
        mascara[indice] = True
    return np.nanmean(resultado["espectro_potencia"][mascara, :], axis=0)


def plotar_evolucao_bandas(coluna, serie_preparada, resultados):
    config = VARIAVEIS_ANALISAR[coluna]
    datas = serie_preparada["datas"]
    fig, eixos = plt.subplots(
        len(BANDAS_TEMPORAIS),
        1,
        figsize=(14, 9),
        sharex=True,
    )

    for eixo, (_, banda) in zip(eixos, BANDAS_TEMPORAIS.items()):
        for wavelet_mae, resultado in resultados.items():
            potencia_banda = calcular_potencia_banda(
                resultado,
                banda["periodo_min"],
                banda["periodo_max"],
            )
            eixo.plot(
                datas,
                potencia_banda,
                color=CORES_WAVELETS.get(wavelet_mae, "black"),
                linewidth=1,
                label=wavelet_mae.title(),
            )
        eixo.set_title(banda["rotulo"])
        eixo.set_ylabel("Potencia media")
        eixo.grid(True, alpha=0.25)
        eixo.legend(loc="upper right", frameon=True, ncol=3)

    eixos[-1].set_xlabel("Data")
    fig.suptitle(f"Evolucao temporal da potencia por banda - {config['rotulo']}")
    fig.tight_layout()
    return fig


def main():
    PASTA_SAIDA_NOVAS_VISUALIZACOES.mkdir(parents=True, exist_ok=True)
    dados = carregar_dados_tratados(ARQUIVO_DADOS_TRATADOS)

    for coluna in VARIAVEIS_ANALISAR:
        if coluna not in dados.columns:
            print(f"[AVISO] Coluna nao encontrada: {coluna}. Pulando.")
            continue

        print(f"Gerando novas visualizacoes para: {coluna}")
        serie_preparada = preparar_serie(dados, coluna)
        resultados = {
            wavelet_mae: calcular_wavelet_por_mae(serie_preparada, wavelet_mae)
            for wavelet_mae in WAVELETS_COMPARAR
        }
        pasta_variavel = PASTA_SAIDA_NOVAS_VISUALIZACOES / coluna

        figura = plotar_espectros_globais(coluna, serie_preparada, resultados)
        caminho = pasta_variavel / f"comparacao_espectros_globais_{coluna}.png"
        print(f"Figura salva em: {salvar_figura(figura, caminho)}")

        for wavelet_a, wavelet_b in combinations(WAVELETS_COMPARAR, 2):
            figura = plotar_heatmap_diferenca(
                coluna,
                serie_preparada,
                resultados,
                wavelet_a,
                wavelet_b,
            )
            caminho = (
                pasta_variavel
                / f"heatmap_diferenca_{wavelet_a.lower()}_menos_{wavelet_b.lower()}_{coluna}.png"
            )
            print(f"Figura salva em: {salvar_figura(figura, caminho)}")

        figura = plotar_histogramas_potencia(coluna, serie_preparada, resultados)
        caminho = pasta_variavel / f"histograma_potencias_{coluna}.png"
        print(f"Figura salva em: {salvar_figura(figura, caminho)}")

        figura = plotar_evolucao_bandas(coluna, serie_preparada, resultados)
        caminho = pasta_variavel / f"evolucao_temporal_bandas_{coluna}.png"
        print(f"Figura salva em: {salvar_figura(figura, caminho)}")


if __name__ == "__main__":
    main()
