import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.wavelet.analise_wavelet as base
import src.wavelet.comparar_wavelets as comparacao


configuracoes = base.VARIAVEIS_ANALISAR.copy()
fontes_e_variaveis = (
    ("nasa_power", ("temperatura", "umidade_relativa", "radiacao_onda_curta")),
    ("sonda_md", ("temperatura", "umidade_relativa")),
    ("sonda_sd", ("radiacao_onda_curta",)),
)

for fonte, variaveis in fontes_e_variaveis:
    print(f"INICIO: {fonte}", flush=True)
    base.FONTE_ANALISE = fonte
    base.VARIAVEIS_ANALISAR = {
        coluna: configuracoes[coluna].copy() for coluna in variaveis
    }
    if "radiacao_onda_curta" in base.VARIAVEIS_ANALISAR:
        base.VARIAVEIS_ANALISAR["radiacao_onda_curta"]["unidade"] = (
            base.UNIDADES_RADIACAO_POR_FONTE[fonte]
        )
    comparacao.ARQUIVO_DADOS_TRATADOS = (
        base.PASTA_DADOS_TRATADOS / base.ARQUIVOS_DADOS_TRATADOS[fonte]
    )
    comparacao.PASTA_SAIDA_COMPARACAO = (
        base.PASTA_PROJETO_DADOS / "figuras_wavelet_comparacao" / fonte
    )
    comparacao.VARIAVEIS_ANALISAR = base.VARIAVEIS_ANALISAR
    comparacao.main()
    print(f"CONCLUIDO: {fonte}", flush=True)
