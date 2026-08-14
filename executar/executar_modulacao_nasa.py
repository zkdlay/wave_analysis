import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import src.wavelet.analise_wavelet as base
import src.wavelet.modulacao_banda_diaria as modulacao


for wavelet_mae in ("PAUL", "MORLET", "DOG"):
    print(f"INICIO: nasa_power | {wavelet_mae}", flush=True)
    modulacao.ARQUIVO_DADOS_TRATADOS = (
        base.PASTA_DADOS_TRATADOS / base.ARQUIVOS_DADOS_TRATADOS["nasa_power"]
    )
    modulacao.PASTA_SAIDA_MODULACAO = (
        base.PASTA_PROJETO_DADOS / "figuras_modulacao" / "nasa_power"
    )
    modulacao.WAVELET_MODULACAO = wavelet_mae
    modulacao.main()
    print(f"CONCLUIDO: nasa_power | {wavelet_mae}", flush=True)
