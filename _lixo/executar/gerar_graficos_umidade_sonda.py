"""Gera os gráficos de umidade da SONDA-MD e a comparação com a NASA POWER."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from scipy.stats import pearsonr


PASTA_PROJETO = Path(__file__).resolve().parents[1]
PASTA_DADOS = PASTA_PROJETO.parent / "2026" / "dados_tratados"
PASTA_FIGURAS = PASTA_DADOS.parent / "resultados" / "figuras"
ARQUIVO_SONDA = PASTA_DADOS / "sonda_md_horario_padronizado.csv"
ARQUIVO_NASA = PASTA_DADOS / "nasa_power_horario_padronizado.csv"


def carregar_umidade(caminho):
    dados = pd.read_csv(caminho, parse_dates=["data_hora"])
    dados["umidade_relativa"] = pd.to_numeric(
        dados["umidade_relativa"], errors="coerce"
    )
    return (
        dados[["data_hora", "umidade_relativa"]]
        .dropna(subset=["data_hora"])
        .sort_values("data_hora")
        .drop_duplicates("data_hora")
    )


def gerar_evolucao_sonda(sonda):
    pasta_saida = PASTA_FIGURAS / "comparacao_bases"
    pasta_saida.mkdir(parents=True, exist_ok=True)
    serie = sonda.set_index("data_hora")["umidade_relativa"]
    diaria = serie.resample("D").agg(["mean", "count"])
    dias_parciais = diaria.index[diaria["count"] < 24]

    fig, ax = plt.subplots(figsize=(14, 4.2), dpi=150)
    diaria["mean"].plot(ax=ax, color="#1f5a85", linewidth=0.8)
    for dia in dias_parciais:
        ax.axvspan(
            dia,
            dia + pd.Timedelta(days=1),
            color="#e6a700",
            alpha=0.22,
            linewidth=0,
        )
    ax.set_title("Umidade relativa da SONDA-MD (média diária)")
    ax.set_xlabel("Data")
    ax.set_ylabel("Umidade relativa (%)")
    ax.legend(
        handles=[
            Patch(
                facecolor="#e6a700",
                alpha=0.22,
                label="Dia com cobertura parcial",
            )
        ],
        loc="best",
        fontsize=8,
    )
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    caminho = pasta_saida / "sonda_md_umidade_evolucao.png"
    fig.savefig(caminho, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return caminho, len(dias_parciais)


def gerar_comparacao_evolucao(sonda, nasa):
    pasta_saida = PASTA_FIGURAS / "comparacao_bases"
    pasta_saida.mkdir(parents=True, exist_ok=True)
    diaria_sonda = (
        sonda.set_index("data_hora")["umidade_relativa"]
        .resample("D")
        .agg(media_umidade_sonda_md="mean", observacoes_sonda_md="count")
    )
    diaria_nasa = (
        nasa.set_index("data_hora")["umidade_relativa"]
        .resample("D")
        .agg(media_umidade_nasa_power="mean", observacoes_nasa_power="count")
    )
    diaria = diaria_nasa.join(diaria_sonda, how="outer")
    dias_parciais = diaria.index[diaria["observacoes_sonda_md"] < 24]

    fig, ax = plt.subplots(figsize=(16, 6), dpi=150)
    ax.plot(
        diaria.index,
        diaria["media_umidade_nasa_power"],
        color="#2166ac",
        linewidth=1.2,
        label="NASA POWER",
    )
    ax.plot(
        diaria.index,
        diaria["media_umidade_sonda_md"],
        color="#b2182b",
        linewidth=1.2,
        label="SONDA-MD",
    )
    for dia in dias_parciais:
        ax.axvspan(
            dia,
            dia + pd.Timedelta(days=1),
            color="#e6a700",
            alpha=0.18,
            linewidth=0,
        )
    ax.set_title("Evolução diária da umidade relativa: NASA POWER e SONDA-MD")
    ax.set_xlabel("Data")
    ax.set_ylabel("Umidade relativa (%)")
    ax.legend(title="Fonte")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    caminho = pasta_saida / "comparacao_media_diaria_umidade_nasa_power_sonda_md.png"
    fig.savefig(caminho, dpi=300, bbox_inches="tight")
    diaria.to_csv(
        pasta_saida / "medias_diarias_umidade_nasa_power_sonda_md.csv",
        date_format="%Y-%m-%d",
    )
    plt.close(fig)
    return caminho, len(dias_parciais)


def gerar_dispersao(sonda, nasa):
    dados = (
        sonda.merge(
            nasa,
            on="data_hora",
            how="inner",
            suffixes=("_sonda_md", "_nasa_power"),
        )
        .dropna(subset=["umidade_relativa_sonda_md", "umidade_relativa_nasa_power"])
        .sort_values("data_hora")
        .reset_index(drop=True)
    )
    if len(dados) != 17_392:
        raise ValueError(f"Esperados 17.392 pares válidos; encontrados {len(dados):,}.")

    r, _ = pearsonr(
        dados["umidade_relativa_sonda_md"],
        dados["umidade_relativa_nasa_power"],
    )
    n_formatado = f"{len(dados):,}".replace(",", ".")
    r_formatado = f"{r:.3f}".replace(".", ",")

    fig, ax = plt.subplots(figsize=(8.5, 7), dpi=150)
    ax.scatter(
        dados["umidade_relativa_sonda_md"],
        dados["umidade_relativa_nasa_power"],
        s=9,
        alpha=0.28,
        color="#2166ac",
        edgecolors="none",
        rasterized=True,
    )
    limite_min = min(
        dados["umidade_relativa_sonda_md"].min(),
        dados["umidade_relativa_nasa_power"].min(),
    )
    limite_max = max(
        dados["umidade_relativa_sonda_md"].max(),
        dados["umidade_relativa_nasa_power"].max(),
    )
    margem = 0.03 * (limite_max - limite_min)
    limites = [limite_min - margem, limite_max + margem]
    ax.plot(limites, limites, color="#333333", linewidth=1.4, label="y = x")
    ax.set_xlim(limites)
    ax.set_ylim(limites)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Umidade relativa da SONDA-MD (%)")
    ax.set_ylabel("Umidade relativa da NASA POWER (%)")
    ax.set_title("Umidade relativa horária: SONDA-MD × NASA POWER")
    ax.text(
        0.04,
        0.96,
        f"n = {n_formatado}\nPearson: r = {r_formatado}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor="white",
            alpha=0.9,
            edgecolor="0.7",
        ),
    )
    ax.grid(True, linestyle=":", alpha=0.35)
    ax.legend(loc="lower right")
    fig.tight_layout()

    pasta_saida = PASTA_FIGURAS / "comparacao_umidade"
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho_figura = pasta_saida / "dispersao_umidade_sonda_md_nasa_power.png"
    caminho_tabela = pasta_saida / "pares_umidade_sonda_md_nasa_power.csv"
    fig.savefig(caminho_figura, dpi=300, bbox_inches="tight")
    dados.to_csv(caminho_tabela, index=False)
    plt.close(fig)
    return caminho_figura, caminho_tabela, len(dados), r


def main():
    if not ARQUIVO_SONDA.exists() or not ARQUIVO_NASA.exists():
        raise FileNotFoundError(f"Bases tratadas não encontradas em {PASTA_DADOS}.")
    sonda = carregar_umidade(ARQUIVO_SONDA)
    nasa = carregar_umidade(ARQUIVO_NASA)
    caminho_evolucao, dias_parciais = gerar_evolucao_sonda(sonda)
    caminho_comparacao, _ = gerar_comparacao_evolucao(sonda, nasa)
    caminho_dispersao, caminho_tabela, n_pares, correlacao = gerar_dispersao(
        sonda, nasa
    )
    print(f"Evolução salva em: {caminho_evolucao}")
    print(f"Comparação NASA POWER × SONDA-MD salva em: {caminho_comparacao}")
    print(f"Dias com cobertura parcial: {dias_parciais}")
    print(f"Dispersão salva em: {caminho_dispersao}")
    print(f"Tabela salva em: {caminho_tabela}")
    print(f"Pares válidos: {n_pares} | Pearson: r = {correlacao:.6f}")


if __name__ == "__main__":
    main()
