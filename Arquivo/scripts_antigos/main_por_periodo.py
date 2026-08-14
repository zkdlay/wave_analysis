from pathlib import Path
import shutil

import matplotlib.pyplot as plt
import pandas as pd

import main__wave
import main_correlacao
import main_modulacao
import main_wave_comparacao
import main_wave_novas_visualizacoes


PASTA_BASE = Path(__file__).resolve().parent.parent
PASTA_WAVE_ANALYSIS = Path(__file__).resolve().parent

ARQUIVO_ORIGINAL = PASTA_BASE / "2026" / "dados_tratados" / "nasa_power_tratado.csv"
PASTA_PERIODO = (
    PASTA_BASE
    / "2026"
    / "wave_analysis_por_periodo"
    / "2024_05_a_2025_05"
)
ARQUIVO_PERIODO = PASTA_PERIODO / "dados_tratados" / "nasa_power_tratado.csv"

INICIO_ESPERADO = pd.Timestamp("2024-05-01 00:00:00")
FIM_ESPERADO = pd.Timestamp("2025-05-01 23:00:00")

PASTAS_GRAFICOS_ANTIGOS = [
    "figuras_wavelet",
    "figuras_wavelet_comparacao",
    "figuras_novas_visualizacoes",
    "figuras_correlacao",
    "figuras_modulacao",
]


def caminho_para_sobrescrever(caminho):
    return caminho


def remover_graficos_antigos():
    for nome_pasta in PASTAS_GRAFICOS_ANTIGOS:
        caminho = PASTA_WAVE_ANALYSIS / nome_pasta
        if caminho.exists():
            shutil.rmtree(caminho)
            print(f"Pasta antiga removida: {caminho}")


def preparar_csv_periodo():
    dados = pd.read_csv(ARQUIVO_ORIGINAL)
    coluna_tempo = "data_hora" if "data_hora" in dados.columns else "data"
    dados[coluna_tempo] = pd.to_datetime(dados[coluna_tempo], errors="coerce")
    dados = dados.dropna(subset=[coluna_tempo])
    dados = dados.sort_values(coluna_tempo)

    inicio = dados[coluna_tempo].min()
    fim = dados[coluna_tempo].max()
    if inicio != INICIO_ESPERADO or fim != FIM_ESPERADO:
        raise ValueError(
            "Periodo inesperado no CSV original. "
            f"Encontrado: {inicio} ate {fim}. "
            f"Esperado: {INICIO_ESPERADO} ate {FIM_ESPERADO}."
        )

    ARQUIVO_PERIODO.parent.mkdir(parents=True, exist_ok=True)
    dados.to_csv(ARQUIVO_PERIODO, index=False)
    return dados


def carregar_dados_periodo(_caminho=None):
    return main__wave.carregar_dados_tratados(ARQUIVO_PERIODO)


def configurar_scripts():
    main__wave.ARQUIVO_DADOS_TRATADOS = ARQUIVO_PERIODO
    main__wave.PASTA_SAIDA_FIGURAS = PASTA_PERIODO / "wavelet_principal"
    main__wave.DPI_FIGURAS = 150
    main__wave.caminho_disponivel = caminho_para_sobrescrever

    main_wave_comparacao.ARQUIVO_DADOS_TRATADOS = ARQUIVO_PERIODO
    main_wave_comparacao.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_wave_comparacao.PASTA_SAIDA_COMPARACAO = (
        PASTA_PERIODO / "comparacao_wavelets"
    )
    main_wave_comparacao.DPI_FIGURAS = 150
    main_wave_comparacao.caminho_disponivel = caminho_para_sobrescrever
    main_wave_comparacao.carregar_dados_tratados = carregar_dados_periodo

    main_wave_novas_visualizacoes.ARQUIVO_DADOS_TRATADOS = ARQUIVO_PERIODO
    main_wave_novas_visualizacoes.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_wave_novas_visualizacoes.PASTA_SAIDA_NOVAS_VISUALIZACOES = (
        PASTA_PERIODO / "novas_visualizacoes"
    )
    main_wave_novas_visualizacoes.DPI_FIGURAS = 150
    main_wave_novas_visualizacoes.caminho_disponivel = caminho_para_sobrescrever
    main_wave_novas_visualizacoes.carregar_dados_tratados = carregar_dados_periodo

    main_correlacao.ARQUIVO_DADOS_TRATADOS = ARQUIVO_PERIODO
    main_correlacao.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_correlacao.PASTA_SAIDA_CORRELACAO = PASTA_PERIODO / "correlacao"
    main_correlacao.DPI_FIGURAS = 150
    main_correlacao.carregar_dados_tratados = carregar_dados_periodo

    main_modulacao.ARQUIVO_DADOS_TRATADOS = ARQUIVO_PERIODO
    main_modulacao.PASTA_SAIDA_FIGURAS = main__wave.PASTA_SAIDA_FIGURAS
    main_modulacao.PASTA_SAIDA_MODULACAO = PASTA_PERIODO / "modulacao_diaria"
    main_modulacao.DPI_FIGURAS = 150
    main_modulacao.caminho_disponivel = caminho_para_sobrescrever
    main_modulacao.carregar_dados_tratados = carregar_dados_periodo


def main():
    print("Removendo graficos antigos da pasta wave_analysis...")
    remover_graficos_antigos()

    print("Preparando CSV do periodo 2024-05 a 2025-05...")
    dados = preparar_csv_periodo()
    print(f"CSV do periodo salvo em: {ARQUIVO_PERIODO}")
    print(f"Amostras: {len(dados)}")

    configurar_scripts()
    PASTA_PERIODO.mkdir(parents=True, exist_ok=True)
    print(f"Saidas das analises em: {PASTA_PERIODO}")

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
