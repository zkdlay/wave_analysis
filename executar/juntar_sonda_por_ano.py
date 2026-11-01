"""Junta os arquivos brutos .dat da SONDA em um arquivo por ano.

Para que serve: primeira etapa do fluxo (dados brutos -> arquivos anuais do MD).
Quem usa: e rodado a mao; a saida e lida por notebooks/sonda/

Os valores e a resolucao original sao mantidos (MD: 10 min). Alteracoes:
- removidos horarios repetidos;
- removidos os registros anteriores a INICIO: antes da troca do datalogger
  (01/12/2023) o MD so media temperatura, umidade e pressao, e a direcao do
  vento era gravada como 0 fixo;
- umidade relativa acima de 100 % convertida para 100 %;
- falhas do barometro (quedas para ~602 mb e as medias contaminadas nas
  bordas) trocadas por interpolacao linear; a coluna press_interpolada marca
  esses registros.
Saida em 2026/sonda_unificada/<tipo>/, em .csv e .xlsx.

Uso:
    .\\.venv\\Scripts\\python.exe -m executar.juntar_sonda_por_ano
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.caminhos_e_parametros import PASTA_SONDA_UNIFICADA, pasta_dados_sonda
from src.dados import sonda


TIPO = "MD"
INICIO = pd.Timestamp("2023-12-01 00:00:00")
UMIDADE_MAXIMA = 100.0
# Registro de pressao a mais de PRESSAO_DESVIO_MB da mediana de 6 h e falha
# do sensor (criterio combinado com o grupo em 10/2026).
PRESSAO_DESVIO_MB = 5.0


def main():
    pasta = pasta_dados_sonda()
    destino = PASTA_SONDA_UNIFICADA / TIPO
    destino.mkdir(parents=True, exist_ok=True)

    por_ano, repetidos = sonda.juntar_por_ano(pasta, TIPO)
    inventario = sonda.listar_arquivos(pasta, TIPO)
    cabecalho = sonda.ler_cabecalho(inventario["caminho"].iloc[0])
    variaveis = pd.DataFrame(
        {
            "variavel": cabecalho["colunas"],
            "unidade": [cabecalho["unidades"][c] for c in cabecalho["colunas"]],
            "processamento": [cabecalho["processamento"][c] for c in cabecalho["colunas"]],
        }
    )

    # A pressao e corrigida na serie inteira: a janela de 6 h atravessa a virada do ano
    pressao = pd.concat(d.set_index("TIMESTAMP")["press"] for d in por_ano.values()).sort_index()
    pressao = pressao[~pressao.index.duplicated()].loc[INICIO:]
    pressao, pressao_interpolada = sonda.interpolar_falhas_pressao(pressao, PRESSAO_DESVIO_MB)

    for ano, dados in por_ano.items():
        nome = f"sonda_{TIPO}_{ano}"
        dados = dados[dados["TIMESTAMP"] >= INICIO]
        if dados.empty:
            continue
        arquivos = inventario[inventario["arquivo"].isin(dados["arquivo_origem"].unique())]
        arquivos = arquivos[["arquivo", "datalogger", "programa"]]
        repetidos_ano = repetidos[repetidos["TIMESTAMP"] >= INICIO] if len(repetidos) else repetidos
        repetidos_ano = repetidos_ano.query("ano == @ano") if len(repetidos_ano) else repetidos_ano
        dados = dados.drop(columns="arquivo_origem")
        dados, umidade_acima = sonda.saturar_umidade(dados, maximo=UMIDADE_MAXIMA)
        dados["press"] = dados["TIMESTAMP"].map(pressao)
        dados.insert(dados.columns.get_loc("press") + 1, "press_interpolada",
                     dados["TIMESTAMP"].map(pressao_interpolada))
        variaveis_ano = pd.concat([variaveis, pd.DataFrame([{
            "variavel": "press_interpolada", "unidade": "",
            "processamento": "True = press trocada por interpolacao linear (falha do sensor)",
        }])], ignore_index=True)

        dados.to_csv(destino / f"{nome}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        with pd.ExcelWriter(destino / f"{nome}.xlsx") as escritor:
            dados.to_excel(escritor, sheet_name="dados", index=False)
            variaveis_ano.to_excel(escritor, sheet_name="variaveis", index=False)
            arquivos.to_excel(escritor, sheet_name="arquivos_origem", index=False)

        print(
            f"{nome}: {len(dados)} registros | {dados['TIMESTAMP'].min()} a "
            f"{dados['TIMESTAMP'].max()} | {len(arquivos)} arquivos | "
            f"{len(repetidos_ano) // 2} horarios repetidos removidos | "
            f"{umidade_acima} valores de umidade > 100 % levados a 100 % | "
            f"{int(dados['press_interpolada'].sum())} valores de pressao interpolados"
        )


if __name__ == "__main__":
    main()
