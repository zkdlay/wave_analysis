import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.wavelet.analise_wavelet as wave


configuracoes = wave.VARIAVEIS_ANALISAR.copy()
for fonte, variaveis in (
    ("nasa_power", ("temperatura", "umidade_relativa", "radiacao_onda_curta")),
    ("sonda_md", ("temperatura", "umidade_relativa")),
    ("sonda_sd", ("radiacao_onda_curta",)),
):
    for wavelet_mae in ("MORLET", "PAUL", "DOG"):
        print(f"INICIO: {fonte} | {wavelet_mae}", flush=True)
        wave.FONTE_ANALISE = fonte
        wave.WAVELET_MAE = wavelet_mae
        wave.ARQUIVO_DADOS_TRATADOS = (
            wave.PASTA_DADOS_TRATADOS / wave.ARQUIVOS_DADOS_TRATADOS[fonte]
        )
        wave.PASTA_SAIDA_FIGURAS = wave.PASTA_PROJETO_DADOS / "figuras_wavelet" / fonte
        wave.VARIAVEIS_ANALISAR = {
            nome: configuracoes[nome].copy() for nome in variaveis
        }
        if "radiacao_onda_curta" in wave.VARIAVEIS_ANALISAR:
            wave.VARIAVEIS_ANALISAR["radiacao_onda_curta"]["unidade"] = (
                wave.UNIDADES_RADIACAO_POR_FONTE.get(fonte, "W/m²")
            )
        wave.main()
        print(f"CONCLUIDO: {fonte} | {wavelet_mae}", flush=True)
