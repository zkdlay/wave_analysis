"""Caminhos e parametros do projeto.

Os dados e resultados ficam na pasta 2026, vizinha ao diretorio do projeto.
Os parametros da wavelet sao valores padrao: as funcoes de src/wavelet os
recebem como argumentos, entao para mudar uma execucao basta passar outro
valor na chamada (nao e preciso editar este arquivo).
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

PASTA_SONDA_UNIFICADA = PASTA_PROJETO_DADOS / "sonda_unificada"
PASTA_SONDA_MD = PASTA_SONDA_UNIFICADA / "MD"
PASTA_SONDA_TRATADA = PASTA_PROJETO_DADOS / "sonda_tratada"
PASTA_FIGURAS_SONDA = PASTA_RESULTADOS / "figuras" / "sonda_tratamento"
PASTA_FIGURAS_WAVELET = PASTA_RESULTADOS / "figuras" / "wavelet_sonda_md"


def pasta_dados_sonda():
    for candidato in CANDIDATOS_PASTA_SONDA:
        if candidato is not None and candidato.is_dir():
            return candidato
    raise FileNotFoundError(
        "Pasta 'Dados SONDA' nao encontrada. Adicione o atalho em 'Meu Drive' "
        "ou defina a variavel de ambiente DADOS_SONDA."
    )


# ---------------------------------------------------------------------------
# Variaveis da SONDA-MD
# ---------------------------------------------------------------------------

VARIAVEIS_MD = {
    "tp_sfc": {"rotulo": "Temperatura do ar", "unidade": "°C"},
    "humid": {"rotulo": "Umidade relativa", "unidade": "%"},
    "press": {"rotulo": "Pressao atmosferica", "unidade": "mb"},
}


# ---------------------------------------------------------------------------
# Parametros padrao da wavelet (tempo em dias)
# ---------------------------------------------------------------------------

PASSO_MD_DIAS = 10 / 1440       # dados MD a cada 10 min
RESOLUCAO_ESCALA = 1 / 8        # dj: 8 escalas por oitava (antes 1/4)
ESCALAS_INICIAIS_EM_PASSOS = 2  # s0 = 2 * dt
PERIODO_MAX_DIAS = 365
USAR_PADDING = True
NIVEL_SIGNIFICANCIA = 0.95
INTERPOLAR_ATE_MINUTOS = 60     # falhas maiores que isso interrompem a analise
DPI_FIGURAS = 200
