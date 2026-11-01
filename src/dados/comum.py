"""Ferramentas de tratamento que servem para qualquer fonte (SONDA, INPE, NASA...).

Para que serve: mudar o passo de tempo, achar e preencher falhas e salvar a
serie pronta que o motor wavelet le.
Quem usa: os notebooks de tratamento (notebooks/<fonte>/).

Serie pronta = arquivo <fonte>_<variavel>_<passo>.csv em 2026/series_prontas,
com as colunas `tempo` e `valor`, datas regulares e sem falhas.
"""

import pandas as pd

from config.caminhos_e_parametros import PASTA_SERIES_PRONTAS


def media_por_passo(serie, passo, passo_original):
    """Media da serie em blocos de `passo` (ex.: "1h" para media horaria).

    O horario marca o FIM do intervalo (convencao da SONDA: o valor de 01:00 e
    a media dos registros de 00:10 a 01:00). Blocos sem nenhum registro ficam
    NaN. Devolve tambem quantos blocos internos (sem contar o primeiro e o
    ultimo, cortados pelas pontas da serie) tiveram a media feita com
    registros faltando.
    """
    passo, passo_original = pd.Timedelta(passo), pd.Timedelta(passo_original)
    blocos = serie.resample(passo, closed="right", label="right")
    contagem = blocos.count()
    esperado = round(passo / passo_original)
    info = {
        "registros_por_bloco": esperado,
        "blocos_incompletos": int((contagem.iloc[1:-1] < esperado).sum()),
    }
    return blocos.mean(), info


def falhas(serie, passo):
    """Tabela com inicio, fim, numero de registros e duracao de cada trecho sem dado."""
    faltante = serie.isna()
    if not faltante.any():
        return pd.DataFrame(columns=["inicio", "fim", "registros", "duracao"])
    grupo = (faltante != faltante.shift()).cumsum()[faltante]
    horarios = pd.Series(serie.index[faltante], index=serie.index[faltante])
    tabela = horarios.groupby(grupo.values).agg(["min", "max", "size"]).reset_index(drop=True)
    tabela.columns = ["inicio", "fim", "registros"]
    tabela["duracao"] = tabela["registros"] * pd.Timedelta(passo)
    return tabela


def preencher_falhas(serie, passo, interpolar_ate="60min"):
    """Interpola linearmente so as falhas curtas.

    A wavelet exige serie sem buracos. Falhas de ate `interpolar_ate` sao
    preenchidas; se houver alguma maior, a funcao para e lista as falhas, para
    que a decisao de como trata-las seja tomada de forma explicita.
    """
    interpolar_ate = pd.Timedelta(interpolar_ate)
    tabela = falhas(serie, passo)
    longas = tabela[tabela["duracao"] > interpolar_ate]
    if len(longas):
        raise ValueError(
            f"{len(longas)} falhas maiores que {interpolar_ate} em '{serie.name}':\n"
            f"{longas.to_string(index=False)}"
        )
    if serie.iloc[[0, -1]].isna().any():
        raise ValueError(f"A serie '{serie.name}' comeca ou termina sem dado; ajuste inicio/fim.")

    preenchida = serie.interpolate(method="time", limit_area="inside")
    info = {
        "falhas_interpoladas": len(tabela),
        "registros_interpolados": int(tabela["registros"].sum()),
        "maior_falha": tabela["duracao"].max() if len(tabela) else pd.Timedelta(0),
    }
    return preenchida, info


def salvar_serie_pronta(serie, nome, pasta=PASTA_SERIES_PRONTAS):
    """Salva <pasta>/<nome>.csv com as colunas tempo e valor.

    `nome` segue <fonte>_<variavel>_<passo>, ex.: sonda_tp_sfc_1h.
    Recusa serie com falhas: o motor nao aceita NaN.
    """
    if serie.isna().any():
        raise ValueError(f"A serie '{nome}' ainda tem {int(serie.isna().sum())} valores faltando.")
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}.csv"
    tabela = pd.DataFrame({"tempo": serie.index, "valor": serie.to_numpy()})
    tabela.to_csv(caminho, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return caminho
