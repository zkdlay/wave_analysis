# wave_analysis-1

## Ambiente

Execute os comandos a partir da pasta raiz do projeto, usando o ambiente
virtual do projeto:

```powershell
.\.venv\Scripts\python.exe -m executar.executar_analise_wavelet_lote
```

## Ordem das execucoes

1. Analise wavelet em lote para NASA POWER, SONDA-MD e SONDA-SD:

   ```powershell
   .\.venv\Scripts\python.exe -m executar.executar_analise_wavelet_lote
   ```

2. Comparacao entre Morlet, Paul e DOG:

   ```powershell
   .\.venv\Scripts\python.exe -m executar.executar_comparacao_wavelets
   ```

3. Visualizacoes adicionais da comparacao:

   ```powershell
   .\.venv\Scripts\python.exe -m executar.executar_visualizacoes_comparacao
   ```

4. Modulacao da banda diaria para NASA POWER:

   ```powershell
   .\.venv\Scripts\python.exe -m executar.executar_modulacao_nasa
   ```

5. Modulacao da banda diaria para a interseccao SONDA-MD/SONDA-SD:

   ```powershell
   .\.venv\Scripts\python.exe -m executar.executar_modulacao_sonda
   ```

## Configuracao

Os caminhos, fontes, arquivos tratados e parametros gerais ficam em
`config/caminhos_e_parametros.py`. Para uma execucao individual, altere
`FONTE_ANALISE` e `WAVELET_MAE` nesse arquivo e execute:

```powershell
.\.venv\Scripts\python.exe -m src.wavelet.analise_wavelet
```

As bases tratadas permanecem na pasta `2026/dados_tratados`, vizinha ao
projeto. Os resultados sao escritos nas pastas de figuras correspondentes
dentro de `2026`.

## Escopo dos modulos

- `src/wavelet/wavelet_core.py`: transformada, significancia e funcoes-base.
- `src/wavelet/analise_wavelet.py`: preparo, analise individual e relatorios.
- `src/wavelet/comparar_wavelets.py`: comparacao entre wavelets-mae.
- `src/wavelet/visualizacoes_comparacao.py`: visualizacoes complementares.
- `src/wavelet/modulacao_banda_diaria.py`: potencia normalizada de 20--28 h e correlacoes.
- `executar/`: somente os lancadores de lotes.
- `notebooks/`: tratamento, validacao e comparacao exploratoria por fonte.
- `Arquivo/`: scripts antigos e experimentos que nao fazem parte do fluxo principal.
