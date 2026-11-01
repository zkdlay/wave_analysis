"""Analise wavelet individual de uma variavel da SONDA-MD: o escalograma.

Fluxo: carregar_variavel_md -> preparar_serie -> calcular_escalograma ->
plotar_escalograma. Todos os parametros chegam como argumentos (os padroes
vem de config/caminhos_e_parametros.py); nenhuma funcao altera variaveis
globais.
"""

import io
import time

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, LogNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from config.caminhos_e_parametros import (
    DPI_FIGURAS,
    ESCALAS_INICIAIS_EM_PASSOS,
    INTERPOLAR_ATE_MINUTOS,
    NIVEL_SIGNIFICANCIA,
    PASSO_MD_DIAS,
    PASTA_SONDA_MD,
    PERIODO_MAX_DIAS,
    RESOLUCAO_ESCALA,
    USAR_PADDING,
)
from .wavelet_core import fator_fourier, wave_signif, wavelet


MARCAS_PERIODO_DIAS = [1 / 24, 3 / 24, 6 / 24, 12 / 24, 1, 2, 4, 8, 16, 32, 64, 128, 256]


# ---------------------------------------------------------------------------
# Leitura e preparo da serie
# ---------------------------------------------------------------------------

def carregar_variavel_md(variavel, pasta=PASTA_SONDA_MD, inicio=None, fim=None):
    """Le a variavel dos CSV anuais e devolve uma serie na grade regular de 10 min."""
    arquivos = sorted(pasta.glob("sonda_MD_*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum sonda_MD_*.csv encontrado em {pasta}")
    partes = [pd.read_csv(a, usecols=["TIMESTAMP", variavel], parse_dates=["TIMESTAMP"]) for a in arquivos]
    dados = pd.concat(partes).drop_duplicates("TIMESTAMP").set_index("TIMESTAMP").sort_index()[variavel]
    dados = dados.loc[inicio:fim]
    grade = pd.date_range(dados.index.min(), dados.index.max(), freq=pd.Timedelta(days=PASSO_MD_DIAS))
    return dados.reindex(grade)


def media_por_passo(serie, passo_dias):
    """Media da serie em blocos de `passo_dias` (ex.: 1/24 para media horaria).

    Segue a convencao da SONDA: o horario marca o FIM do intervalo (o valor
    de 01:00 e a media dos registros de 00:10 a 01:00). Blocos sem nenhum
    registro ficam NaN. Devolve tambem quantos blocos internos (sem contar o
    primeiro e o ultimo, cortados pelas pontas da serie) tiveram a media feita
    com registros faltando.
    """
    blocos = serie.resample(pd.Timedelta(days=passo_dias), closed="right", label="right")
    contagem = blocos.count()
    esperado = round(passo_dias / PASSO_MD_DIAS)
    info = {
        "registros_por_bloco": esperado,
        "blocos_incompletos": int((contagem.iloc[1:-1] < esperado).sum()),
    }
    return blocos.mean(), info


def falhas(serie):
    """Tabela com inicio, fim e numero de registros de cada trecho sem dado."""
    faltante = serie.isna()
    if not faltante.any():
        return pd.DataFrame(columns=["inicio", "fim", "registros"])
    grupo = (faltante != faltante.shift()).cumsum()[faltante]
    horarios = pd.Series(serie.index[faltante], index=serie.index[faltante])
    tabela = horarios.groupby(grupo.values).agg(["min", "max", "size"]).reset_index(drop=True)
    tabela.columns = ["inicio", "fim", "registros"]
    return tabela


def preencher_falhas(serie, passo_dias=PASSO_MD_DIAS, interpolar_ate_minutos=INTERPOLAR_ATE_MINUTOS):
    """Interpola linearmente so as falhas curtas.

    A wavelet exige serie sem buracos. Falhas de ate `interpolar_ate_minutos`
    sao preenchidas; se houver alguma maior, a funcao para e lista as falhas,
    para que a decisao de como trata-las seja tomada de forma explicita.
    """
    tabela = falhas(serie)
    passo_min = passo_dias * 1440
    tabela["duracao_min"] = tabela["registros"] * passo_min
    longas = tabela[tabela["duracao_min"] > interpolar_ate_minutos]
    if len(longas):
        raise ValueError(
            f"{len(longas)} falhas maiores que {interpolar_ate_minutos} min em '{serie.name}':\n"
            f"{longas.to_string(index=False)}"
        )
    if serie.iloc[[0, -1]].isna().any():
        raise ValueError(f"A serie '{serie.name}' comeca ou termina sem dado; ajuste inicio/fim.")

    preenchida = serie.interpolate(method="time", limit_area="inside")
    info = {
        "falhas_interpoladas": len(tabela),
        "registros_interpolados": int(tabela["registros"].sum()),
        "maior_falha_min": float(tabela["duracao_min"].max()) if len(tabela) else 0.0,
    }
    return preenchida, info


def preparar_serie(serie, normalizar=True, passo_dias=PASSO_MD_DIAS,
                   interpolar_ate_minutos=INTERPOLAR_ATE_MINUTOS, agregacao=None):
    """Preenche falhas curtas, remove a media e (opcionalmente) divide pelo desvio padrao.

    `agregacao` e o info devolvido por `media_por_passo`, quando a serie foi
    reamostrada; ele so e repassado para o titulo da figura.
    """
    completa, preenchimento = preencher_falhas(serie, passo_dias, interpolar_ate_minutos)
    anomalia = completa - completa.mean()
    desvio = anomalia.std(ddof=1)
    if not desvio > 0:
        raise ValueError(f"A serie '{serie.name}' tem desvio padrao zero ou invalido.")

    # Autocorrelacao lag-1 para o ruido vermelho do teste de significancia.
    # Com dados a cada 10 min ela fica perto de 1 (ex.: 0,998): nao limitar em
    # 0,99 como antes, o que subestimava o ruido de fundo nos periodos longos.
    lag1 = anomalia.autocorr(lag=1)
    lag1 = 0.0 if np.isnan(lag1) else float(min(lag1, 0.9999))

    return {
        "nome": serie.name,
        "datas": completa.index,
        "valores": (anomalia / desvio if normalizar else anomalia).to_numpy(dtype=float),
        "variancia": 1.0 if normalizar else float(desvio ** 2),
        "normalizada": normalizar,
        "media": float(completa.mean()),
        "desvio": float(desvio),
        "lag1": lag1,
        "passo_dias": passo_dias,
        "preenchimento": preenchimento,
        "agregacao": agregacao,
    }


# ---------------------------------------------------------------------------
# Transformada
# ---------------------------------------------------------------------------

def calcular_escalograma(serie_preparada, wavelet_mae="MORLET", dj=RESOLUCAO_ESCALA,
                         escalas_iniciais_em_passos=ESCALAS_INICIAIS_EM_PASSOS,
                         periodo_max_dias=PERIODO_MAX_DIAS, padding=USAR_PADDING,
                         nivel=NIVEL_SIGNIFICANCIA, com_fase=True):
    """Potencia wavelet local, fase, espectro global e limiares de significancia.

    A fase theta(a, tau) = arg W(a, tau) so existe para wavelets complexas
    (Morlet e Paul); para a DOG, ou com `com_fase=False`, ela fica None.
    """
    wavelet_mae = wavelet_mae.upper()
    dt = serie_preparada["passo_dias"]
    valores = serie_preparada["valores"]
    s0 = escalas_iniciais_em_passos * dt
    escala_max = periodo_max_dias / fator_fourier(wavelet_mae)
    numero_escalas = int(np.floor(np.log2(escala_max / s0) / dj))

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

    parametros_signif = dict(dt=dt, scale=escala, lag1=serie_preparada["lag1"], siglvl=nivel, mother=wavelet_mae)
    significancia = wave_signif([serie_preparada["variancia"]], sigtest=0, **parametros_signif)

    # Espectro global: media da potencia no tempo (Torrence & Compo, 1998, eq. 22).
    # Os graus de liberdade descontam os pontos afetados pela borda em cada
    # escala: N - escala/dt pontos efetivos (eq. 23).
    espectro_global = potencia.mean(axis=1, dtype=np.float64)
    significancia_global = wave_signif(
        [serie_preparada["variancia"]], sigtest=1, dof=len(valores) - escala / dt, **parametros_signif,
    )
    return {
        "wavelet_mae": wavelet_mae,
        "potencia": potencia,
        "fase": fase,
        "periodo": periodo,
        "escala": escala,
        "coi": coi,
        "significancia": np.asarray(significancia, dtype=float),
        "espectro_global": espectro_global,
        "significancia_global": np.asarray(significancia_global, dtype=float),
        "nivel": nivel,
        "dj": dj,
    }


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------

def formatar_periodo(dias):
    return f"{dias * 24:.0f} h" if dias < 1 else f"{dias:g} d"


def formatar_passo(dias):
    minutos = dias * 1440
    return f"{minutos:.0f} min" if minutos < 60 else f"{minutos / 60:g} h"


def descrever_falhas(serie_preparada):
    """Texto do titulo sobre as falhas interpoladas e as medias incompletas."""
    preenchimento = serie_preparada["preenchimento"]
    if preenchimento["registros_interpolados"]:
        partes = [f"{preenchimento['registros_interpolados']} registros interpolados "
                  f"(maior falha: {preenchimento['maior_falha_min']:.0f} min)"]
    else:
        partes = ["sem falhas interpoladas"]
    agregacao = serie_preparada.get("agregacao")
    if agregacao and agregacao["blocos_incompletos"]:
        partes.append(f"{agregacao['blocos_incompletos']} medias de {formatar_passo(serie_preparada['passo_dias'])} "
                      f"com menos de {agregacao['registros_por_bloco']} registros")
    return " | ".join(partes)


def subtitulo(serie_preparada, datas):
    return (f"{datas[0]:%d/%m/%Y} a {datas[-1]:%d/%m/%Y} | "
            f"passo de {formatar_passo(serie_preparada['passo_dias'])} | {descrever_falhas(serie_preparada)}")


def media_em_blocos(matriz, tamanho):
    """Media de blocos de `tamanho` colunas (para desenhar contornos de series longas)."""
    if tamanho <= 1:
        return matriz
    colunas = (matriz.shape[-1] // tamanho) * tamanho
    return matriz[..., :colunas].reshape(*matriz.shape[:-1], -1, tamanho).mean(axis=-1)


def recortar(serie_preparada, inicio=None, fim=None):
    """Indices do trecho entre `inicio` e `fim` (so para o desenho)."""
    datas = serie_preparada["datas"]
    return slice(
        0 if inicio is None else datas.searchsorted(pd.Timestamp(inicio)),
        len(datas) if fim is None else datas.searchsorted(pd.Timestamp(fim), side="right"),
    )


def formatar_eixo_datas(eixo):
    eixo.xaxis_date()
    localizador = mdates.AutoDateLocator()
    eixo.xaxis.set_major_locator(localizador)
    eixo.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))
    eixo.set_xlabel("Data (UTC)")


def formatar_eixo_periodo(eixo, resultado):
    """Eixo de periodo em log2, com os periodos curtos em cima."""
    periodo, dj = resultado["periodo"], resultado["dj"]
    log_periodo = np.log2(periodo)
    marcas = [p for p in MARCAS_PERIODO_DIAS if periodo[0] <= p <= periodo[-1]]
    eixo.set_yticks(np.log2(marcas), [formatar_periodo(p) for p in marcas])
    eixo.set_ylim(log_periodo[-1] + dj / 2, log_periodo[0] - dj / 2)
    eixo.set_ylabel("Periodo")


def desenhar_mapa(eixo, matriz, x, resultado, **kwargs_imshow):
    """Desenha uma matriz (escala x tempo) no eixo de periodo em log2."""
    log_periodo, dj = np.log2(resultado["periodo"]), resultado["dj"]
    extensao = [x[0], x[-1], log_periodo[0] - dj / 2, log_periodo[-1] + dj / 2]
    return eixo.imshow(matriz, aspect="auto", origin="lower", extent=extensao, **kwargs_imshow)


def desenhar_coi(eixo, x, coi, resultado, bloco):
    """Linha do COI e hachura na regiao fora dele (media de blocos em trechos longos)."""
    periodo, dj = resultado["periodo"], resultado["dj"]
    x_bloco = media_em_blocos(x, bloco)
    coi = np.log2(np.clip(media_em_blocos(coi, bloco), periodo[0], None))
    base = np.log2(periodo[-1]) + dj / 2
    eixo.plot(x_bloco, coi, color="black", linewidth=1.3)
    eixo.fill_between(x_bloco, coi, base, color="white", alpha=0.4, hatch="///", edgecolor="#333333", linewidth=0)


LEGENDA_COI = [
    Line2D([0], [0], color="black", linewidth=1.3, label="COI"),
    Patch(facecolor="white", edgecolor="#333333", hatch="///", label="Fora do COI (efeito de borda)"),
]


def plotar_sinal(serie_preparada, rotulo, unidade, inicio=None, fim=None):
    """Sinal original (na unidade da variavel) que entrou na transformada."""
    trecho = recortar(serie_preparada, inicio, fim)
    datas = serie_preparada["datas"][trecho]
    fator = serie_preparada["desvio"] if serie_preparada["normalizada"] else 1.0
    valores = serie_preparada["valores"][trecho] * fator + serie_preparada["media"]

    fig, eixo = plt.subplots(figsize=(15, 4.5))
    eixo.plot(datas, valores, color="#1f4e79", linewidth=0.4)
    eixo.axhline(serie_preparada["media"], color="#c0392b", linewidth=0.9, linestyle="--",
                 label=f"Media: {serie_preparada['media']:.2f} {unidade}")
    eixo.set_ylabel(f"{rotulo} ({unidade})")
    formatar_eixo_datas(eixo)
    eixo.set_xlim(datas[0], datas[-1])
    eixo.grid(True, alpha=0.3)
    eixo.legend(loc="upper right", fontsize=9)
    eixo.set_title(f"Sinal original - {rotulo}\n{subtitulo(serie_preparada, datas)}", fontsize=11)
    fig.tight_layout()
    return fig


def plotar_escalograma(serie_preparada, resultado, rotulo, unidade, inicio=None, fim=None, esmaecer=False):
    """Escalograma com significancia e cone de influencia (COI).

    `inicio` e `fim` recortam so o desenho (a transformada usa a serie inteira).
    A borda das regioes significativas e contornada em preto. Com
    `esmaecer=True`, as regioes nao significativas tambem ficam cobertas por
    uma camada branca translucida. O COI de trechos longos e desenhado com a
    media de blocos de pontos.
    """
    trecho = recortar(serie_preparada, inicio, fim)
    datas = serie_preparada["datas"][trecho]
    potencia = resultado["potencia"][:, trecho]
    x = mdates.date2num(datas)

    amostra = potencia[:, :: max(1, potencia.shape[1] // 5000)]
    amostra = amostra[amostra > 0]
    vmin = max(float(np.percentile(amostra, 2)), 1e-6)
    vmax = max(float(np.percentile(amostra, 99.5)), vmin * 10)

    fig, eixo = plt.subplots(figsize=(15, 6.5))
    imagem = desenhar_mapa(eixo, np.clip(potencia, vmin, vmax), x, resultado, cmap="turbo",
                           norm=LogNorm(vmin, vmax), interpolation="antialiased")

    significativo = potencia >= resultado["significancia"][:, None].astype(np.float32)
    if esmaecer:
        desenhar_mapa(eixo, np.where(significativo, np.nan, 1.0).astype(np.float32), x, resultado,
                      cmap=ListedColormap(["white"]), alpha=0.55, interpolation="nearest")
    eixo.contour(x, np.log2(resultado["periodo"]), significativo.astype(np.float32),
                 levels=[0.5], colors="black", linewidths=0.6)
    desenhar_coi(eixo, x, resultado["coi"][trecho], resultado, int(np.ceil(len(x) / 20000)))

    formatar_eixo_periodo(eixo, resultado)
    formatar_eixo_datas(eixo)
    eixo.grid(False)
    eixo.set_title(
        f"Escalograma {resultado['wavelet_mae'].title()} - {rotulo}\n"
        f"{subtitulo(serie_preparada, datas)} | lag-1 = {serie_preparada['lag1']:.4f}",
        fontsize=11,
    )
    nivel = f"{resultado['nivel']:.0%}"
    legenda = []
    if esmaecer:
        legenda.append(Patch(facecolor="#e8e8e8", edgecolor="#999999", label=f"Esmaecido: nao significativo ({nivel})"))
    legenda.append(Line2D([0], [0], color="black", linewidth=0.6, label=f"Contorno: significativo ({nivel})"))
    eixo.legend(handles=legenda + LEGENDA_COI, loc="lower left", framealpha=0.85, fontsize=9)
    unidade_potencia = "variancia normalizada" if serie_preparada["normalizada"] else f"({unidade})²"
    fig.colorbar(imagem, ax=eixo, pad=0.01, extend="both").set_label(f"Potencia wavelet ({unidade_potencia})")
    fig.tight_layout()
    return fig


def plotar_espectro_global(serie_preparada, resultado, rotulo, unidade):
    """Espectro global (media da potencia no tempo) com o limiar de significancia."""
    log_periodo = np.log2(resultado["periodo"])
    nivel = f"{resultado['nivel']:.0%}"

    fig, eixo = plt.subplots(figsize=(7, 6.5))
    eixo.plot(resultado["espectro_global"], log_periodo, color="black", linewidth=1.4,
              label="Espectro global")
    eixo.plot(resultado["significancia_global"], log_periodo, color="#c0392b", linewidth=1.1, linestyle="--",
              label=f"Significancia {nivel} (ruido vermelho, lag-1 = {serie_preparada['lag1']:.4f})")
    eixo.set_xscale("log")
    formatar_eixo_periodo(eixo, resultado)
    unidade_potencia = "variancia normalizada" if serie_preparada["normalizada"] else f"({unidade})²"
    eixo.set_xlabel(f"Potencia media ({unidade_potencia})")
    eixo.grid(True, which="both", alpha=0.3)
    eixo.legend(loc="lower left", fontsize=8.5, framealpha=0.85)
    datas = serie_preparada["datas"]
    eixo.set_title(
        f"Espectro global {resultado['wavelet_mae'].title()} - {rotulo}\n"
        f"{datas[0]:%d/%m/%Y} a {datas[-1]:%d/%m/%Y} | passo de {formatar_passo(serie_preparada['passo_dias'])}",
        fontsize=11,
    )
    fig.tight_layout()
    return fig


def plotar_fase(serie_preparada, resultado, rotulo, inicio=None, fim=None):
    """Fase theta(a, tau) = arg W(a, tau), em graus, com o COI.

    A fase e ciclica (-180 = 180), por isso usa um mapa de cores ciclico e
    nao e suavizada no desenho. Numa serie longa, cada coluna de pixels cobre
    varios passos de tempo: nos periodos mais curtos que ~2 colunas a fase
    aparece como ruido, e so um recorte (`inicio`/`fim`) a mostra de fato.
    """
    if resultado["fase"] is None:
        raise ValueError(f"A wavelet {resultado['wavelet_mae']} e real: nao tem fase.")
    trecho = recortar(serie_preparada, inicio, fim)
    datas = serie_preparada["datas"][trecho]
    x = mdates.date2num(datas)

    fig, eixo = plt.subplots(figsize=(15, 6.5))
    imagem = desenhar_mapa(eixo, np.degrees(resultado["fase"][:, trecho]), x, resultado,
                           cmap="twilight", vmin=-180, vmax=180, interpolation="nearest")
    bloco = int(np.ceil(len(x) / 20000))
    desenhar_coi(eixo, x, resultado["coi"][trecho], resultado, bloco)
    formatar_eixo_periodo(eixo, resultado)
    formatar_eixo_datas(eixo)
    eixo.grid(False)
    eixo.legend(handles=LEGENDA_COI, loc="lower left", framealpha=0.85, fontsize=9)
    eixo.set_title(f"Fase {resultado['wavelet_mae'].title()} - {rotulo}\n{subtitulo(serie_preparada, datas)}",
                   fontsize=11)
    barra = fig.colorbar(imagem, ax=eixo, pad=0.01, ticks=[-180, -90, 0, 90, 180])
    barra.set_label("Fase θ(a, τ) (graus)")
    fig.tight_layout()
    return fig


def salvar_figura(figura, caminho, dpi=DPI_FIGURAS):
    """Salva sobrescrevendo o arquivo anterior (sem criar copias _01, _02...).

    A pasta fica no OneDrive, que trava o arquivo por alguns segundos enquanto
    sincroniza; por isso a figura e gerada na memoria e a gravacao e repetida.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conteudo = io.BytesIO()
    figura.savefig(conteudo, dpi=dpi, format=caminho.suffix.lstrip("."))
    for tentativa in range(30):
        try:
            caminho.write_bytes(conteudo.getvalue())
            return caminho
        except OSError:
            if tentativa == 29:
                raise
            time.sleep(1)
