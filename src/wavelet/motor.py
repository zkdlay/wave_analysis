"""Motor wavelet generico: recebe uma serie pronta e calcula a transformada.

Para que serve: validar a serie (datas regulares, sem falhas), descobrir o
passo de tempo sozinho, normalizar, estimar o lag-1 do ruido vermelho e
calcular potencia, fase, espectro global e testes de significancia.
Quem usa: notebooks/wavelet/rodar_wavelet.ipynb.

O motor nao sabe de onde a serie veio (SONDA, INPE, NASA...) e nao altera o
dado: mudar o passo e preencher falhas e trabalho do tratamento.
Internamente o tempo e contado em DIAS (passo, escalas e periodos).

Fluxo: carregar_serie_pronta -> preparar_serie -> calcular
"""

import numpy as np
import pandas as pd

from config.caminhos_e_parametros import (
    ESCALAS_INICIAIS_EM_PASSOS,
    NIVEL_SIGNIFICANCIA,
    PASTA_SERIES_PRONTAS,
    RESOLUCAO_ESCALA,
    USAR_PADDING,
)
from .significancia import aplicar_testes
from .wavelet_core import fator_fourier, wavelet

UM_DIA = pd.Timedelta(days=1)


# ---------------------------------------------------------------------------
# Serie de entrada
# ---------------------------------------------------------------------------

def carregar_serie_pronta(nome, pasta=PASTA_SERIES_PRONTAS):
    """Le <pasta>/<nome>.csv (colunas tempo, valor) e devolve uma pd.Series."""
    caminho = pasta / f"{nome}.csv"
    if not caminho.exists():
        disponiveis = sorted(p.stem for p in pasta.glob("*.csv"))
        raise FileNotFoundError(f"Serie '{nome}' nao encontrada em {pasta}. Disponiveis: {disponiveis}")
    tabela = pd.read_csv(caminho, parse_dates=["tempo"])
    serie = tabela.set_index("tempo")["valor"]
    serie.name = nome
    return serie


def separar_nome_serie(nome):
    """'sonda_tp_sfc_1h' -> ('sonda', 'tp_sfc', '1h'), pela convencao <fonte>_<variavel>_<passo>."""
    partes = nome.split("_")
    if len(partes) < 3:
        raise ValueError(f"Nome '{nome}' fora do padrao <fonte>_<variavel>_<passo>.")
    return partes[0], "_".join(partes[1:-1]), partes[-1]


def detectar_passo(serie):
    """Passo de tempo da serie (pd.Timedelta), deduzido das datas.

    Para com um aviso se as datas nao forem crescentes, se houver datas
    repetidas ou se o espacamento nao for sempre o mesmo.
    """
    if not isinstance(serie.index, pd.DatetimeIndex):
        raise TypeError("A serie precisa ter datas no indice (pd.DatetimeIndex).")
    if len(serie) < 3:
        raise ValueError("A serie precisa ter pelo menos 3 pontos.")
    diferencas = pd.Series(serie.index[1:] - serie.index[:-1])
    if (diferencas <= pd.Timedelta(0)).any():
        raise ValueError("As datas precisam ser crescentes e sem repeticao.")
    contagem = diferencas.value_counts()
    if len(contagem) > 1:
        raise ValueError(
            "As datas nao sao regulares (o passo muda ao longo da serie). Espacamentos encontrados:\n"
            f"{contagem.head(10).to_string()}\n"
            "Regularize a serie no tratamento antes de usar o motor."
        )
    return contagem.index[0]


def preparar_serie(serie, normalizar=True):
    """Valida a serie, remove a media e (opcionalmente) divide pelo desvio padrao."""
    passo = detectar_passo(serie)
    if serie.isna().any():
        faltando = serie.index[serie.isna()]
        raise ValueError(
            f"A serie '{serie.name}' tem {len(faltando)} valores faltando (primeiro em {faltando[0]}). "
            "O motor nao preenche falhas: trate-as no notebook de tratamento."
        )
    anomalia = serie - serie.mean()
    desvio = anomalia.std(ddof=1)
    if not desvio > 0:
        raise ValueError(f"A serie '{serie.name}' tem desvio padrao zero ou invalido.")

    # Autocorrelacao lag-1 para o ruido vermelho do teste de significancia.
    # Com dados a cada 10 min ela fica perto de 1 (ex.: 0,998): nao limitar em
    # 0,99, o que subestimaria o ruido de fundo nos periodos longos.
    lag1 = anomalia.autocorr(lag=1)
    lag1 = 0.0 if np.isnan(lag1) else float(min(lag1, 0.9999))

    return {
        "nome": serie.name,
        "datas": serie.index,
        "valores": (anomalia / desvio if normalizar else anomalia).to_numpy(dtype=float),
        "variancia": 1.0 if normalizar else float(desvio ** 2),
        "normalizada": normalizar,
        "media": float(serie.mean()),
        "desvio": float(desvio),
        "lag1": lag1,
        "passo": passo,
        "passo_dias": passo / UM_DIA,
    }


# ---------------------------------------------------------------------------
# Transformada
# ---------------------------------------------------------------------------

def fator_coi(wavelet_mae):
    """Razao entre o periodo do COI e a distancia a borda (mesma conta de wavelet_core.wave_bases)."""
    fator = fator_fourier(wavelet_mae)
    return fator * np.sqrt(2) if wavelet_mae.upper() == "PAUL" else fator / np.sqrt(2)


def faixa_de_escalas(n, dt, wavelet_mae, dj, escalas_iniciais_em_passos, periodo_min=None, periodo_max=None):
    """Menor escala (s0) e numero de escalas, em dias.

    Sem `periodo_min`: s0 = escalas_iniciais_em_passos * passo.
    Sem `periodo_max`: vai ate o maior periodo que ainda tem algum trecho fora
    do cone de influencia (COI), no meio da serie. Periodos maiores que esse
    estariam inteiros na regiao de efeito de borda.
    """
    fator = fator_fourier(wavelet_mae)
    if periodo_min is None:
        s0 = escalas_iniciais_em_passos * dt
    else:
        s0 = (pd.Timedelta(periodo_min) / UM_DIA) / fator
    if periodo_max is None:
        periodo_max_dias = fator_coi(wavelet_mae) * dt * ((n + 1) // 2 - 2)
        numero = int(np.ceil(np.log2(periodo_max_dias / fator / s0) / dj))
    else:
        periodo_max_dias = pd.Timedelta(periodo_max) / UM_DIA
        numero = int(np.floor(np.log2(periodo_max_dias / fator / s0) / dj))
    if numero < 1:
        raise ValueError("Faixa de periodos vazia: confira PERIODO_MIN e PERIODO_MAX.")
    return s0, numero


def calcular(serie_preparada, wavelet_mae="MORLET", testes=("local", "global"), dj=RESOLUCAO_ESCALA,
             escalas_iniciais_em_passos=ESCALAS_INICIAIS_EM_PASSOS, periodo_min=None, periodo_max=None,
             padding=USAR_PADDING, nivel=NIVEL_SIGNIFICANCIA, com_fase=True):
    """Potencia wavelet local, fase, espectro global e testes de significancia.

    `periodo_min` e `periodo_max` aceitam textos como "1h", "2D" ou "365D";
    com None (padrao) a faixa sai da propria serie (ver faixa_de_escalas).
    A fase theta(a, tau) = arg W(a, tau) so existe para wavelets complexas
    (Morlet e Paul); para a DOG, ou com `com_fase=False`, ela fica None.
    """
    wavelet_mae = wavelet_mae.upper()
    dt = serie_preparada["passo_dias"]
    valores = serie_preparada["valores"]
    s0, numero_escalas = faixa_de_escalas(
        len(valores), dt, wavelet_mae, dj, escalas_iniciais_em_passos, periodo_min, periodo_max,
    )

    calcular_fase = com_fase and wavelet_mae != "DOG"
    coeficientes, periodo, escala, coi = wavelet(
        valores, dt, int(padding), dj, s0, numero_escalas, wavelet_mae,
        somente_potencia=not calcular_fase, precisao_simples=True,
    )
    if calcular_fase:
        potencia = np.abs(coeficientes) ** 2
        fase = np.angle(coeficientes)
        del coeficientes
    else:
        potencia, fase = coeficientes, None

    resultado = {
        "wavelet_mae": wavelet_mae,
        "potencia": potencia,
        "fase": fase,
        "periodo": periodo,
        "escala": escala,
        "coi": coi,
        # Espectro global: media da potencia no tempo (Torrence & Compo, 1998, eq. 22)
        "espectro_global": potencia.mean(axis=1, dtype=np.float64),
        "nivel": nivel,
        "dj": dj,
    }
    resultado["testes"] = aplicar_testes(serie_preparada, resultado, testes, nivel)
    return resultado


def resumo(serie_preparada, resultado):
    """Uma linha de texto com o principal da execucao."""
    from .graficos import formatar_periodo, formatar_passo

    periodo = resultado["periodo"]
    return (
        f"{serie_preparada['nome']}: {len(serie_preparada['valores'])} pontos, passo de "
        f"{formatar_passo(serie_preparada['passo'])} | lag-1 = {serie_preparada['lag1']:.4f} | "
        f"{resultado['wavelet_mae'].title()}: {len(periodo)} escalas, de {formatar_periodo(periodo[0])} "
        f"a {formatar_periodo(periodo[-1])} | testes: {', '.join(resultado['testes']) or 'nenhum'}"
    )
