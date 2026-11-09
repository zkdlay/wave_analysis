"""Leitura dos dados horarios do NASA POWER (arquivo CSV baixado do site).

Para que serve: ler o cabecalho (local, elevacao, codigo de falta, variaveis e
unidades) e os dados, trocando o codigo de falta (-999) por NaN. Tambem calcula
a irradiancia no topo da atmosfera, usada para conferir a radiacao de onda curta
e a convencao de horario.
Quem usa: notebooks/nasa_power/.

O NASA POWER nao e uma estacao: os valores vem de modelos e satelite
(MERRA-2 para temperatura, umidade, pressao e vento; CERES SYN1deg para a
radiacao), numa celula de grade de ~0,5 x 0,625 grau ao redor do ponto pedido.

Horario em UTC. A coluna HR marca o INICIO da hora: o valor de HR = 14 e a media
de 14:00 a 14:59 UTC. Conferido na radiacao (irradiancia no topo da atmosfera,
notebook de diagnostico) e na pressao do MERRA-2 (mare semidiurna comparada com a
SONDA, 11/2026). Na SONDA e o contrario: o TIMESTAMP marca o FIM; use
para_fim_do_intervalo para seguir a convencao da SONDA.
"""

import re

import numpy as np
import pandas as pd


COLUNAS_DATA = ["YEAR", "MO", "DY", "HR"]
CONSTANTE_SOLAR = 1361.0  # W/m2

DESCRICOES = {
    "T2M": "Temperatura do ar a 2 m",
    "RH2M": "Umidade relativa a 2 m",
    "PS": "Pressao na superficie",
    "WS2M": "Velocidade do vento a 2 m",
    "WS10M": "Velocidade do vento a 10 m",
    "ALLSKY_SFC_SW_DWN": "Radiacao de onda curta incidente (ceu real)",
    "ALLSKY_SFC_LW_DWN": "Radiacao de onda longa incidente (ceu real)",
}


def ler_cabecalho(caminho):
    """Le o bloco entre -BEGIN HEADER- e -END HEADER-.

    Devolve um dicionario com latitude, longitude, elevacao do modelo, codigo
    de falta, a tabela das variaveis (fonte, descricao, unidade) e quantas
    linhas pular para chegar aos dados.
    """
    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        linhas = []
        for linha in arquivo:
            linhas.append(linha.rstrip("\n"))
            if linha.startswith("-END HEADER-"):
                break
    texto = "\n".join(linhas)

    local = re.search(r"Latitude\s+(-?[\d.]+)\s+Longitude\s+(-?[\d.]+)", texto)
    elevacao = re.search(r"=\s*(-?[\d.]+)\s*meters", texto)
    codigo = re.search(r"range:\s*(-?\d+)", texto)

    parametros = []
    dentro = False
    for linha in linhas:
        if linha.startswith("Parameter(s)"):
            dentro = True
            continue
        if linha.startswith("-END HEADER-"):
            break
        if dentro and linha.strip():
            nome, descricao = re.split(r"\s{2,}", linha.strip(), maxsplit=1)
            unidade = re.search(r"\(([^)]*)\)\s*$", descricao)
            parametros.append({
                "variavel": nome,
                "fonte": descricao.split()[0],
                "descricao_original": descricao,
                "descricao": DESCRICOES.get(nome, ""),
                "unidade": unidade.group(1) if unidade else "",
            })

    return {
        "latitude": float(local.group(1)),
        "longitude": float(local.group(2)),
        "elevacao_modelo_m": float(elevacao.group(1)) if elevacao else np.nan,
        "codigo_faltante": float(codigo.group(1)) if codigo else -999.0,
        "parametros": pd.DataFrame(parametros),
        "linhas_cabecalho": len(linhas),
    }


def carregar_nasa_power(caminho):
    """Le os dados horarios. Indice `tempo` em UTC, no INICIO da hora.

    O codigo de falta (-999) vira NaN. Devolve (dados, cabecalho).
    """
    cabecalho = ler_cabecalho(caminho)
    bruto = pd.read_csv(caminho, skiprows=cabecalho["linhas_cabecalho"])
    tempo = pd.to_datetime(dict(year=bruto["YEAR"], month=bruto["MO"], day=bruto["DY"], hour=bruto["HR"]))
    dados = bruto.drop(columns=COLUNAS_DATA)
    dados.index = pd.DatetimeIndex(tempo, name="tempo")
    dados = dados.where(dados != cabecalho["codigo_faltante"])
    return dados, cabecalho


def para_fim_do_intervalo(serie, passo="1h"):
    """Muda o rotulo de horario do INICIO para o FIM do intervalo (convencao da SONDA).

    Nao muda nenhum valor: so soma `passo` a cada horario. Ex.: o valor de
    HR = 14 (media de 14:00 a 15:00 UTC) passa a se chamar 15:00, como a media
    horaria da SONDA do mesmo intervalo.
    """
    deslocada = serie.copy()
    deslocada.index = deslocada.index + pd.Timedelta(passo)
    return deslocada


def irradiancia_topo(inicios, latitude, longitude, passo="1h", amostras=12):
    """Irradiancia media no topo da atmosfera (W/m2) em cada intervalo [inicio, inicio + passo).

    Usa as formulas de Spencer (1971) para declinacao, equacao do tempo e
    distancia Terra-Sol, e faz a media de `amostras` instantes dentro do
    intervalo. Serve como teto fisico: a radiacao na superficie nao pode passar
    dela, e ela e zero quando o sol esta abaixo do horizonte.
    """
    inicios = pd.DatetimeIndex(inicios)
    passo = pd.Timedelta(passo)
    lat = np.radians(latitude)
    soma = np.zeros(len(inicios))
    for k in range(amostras):
        t = inicios + passo * ((k + 0.5) / amostras)
        horas = t.hour + t.minute / 60 + t.second / 3600
        g = 2 * np.pi / 365 * (t.dayofyear - 1 + (horas - 12) / 24)
        declinacao = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g)
                      - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g)
                      - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
        equacao_tempo = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                                  - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
        distancia = (1.000110 + 0.034221 * np.cos(g) + 0.001280 * np.sin(g)
                     + 0.000719 * np.cos(2 * g) + 0.000077 * np.sin(2 * g))
        minuto_solar = horas * 60 + equacao_tempo + 4 * longitude
        angulo_horario = np.radians(minuto_solar / 4 - 180)
        cos_zenite = (np.sin(lat) * np.sin(declinacao)
                      + np.cos(lat) * np.cos(declinacao) * np.cos(angulo_horario))
        soma += CONSTANTE_SOLAR * distancia * np.clip(cos_zenite, 0, None)
    return pd.Series(soma / amostras, index=inicios, name="toa")
