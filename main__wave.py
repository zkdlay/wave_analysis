from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import ticker
from matplotlib.colors import LogNorm

from funcoeswave import wave_signif, wavelet


# ---------------------------------------------------------------------------
# 1. Configuracoes gerais
# ---------------------------------------------------------------------------

PASTA_PROJETO_DADOS = Path(
    r"C:\Users\Windows\OneDrive\Documentos\Iniciação Cientifica - INPE\2026"
)
ARQUIVO_DADOS_TRATADOS = (
    PASTA_PROJETO_DADOS / "dados_tratados" / "nasa_power_tratado.csv"
)
PASTA_SAIDA_FIGURAS = Path(__file__).resolve().parent / "figuras_wavelet"

# Ative para comparar variaveis em escala padronizada. Desative para manter
# as unidades fisicas originais de cada serie.
NORMALIZAR_SERIES = True

# A transformada wavelet precisa de uma serie regular. Se houver falhas na
# sequencia horaria, os valores ausentes serao interpolados quando esta opcao
# estiver ativa.
INTERPOLAR_FALTANTES = True

VARIAVEIS_ANALISAR = {
    "temperatura": {
        "rotulo": "Temperatura",
        "unidade": "degC",
        "cor": "#b2182b",
    },
    "umidade_relativa": {
        "rotulo": "Umidade relativa",
        "unidade": "%",
        "cor": "#2166ac",
    },
    "radiacao_onda_curta": {
        "rotulo": "Radiacao de onda curta",
        "unidade": "MJ/m2/h",
        "cor": "#ef8a00",
    },
}


# ---------------------------------------------------------------------------
# 2. Parametros da analise wavelet
# ---------------------------------------------------------------------------

PASSO_TEMPO = 1 / 24  # dias; a base tratada esta em frequencia horaria.
USAR_PADDING = 1
RESOLUCAO_ESCALA = 0.25
ESCALA_INICIAL = 2 * PASSO_TEMPO  # 2 horas, em unidade de dias.
PERIODO_MAX_ANALISE_DIAS = 365
WAVELET_MAE = "PAUL"

PERIODO_MIN_MEDIA_ESCALA = 2
PERIODO_MAX_MEDIA_ESCALA = 8
CONSTANTE_RECONSTRUCAO = 1.132  # Cdelta para wavelet PAUL com parametro 4.
LIMIAR_EVENTO_EXTREMO = 2.0
QUANTIDADE_PICOS_GLOBAIS = 3
DPI_FIGURAS = 300


# ---------------------------------------------------------------------------
# 3. Leitura e preparo da base tratada
# ---------------------------------------------------------------------------

def carregar_dados_tratados(caminho_csv):
    dados = pd.read_csv(caminho_csv)

    coluna_tempo = "data_hora" if "data_hora" in dados.columns else "data"
    dados[coluna_tempo] = pd.to_datetime(dados[coluna_tempo])
    dados = dados.sort_values(coluna_tempo).drop_duplicates(
        subset=coluna_tempo,
        keep="first",
    )
    dados = dados.set_index(coluna_tempo)
    dados = dados.asfreq("h")
    return dados


def preparar_serie(dados, coluna):
    serie = pd.to_numeric(dados[coluna], errors="coerce")

    if INTERPOLAR_FALTANTES:
        serie = serie.interpolate(method="time").bfill().ffill()
    else:
        serie = serie.dropna()

    serie_anomalia = serie - serie.mean()
    desvio_padrao = serie_anomalia.std(ddof=1)
    autocorrelacao_lag1 = estimar_lag1(serie_anomalia)

    if desvio_padrao == 0 or np.isnan(desvio_padrao):
        raise ValueError(f"A serie '{coluna}' tem desvio padrao zero ou invalido.")

    if NORMALIZAR_SERIES:
        serie_wavelet = serie_anomalia / desvio_padrao
        variancia = 1.0
        unidade_potencia = "adimensional"
    else:
        serie_wavelet = serie_anomalia
        variancia = desvio_padrao**2
        unidade_potencia = f"{VARIAVEIS_ANALISAR[coluna]['unidade']}^2"

    return {
        "datas": serie_wavelet.index,
        "serie_original": serie,
        "serie_wavelet": serie_wavelet.to_numpy(),
        "media_original": serie.mean(),
        "desvio_padrao_original": serie.std(ddof=1),
        "variancia": variancia,
        "lag1": autocorrelacao_lag1,
        "unidade_potencia": unidade_potencia,
    }


# ---------------------------------------------------------------------------
# 4. Calculo da transformada wavelet
# ---------------------------------------------------------------------------

def fator_fourier(wavelet_mae):
    if wavelet_mae.upper() == "MORLET":
        parametro = 6.0
        return 4 * np.pi / (parametro + np.sqrt(2 + parametro**2))
    if wavelet_mae.upper() == "PAUL":
        parametro = 4.0
        return 4 * np.pi / (2 * parametro + 1)
    if wavelet_mae.upper() == "DOG":
        parametro = 2.0
        return 2 * np.pi * np.sqrt(2.0 / (2 * parametro + 1))
    raise ValueError("Wavelet mae deve ser MORLET, PAUL ou DOG.")


def calcular_numero_escalas():
    escala_maxima = PERIODO_MAX_ANALISE_DIAS / fator_fourier(WAVELET_MAE)
    return int(np.floor(np.log2(escala_maxima / ESCALA_INICIAL) / RESOLUCAO_ESCALA))


def estimar_lag1(serie):
    lag1 = serie.autocorr(lag=1)
    if np.isnan(lag1):
        return 0.0
    return float(np.clip(lag1, -0.99, 0.99))


def calcular_wavelet(serie_preparada):
    valores = serie_preparada["serie_wavelet"]
    numero_amostras = len(valores)
    numero_escalas = calcular_numero_escalas()
    autocorrelacao_lag1 = serie_preparada["lag1"]

    coeficientes, periodo, escala, cone_influencia = wavelet(
        valores,
        PASSO_TEMPO,
        USAR_PADDING,
        RESOLUCAO_ESCALA,
        ESCALA_INICIAL,
        numero_escalas,
        WAVELET_MAE,
    )

    espectro_potencia = np.abs(coeficientes) ** 2
    espectro_wavelet_global = np.sum(espectro_potencia, axis=1) / numero_amostras

    significancia_teorica = wave_signif(
        [serie_preparada["variancia"]],
        dt=PASSO_TEMPO,
        sigtest=0,
        scale=escala,
        lag1=autocorrelacao_lag1,
        mother=WAVELET_MAE,
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
        mother=WAVELET_MAE,
    )

    periodo_min_escala = PERIODO_MIN_MEDIA_ESCALA / fator_fourier(WAVELET_MAE)
    periodo_max_escala = PERIODO_MAX_MEDIA_ESCALA / fator_fourier(WAVELET_MAE)
    intervalo_media_escala = np.logical_and(
        escala >= periodo_min_escala,
        escala < periodo_max_escala,
    )
    escala_expandida = escala[:, np.newaxis].dot(
        np.ones(numero_amostras)[np.newaxis, :]
    )
    potencia_normalizada_por_escala = espectro_potencia / escala_expandida
    media_escala = (
        RESOLUCAO_ESCALA
        * PASSO_TEMPO
        / CONSTANTE_RECONSTRUCAO
        * np.sum(potencia_normalizada_por_escala[intervalo_media_escala, :], axis=0)
    )

    significancia_media_escala = wave_signif(
        serie_preparada["variancia"],
        dt=PASSO_TEMPO,
        scale=escala,
        sigtest=2,
        lag1=autocorrelacao_lag1,
        dof=[periodo_min_escala, periodo_max_escala],
        mother=WAVELET_MAE,
    )

    return {
        "wavelet_mae": WAVELET_MAE,
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
    }


# ---------------------------------------------------------------------------
# 5. Plotagem em quadro unico com paineis separados
# ---------------------------------------------------------------------------

def formatar_periodo(periodo_dias):
    horas = periodo_dias * 24
    if horas < 48:
        return f"{horas:.0f} h"
    return f"{periodo_dias:.1f} d"


def detectar_eventos_extremos(serie_preparada):
    serie = serie_preparada["serie_original"]
    media = serie_preparada["media_original"]
    desvio = serie_preparada["desvio_padrao_original"]
    zscore = (serie - media) / desvio
    return serie[np.abs(zscore) >= LIMIAR_EVENTO_EXTREMO]


def detectar_picos_globais(resultado, quantidade=QUANTIDADE_PICOS_GLOBAIS):
    espectro = np.asarray(resultado["espectro_wavelet_global"])
    periodos = np.asarray(resultado["periodo"])
    significancia = np.asarray(resultado["significancia_global"])
    candidatos = []

    for indice in range(1, len(espectro) - 1):
        if espectro[indice] <= espectro[indice - 1]:
            continue
        if espectro[indice] <= espectro[indice + 1]:
            continue
        if espectro[indice] <= significancia[indice]:
            continue
        candidatos.append(indice)

    if not candidatos:
        candidatos = list(np.argsort(espectro)[-quantidade:])

    candidatos = sorted(candidatos, key=lambda indice: espectro[indice], reverse=True)
    picos = []
    for indice in candidatos:
        periodo = periodos[indice]
        if any(abs(np.log2(periodo / pico["periodo"])) < 0.25 for pico in picos):
            continue
        picos.append(
            {
                "indice": indice,
                "periodo": periodo,
                "potencia": espectro[indice],
                "rotulo": formatar_periodo(periodo),
            }
        )
        if len(picos) == quantidade:
            break

    return picos


def calcular_potencia_maxima(serie_preparada, resultado):
    indice_periodo, indice_tempo = np.unravel_index(
        np.nanargmax(resultado["espectro_potencia"]),
        resultado["espectro_potencia"].shape,
    )
    return {
        "potencia": float(resultado["espectro_potencia"][indice_periodo, indice_tempo]),
        "instante": serie_preparada["datas"][indice_tempo],
        "periodo": float(resultado["periodo"][indice_periodo]),
        "periodo_formatado": formatar_periodo(resultado["periodo"][indice_periodo]),
    }


def calcular_percentual_area_significativa(resultado):
    area_significativa = np.asarray(resultado["significancia_95"]) > 1
    return float(100 * np.nanmean(area_significativa))


def gerar_texto_relatorio_individual(coluna, serie_preparada, resultado, picos):
    config = VARIAVEIS_ANALISAR[coluna]
    wavelet_mae = resultado.get("wavelet_mae", WAVELET_MAE)
    potencia_maxima = calcular_potencia_maxima(serie_preparada, resultado)
    percentual_significativo = calcular_percentual_area_significativa(resultado)

    linhas = [
        f"Relatorio Wavelet - {config['rotulo']}",
        "=" * 72,
        f"Wavelet: {wavelet_mae}",
        f"Normalizacao: {'ativada' if NORMALIZAR_SERIES else 'desativada'}",
        f"Unidade da serie: {config['unidade']}",
        f"Unidade da potencia: {serie_preparada['unidade_potencia']}",
        f"Amostras: {len(serie_preparada['datas'])}",
        f"Lag-1 estimado: {serie_preparada['lag1']:.6f}",
        "",
        "Periodo dominante pelo espectro global",
        "-" * 72,
        "Ordem\tPeriodo\tPeriodo_dias\tPotencia_global",
    ]

    nomes = ["principal", "secundario", "terceiro"]
    for ordem, pico in enumerate(picos, start=1):
        nome = nomes[ordem - 1] if ordem <= len(nomes) else f"pico_{ordem}"
        linhas.append(
            f"{nome}\t{pico['rotulo']}\t{pico['periodo']:.8f}\t{pico['potencia']:.8g}"
        )

    linhas.extend(
        [
            "",
            "Potencia maxima local no escalograma",
            "-" * 72,
            f"Potencia maxima: {potencia_maxima['potencia']:.8g}",
            f"Instante da potencia maxima: {potencia_maxima['instante']}",
            f"Periodo correspondente: {potencia_maxima['periodo_formatado']}",
            f"Periodo correspondente (dias): {potencia_maxima['periodo']:.8f}",
            "",
            "Regioes significativas",
            "-" * 72,
            f"Percentual da area significativa: {percentual_significativo:.3f}%",
        ]
    )

    return "\n".join(linhas) + "\n"


def salvar_texto(conteudo, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def configurar_eixo_periodo(eixo, periodo):
    eixo.set_yscale("log", base=2, subs=None)
    eixo.set_ylim([np.min(periodo), np.max(periodo)])
    eixo.invert_yaxis()
    eixo.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda valor, _: formatar_periodo(valor))
    )


def plotar_serie_temporal(coluna, serie_preparada):
    config = VARIAVEIS_ANALISAR[coluna]
    datas = serie_preparada["datas"]
    serie = serie_preparada["serie_original"]
    media = serie_preparada["media_original"]
    desvio = serie_preparada["desvio_padrao_original"]
    extremos = detectar_eventos_extremos(serie_preparada)

    fig, eixo = plt.subplots(figsize=(14, 4.8))
    eixo.plot(datas, serie, color=config["cor"], linewidth=1, label=config["rotulo"])
    eixo.axhline(media, color="black", linestyle="-", linewidth=1, label="Media")
    eixo.axhline(
        media + desvio,
        color="#555555",
        linestyle="--",
        linewidth=0.9,
        label="+/- 1 desvio padrao",
    )
    eixo.axhline(media - desvio, color="#555555", linestyle="--", linewidth=0.9)

    if not extremos.empty:
        eixo.scatter(
            extremos.index,
            extremos.values,
            s=18,
            color="#d73027",
            edgecolor="white",
            linewidth=0.4,
            zorder=3,
            label=f"Eventos extremos (|z| >= {LIMIAR_EVENTO_EXTREMO:g})",
        )

    texto = (
        f"Media = {media:.2f} {config['unidade']}\n"
        f"Desvio padrao = {desvio:.2f} {config['unidade']}\n"
        f"Extremos = {len(extremos)}"
    )
    eixo.text(
        0.01,
        0.97,
        texto,
        transform=eixo.transAxes,
        va="top",
        ha="left",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
        fontsize=10,
    )

    eixo.set_title(f"Serie temporal - {config['rotulo']}")
    eixo.set_ylabel(config["unidade"])
    eixo.set_xlabel("Data")
    eixo.legend(loc="upper right", frameon=True)
    eixo.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def plotar_escalograma(coluna, serie_preparada, resultado):
    config = VARIAVEIS_ANALISAR[coluna]
    datas = serie_preparada["datas"]
    potencia = resultado["espectro_potencia"]
    potencia_positiva = potencia[potencia > 0]
    minimo = np.nanpercentile(potencia_positiva, 2) if potencia_positiva.size else 1e-6
    maximo = np.nanpercentile(potencia_positiva, 99) if potencia_positiva.size else 1.0
    minimo = max(minimo, 1e-8)
    maximo = max(maximo, minimo * 10)

    fig, eixo = plt.subplots(figsize=(14, 6))
    preenchimento = eixo.contourf(
        datas,
        resultado["periodo"],
        potencia,
        levels=np.geomspace(minimo, maximo, 24),
        cmap="turbo",
        norm=LogNorm(vmin=minimo, vmax=maximo),
        extend="both",
    )
    contorno = eixo.contour(
        datas,
        resultado["periodo"],
        resultado["significancia_95"],
        levels=[1],
        colors="white",
        linewidths=1.4,
    )
    eixo.plot(
        datas,
        resultado["cone_influencia"],
        color="black",
        linewidth=1.6,
        label="COI",
    )
    eixo.fill_between(
        datas,
        resultado["cone_influencia"],
        resultado["periodo"][-1],
        color="white",
        alpha=0.35,
        hatch="///",
        edgecolor="#333333",
        linewidth=0.0,
        label="Fora do COI",
    )

    configurar_eixo_periodo(eixo, resultado["periodo"])
    eixo.set_title(f"Escalograma Wavelet - {config['rotulo']}")
    eixo.set_ylabel("Periodo")
    eixo.set_xlabel("Data")
    eixo.legend(loc="upper right", frameon=True)
    eixo.clabel(contorno, fmt={1: "95%"}, inline=True, fontsize=9)
    barra = fig.colorbar(preenchimento, ax=eixo, pad=0.02)
    barra.set_label(f"Potencia wavelet ({serie_preparada['unidade_potencia']})")
    fig.tight_layout()
    return fig


def plotar_espectro_global(coluna, serie_preparada, resultado, picos):
    config = VARIAVEIS_ANALISAR[coluna]
    fig, eixo = plt.subplots(figsize=(7.5, 7.5))
    eixo.plot(
        resultado["espectro_wavelet_global"],
        resultado["periodo"],
        color="black",
        linewidth=1.5,
        label="Espectro global",
    )
    eixo.plot(
        resultado["significancia_global"],
        resultado["periodo"],
        color="#d73027",
        linestyle="--",
        linewidth=1.2,
        label="Significancia 95%",
    )

    for posicao, pico in enumerate(picos, start=1):
        eixo.scatter(pico["potencia"], pico["periodo"], s=45, color="#2166ac", zorder=3)
        eixo.annotate(
            f"P{posicao}: {pico['rotulo']}",
            xy=(pico["potencia"], pico["periodo"]),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )

    if picos:
        linhas = []
        nomes = ["Pico principal", "Pico secundario", "Terceiro pico"]
        for nome, pico in zip(nomes, picos):
            linhas.append(f"{nome}: {pico['rotulo']}")
        texto = "\n".join(linhas)
        eixo.text(
            0.98,
            0.98,
            texto,
            transform=eixo.transAxes,
            va="top",
            ha="right",
            bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#cccccc"},
            fontsize=10,
        )

    configurar_eixo_periodo(eixo, resultado["periodo"])
    eixo.set_title(f"Espectro global - {config['rotulo']}")
    eixo.set_xlabel(f"Potencia ({serie_preparada['unidade_potencia']})")
    eixo.set_ylabel("Periodo")
    eixo.legend(loc="lower right", frameon=True)
    eixo.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def plotar_espectro_global_horizontal(coluna, serie_preparada, resultado, picos):
    config = VARIAVEIS_ANALISAR[coluna]
    periodo_horas = resultado["periodo"] * 24
    potencia = resultado["espectro_wavelet_global"]
    significancia = resultado["significancia_global"]

    fig, eixo = plt.subplots(figsize=(12, 5.5))
    eixo.fill_between(
        periodo_horas,
        potencia,
        color=config["cor"],
        alpha=0.35,
        label="Potencia global",
    )
    eixo.plot(periodo_horas, potencia, color=config["cor"], linewidth=1.8)
    eixo.plot(
        periodo_horas,
        significancia,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="Significancia 95%",
    )

    for posicao, pico in enumerate(picos, start=1):
        periodo_pico_horas = pico["periodo"] * 24
        eixo.scatter(
            periodo_pico_horas,
            pico["potencia"],
            color="#d73027",
            s=45,
            zorder=3,
        )
        eixo.annotate(
            f"P{posicao}: {pico['rotulo']}",
            xy=(periodo_pico_horas, pico["potencia"]),
            xytext=(6, 8),
            textcoords="offset points",
            fontsize=9,
        )

    eixo.axvline(24, color="#555555", linestyle=":", linewidth=1, label="24 h")
    eixo.set_xscale("log", base=2)
    eixo.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda valor, _: formatar_periodo(valor / 24))
    )
    eixo.set_title(f"Espectro global horizontal - {config['rotulo']}")
    eixo.set_xlabel("Periodo")
    eixo.set_ylabel(f"Potencia ({serie_preparada['unidade_potencia']})")
    eixo.grid(True, alpha=0.25)
    eixo.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    return fig


def plotar_quadro_wavelet(coluna, serie_preparada, resultado):
    config = VARIAVEIS_ANALISAR[coluna]
    datas = serie_preparada["datas"]
    unidade = config["unidade"]
    unidade_potencia = serie_preparada["unidade_potencia"]

    fig = plt.figure(figsize=(15, 10), constrained_layout=True)
    grade = fig.add_gridspec(
        nrows=3,
        ncols=2,
        width_ratios=[4, 1.35],
        height_ratios=[1, 2.2, 1],
    )

    eixo_serie = fig.add_subplot(grade[0, 0])
    eixo_potencia = fig.add_subplot(grade[1, 0], sharex=eixo_serie)
    eixo_media = fig.add_subplot(grade[2, 0], sharex=eixo_serie)
    eixo_global = fig.add_subplot(grade[1, 1], sharey=eixo_potencia)
    eixo_info = fig.add_subplot(grade[0, 1])
    eixo_legenda = fig.add_subplot(grade[2, 1])

    eixo_serie.plot(
        datas,
        serie_preparada["serie_wavelet"],
        color=config["cor"],
        linewidth=1.2,
    )
    eixo_serie.set_title(f"{config['rotulo']} - serie usada na Wavelet")
    eixo_serie.set_ylabel("z-score" if NORMALIZAR_SERIES else unidade)

    potencia = resultado["espectro_potencia"]
    potencia_positiva = potencia[potencia > 0]
    minimo = np.nanpercentile(potencia_positiva, 2) if potencia_positiva.size else 1e-6
    maximo = np.nanpercentile(potencia_positiva, 99) if potencia_positiva.size else 1.0
    minimo = max(minimo, 1e-8)
    maximo = max(maximo, minimo * 10)
    preenchimento = eixo_potencia.contourf(
        datas,
        resultado["periodo"],
        potencia,
        levels=np.geomspace(minimo, maximo, 20),
        cmap="turbo",
        norm=LogNorm(vmin=minimo, vmax=maximo),
        extend="both",
    )
    eixo_potencia.contour(
        datas,
        resultado["periodo"],
        resultado["significancia_95"],
        levels=[1],
        colors="white",
        linewidths=1.2,
    )
    eixo_potencia.fill_between(
        datas,
        resultado["cone_influencia"] * 0 + resultado["periodo"][-1],
        resultado["cone_influencia"],
        color="white",
        alpha=0.35,
        hatch="///",
        edgecolor="#333333",
        linewidth=0.0,
    )
    eixo_potencia.plot(datas, resultado["cone_influencia"], color="black", linewidth=1)
    eixo_potencia.set_title("Espectro de potencia Wavelet")
    eixo_potencia.set_ylabel("Periodo (dias)")
    configurar_eixo_periodo(eixo_potencia, resultado["periodo"])

    eixo_media.plot(datas, resultado["media_escala"], color="black", linewidth=1.2)
    eixo_media.axhline(
        resultado["significancia_media_escala"],
        color="black",
        linestyle="--",
        linewidth=1,
    )
    eixo_media.set_title(
        f"Media de escala ({PERIODO_MIN_MEDIA_ESCALA}-{PERIODO_MAX_MEDIA_ESCALA} dias)"
    )
    eixo_media.set_ylabel(unidade_potencia)
    eixo_media.set_xlabel("Data")

    eixo_global.plot(
        resultado["espectro_wavelet_global"],
        resultado["periodo"],
        color="black",
        linewidth=1.2,
    )
    eixo_global.plot(
        resultado["significancia_global"],
        resultado["periodo"],
        color="black",
        linestyle="--",
        linewidth=1,
    )
    eixo_global.set_title("Espectro global")
    eixo_global.set_xlabel(unidade_potencia)
    configurar_eixo_periodo(eixo_global, resultado["periodo"])
    eixo_global.tick_params(labelleft=False)

    eixo_info.axis("off")
    eixo_info.text(
        0,
        0.9,
        (
            f"Wavelet: {WAVELET_MAE}\n"
            f"Normalizacao: {'ativada' if NORMALIZAR_SERIES else 'desativada'}\n"
            f"Lag-1 estimado: {serie_preparada['lag1']:.3f}\n"
            f"s0: {ESCALA_INICIAL:.4f} dias ({ESCALA_INICIAL * 24:.1f} h)\n"
            f"Periodo max.: {PERIODO_MAX_ANALISE_DIAS} dias\n"
            f"Amostras: {len(datas)}"
        ),
        va="top",
        fontsize=11,
    )

    eixo_legenda.axis("off")
    barra_cores = fig.colorbar(preenchimento, ax=eixo_legenda, orientation="vertical")
    barra_cores.set_label(f"Potencia wavelet ({unidade_potencia})")

    fig.suptitle(f"Analise Wavelet - {config['rotulo']}", fontsize=16)
    return fig


def caminho_disponivel(caminho):
    if not caminho.exists():
        return caminho

    for numero in range(1, 1000):
        candidato = caminho.with_name(f"{caminho.stem}_{numero:02d}{caminho.suffix}")
        if not candidato.exists():
            return candidato

    raise RuntimeError(f"Nao foi possivel gerar um nome livre para {caminho}")


def salvar_figura(figura, caminho):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho_final = caminho_disponivel(caminho)
    figura.savefig(caminho_final, dpi=DPI_FIGURAS)
    return caminho_final


# ---------------------------------------------------------------------------
# 6. Execucao
# ---------------------------------------------------------------------------

def main():
    PASTA_SAIDA_FIGURAS.mkdir(parents=True, exist_ok=True)
    dados = carregar_dados_tratados(ARQUIVO_DADOS_TRATADOS)

    for coluna in VARIAVEIS_ANALISAR:
        if coluna not in dados.columns:
            print(f"[AVISO] Coluna nao encontrada: {coluna}. Pulando.")
            continue

        print(f"Gerando analise Wavelet para: {coluna}")
        serie_preparada = preparar_serie(dados, coluna)
        resultado = calcular_wavelet(serie_preparada)
        picos = detectar_picos_globais(resultado)

        sufixo_normalizacao = "normalizado" if NORMALIZAR_SERIES else "original"
        pasta_variavel = PASTA_SAIDA_FIGURAS / coluna
        figuras = {
            "serie_temporal": plotar_serie_temporal(coluna, serie_preparada),
            "escalograma": plotar_escalograma(coluna, serie_preparada, resultado),
            "espectro_global": plotar_espectro_global(
                coluna,
                serie_preparada,
                resultado,
                picos,
            ),
            "espectro_global_horizontal": plotar_espectro_global_horizontal(
                coluna,
                serie_preparada,
                resultado,
                picos,
            ),
            "painel_completo": plotar_quadro_wavelet(coluna, serie_preparada, resultado),
        }

        for nome_figura, figura in figuras.items():
            arquivo_figura = (
                pasta_variavel / f"{nome_figura}_{coluna}_{sufixo_normalizacao}.png"
            )
            arquivo_figura = salvar_figura(figura, arquivo_figura)
            plt.close(figura)
            print(f"Figura salva em: {arquivo_figura}")

        if picos:
            periodos = ", ".join(pico["rotulo"] for pico in picos)
            print(f"Periodos dominantes identificados: {periodos}")

        relatorio = gerar_texto_relatorio_individual(
            coluna,
            serie_preparada,
            resultado,
            picos,
        )
        arquivo_relatorio = pasta_variavel / f"relatorio_{coluna}_{sufixo_normalizacao}.txt"
        print(f"Relatorio salvo em: {salvar_texto(relatorio, arquivo_relatorio)}")


if __name__ == "__main__":
    main()
