from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import main__wave
import main_correlacao
import main_modulacao
import main_wave_comparacao
import main_wave_novas_visualizacoes


PASTA_BASE = Path(__file__).resolve().parent.parent
ARQUIVO_INPE = PASTA_BASE / "analises_2025" / "table_onehour.xlsx"
PASTA_SAIDA_INPE = PASTA_BASE / "2026" / "wave_analisys_inpe"
ARQUIVO_DADOS_TRATADOS_INPE = PASTA_SAIDA_INPE / "dados_tratados" / "inpe_onehour_tratado.csv"

COLUNAS_INPE = {
    "TIMESTAMP": "data_hora",
    "Piranometro_G_Avg": "radiacao_onda_curta",
    "Temperatura_Avg": "temperatura",
    "Umidade_Avg": "umidade_relativa",
}

VARIAVEIS_INPE = {
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
        "unidade": "W/m2",
        "cor": "#ef8a00",
    },
}


def caminho_para_sobrescrever(caminho):
    return caminho


def tratar_base_inpe():
    dados = pd.read_excel(ARQUIVO_INPE, sheet_name="Tabela_1Hora")
    colunas_necessarias = list(COLUNAS_INPE)
    ausentes = [coluna for coluna in colunas_necessarias if coluna not in dados.columns]
    if ausentes:
        raise ValueError(f"Colunas ausentes na planilha INPE: {ausentes}")

    dados = dados[colunas_necessarias].rename(columns=COLUNAS_INPE)
    dados["data_hora"] = pd.to_datetime(dados["data_hora"], errors="coerce")
    dados = dados.dropna(subset=["data_hora"])
    dados = dados.sort_values("data_hora").drop_duplicates(
        subset="data_hora",
        keep="first",
    )

    for coluna in ["radiacao_onda_curta", "temperatura", "umidade_relativa"]:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")

    ARQUIVO_DADOS_TRATADOS_INPE.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(ARQUIVO_DADOS_TRATADOS_INPE, index=False)
    return dados


def carregar_dados_inpe(_caminho=None):
    if not ARQUIVO_DADOS_TRATADOS_INPE.exists():
        tratar_base_inpe()
    return main__wave.carregar_dados_tratados(ARQUIVO_DADOS_TRATADOS_INPE)


def configurar_scripts_para_inpe():
    PASTA_SAIDA_INPE.mkdir(parents=True, exist_ok=True)
    tratar_base_inpe()

    main__wave.ARQUIVO_DADOS_TRATADOS = ARQUIVO_DADOS_TRATADOS_INPE
    main__wave.PASTA_SAIDA_FIGURAS = PASTA_SAIDA_INPE / "figuras_wavelet"
    main__wave.VARIAVEIS_ANALISAR = VARIAVEIS_INPE
    main__wave.DPI_FIGURAS = 150
    main__wave.caminho_disponivel = caminho_para_sobrescrever

    main_wave_comparacao.ARQUIVO_DADOS_TRATADOS = ARQUIVO_DADOS_TRATADOS_INPE
    main_wave_comparacao.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_wave_comparacao.PASTA_SAIDA_COMPARACAO = (
        PASTA_SAIDA_INPE / "figuras_wavelet_comparacao"
    )
    main_wave_comparacao.VARIAVEIS_ANALISAR = VARIAVEIS_INPE
    main_wave_comparacao.DPI_FIGURAS = 150
    main_wave_comparacao.caminho_disponivel = caminho_para_sobrescrever
    main_wave_comparacao.carregar_dados_tratados = carregar_dados_inpe

    main_wave_novas_visualizacoes.ARQUIVO_DADOS_TRATADOS = ARQUIVO_DADOS_TRATADOS_INPE
    main_wave_novas_visualizacoes.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_wave_novas_visualizacoes.PASTA_SAIDA_NOVAS_VISUALIZACOES = (
        PASTA_SAIDA_INPE / "figuras_novas_visualizacoes"
    )
    main_wave_novas_visualizacoes.VARIAVEIS_ANALISAR = VARIAVEIS_INPE
    main_wave_novas_visualizacoes.DPI_FIGURAS = 150
    main_wave_novas_visualizacoes.caminho_disponivel = caminho_para_sobrescrever
    main_wave_novas_visualizacoes.carregar_dados_tratados = carregar_dados_inpe

    main_correlacao.ARQUIVO_DADOS_TRATADOS = ARQUIVO_DADOS_TRATADOS_INPE
    main_correlacao.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_correlacao.PASTA_SAIDA_CORRELACAO = PASTA_SAIDA_INPE / "figuras_correlacao"
    main_correlacao.DPI_FIGURAS = 150
    main_correlacao.carregar_dados_tratados = carregar_dados_inpe

    main_modulacao.ARQUIVO_DADOS_TRATADOS = ARQUIVO_DADOS_TRATADOS_INPE
    main_modulacao.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_modulacao.PASTA_SAIDA_MODULACAO = PASTA_SAIDA_INPE / "figuras_modulacao"
    main_modulacao.VARIAVEIS_ANALISAR = VARIAVEIS_INPE
    main_modulacao.DPI_FIGURAS = 150
    main_modulacao.caminho_disponivel = caminho_para_sobrescrever
    main_modulacao.carregar_dados_tratados = carregar_dados_inpe


def main():
    configurar_scripts_para_inpe()

    print(f"Base tratada salva em: {ARQUIVO_DADOS_TRATADOS_INPE}")
    print(f"Saidas das analises em: {PASTA_SAIDA_INPE}")

    print("\n[1/5] Analise wavelet principal")
    main__wave.main()
    plt.close("all")

    print("\n[2/5] Comparacao entre wavelets")
    main_wave_comparacao.main()
    plt.close("all")

    print("\n[3/5] Novas visualizacoes")
    main_wave_novas_visualizacoes.main()
    plt.close("all")

    print("\n[4/5] Correlacao")
    main_correlacao.main()
    plt.close("all")

    print("\n[5/5] Modulacao diaria")
    main_modulacao.main()
    plt.close("all")

    print("\nConcluido.")


if __name__ == "__main__":
    main()
