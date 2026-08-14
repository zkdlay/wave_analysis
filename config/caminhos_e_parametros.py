"""Caminhos e parametros compartilhados pela analise wavelet.

Os dados tratados ficam na pasta 2026, vizinha ao diretorio do projeto.
Os executores podem sobrescrever as variaveis mutaveis deste modulo durante
uma execucao em lote, mantendo um unico ponto de configuracao inicial.
"""

from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parents[1]
PASTA_PROJETO_DADOS = PASTA_PROJETO.parent / "2026"
PASTA_DADOS_TRATADOS = PASTA_PROJETO_DADOS / "dados_tratados"

FONTE_ANALISE = "sonda_sd"
ARQUIVOS_DADOS_TRATADOS = {
    "nasa_power": "nasa_power_horario_padronizado.csv",
    "inpe": "inpe_2024-08-28_11h_continua_umidade_tratada.csv",
    "sonda_md": "sonda_md_horario_padronizado.csv",
    "sonda_sd": "sonda_sd_depois_lacuna.csv",
}
UNIDADES_RADIACAO_POR_FONTE = {
    "nasa_power": "Wh/m²",
    "inpe": "W/m²",
    "sonda_sd": "W/m²",
}


def validar_fonte(fonte):
    if fonte not in ARQUIVOS_DADOS_TRATADOS:
        raise ValueError(
            "FONTE_ANALISE deve ser uma das opcoes: "
            f"{', '.join(ARQUIVOS_DADOS_TRATADOS)}."
        )


def caminho_dados_fonte(fonte):
    validar_fonte(fonte)
    return PASTA_DADOS_TRATADOS / ARQUIVOS_DADOS_TRATADOS[fonte]


def caminho_saida_wavelet(fonte):
    validar_fonte(fonte)
    return PASTA_PROJETO_DADOS / "figuras_wavelet" / fonte


ARQUIVO_DADOS_TRATADOS = caminho_dados_fonte(FONTE_ANALISE)
PASTA_SAIDA_FIGURAS = caminho_saida_wavelet(FONTE_ANALISE)

NORMALIZAR_SERIES = True
INTERPOLAR_FALTANTES = True

VARIAVEIS_ANALISAR = {
    "temperatura": {
        "rotulo": "Temperatura",
        "unidade": "degC",
        "cor": "#b2182b",
    },
    "umidade_relativa": {
        "rotulo": "Umidade relativa",
        "unidade": "%",
        "cor": "#2166ac",
    },
    "radiacao_onda_curta": {
        "rotulo": "Radiacao de onda curta",
        "unidade": UNIDADES_RADIACAO_POR_FONTE.get(FONTE_ANALISE, "W/m²"),
        "cor": "#ef8a00",
    },
}

PASSO_TEMPO = 1 / 24
USAR_PADDING = 1
RESOLUCAO_ESCALA = 0.25
ESCALA_INICIAL = 2 * PASSO_TEMPO
PERIODO_MAX_ANALISE_DIAS = 365
WAVELET_MAE = "MORLET"
PERIODO_MIN_MEDIA_ESCALA = 2
PERIODO_MAX_MEDIA_ESCALA = 8
CONSTANTE_RECONSTRUCAO = 1.132
LIMIAR_EVENTO_EXTREMO = 2.0
QUANTIDADE_PICOS_GLOBAIS = 3
MINIMO_CICLOS_FORA_COI = 3.0
DPI_FIGURAS = 300
