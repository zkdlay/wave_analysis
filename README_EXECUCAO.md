# wave_analysis

Análise wavelet de séries meteorológicas. Hoje a única fonte é a estação SONDA
de Cachoeira Paulista (INPE), pasta **"Dados SONDA"** do Google Drive. O
material antigo (NASA POWER, INPE e o fluxo wavelet anterior) está em `_lixo/`,
fora do git.

```text
tratamento por fonte  ->  série pronta  ->  notebook do motor  ->  figuras
(notebooks/<fonte>/)      (02_dados/series_prontas/)  (notebooks/wavelet/)  (02_dados/resultados/wavelet/)
```

Ambiente: `.\.venv\Scripts\python.exe`. Para recriar o `.venv`:
`python -m venv .venv` e `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.

## Etapas

1. **Acesso aos dados brutos.** No Google Drive, adicione o atalho da pasta
   "Dados SONDA" em "Meu Drive". O caminho é localizado por
   `pasta_dados_sonda()` no `config` (ou pela variável de ambiente `DADOS_SONDA`).

2. **Arquivos anuais do MD (meteorologia, 10 min).** Só quando chegarem dados novos.

   ```powershell
   .\.venv\Scripts\python.exe -m executar.juntar_sonda_por_ano
   ```

   Gera `02_dados/sonda_unificada/MD/sonda_MD_AAAA.csv` e `.xlsx`, a partir de
   01/12/2023, com a umidade acima de 100 % convertida para 100 % e com as
   falhas do barômetro (~602 mb) trocadas por interpolação linear (coluna
   `press_interpolada`).

3. **Diagnóstico** — `notebooks/sonda/01_diagnostico.ipynb`: falhas e valores
   estranhos de cada variável. Só mostra, não altera nada.

4. **Tratamento** — `notebooks/sonda/02_tratamento.ipynb`: escolhe a variável e
   os passos (10 min, 1 h...), interpola falhas de até 60 min e grava as séries
   prontas `02_dados/series_prontas/sonda_<variavel>_<passo>.csv`.

5. **Motor wavelet** — `notebooks/wavelet/rodar_wavelet.ipynb`: na célula de
   configuração escolha `SERIE`, os textos dos títulos (`FONTE`, `LOCAL`,
   `VARIAVEL`, `UNIDADE`, `TEXTO_EXTRA`), `WAVELET`, `TESTES`, `GRAFICOS` e,
   se quiser, `PERIODO_MIN`/`PERIODO_MAX`. As figuras ficam em
   `02_dados/resultados/wavelet/<fonte>/<variavel>/<wavelet>_<passo>/`.

Mapa completo das pastas e dos arquivos: `docs/mapa_do_projeto.md`.
