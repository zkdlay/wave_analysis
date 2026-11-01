"""Testes de significancia do motor wavelet.

Para que serve: guardar cada teste de significancia como uma funcao
`teste_<nome>`, escolhida pela lista TESTES do notebook do motor.
Quem usa: src/wavelet/motor.py (calcular) e src/wavelet/graficos.py.

Para criar um teste novo:
1. escreva `teste_<nome>(serie_preparada, resultado, nivel)` devolvendo o
   limiar (array) ou o que o grafico precisar;
2. registre em TESTES_DISPONIVEIS;
3. coloque "<nome>" na lista TESTES do notebook.

Todos os testes usam ruido vermelho (AR(1)) com o lag-1 da serie como
espectro de fundo (Torrence & Compo, 1998).
"""

import numpy as np

from .wavelet_core import wave_signif


def _parametros(serie_preparada, resultado, nivel):
    return dict(
        dt=serie_preparada["passo_dias"], scale=resultado["escala"], lag1=serie_preparada["lag1"],
        siglvl=nivel, mother=resultado["wavelet_mae"],
    )


def teste_local(serie_preparada, resultado, nivel):
    """Ponto a ponto no escalograma: limiar de potencia por escala (qui-quadrado, 2 g.l.; eq. 18)."""
    return wave_signif([serie_preparada["variancia"]], sigtest=0, **_parametros(serie_preparada, resultado, nivel))


def teste_global(serie_preparada, resultado, nivel):
    """Espectro global: graus de liberdade N - escala/dt em cada escala, descontando a borda (eq. 23)."""
    graus = len(serie_preparada["valores"]) - resultado["escala"] / serie_preparada["passo_dias"]
    return wave_signif([serie_preparada["variancia"]], sigtest=1, dof=graus,
                       **_parametros(serie_preparada, resultado, nivel))


TESTES_DISPONIVEIS = {
    "local": teste_local,
    "global": teste_global,
}


def aplicar_testes(serie_preparada, resultado, testes, nivel):
    """Roda os testes pedidos e devolve {nome: limiar}."""
    desconhecidos = [t for t in testes if t not in TESTES_DISPONIVEIS]
    if desconhecidos:
        raise ValueError(f"Testes desconhecidos: {desconhecidos}. Disponiveis: {list(TESTES_DISPONIVEIS)}")

    return {nome: np.asarray(TESTES_DISPONIVEIS[nome](serie_preparada, resultado, nivel), dtype=float)
            for nome in testes}
