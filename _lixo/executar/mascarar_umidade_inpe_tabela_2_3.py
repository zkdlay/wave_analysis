"""Mascara valores baixos de umidade da base INPE para a Tabela 2.3.

Esta etapa parte da base INPE que já passou pelo tratamento de valores acima
de 100 %. Ela preserva todas as linhas e substitui por NaN os valores de
umidade estritamente menores que 10 %, deixando explícitos o critério e os
contadores usados no relatório.
"""

from pathlib import Path

import pandas as pd


PASTA_PROJETO = Path(__file__).resolve().parents[1]
PASTA_DADOS = PASTA_PROJETO.parent / "2026" / "dados_tratados"
ARQUIVO_ENTRADA = (
    PASTA_DADOS / "inpe_2024-08-28_11h_continua_umidade_tratada.csv"
)
ARQUIVO_SAIDA = (
    PASTA_DADOS / "inpe_2024-08-28_11h_continua_umidade_mascarada_abaixo_10.csv"
)
ARQUIVO_RELATORIO = (
    PASTA_DADOS / "inpe_2024-08-28_11h_continua_umidade_mascarada_abaixo_10_relatorio.csv"
)

LIMIAR_UMIDADE = 10.0


def mascarar_umidade():
    if not ARQUIVO_ENTRADA.exists():
        raise FileNotFoundError(f"Base de entrada não encontrada: {ARQUIVO_ENTRADA}")

    dados = pd.read_csv(ARQUIVO_ENTRADA)
    colunas_necessarias = {
        "data_hora",
        "radiacao_onda_curta",
        "temperatura",
        "umidade_relativa",
    }
    ausentes = colunas_necessarias.difference(dados.columns)
    if ausentes:
        raise ValueError(f"Colunas ausentes na base INPE: {sorted(ausentes)}")

    dados["data_hora"] = pd.to_datetime(dados["data_hora"], errors="coerce")
    dados["umidade_relativa"] = pd.to_numeric(
        dados["umidade_relativa"], errors="coerce"
    )

    mascara_baixa = dados["umidade_relativa"] < LIMIAR_UMIDADE
    quantidade_mascarada = int(mascara_baixa.sum())
    dados.loc[mascara_baixa, "umidade_relativa"] = float("nan")

    quantidade_linhas = len(dados)
    quantidade_valida = int(dados["umidade_relativa"].notna().sum())
    quantidade_nan = int(dados["umidade_relativa"].isna().sum())

    if quantidade_mascarada != 944 or quantidade_valida != 2476:
        raise AssertionError(
            "A base atual não reproduziu os números da Tabela 2.3: "
            f"mascarados={quantidade_mascarada}, válidos={quantidade_valida}."
        )

    dados.to_csv(ARQUIVO_SAIDA, index=False, date_format="%Y-%m-%d %H:%M:%S")

    relatorio = pd.DataFrame(
        [
            {"indicador": "arquivo_entrada", "valor": str(ARQUIVO_ENTRADA)},
            {"indicador": "criterio", "valor": "umidade_relativa < 10.0"},
            {"indicador": "linhas_na_base", "valor": quantidade_linhas},
            {"indicador": "valores_mascarados", "valor": quantidade_mascarada},
            {"indicador": "valores_validos_depois", "valor": quantidade_valida},
            {"indicador": "valores_ausentes_depois", "valor": quantidade_nan},
            {"indicador": "arquivo_saida", "valor": str(ARQUIVO_SAIDA)},
        ]
    )
    relatorio.to_csv(ARQUIVO_RELATORIO, index=False)

    print(f"Critério: umidade_relativa < {LIMIAR_UMIDADE:.1f}%")
    print(f"Linhas preservadas: {quantidade_linhas}")
    print(f"Valores mascarados: {quantidade_mascarada}")
    print(f"Valores válidos: {quantidade_valida}")
    print(f"Base salva em: {ARQUIVO_SAIDA}")
    print(f"Relatório salvo em: {ARQUIVO_RELATORIO}")


if __name__ == "__main__":
    mascarar_umidade()
