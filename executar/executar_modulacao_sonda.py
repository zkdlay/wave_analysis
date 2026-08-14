from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.wavelet.analise_wavelet as base
import src.wavelet.modulacao_banda_diaria as modulacao


pasta_dados = base.PASTA_DADOS_TRATADOS
md = pd.read_csv(pasta_dados / "sonda_md_horario_padronizado.csv", parse_dates=["data_hora"])
sd = pd.read_csv(pasta_dados / "sonda_sd_depois_lacuna.csv", parse_dates=["data_hora"])
dados = (
    md.merge(sd, on="data_hora", how="inner")
    .dropna(subset=["temperatura", "umidade_relativa", "radiacao_onda_curta"])
    .sort_values("data_hora")
    .reset_index(drop=True)
)
grupos = (
    dados["data_hora"].diff().fillna(pd.Timedelta(hours=1)) != pd.Timedelta(hours=1)
).cumsum()
maior_grupo = grupos.value_counts().idxmax()
dados = dados.loc[grupos == maior_grupo].copy()
dados = dados.set_index("data_hora")

for wavelet_mae in ("PAUL", "MORLET", "DOG"):
    print(f"INICIO: sonda_md_sd | {wavelet_mae}", flush=True)
    modulacao.WAVELET_MODULACAO = wavelet_mae
    modulacao.PASTA_SAIDA_MODULACAO = (
        base.PASTA_PROJETO_DADOS / "figuras_modulacao" / "sonda_md_sd"
    )
    resultados = modulacao.calcular_modulacao_diaria(dados)
    sufixo_wavelet = wavelet_mae.lower()

    for variavel_a, variavel_b in modulacao.PARES_MODULACAO:
        figura, correlacao = modulacao.plotar_modulacao_par(
            resultados, variavel_a, variavel_b
        )
        sufixo = f"{modulacao.nome_curto_variavel(variavel_a)}_{modulacao.nome_curto_variavel(variavel_b)}"
        modulacao.salvar_figura(
            figura,
            modulacao.PASTA_SAIDA_MODULACAO
            / f"modulacao_banda_diaria_{sufixo}_{sufixo_wavelet}.png",
        )
        modulacao.salvar_texto(
            modulacao.gerar_relatorio_par(resultados, correlacao, variavel_a, variavel_b),
            modulacao.PASTA_SAIDA_MODULACAO
            / f"relatorio_modulacao_banda_diaria_{sufixo}_{sufixo_wavelet}.txt",
        )

    figura = modulacao.plotar_modulacao_tres_variaveis(resultados)
    modulacao.salvar_figura(
        figura,
        modulacao.PASTA_SAIDA_MODULACAO
        / f"modulacao_banda_diaria_tres_variaveis_{sufixo_wavelet}.png",
    )
    modulacao.salvar_texto(
        modulacao.gerar_relatorio_tres_variaveis(resultados),
        modulacao.PASTA_SAIDA_MODULACAO
        / f"relatorio_modulacao_banda_diaria_tres_variaveis_{sufixo_wavelet}.txt",
    )
    print(f"CONCLUIDO: sonda_md_sd | {wavelet_mae}", flush=True)
