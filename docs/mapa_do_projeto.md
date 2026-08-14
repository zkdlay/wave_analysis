# Mapa do projeto

```text
wave_analysis-1/
├── README_EXECUCAO.md
├── config/
│   └── caminhos_e_parametros.py
├── src/wavelet/
│   ├── wavelet_core.py
│   ├── analise_wavelet.py
│   ├── comparar_wavelets.py
│   ├── visualizacoes_comparacao.py
│   └── modulacao_banda_diaria.py
├── executar/
│   ├── executar_analise_wavelet_lote.py
│   ├── executar_comparacao_wavelets.py
│   ├── executar_visualizacoes_comparacao.py
│   ├── executar_modulacao_nasa.py
│   └── executar_modulacao_sonda.py
├── notebooks/
│   ├── 01_nasa_power/
│   ├── 02_inpe/
│   ├── 03_sonda/
│   └── 04_comparacao_bases/
├── docs/
└── Arquivo/
    ├── scripts_antigos/
    ├── experimentos/
    └── notebooks_antigos/wave_analysis-1/
```

## Fluxo principal

```text
dados tratados
      │
      ▼
config/caminhos_e_parametros.py
      │
      ▼
src/wavelet/analise_wavelet.py
      ├── wavelet_core.py
      ├── comparar_wavelets.py
      ├── visualizacoes_comparacao.py
      └── modulacao_banda_diaria.py
      │
      ▼
executar/
      │
      ▼
figuras, relatórios e tabelas na pasta 2026/
```

Os notebooks são materiais de tratamento, inspeção e comparação. Eles não
substituem os executores reprodutíveis do fluxo principal.
