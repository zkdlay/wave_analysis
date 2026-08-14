import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.wavelet.analise_wavelet as base
import src.wavelet.visualizacoes_comparacao as visualizacoes


for fonte in ("nasa_power", "sonda_md", "sonda_sd"):
    print(f"INICIO: {fonte}", flush=True)
    visualizacoes.ARQUIVO_DADOS_TRATADOS = (
        base.PASTA_DADOS_TRATADOS / base.ARQUIVOS_DADOS_TRATADOS[fonte]
    )
    visualizacoes.PASTA_SAIDA_NOVAS_VISUALIZACOES = (
        base.PASTA_PROJETO_DADOS / "figuras_novas_visualizacoes" / fonte
    )
    visualizacoes.main()
    print(f"CONCLUIDO: {fonte}", flush=True)
