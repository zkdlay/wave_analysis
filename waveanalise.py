import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker
from pathlib import Path

from funcoeswave import wave_signif, wavelet


# ---------------------------------------------------------------------------
# 1. Carregamento e agregacao dos dados
# ---------------------------------------------------------------------------

arquivo_dados = Path(__file__).resolve().parent.parent / "table_onehour.xlsx"

dados_horarios = pd.read_excel(arquivo_dados)
dados_horarios["TIMESTAMP"] = pd.to_datetime(dados_horarios["TIMESTAMP"])
dados_horarios["data"] = dados_horarios["TIMESTAMP"].dt.date

dados_diarios = (
    dados_horarios.groupby("data")[["Temperatura_Avg", "Umidade_Avg"]]
    .mean()
    .reset_index()
)


# ---------------------------------------------------------------------------
# 2. Preparacao da serie temporal analisada
# ---------------------------------------------------------------------------

umidade_media_diaria = dados_diarios["Umidade_Avg"].values
umidade_anomalia = umidade_media_diaria - np.mean(umidade_media_diaria)
variancia_umidade = np.std(umidade_anomalia, ddof=1) ** 2

print("variancia da umidade = ", variancia_umidade)

normalizar_serie = False
if normalizar_serie:
    variancia_umidade = 1.0
    umidade_anomalia = umidade_anomalia / np.std(umidade_anomalia, ddof=1)


# ---------------------------------------------------------------------------
# 3. Definicao dos parametros da transformada wavelet
# ---------------------------------------------------------------------------

numero_amostras = len(umidade_anomalia)
passo_tempo = 1.0  # dias, pois a serie foi agregada para medias diarias
usar_padding = 1
resolucao_escala = 0.25  # 4 sub-octavas por octava
escala_inicial = 2  # menor escala analisada, em dias
numero_escalas = 7 / resolucao_escala
autocorrelacao_lag1 = 0.72
wavelet_mae = "PAUL"

print("autocorrelacao de primeiro atraso (lag1) = ", autocorrelacao_lag1)


# ---------------------------------------------------------------------------
# 4. Transformada wavelet e espectros de potencia
# ---------------------------------------------------------------------------

coeficientes_wavelet, periodo, escala, cone_influencia = wavelet(
    umidade_anomalia,
    passo_tempo,
    usar_padding,
    resolucao_escala,
    escala_inicial,
    numero_escalas,
    wavelet_mae,
)

espectro_potencia = np.abs(coeficientes_wavelet) ** 2
espectro_wavelet_global = np.sum(espectro_potencia, axis=1) / numero_amostras


# ---------------------------------------------------------------------------
# 5. Significancia local de 95% para o espectro de potencia
# ---------------------------------------------------------------------------

significancia_teorica = wave_signif(
    [variancia_umidade],
    dt=passo_tempo,
    sigtest=0,
    scale=escala,
    lag1=autocorrelacao_lag1,
    mother=wavelet_mae,
)

significancia_95 = significancia_teorica[:, np.newaxis].dot(
    np.ones(numero_amostras)[np.newaxis, :]
)
significancia_95 = espectro_potencia / significancia_95


# ---------------------------------------------------------------------------
# 6. Significancia do espectro global
# ---------------------------------------------------------------------------

graus_liberdade_global = numero_amostras - escala
significancia_global = wave_signif(
    variancia_umidade,
    dt=passo_tempo,
    scale=escala,
    sigtest=1,
    lag1=autocorrelacao_lag1,
    dof=graus_liberdade_global,
    mother=wavelet_mae,
)


# ---------------------------------------------------------------------------
# 7. Media de escala no intervalo de periodos de interesse
# ---------------------------------------------------------------------------

intervalo_media_escala = np.logical_and(escala >= 2, escala < 8)
constante_reconstrucao = 1.132  # Cdelta para wavelet PAUL com parametro 4

escala_expandida = escala[:, np.newaxis].dot(
    np.ones(numero_amostras)[np.newaxis, :]
)
potencia_normalizada_por_escala = espectro_potencia / escala_expandida
media_escala = (
    resolucao_escala
    * passo_tempo
    / constante_reconstrucao
    * sum(potencia_normalizada_por_escala[intervalo_media_escala, :])
)

significancia_media_escala = wave_signif(
    variancia_umidade,
    dt=passo_tempo,
    scale=escala,
    sigtest=2,
    lag1=autocorrelacao_lag1,
    dof=[2, 7.9],
    mother=wavelet_mae,
)


# ---------------------------------------------------------------------------
# 8. Plotagem da serie temporal de umidade
# ---------------------------------------------------------------------------

fig = plt.figure(figsize=(12, 10))
plt.subplots_adjust(left=0.1, bottom=0.05, right=0.9, top=0.95, wspace=0, hspace=0)
plt.plot(dados_diarios["data"], umidade_anomalia, "k", linewidth=1.5)
plt.xlabel("Tempo em meses")
plt.ylabel("Umidade relativa (%)")
plt.title("Variacao da umidade", fontsize=10)
plt.xticks(rotation=45)
plt.show()


# ---------------------------------------------------------------------------
# 9. Plotagem do espectro de potencia wavelet
# ---------------------------------------------------------------------------

fig = plt.figure(figsize=(12, 6))
niveis_potencia = [0, 0.5, 1, 2, 4, 999]
contornos = plt.contourf(
    dados_diarios["data"],
    periodo,
    espectro_potencia,
    len(niveis_potencia),
    cmap="RdYlBu_r",
)
imagem_potencia = plt.contourf(
    contornos,
    levels=niveis_potencia,
    colors=["white", "bisque", "orange", "orangered", "darkred"],
)
plt.xlabel("Tempo em meses")
plt.ylabel("Periodo em dias")
plt.title("Espectro de potencia da wavelet", fontsize=10)
plt.contour(dados_diarios["data"], periodo, significancia_95, [-99, 1], colors="k")
plt.fill_between(
    dados_diarios["data"],
    cone_influencia * 0 + periodo[-1],
    cone_influencia,
    facecolor="none",
    edgecolor="#00000040",
    hatch="x",
)
plt.plot(dados_diarios["data"], cone_influencia, "k")
plt.gca().set_yscale("log", base=2, subs=None)
plt.ylim([np.min(periodo), np.max(periodo)])
eixo_y = plt.gca().yaxis
eixo_y.set_major_formatter(ticker.ScalarFormatter())
plt.ticklabel_format(axis="y", style="plain")
plt.gca().invert_yaxis()
eixo_barra_cores = fig.add_axes([0.15, 0.56, 0.02, 0.2])
plt.colorbar(
    imagem_potencia,
    cax=eixo_barra_cores,
    orientation="vertical",
    label="Potencia (%^2)",
)
plt.show()


# ---------------------------------------------------------------------------
# 10. Plotagem da media de escala
# ---------------------------------------------------------------------------

significancia_media_expandida = np.repeat(
    significancia_media_escala,
    len(dados_diarios["data"]),
)
plt.plot(dados_diarios["data"], media_escala, "k", linewidth=1.5)
plt.xlabel("Tempo (meses)")
plt.ylabel("Variancia media (%^2)")
plt.title("Serie temporal media", fontsize=10)
plt.plot(dados_diarios["data"], significancia_media_expandida, "--k", linewidth=1.5)
plt.show()


# ---------------------------------------------------------------------------
# 11. Plotagem do espectro global de wavelet
# ---------------------------------------------------------------------------

plt.plot(espectro_wavelet_global, periodo, "k", linewidth=1.5)
plt.plot(significancia_global, periodo, "--k", linewidth=1.5)
plt.xlabel("Potencia (%^2)")
plt.title("Espectro global de wavelet", fontsize=10)
plt.xlim([0, 1.25 * np.max(espectro_wavelet_global)])
plt.yscale("log", base=2, subs=None)
plt.ylim([np.min(periodo), np.max(periodo)])
eixo_y = plt.gca().yaxis
eixo_y.set_major_formatter(ticker.ScalarFormatter())
plt.ticklabel_format(axis="y", style="plain")
plt.gca().invert_yaxis()
plt.ylabel("Periodo em dias")
plt.tight_layout()
plt.show()
