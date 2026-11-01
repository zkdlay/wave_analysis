"""Caminhos das pastas e valores padrao da wavelet.

Para que serve: um lugar so para as pastas (dados, series prontas, resultados)
e para os parametros padrao do motor wavelet.
Quem usa: src/dados, src/wavelet, executar/ e os notebooks.

Os dados e resultados ficam na pasta 2026, vizinha ao diretorio do projeto.
Os parametros da wavelet sao so valores padrao: o notebook do motor pode
trocar qualquer um deles sem editar este arquivo.
"""

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Pastas
# ---------------------------------------------------------------------------

PASTA_PROJETO = Path(__file__).resolve().parents[1]
PASTA_PROJETO_DADOS = PASTA_PROJETO.parent / "2026"
PASTA_RESULTADOS = PASTA_PROJETO_DADOS / "resultados"

# Dados brutos da SONDA (.dat), na pasta "Dados SONDA" do Google Drive para
# computador. A variavel de ambiente DADOS_SONDA substitui os candidatos.
ID_PASTA_DRIVE_SONDA = "16ch5d4P2kFqiX3nc1-Dd0zlMsHKTNDfV"
CANDIDATOS_PASTA_SONDA = [
    Path(os.environ["DADOS_SONDA"]) if "DADOS_SONDA" in os.environ else None,
    Path("G:/Meu Drive/Dados SONDA"),
    Path(f"G:/.shortcut-targets-by-id/{ID_PASTA_DRIVE_SONDA}/Dados SONDA"),
]

# SAIDA de executar/juntar_sonda_por_ano.py (um arquivo por ano, MD 10 min)
PASTA_SONDA_UNIFICADA = PASTA_PROJETO_DADOS / "sonda_unificada"
PASTA_SONDA_MD = PASTA_SONDA_UNIFICADA / "MD"

# Fronteira entre tratamento e motor: <fonte>_<variavel>_<passo>.csv (tempo, valor)
PASTA_SERIES_PRONTAS = PASTA_PROJETO_DADOS / "series_prontas"

# Figuras do motor: wavelet/<fonte>/<variavel>/<wavelet>_<passo>/
PASTA_RESULTADOS_WAVELET = PASTA_RESULTADOS / "wavelet"


def pasta_dados_sonda():
    for candidato in CANDIDATOS_PASTA_SONDA:
        if candidato is not None and candidato.is_dir():
            return candidato
    raise FileNotFoundError(
        "Pasta 'Dados SONDA' nao encontrada. Adicione o atalho em 'Meu Drive' "
        "ou defina a variavel de ambiente DADOS_SONDA."
    )


# ---------------------------------------------------------------------------
# Parametros padrao do motor wavelet
# ---------------------------------------------------------------------------

RESOLUCAO_ESCALA = 1 / 8        # dj: 8 escalas por oitava
ESCALAS_INICIAIS_EM_PASSOS = 2  # menor escala s0 = 2 * passo da serie
USAR_PADDING = True             # completa com zeros ate potencia de 2
NIVEL_SIGNIFICANCIA = 0.95
DPI_FIGURAS = 200
