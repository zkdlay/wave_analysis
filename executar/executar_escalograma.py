"""Gera, para uma variavel da SONDA-MD e para cada passo de tempo, as figuras:
sinal original, escalograma, espectro global e fase.

Uso:
    .\\.venv\\Scripts\\python.exe -m executar.executar_escalograma
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.caminhos_e_parametros import PASSO_MD_DIAS, PASTA_FIGURAS_WAVELET, VARIAVEIS_MD
from src.wavelet.analise_wavelet import (
    calcular_escalograma,
    carregar_variavel_md,
    media_por_passo,
    plotar_escalograma,
    plotar_espectro_global,
    plotar_fase,
    plotar_sinal,
    preparar_serie,
    salvar_figura,
)


VARIAVEL = "tp_sfc"
WAVELET = "MORLET"
# Nome usado nos arquivos -> passo em dias. 10 min e o passo original do MD;
# os outros passos usam a media dos registros (media_por_passo).
PASSOS = {"10min": PASSO_MD_DIAS, "1h": 1 / 24}


def main():
    descricao = VARIAVEIS_MD[VARIAVEL]
    rotulo, unidade = descricao["rotulo"], descricao["unidade"]
    serie_md = carregar_variavel_md(VARIAVEL)
    pasta = PASTA_FIGURAS_WAVELET / VARIAVEL
    mae = WAVELET.lower()

    for nome_passo, passo in PASSOS.items():
        if passo == PASSO_MD_DIAS:
            serie, agregacao = serie_md, None
        else:
            serie, agregacao = media_por_passo(serie_md, passo)
        preparada = preparar_serie(serie, passo_dias=passo, agregacao=agregacao)
        resultado = calcular_escalograma(preparada, WAVELET)
        print(
            f"{rotulo}, passo {nome_passo}: {len(serie)} pontos | lag-1 = {preparada['lag1']:.4f} | "
            f"{len(resultado['periodo'])} escalas, {resultado['periodo'][0] * 24:.2f} h a "
            f"{resultado['periodo'][-1]:.0f} d"
        )

        figuras = {
            f"sinal_{VARIAVEL}_{nome_passo}": lambda: plotar_sinal(preparada, rotulo, unidade),
            f"escalograma_{VARIAVEL}_{mae}_{nome_passo}": lambda: plotar_escalograma(preparada, resultado, rotulo, unidade),
            f"espectro_global_{VARIAVEL}_{mae}_{nome_passo}": lambda: plotar_espectro_global(preparada, resultado, rotulo, unidade),
            f"fase_{VARIAVEL}_{mae}_{nome_passo}": lambda: plotar_fase(preparada, resultado, rotulo),
        }
        for nome, desenhar in figuras.items():
            figura = desenhar()
            print(f"  -> {salvar_figura(figura, pasta / f'{nome}.png')}")
            plt.close(figura)
        del resultado


if __name__ == "__main__":
    main()
