"""Leitura e tratamento dos dados da estacao SONDA de Cachoeira Paulista.

Para que serve: ler os .dat brutos (TOA5), juntar por ano, corrigir umidade e
pressao e ler a variavel dos arquivos anuais do MD.
Quem usa: executar/juntar_sonda_por_ano.py e os notebooks de notebooks/sonda/.

Cada arquivo cobre um intervalo de dias do ano e tem 4 linhas de cabecalho:
metadados do datalogger, nomes das colunas, unidades e tipo de processamento
(Avg, Tot, Std, Min, Max, WVc, Smp). Ha dois tipos de arquivo:

- MD: meteorologia, registros a cada 10 min;
- SD: radiacao, registros a cada 1 min.

O TIMESTAMP esta em UTC (hora local = UTC-3) e marca o FIM do intervalo de
integracao (o registro de 00:00 do MD tem Min = 1440, isto e, fecha o dia
anterior). O UTC foi conferido pelo meio-dia solar da radiacao global, que cai
a menos de 1 min do previsto para a longitude 45 W.
"""

import csv
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


TIPOS = ("MD", "SD")
INTERVALO_REGISTRO = {"MD": pd.Timedelta(minutes=10), "SD": pd.Timedelta(minutes=1)}
COLUNAS_CONTROLE = ["RECORD", "Id", "Year", "Jday", "Min"]
COLUNAS_DIRECAO = ["wd10_avg"]
PADRAO_ARQUIVO = re.compile(r"CPA_(\d{4})_(\d{3})_a_(\d{3})_(MD|SD)\.dat$")
CODIGOS_INVALIDOS = [-9999, -999, -6999, 6999, 7999, 9999]

# Limites fisicos por variavel; valores fora deles viram NaN. As colunas
# _std, _min e _max seguem o limite da variavel base (ex.: glo_max -> glo).
LIMITES_FISICOS = {
    "tp_sfc": (-10, 45),            # degC
    "humid": (0, 105),              # % (100-105: saturacao do sensor, ver saturar_umidade)
    "press": (900, 1000),           # mb; a estacao fica ~950 mb, 602 mb e falha do sensor
    "rain": (0, 50),                # mm em 10 min
    "ws10": (0, 50),                # m/s; 999.99 e codigo de falha
    "wd10": (0, 360),               # graus; 999 e codigo de falha
    "glo": (-10, 1500),             # W/m2
    "dif": (-10, 1000),             # W/m2
    "dir": (-10, 1200),             # W/m2
    "lw_raw": (-300, 100),          # W/m2 (sinal liquido da termopilha, negativo e normal)
    "lw_calc": (100, 600),          # W/m2
    "par": (-5, 3000),              # umol/s m2
    "tp_dir": (-10, 60),            # degC
    "tp_lw_case": (-10, 60),        # degC
}
LIMITES_STD = {"ws10_std": (0, 20), "wd10_std": (0, 180)}

# Intervalos em que o instrumento estava fora de operacao ou mal configurado
# (troca do datalogger CR3000 -> CR1000X em 01/12/2023). Fim exclusivo.
# De 08/02 a 12/03/2024 o rastreador solar ficou parado: direta ~0 e difusa
# igual a global (a esfera de sombreamento nao cobria o sensor).
INTERVALOS_INVALIDOS = {
    "glo": [("2023-12-01", "2024-02-08")],
    "dif": [("2023-12-01", "2024-03-13")],
    "dir": [("2023-12-01", "2024-03-13")],
}

DESCRICOES = {
    "tp_sfc": "Temperatura do ar",
    "humid": "Umidade relativa",
    "press": "Pressao atmosferica",
    "rain": "Precipitacao",
    "ws10": "Velocidade do vento (10 m)",
    "wd10": "Direcao do vento (10 m)",
    "glo": "Radiacao global (onda curta)",
    "dif": "Radiacao difusa",
    "dir": "Radiacao direta",
    "lw_raw": "Onda longa - sinal da termopilha",
    "lw_calc": "Radiacao de onda longa",
    "par": "Radiacao fotossinteticamente ativa (PAR)",
    "lux": "Iluminancia",
    "tilt": "Radiacao em plano inclinado",
    "tp_dir": "Temperatura do pireliometro",
    "tp_lw_case": "Temperatura do corpo do pirgeometro",
}

# Variaveis sem uso possivel ou com unidade inconsistente nos arquivos.
VARIAVEIS_DESCARTADAS = ["tilt_avg", "tilt_std", "tilt_min", "tilt_max"]  # 100 % NaN
VARIAVEIS_SUSPEITAS = {
    "lux": "valores ~1000 kLux ao meio-dia desde 12/2023 (sol pleno ~100 kLux); confirmar unidade",
    "par": "periodos com PAR/glo ~100 (esperado ~2); filtrado por consistencia com glo",
}


# ---------------------------------------------------------------------------
# Inventario e cabecalho
# ---------------------------------------------------------------------------

def ler_cabecalho(caminho):
    with open(caminho, encoding="utf-8", errors="replace") as arquivo:
        linhas = [next(csv.reader([arquivo.readline()])) for _ in range(4)]
    metadados, nomes, unidades, processamento = linhas
    return {
        "estacao": metadados[1],
        "datalogger": metadados[2],
        "numero_serie": metadados[3],
        "sistema_operacional": metadados[4],
        "programa": metadados[5].removeprefix("CPU:"),
        "tabela": metadados[7],
        "colunas": nomes,
        "unidades": dict(zip(nomes, unidades)),
        "processamento": dict(zip(nomes, processamento)),
    }


def listar_arquivos(pasta, tipo=None):
    registros = []
    for caminho in sorted(Path(pasta).glob("*/*.dat")):
        encontrado = PADRAO_ARQUIVO.search(caminho.name)
        if not encontrado:
            continue
        ano, dia_inicio, dia_fim, tipo_arquivo = encontrado.groups()
        if tipo and tipo_arquivo != tipo:
            continue
        inicio_ano = pd.Timestamp(f"{ano}-01-01")
        cabecalho = ler_cabecalho(caminho)
        registros.append(
            {
                "arquivo": caminho.name,
                "tipo": tipo_arquivo,
                "ano": int(ano),
                "dia_inicio": int(dia_inicio),
                "dia_fim": int(dia_fim),
                "data_inicio": inicio_ano + pd.Timedelta(days=int(dia_inicio) - 1),
                "data_fim": inicio_ano + pd.Timedelta(days=int(dia_fim)),
                "datalogger": cabecalho["datalogger"],
                "programa": cabecalho["programa"],
                "tamanho_mb": caminho.stat().st_size / 1e6,
                "caminho": caminho,
            }
        )
    return pd.DataFrame(registros)


def dicionario_variaveis(pasta, tipo):
    primeiro = listar_arquivos(pasta, tipo)["caminho"].iloc[0]
    cabecalho = ler_cabecalho(primeiro)
    colunas = [c for c in cabecalho["colunas"] if c not in ["TIMESTAMP", *COLUNAS_CONTROLE]]
    return pd.DataFrame(
        {
            "variavel": colunas,
            "unidade": [cabecalho["unidades"][c] for c in colunas],
            "processamento": [cabecalho["processamento"][c] for c in colunas],
        }
    )


def dias_sem_arquivo(inventario):
    """Dias do periodo coberto que nao pertencem a nenhum arquivo."""
    cobertos = set()
    for linha in inventario.itertuples():
        cobertos.update(pd.date_range(linha.data_inicio, linha.data_fim, freq="D", inclusive="left"))
    periodo = pd.date_range(inventario["data_inicio"].min(), inventario["data_fim"].max(), freq="D", inclusive="left")
    return periodo.difference(pd.DatetimeIndex(sorted(cobertos)))


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

def ler_arquivo_dat(caminho, manter_controle=False):
    dados = pd.read_csv(
        caminho,
        skiprows=[0, 2, 3],
        na_values=["NAN", "NaN", "INF", "-INF"],
        low_memory=False,
    )
    dados["TIMESTAMP"] = pd.to_datetime(dados["TIMESTAMP"], errors="coerce")
    dados = dados.dropna(subset=["TIMESTAMP"]).set_index("TIMESTAMP")
    dados.index.name = "data_hora"
    if not manter_controle:
        dados = dados.drop(columns=COLUNAS_CONTROLE, errors="ignore")
    dados = dados.apply(pd.to_numeric, errors="coerce").astype("float32")
    return dados.replace(CODIGOS_INVALIDOS, np.nan)


def carregar_sonda(pasta, tipo, manter_controle=False):
    """Concatena todos os arquivos de um tipo e devolve (dados, relatorio)."""
    inventario = listar_arquivos(pasta, tipo)
    partes = [ler_arquivo_dat(c, manter_controle) for c in inventario["caminho"]]
    dados = pd.concat(partes).sort_index()

    duplicados = dados.index.duplicated(keep="first")
    dados = dados[~duplicados]

    passo = INTERVALO_REGISTRO[tipo]
    grade = pd.date_range(dados.index.min(), dados.index.max(), freq=passo)
    fora_da_grade = dados.index.difference(grade)
    relatorio = {
        "tipo": tipo,
        "arquivos": len(inventario),
        "registros": len(dados),
        "duplicados_removidos": int(duplicados.sum()),
        "inicio": dados.index.min(),
        "fim": dados.index.max(),
        "registros_esperados": len(grade),
        "registros_ausentes": len(grade.difference(dados.index)),
        "fora_da_grade": len(fora_da_grade),
    }
    return dados, relatorio


def juntar_por_ano(pasta, tipo):
    """Junta os arquivos brutos de cada ano, sem alterar nenhum valor.

    Mantem todas as colunas e a resolucao original; "NAN" vira celula vazia.
    Remove apenas horarios repetidos (mantendo o primeiro) e os registra.
    Devolve {ano: dados} e uma tabela com os horarios repetidos.
    """
    inventario = listar_arquivos(pasta, tipo)
    por_ano, repetidos = {}, []
    for ano, arquivos in inventario.groupby("ano"):
        partes = []
        for linha in arquivos.itertuples():
            parte = pd.read_csv(linha.caminho, skiprows=[0, 2, 3], na_values=["NAN"], low_memory=False)
            parte.insert(1, "arquivo_origem", linha.arquivo)
            partes.append(parte)
        dados = pd.concat(partes, ignore_index=True)
        dados["TIMESTAMP"] = pd.to_datetime(dados["TIMESTAMP"])
        dados = dados.sort_values("TIMESTAMP", kind="stable")

        duplicado = dados["TIMESTAMP"].duplicated(keep=False)
        if duplicado.any():
            repetidos.append(dados[duplicado].assign(ano=ano))
        por_ano[ano] = dados.drop_duplicates("TIMESTAMP", keep="first").reset_index(drop=True)

    repetidos = pd.concat(repetidos, ignore_index=True) if repetidos else pd.DataFrame()
    return por_ano, repetidos


# ---------------------------------------------------------------------------
# Diagnostico
# ---------------------------------------------------------------------------

def resumo_variaveis(dados):
    resumo = dados.describe(percentiles=[0.01, 0.5, 0.99]).T
    resumo.insert(0, "faltantes_%", 100 * dados.isna().mean())
    return resumo


def lacunas(serie, passo):
    """Tabela com inicio, fim e duracao de cada lacuna de uma serie regular."""
    serie = serie.reindex(pd.date_range(serie.index.min(), serie.index.max(), freq=passo))
    faltante = serie.isna()
    if not faltante.any():
        return pd.DataFrame(columns=["inicio", "fim", "duracao_h"])
    grupo = (faltante != faltante.shift()).cumsum()[faltante]
    blocos = faltante[faltante].groupby(grupo).apply(lambda b: (b.index.min(), b.index.max()))
    tabela = pd.DataFrame(blocos.tolist(), columns=["inicio", "fim"])
    tabela["duracao_h"] = ((tabela["fim"] - tabela["inicio"]) + passo) / pd.Timedelta(hours=1)
    return tabela.sort_values("duracao_h", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Controle de qualidade
# ---------------------------------------------------------------------------

def variavel_base(coluna):
    for sufixo in ("_avg", "_std", "_min", "_max"):
        if coluna.endswith(sufixo):
            return coluna.removesuffix(sufixo)
    return coluna


def controle_qualidade(dados):
    """Aplica descarte, intervalos invalidos, limites fisicos e consistencia.

    Devolve (dados_limpos, relatorio) em que o relatorio conta, por coluna,
    quantos valores validos cada regra transformou em NaN.
    """
    dados = dados.drop(columns=VARIAVEIS_DESCARTADAS, errors="ignore").copy()
    contagem = {}

    def anular(coluna, mascara, regra):
        mascara = mascara & dados[coluna].notna()
        contagem[(coluna, regra)] = int(mascara.sum())
        dados.loc[mascara, coluna] = np.nan

    for coluna in dados.columns:
        base = variavel_base(coluna)
        for inicio, fim in INTERVALOS_INVALIDOS.get(base, []):
            anular(coluna, (dados.index >= inicio) & (dados.index < fim), "intervalo_invalido")

        limites = LIMITES_STD.get(coluna, LIMITES_FISICOS.get(base))
        if coluna.endswith("_std") and coluna not in LIMITES_STD:
            limites = (0, limites[1] - limites[0]) if limites else None
        if limites:
            anular(coluna, (dados[coluna] < limites[0]) | (dados[coluna] > limites[1]), "limite_fisico")

    if {"lw_calc_avg", "tp_lw_case"} <= set(dados.columns):
        # lw_calc depende da temperatura do corpo do pirgeometro
        sem_tp_case = dados["tp_lw_case"].isna()
        for coluna in [c for c in dados.columns if c.startswith("lw_calc")]:
            anular(coluna, sem_tp_case, "sem_tp_lw_case")

    if {"par_avg", "glo_avg"} <= set(dados.columns):
        # PAR ~ 2 umol/J da global; acima de 3x(glo)+20 e erro de escala
        inconsistente = dados["par_avg"] > 3 * dados["glo_avg"].clip(lower=10) + 20
        inconsistente |= dados["glo_avg"].isna()
        for coluna in [c for c in dados.columns if c.startswith("par")]:
            anular(coluna, inconsistente, "consistencia_par_glo")

    relatorio = (
        pd.Series(contagem, name="valores_anulados")
        .rename_axis(["variavel", "regra"])
        .unstack(fill_value=0)
    )
    relatorio = relatorio.loc[relatorio.sum(axis=1) > 0]
    return dados, relatorio


def saturar_umidade(dados, coluna="humid", maximo=100.0):
    """Leva a 100 % os valores entre 100 e o limite fisico (saturacao do sensor)."""
    dados = dados.copy()
    acima = dados[coluna] > maximo
    dados.loc[acima, coluna] = maximo
    return dados, int(acima.sum())


def interpolar_falhas_pressao(serie, limite_mb=5.0, janela="6h"):
    """Troca por interpolacao linear os registros de pressao com falha do sensor.

    Entre out/2025 e mar/2026 o barometro cai algumas vezes para ~602 mb (sem
    sinal) por 10 min a 2 h 20, e as medias de 10 min nas bordas dessas quedas
    ficam com valores intermediarios (ex.: 805, 934 mb). Sao marcados os
    registros que se afastam mais de `limite_mb` da mediana movel de `janela`
    centrada, que nao e afetada por quedas curtas. Eles sao trocados pela
    interpolacao linear no tempo entre os registros bons vizinhos; valores
    ausentes (NaN) continuam ausentes. `serie` deve ter o TIMESTAMP como
    indice, sem repeticoes. Devolve a serie corrigida e a mascara dos
    registros trocados.
    """
    mediana = serie.rolling(janela, center=True, min_periods=6).median()
    falha = (serie - mediana).abs() > limite_mb
    bons = (serie.notna() & ~falha).to_numpy()
    segundos = (serie.index - serie.index[0]).total_seconds().to_numpy()
    corrigida = serie.copy()
    corrigida[falha] = interp1d(segundos[bons], serie.to_numpy()[bons])(segundos[falha.to_numpy()])
    return corrigida, falha


# ---------------------------------------------------------------------------
# Agregacao horaria
# ---------------------------------------------------------------------------

def media_circular_graus(valores):
    valores = valores.dropna()
    if valores.empty:
        return np.nan
    radianos = np.deg2rad(valores.to_numpy(dtype=float))
    seno, cosseno = np.sin(radianos).mean(), np.cos(radianos).mean()
    if np.hypot(seno, cosseno) < 1e-6:
        return np.nan
    return float(np.rad2deg(np.arctan2(seno, cosseno)) % 360)


def regra_agregacao(processamento, coluna):
    if coluna in COLUNAS_DIRECAO:
        return media_circular_graus
    return {"Tot": "sum", "Max": "max", "Min": "min"}.get(processamento, "mean")


def agregar_horario(dados, tipo, processamento, cobertura_minima=0.75):
    """Agrega para medias horarias rotuladas pelo INICIO da hora.

    Como o TIMESTAMP marca o fim do intervalo, o registro de 13:00 pertence a
    hora 12:00-13:00. Horas com menos de `cobertura_minima` dos registros
    esperados ficam NaN. Colunas Std sao agregadas pela media (aproximacao).
    """
    passo = INTERVALO_REGISTRO[tipo]
    esperados = pd.Timedelta(hours=1) / passo
    hora = (dados.index - passo).floor("h")
    grupos = dados.groupby(hora)

    regras = {c: regra_agregacao(processamento.get(c, "Avg"), c) for c in dados.columns}
    horario = grupos.agg(regras)
    contagem = grupos.count()
    horario = horario.where(contagem >= cobertura_minima * esperados)

    com_dados = horario.dropna(how="all").index
    grade = pd.date_range(com_dados.min(), com_dados.max(), freq="h")
    horario = horario.reindex(grade)
    horario.index.name = "data_hora"
    return horario, contagem.reindex(grade, fill_value=0)


# ---------------------------------------------------------------------------
# Leitura dos arquivos anuais (saida de executar/juntar_sonda_por_ano.py)
# ---------------------------------------------------------------------------

def carregar_variavel_md(variavel, pasta=None, inicio=None, fim=None):
    """Le uma variavel dos sonda_MD_AAAA.csv e devolve a serie na grade regular de 10 min.

    Horarios sem registro entram como NaN (para o tratamento ver as falhas).
    """
    if pasta is None:
        from config.caminhos_e_parametros import PASTA_SONDA_MD as pasta
    arquivos = sorted(Path(pasta).glob("sonda_MD_*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum sonda_MD_*.csv encontrado em {pasta}")
    partes = [pd.read_csv(a, usecols=["TIMESTAMP", variavel], parse_dates=["TIMESTAMP"]) for a in arquivos]
    dados = pd.concat(partes).drop_duplicates("TIMESTAMP").set_index("TIMESTAMP").sort_index()[variavel]
    dados = dados.loc[inicio:fim]
    grade = pd.date_range(dados.index.min(), dados.index.max(), freq=INTERVALO_REGISTRO["MD"])
    return dados.reindex(grade)
