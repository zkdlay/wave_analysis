from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.colors import LogNorm

from funcoeswave import wave_signif, wavelet
from main__wave import (
    ARQUIVO_DADOS_TRATADOS,
    ESCALA_INICIAL,
    NORMALIZAR_SERIES,
    PASSO_TEMPO,
    PERIODO_MAX_MEDIA_ESCALA,
    PERIODO_MAX_ANALISE_DIAS,
    PERIODO_MIN_MEDIA_ESCALA,
    PASTA_SAIDA_FIGURAS,
    QUANTIDADE_PICOS_GLOBAIS,
    RESOLUCAO_ESCALA,
    USAR_PADDING,
    VARIAVEIS_ANALISAR,
    calcular_percentual_area_significativa,
    calcular_potencia_maxima,
    carregar_dados_tratados,
    caminho_disponivel,
    detectar_picos_globais,
    estimar_lag1,
    fator_fourier,
    formatar_periodo,
    gerar_texto_relatorio_individual,
    plotar_escalograma,
    plotar_espectro_global,
    plotar_serie_temporal,
    preparar_serie,
    salvar_texto,
)


# ---------------------------------------------------------------------------
# 1. Configuracoes
# ---------------------------------------------------------------------------

# Edite esta lista se quiser comparar apenas parte das wavelets.
WAVELETS_COMPARAR = ["MORLET", "PAUL", "DOG"]

PASTA_SAIDA_COMPARACAO = PASTA_SAIDA_FIGURAS.parent / "figuras_wavelet_comparacao"
DPI_FIGURAS = 300

CORES_WAVELETS = {
    "MORLET": "#1b9e77",
    "PAUL": "#d95f02",
    "DOG": "#7570b3",
}

CONSTANTES_RECONSTRUCAO = {
    "MORLET": 0.776,
    "PAUL": 1.132,
    "DOG": 3.541,
}


# ---------------------------------------------------------------------------
# 2. Calculo Wavelet parametrizado por wavelet mae
# ---------------------------------------------------------------------------

def calcular_numero_escalas(wavelet_mae):
    escala_maxima = PERIODO_MAX_ANALISE_DIAS / fator_fourier(wavelet_mae)
    return int(np.floor(np.log2(escala_maxima / ESCALA_INICIAL) / RESOLUCAO_ESCALA))


def calcular_wavelet_por_mae(serie_preparada, wavelet_mae):
    valores = serie_preparada["serie_wavelet"]
    numero_amostras = len(valores)
    numero_escalas = calcular_numero_escalas(wavelet_mae)
    autocorrelacao_lag1 = estimar_lag1(serie_preparada["serie_original"])

    coeficientes, periodo, escala, cone_influencia = wavelet(
        valores,
        PASSO_TEMPO,
        USAR_PADDING,
        RESOLUCAO_ESCALA,
        ESCALA_INICIAL,
        numero_escalas,
        wavelet_mae,
    )

    espectro_potencia = np.abs(coeficientes) ** 2
    espectro_wavelet_global = np.sum(espectro_potencia, axis=1) / numero_amostras

    significancia_teorica = wave_signif(
        [serie_preparada["variancia"]],
        dt=PASSO_TEMPO,
        sigtest=0,
        scale=escala,
        lag1=autocorrelacao_lag1,
        mother=wavelet_mae,
    )
    significancia_95 = significancia_teorica[:, np.newaxis].dot(
        np.ones(numero_amostras)[np.newaxis, :]
    )
    significancia_95 = espectro_potencia / significancia_95

    graus_liberdade_global = numero_amostras - escala
    significancia_global = wave_signif(
        serie_preparada["variancia"],
        dt=PASSO_TEMPO,
        scale=escala,
        sigtest=1,
        lag1=autocorrelacao_lag1,
        dof=graus_liberdade_global,
        mother=wavelet_mae,
    )

    periodo_min_escala = PERIODO_MIN_MEDIA_ESCALA / fator_fourier(wavelet_mae)
    periodo_max_escala = PERIODO_MAX_MEDIA_ESCALA / fator_fourier(wavelet_mae)
    intervalo_media_escala = np.logical_and(
        escala >= periodo_min_escala,
        escala < periodo_max_escala,
    )
    escala_expandida = escala[:, np.newaxis].dot(
        np.ones(numero_amostras)[np.newaxis, :]
    )
    potencia_normalizada_por_escala = espectro_potencia / escala_expandida
    constante_reconstrucao = CONSTANTES_RECONSTRUCAO[wavelet_mae.upper()]
    media_escala = (
        RESOLUCAO_ESCALA
        * PASSO_TEMPO
        / constante_reconstrucao
        * np.sum(potencia_normalizada_por_escala[intervalo_media_escala, :], axis=0)
    )

    significancia_media_escala = wave_signif(
        serie_preparada["variancia"],
        dt=PASSO_TEMPO,
        scale=escala,
        sigtest=2,
        lag1=autocorrelacao_lag1,
        dof=[periodo_min_escala, periodo_max_escala],
        mother=wavelet_mae,
    )

    return {
        "wavelet_mae": wavelet_mae,
        "periodo": periodo,
        "escala": escala,
        "cone_influencia": cone_influencia,
        "espectro_potencia": espectro_potencia,
        "espectro_wavelet_global": espectro_wavelet_global,
        "significancia_95": significancia_95,
        "significancia_global": significancia_global,
        "media_escala": media_escala,
        "significancia_media_escala": significancia_media_escala,
        "numero_escalas": numero_escalas,
        "lag1": autocorrelacao_lag1,
    }


# ---------------------------------------------------------------------------
# 3. Utilitarios de plotagem
# ---------------------------------------------------------------------------

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


def escala_cor_potencia(resultados):
    potencias = []
    for resultado in resultados.values():
        positivos = resultado["espectro_potencia"][resultado["espectro_potencia"] > 0]
        if positivos.size:
            potencias.append(positivos)

    if not potencias:
        return 1e-8, 1.0

    valores = np.concatenate(potencias)
    minimo = max(np.nanpercentile(valores, 2), 1e-8)
    maximo = max(np.nanpercentile(valores, 99), minimo * 10)
    return minimo, maximo


# ---------------------------------------------------------------------------
# 4. Figuras de comparacao
# ---------------------------------------------------------------------------

def plotar_par_escalogramas(coluna, serie_preparada, resultados, par_wavelets):
    config = VARIAVEIS_ANALISAR[coluna]
    datas = serie_preparada["datas"]
    minimo, maximo = escala_cor_potencia(
        {nome: resultados[nome] for nome in par_wavelets}
    )

    fig, eixos = plt.subplots(1, 2, figsize=(16, 6), sharex=True, sharey=True)

    for eixo, wavelet_mae in zip(eixos, par_wavelets):
        resultado = resultados[wavelet_mae]
        preenchimento = eixo.contourf(
            datas,
            resultado["periodo"],
            resultado["espectro_potencia"],
            levels=np.geomspace(minimo, maximo, 24),
            cmap="turbo",
            norm=LogNorm(vmin=minimo, vmax=maximo),
            extend="both",
        )
        eixo.contour(
            datas,
            resultado["periodo"],
            resultado["significancia_95"],
            levels=[1],
            colors="white",
            linewidths=1.2,
        )
        eixo.plot(
            datas,
            resultado["cone_influencia"],
            color="black",
            linewidth=1.4,
            label="COI",
        )
        eixo.fill_between(
            datas,
            resultado["cone_influencia"],
            resultado["periodo"][-1],
            color="white",
            alpha=0.32,
            hatch="///",
            edgecolor="#333333",
            linewidth=0.0,
        )
        configurar_eixo_periodo(eixo, resultado["periodo"])
        eixo.set_title(wavelet_mae.title())
        eixo.set_xlabel("Data")
        eixo.grid(True, alpha=0.18)

    eixos[0].set_ylabel("Periodo")
    barra = fig.colorbar(preenchimento, ax=eixos, pad=0.02)
    barra.set_label(f"Potencia wavelet ({serie_preparada['unidade_potencia']})")
    fig.suptitle(
        f"Comparacao de escalogramas - {config['rotulo']}: "
        f"{par_wavelets[0].title()} x {par_wavelets[1].title()}",
        fontsize=15,
    )
    return fig


def plotar_espectros_globais_sobrepostos(coluna, serie_preparada, resultados):
    config = VARIAVEIS_ANALISAR[coluna]
    fig, eixo = plt.subplots(figsize=(8, 7.5))

    textos_picos = []
    for wavelet_mae, resultado in resultados.items():
        cor = CORES_WAVELETS.get(wavelet_mae, "black")
        eixo.plot(
            resultado["espectro_wavelet_global"],
            resultado["periodo"],
            color=cor,
            linewidth=1.7,
            label=wavelet_mae.title(),
        )
        eixo.plot(
            resultado["significancia_global"],
            resultado["periodo"],
            color=cor,
            linestyle="--",
            linewidth=0.9,
            alpha=0.75,
            label=f"{wavelet_mae.title()} 95%",
        )

        picos = detectar_picos_globais(resultado, quantidade=QUANTIDADE_PICOS_GLOBAIS)
        if picos:
            eixo.scatter(
                [pico["potencia"] for pico in picos],
                [pico["periodo"] for pico in picos],
                color=cor,
                s=35,
                zorder=3,
            )
            textos_picos.append(
                f"{wavelet_mae.title()}: "
                + ", ".join(pico["rotulo"] for pico in picos)
            )

    configurar_eixo_periodo(eixo, next(iter(resultados.values()))["periodo"])
    eixo.set_title(f"Espectros globais sobrepostos - {config['rotulo']}")
    eixo.set_xlabel(f"Potencia ({serie_preparada['unidade_potencia']})")
    eixo.set_ylabel("Periodo")
    eixo.legend(loc="lower right", frameon=True, fontsize=9)
    eixo.grid(True, alpha=0.25)

    if textos_picos:
        eixo.text(
            0.02,
            0.98,
            "\n".join(textos_picos),
            transform=eixo.transAxes,
            va="top",
            ha="left",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
            fontsize=9,
        )

    fig.tight_layout()
    return fig


def plotar_espectros_globais_horizontais(coluna, serie_preparada, resultados):
    config = VARIAVEIS_ANALISAR[coluna]
    fig, eixo = plt.subplots(figsize=(12, 5.5))

    for wavelet_mae, resultado in resultados.items():
        periodo_horas = resultado["periodo"] * 24
        potencia = resultado["espectro_wavelet_global"]
        cor = CORES_WAVELETS.get(wavelet_mae, "black")
        eixo.fill_between(periodo_horas, potencia, color=cor, alpha=0.12)
        eixo.plot(
            periodo_horas,
            potencia,
            color=cor,
            linewidth=1.8,
            label=wavelet_mae.title(),
        )

        picos = detectar_picos_globais(resultado, quantidade=QUANTIDADE_PICOS_GLOBAIS)
        for pico in picos:
            eixo.scatter(pico["periodo"] * 24, pico["potencia"], color=cor, s=32)

    eixo.axvline(24, color="#555555", linestyle=":", linewidth=1, label="24 h")
    eixo.set_xscale("log", base=2)
    eixo.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda valor, _: formatar_periodo(valor / 24))
    )
    eixo.set_title(f"Espectros globais horizontais - {config['rotulo']}")
    eixo.set_xlabel("Periodo")
    eixo.set_ylabel(f"Potencia ({serie_preparada['unidade_potencia']})")
    eixo.grid(True, alpha=0.25)
    eixo.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    return fig


def plotar_espectro_global_individual(coluna, serie_preparada, resultado):
    config = VARIAVEIS_ANALISAR[coluna]
    wavelet_mae = resultado["wavelet_mae"]
    cor = CORES_WAVELETS.get(wavelet_mae, "black")
    picos = detectar_picos_globais(resultado, quantidade=QUANTIDADE_PICOS_GLOBAIS)

    fig, eixo = plt.subplots(figsize=(7.2, 7.2))
    eixo.plot(
        resultado["espectro_wavelet_global"],
        resultado["periodo"],
        color=cor,
        linewidth=1.7,
        label=f"{wavelet_mae.title()}",
    )
    eixo.plot(
        resultado["significancia_global"],
        resultado["periodo"],
        color="black",
        linestyle="--",
        linewidth=1,
        label="Significancia 95%",
    )

    for posicao, pico in enumerate(picos, start=1):
        eixo.scatter(pico["potencia"], pico["periodo"], color=cor, s=45, zorder=3)
        eixo.annotate(
            f"P{posicao}: {pico['rotulo']}",
            xy=(pico["potencia"], pico["periodo"]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )

    if picos:
        nomes = ["Pico principal", "Pico secundario", "Terceiro pico"]
        texto = "\n".join(
            f"{nome}: {pico['rotulo']}" for nome, pico in zip(nomes, picos)
        )
        eixo.text(
            0.98,
            0.98,
            texto,
            transform=eixo.transAxes,
            va="top",
            ha="right",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
            fontsize=9,
        )

    configurar_eixo_periodo(eixo, resultado["periodo"])
    eixo.set_title(f"Espectro global {wavelet_mae.title()} - {config['rotulo']}")
    eixo.set_xlabel(f"Potencia ({serie_preparada['unidade_potencia']})")
    eixo.set_ylabel("Periodo")
    eixo.legend(loc="lower right", frameon=True)
    eixo.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def plotar_media_escala_individual(coluna, serie_preparada, resultado):
    config = VARIAVEIS_ANALISAR[coluna]
    wavelet_mae = resultado["wavelet_mae"]
    cor = CORES_WAVELETS.get(wavelet_mae, "black")

    fig, eixo = plt.subplots(figsize=(14, 4.8))
    eixo.plot(
        serie_preparada["datas"],
        resultado["media_escala"],
        color=cor,
        linewidth=1.2,
        label=f"{wavelet_mae.title()}",
    )
    eixo.axhline(
        resultado["significancia_media_escala"],
        color="black",
        linestyle="--",
        linewidth=1,
        label="Significancia 95%",
    )
    eixo.set_title(
        f"Media de escala {PERIODO_MIN_MEDIA_ESCALA}-{PERIODO_MAX_MEDIA_ESCALA} dias "
        f"- {wavelet_mae.title()} - {config['rotulo']}"
    )
    eixo.set_xlabel("Data")
    eixo.set_ylabel(f"Potencia media ({serie_preparada['unidade_potencia']})")
    eixo.grid(True, alpha=0.25)
    eixo.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    return fig


def gerar_texto_relatorio_comparacao(coluna, serie_preparada, resultados):
    config = VARIAVEIS_ANALISAR[coluna]
    linhas = [
        f"Relatorio comparativo de wavelets - {config['rotulo']}",
        "=" * 88,
        f"Normalizacao: {'ativada' if NORMALIZAR_SERIES else 'desativada'}",
        f"Unidade da serie: {config['unidade']}",
        f"Unidade da potencia: {serie_preparada['unidade_potencia']}",
        f"Amostras: {len(serie_preparada['datas'])}",
        "",
        "Periodos dominantes",
        "-" * 88,
        "Wavelet\tOrdem\tPeriodo\tPeriodo_dias\tPotencia_global",
    ]

    metricas = {}
    nomes = ["principal", "secundario", "terceiro"]
    for wavelet_mae, resultado in resultados.items():
        picos = detectar_picos_globais(resultado, quantidade=QUANTIDADE_PICOS_GLOBAIS)
        potencia_maxima = calcular_potencia_maxima(serie_preparada, resultado)
        percentual_significativo = calcular_percentual_area_significativa(resultado)
        metricas[wavelet_mae] = {
            "picos": picos,
            "potencia_maxima": potencia_maxima,
            "percentual_significativo": percentual_significativo,
        }

        for ordem, pico in enumerate(picos, start=1):
            nome = nomes[ordem - 1] if ordem <= len(nomes) else f"pico_{ordem}"
            linhas.append(
                f"{wavelet_mae}\t{nome}\t{pico['rotulo']}\t"
                f"{pico['periodo']:.8f}\t{pico['potencia']:.8g}"
            )

    linhas.extend(
        [
            "",
            "Potencia maxima local no escalograma",
            "-" * 88,
            "Wavelet\tPotencia_maxima\tInstante\tPeriodo\tPeriodo_dias",
        ]
    )
    for wavelet_mae, valores in metricas.items():
        potencia_maxima = valores["potencia_maxima"]
        linhas.append(
            f"{wavelet_mae}\t{potencia_maxima['potencia']:.8g}\t"
            f"{potencia_maxima['instante']}\t"
            f"{potencia_maxima['periodo_formatado']}\t"
            f"{potencia_maxima['periodo']:.8f}"
        )

    linhas.extend(
        [
            "",
            "Regioes significativas",
            "-" * 88,
            "Wavelet\tPercentual_area_significativa",
        ]
    )
    for wavelet_mae, valores in metricas.items():
        linhas.append(
            f"{wavelet_mae}\t{valores['percentual_significativo']:.3f}%"
        )

    linhas.extend(
        [
            "",
            "Comparacao direta do percentual significativo",
            "-" * 88,
        ]
    )
    ordenados = sorted(
        metricas.items(),
        key=lambda item: item[1]["percentual_significativo"],
        reverse=True,
    )
    for posicao, (wavelet_mae, valores) in enumerate(ordenados, start=1):
        linhas.append(
            f"{posicao}. {wavelet_mae}: {valores['percentual_significativo']:.3f}%"
        )

    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------------------
# 5. Execucao
# ---------------------------------------------------------------------------

def main():
    PASTA_SAIDA_COMPARACAO.mkdir(parents=True, exist_ok=True)
    dados = carregar_dados_tratados(ARQUIVO_DADOS_TRATADOS)

    for coluna in VARIAVEIS_ANALISAR:
        if coluna not in dados.columns:
            print(f"[AVISO] Coluna nao encontrada: {coluna}. Pulando.")
            continue

        print(f"Comparando wavelets para: {coluna}")
        serie_preparada = preparar_serie(dados, coluna)
        resultados = {
            wavelet_mae: calcular_wavelet_por_mae(serie_preparada, wavelet_mae)
            for wavelet_mae in WAVELETS_COMPARAR
        }

        pasta_variavel = PASTA_SAIDA_COMPARACAO / coluna

        for wavelet_mae, resultado in resultados.items():
            pasta_wavelet = pasta_variavel / wavelet_mae.lower()
            picos = detectar_picos_globais(
                resultado,
                quantidade=QUANTIDADE_PICOS_GLOBAIS,
            )

            figura = plotar_serie_temporal(coluna, serie_preparada)
            caminho = (
                pasta_wavelet
                / f"serie_temporal_{wavelet_mae.lower()}_{coluna}.png"
            )
            print(f"Figura salva em: {salvar_figura(figura, caminho)}")

            figura = plotar_escalograma(coluna, serie_preparada, resultado)
            caminho = pasta_wavelet / f"escalograma_{wavelet_mae.lower()}_{coluna}.png"
            print(f"Figura salva em: {salvar_figura(figura, caminho)}")

            figura = plotar_espectro_global_individual(
                coluna,
                serie_preparada,
                resultado,
            )
            caminho = (
                pasta_wavelet
                / f"espectro_global_{wavelet_mae.lower()}_{coluna}.png"
            )
            print(f"Figura salva em: {salvar_figura(figura, caminho)}")

            figura = plotar_media_escala_individual(coluna, serie_preparada, resultado)
            caminho = (
                pasta_wavelet
                / f"media_escala_{wavelet_mae.lower()}_{coluna}.png"
            )
            print(f"Figura salva em: {salvar_figura(figura, caminho)}")

            relatorio = gerar_texto_relatorio_individual(
                coluna,
                serie_preparada,
                resultado,
                picos,
            )
            caminho_relatorio = (
                pasta_wavelet
                / f"relatorio_{wavelet_mae.lower()}_{coluna}.txt"
            )
            print(f"Relatorio salvo em: {salvar_texto(relatorio, caminho_relatorio)}")

        figura = plotar_espectros_globais_sobrepostos(
            coluna,
            serie_preparada,
            resultados,
        )
        caminho = pasta_variavel / f"espectros_globais_sobrepostos_{coluna}.png"
        print(f"Figura salva em: {salvar_figura(figura, caminho)}")

        figura = plotar_espectros_globais_horizontais(
            coluna,
            serie_preparada,
            resultados,
        )
        caminho = pasta_variavel / f"espectros_globais_horizontais_{coluna}.png"
        print(f"Figura salva em: {salvar_figura(figura, caminho)}")

        for wavelet_a, wavelet_b in combinations(WAVELETS_COMPARAR, 2):
            figura = plotar_par_escalogramas(
                coluna,
                serie_preparada,
                resultados,
                (wavelet_a, wavelet_b),
            )
            caminho = (
                pasta_variavel
                / f"escalogramas_{wavelet_a.lower()}_x_{wavelet_b.lower()}_{coluna}.png"
            )
            print(f"Figura salva em: {salvar_figura(figura, caminho)}")

        relatorio = gerar_texto_relatorio_comparacao(
            coluna,
            serie_preparada,
            resultados,
        )
        caminho_relatorio = pasta_variavel / f"relatorio_comparacao_{coluna}.txt"
        print(f"Relatorio salvo em: {salvar_texto(relatorio, caminho_relatorio)}")


if __name__ == "__main__":
    main()
