"""Graficos do motor wavelet.

Para que serve: desenhar e salvar as figuras de uma execucao do motor. Cada
grafico e uma funcao `plotar_<nome>`, escolhida pela lista GRAFICOS do
notebook do motor.
Quem usa: notebooks/wavelet/rodar_wavelet.ipynb.

Todas as funcoes de grafico recebem os mesmos argumentos:
    plotar_<nome>(serie_preparada, resultado, info, opcoes) -> figura
- serie_preparada: saida de motor.preparar_serie
- resultado: saida de motor.calcular
- info: textos dos titulos {"fonte", "local", "variavel", "unidade", "texto_extra", "fuso"}
- opcoes: ajustes de desenho {"inicio", "fim", "esmaecer"}

Para criar um grafico novo: escreva a funcao com essa assinatura, registre em
GRAFICOS_DISPONIVEIS e coloque o nome na lista GRAFICOS do notebook.
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

from config.caminhos_e_parametros import DPI_FIGURAS, PASTA_RESULTADOS_WAVELET

UM_DIA = pd.Timedelta(days=1)
DIAS_MES = 365.25 / 12
DIAS_ANO = 365.25

# Marcas candidatas do eixo de periodo (em dias); so entram as que caem na faixa calculada
MARCAS_PERIODO = [
    (10 / 1440, "10 min"), (20 / 1440, "20 min"), (30 / 1440, "30 min"),
    (1 / 24, "1 h"), (2 / 24, "2 h"), (3 / 24, "3 h"), (6 / 24, "6 h"), (12 / 24, "12 h"),
    (1, "1 d"), (2, "2 d"), (4, "4 d"), (7, "7 d"), (15, "15 d"),
    (DIAS_MES, "1 mês"), (2 * DIAS_MES, "2 meses"), (3 * DIAS_MES, "3 meses"), (6 * DIAS_MES, "6 meses"),
    (DIAS_ANO, "1 ano"), (2 * DIAS_ANO, "2 anos"), (4 * DIAS_ANO, "4 anos"), (8 * DIAS_ANO, "8 anos"),
    (16 * DIAS_ANO, "16 anos"), (32 * DIAS_ANO, "32 anos"),
]
MAXIMO_MARCAS = 14


# ---------------------------------------------------------------------------
# Textos
# ---------------------------------------------------------------------------

def _numero(x):
    return f"{x:.3g}".replace(".", ",")


def formatar_periodo(dias):
    """Periodo em dias -> texto na unidade mais legivel (min, h, d, meses, anos)."""
    if dias < 1 / 24:
        return f"{dias * 1440:.0f} min"
    if dias < 1:
        return f"{_numero(dias * 24)} h"
    if dias < 60:
        return f"{_numero(dias)} d"
    if dias < 2 * DIAS_ANO:
        meses = dias / DIAS_MES
        return f"{_numero(meses)} {'mês' if round(meses, 2) == 1 else 'meses'}"
    return f"{_numero(dias / DIAS_ANO)} anos"


def formatar_passo(passo):
    return formatar_periodo(pd.Timedelta(passo) / UM_DIA)


def titulo(nome_grafico, serie_preparada, resultado, info, datas, extra=""):
    """Duas linhas: o que e o grafico (variavel, fonte, local) e o recorte (datas, passo)."""
    wavelet = f" ({resultado['wavelet_mae'].title()})" if resultado is not None else ""
    variavel = info.get("variavel") or serie_preparada["nome"]
    if info.get("unidade"):
        variavel += f" ({info['unidade']})"
    origem = ", ".join(p for p in (info.get("fonte"), info.get("local")) if p)
    linha1 = " — ".join(p for p in (f"{nome_grafico}{wavelet}", variavel, origem) if p)
    linha2 = (f"{datas[0]:%d/%m/%Y} a {datas[-1]:%d/%m/%Y} | passo de "
              f"{formatar_passo(serie_preparada['passo'])}{extra}")
    if info.get("texto_extra"):
        linha2 += f" | {info['texto_extra']}"
    return f"{linha1}\n{linha2}"


def unidade_potencia(serie_preparada, info):
    return "variancia normalizada" if serie_preparada["normalizada"] else f"({info.get('unidade', '')})²"


# ---------------------------------------------------------------------------
# Pecas comuns
# ---------------------------------------------------------------------------

def media_em_blocos(matriz, tamanho):
    """Media de blocos de `tamanho` colunas (para desenhar contornos de series longas)."""
    if tamanho <= 1:
        return matriz
    colunas = (matriz.shape[-1] // tamanho) * tamanho
    return matriz[..., :colunas].reshape(*matriz.shape[:-1], -1, tamanho).mean(axis=-1)


def recortar(serie_preparada, opcoes):
    """Indices do trecho entre opcoes['inicio'] e opcoes['fim'] (so para o desenho)."""
    datas = serie_preparada["datas"]
    inicio, fim = opcoes.get("inicio"), opcoes.get("fim")
    return slice(
        0 if inicio is None else datas.searchsorted(pd.Timestamp(inicio)),
        len(datas) if fim is None else datas.searchsorted(pd.Timestamp(fim), side="right"),
    )


def formatar_eixo_datas(eixo, info):
    eixo.xaxis_date()
    localizador = mdates.AutoDateLocator()
    eixo.xaxis.set_major_locator(localizador)
    eixo.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))
    eixo.set_xlabel(f"Data ({info.get('fuso', 'UTC')})")


def formatar_eixo_periodo(eixo, resultado):
    """Eixo de periodo em log2, com os periodos curtos em cima e marcas escolhidas pela faixa."""
    periodo, dj = resultado["periodo"], resultado["dj"]
    log_periodo = np.log2(periodo)
    marcas = [(p, r) for p, r in MARCAS_PERIODO if periodo[0] <= p <= periodo[-1]]
    while len(marcas) > MAXIMO_MARCAS:
        marcas = marcas[::2]
    eixo.set_yticks(np.log2([p for p, _ in marcas]), [r for _, r in marcas])
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


# ---------------------------------------------------------------------------
# Graficos
# ---------------------------------------------------------------------------

def plotar_sinal(serie_preparada, resultado, info, opcoes):
    """Sinal original (na unidade da variavel) que entrou na transformada."""
    trecho = recortar(serie_preparada, opcoes)
    datas = serie_preparada["datas"][trecho]
    fator = serie_preparada["desvio"] if serie_preparada["normalizada"] else 1.0
    valores = serie_preparada["valores"][trecho] * fator + serie_preparada["media"]
    unidade = info.get("unidade", "")

    fig, eixo = plt.subplots(figsize=(15, 4.5))
    eixo.plot(datas, valores, color="#1f4e79", linewidth=0.4)
    eixo.axhline(serie_preparada["media"], color="#c0392b", linewidth=0.9, linestyle="--",
                 label=f"Media: {serie_preparada['media']:.2f} {unidade}")
    eixo.set_ylabel(f"{info.get('variavel', '')} ({unidade})")
    formatar_eixo_datas(eixo, info)
    eixo.set_xlim(datas[0], datas[-1])
    eixo.grid(True, alpha=0.3)
    eixo.legend(loc="upper right", fontsize=9)
    eixo.set_title(titulo("Sinal original", serie_preparada, None, info, datas), fontsize=11)
    fig.tight_layout()
    return fig


def plotar_escalograma(serie_preparada, resultado, info, opcoes):
    """Escalograma com o teste "local" (contorno) e o cone de influencia (COI).

    opcoes['inicio'] e opcoes['fim'] recortam so o desenho (a transformada usa
    a serie inteira). Com opcoes['esmaecer'] = True, as regioes nao
    significativas ficam cobertas por uma camada branca translucida.
    """
    trecho = recortar(serie_preparada, opcoes)
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

    legenda = []
    nivel = f"{resultado['nivel']:.0%}"
    if "local" in resultado["testes"]:
        significativo = potencia >= resultado["testes"]["local"][:, None].astype(np.float32)
        if opcoes.get("esmaecer"):
            desenhar_mapa(eixo, np.where(significativo, np.nan, 1.0).astype(np.float32), x, resultado,
                          cmap=ListedColormap(["white"]), alpha=0.55, interpolation="nearest")
            legenda.append(Patch(facecolor="#e8e8e8", edgecolor="#999999",
                                 label=f"Esmaecido: nao significativo ({nivel})"))
        eixo.contour(x, np.log2(resultado["periodo"]), significativo.astype(np.float32),
                     levels=[0.5], colors="black", linewidths=0.6)
        legenda.append(Line2D([0], [0], color="black", linewidth=0.6, label=f"Contorno: significativo ({nivel})"))
    desenhar_coi(eixo, x, resultado["coi"][trecho], resultado, int(np.ceil(len(x) / 20000)))

    formatar_eixo_periodo(eixo, resultado)
    formatar_eixo_datas(eixo, info)
    eixo.grid(False)
    eixo.set_title(titulo("Escalograma", serie_preparada, resultado, info, datas,
                          f" | lag-1 = {serie_preparada['lag1']:.4f}"), fontsize=11)
    eixo.legend(handles=legenda + LEGENDA_COI, loc="lower left", framealpha=0.85, fontsize=9)
    fig.colorbar(imagem, ax=eixo, pad=0.01, extend="both").set_label(
        f"Potencia wavelet ({unidade_potencia(serie_preparada, info)})")
    fig.tight_layout()
    return fig


def plotar_espectro_global(serie_preparada, resultado, info, opcoes):
    """Espectro global (media da potencia no tempo) com o teste "global"."""
    log_periodo = np.log2(resultado["periodo"])

    fig, eixo = plt.subplots(figsize=(7, 6.5))
    eixo.plot(resultado["espectro_global"], log_periodo, color="black", linewidth=1.4, label="Espectro global")
    if "global" in resultado["testes"]:
        eixo.plot(resultado["testes"]["global"], log_periodo, color="#c0392b", linewidth=1.1, linestyle="--",
                  label=f"Significancia {resultado['nivel']:.0%} (ruido vermelho, "
                        f"lag-1 = {serie_preparada['lag1']:.4f})")
    eixo.set_xscale("log")
    formatar_eixo_periodo(eixo, resultado)
    eixo.set_xlabel(f"Potencia media ({unidade_potencia(serie_preparada, info)})")
    eixo.grid(True, which="both", alpha=0.3)
    eixo.legend(loc="lower left", fontsize=8.5, framealpha=0.85)
    eixo.set_title(titulo("Espectro global", serie_preparada, resultado, info, serie_preparada["datas"]),
                   fontsize=9)
    fig.tight_layout()
    return fig


def plotar_fase(serie_preparada, resultado, info, opcoes):
    """Fase theta(a, tau) = arg W(a, tau), em graus, com o COI.

    A fase e ciclica (-180 = 180), por isso usa um mapa de cores ciclico e
    nao e suavizada no desenho. Numa serie longa, cada coluna de pixels cobre
    varios passos de tempo: nos periodos mais curtos que ~2 colunas a fase
    aparece como ruido, e so um recorte (inicio/fim) a mostra de fato.
    """
    if resultado["fase"] is None:
        raise ValueError(f"A wavelet {resultado['wavelet_mae']} e real: nao tem fase.")
    trecho = recortar(serie_preparada, opcoes)
    datas = serie_preparada["datas"][trecho]
    x = mdates.date2num(datas)

    fig, eixo = plt.subplots(figsize=(15, 6.5))
    imagem = desenhar_mapa(eixo, np.degrees(resultado["fase"][:, trecho]), x, resultado,
                           cmap="twilight", vmin=-180, vmax=180, interpolation="nearest")
    desenhar_coi(eixo, x, resultado["coi"][trecho], resultado, int(np.ceil(len(x) / 20000)))
    formatar_eixo_periodo(eixo, resultado)
    formatar_eixo_datas(eixo, info)
    eixo.grid(False)
    eixo.legend(handles=LEGENDA_COI, loc="lower left", framealpha=0.85, fontsize=9)
    eixo.set_title(titulo("Fase", serie_preparada, resultado, info, datas), fontsize=11)
    barra = fig.colorbar(imagem, ax=eixo, pad=0.01, ticks=[-180, -90, 0, 90, 180])
    barra.set_label("Fase θ(a, τ) (graus)")
    fig.tight_layout()
    return fig


GRAFICOS_DISPONIVEIS = {
    "sinal": plotar_sinal,
    "escalograma": plotar_escalograma,
    "espectro_global": plotar_espectro_global,
    "fase": plotar_fase,
}


# ---------------------------------------------------------------------------
# Gerar e salvar
# ---------------------------------------------------------------------------

def pasta_da_execucao(nome_serie, wavelet_mae, pasta_base=PASTA_RESULTADOS_WAVELET):
    """resultados/wavelet/<fonte>/<variavel>/<wavelet>_<passo>/ a partir do nome da serie."""
    from .motor import separar_nome_serie

    fonte, variavel, passo = separar_nome_serie(nome_serie)
    return pasta_base / fonte / variavel / f"{wavelet_mae.lower()}_{passo}"


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


def gerar_graficos(serie_preparada, resultado, info, graficos, opcoes=None, salvar=True, mostrar=True):
    """Desenha os graficos pedidos; salva na pasta da execucao e/ou mostra na tela.

    Devolve a lista de arquivos salvos.
    """
    desconhecidos = [g for g in graficos if g not in GRAFICOS_DISPONIVEIS]
    if desconhecidos:
        raise ValueError(f"Graficos desconhecidos: {desconhecidos}. Disponiveis: {list(GRAFICOS_DISPONIVEIS)}")
    opcoes = opcoes or {}
    pasta = pasta_da_execucao(serie_preparada["nome"], resultado["wavelet_mae"])
    salvos = []
    for nome in graficos:
        figura = GRAFICOS_DISPONIVEIS[nome](serie_preparada, resultado, info, opcoes)
        if salvar:
            arquivo = f"{nome}_{serie_preparada['nome']}_{resultado['wavelet_mae'].lower()}.png"
            salvos.append(salvar_figura(figura, pasta / arquivo))
        if mostrar:
            plt.show()
        else:
            plt.close(figura)
    return salvos
