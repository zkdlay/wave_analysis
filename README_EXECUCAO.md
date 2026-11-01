# wave_analysis-1

Análise wavelet dos dados da estação SONDA de Cachoeira Paulista (INPE).
A única fonte de dados é a pasta **"Dados SONDA"** do Google Drive. O material
antigo (NASA POWER, INPE e o fluxo wavelet anterior) está em `_lixo/`.

Execute os comandos a partir da pasta raiz do projeto, com o ambiente virtual:

```powershell
.\.venv\Scripts\python.exe -m <modulo>
```

## Etapas

1. **Acesso aos dados brutos.** No Google Drive, adicione o atalho da pasta
   "Dados SONDA" em "Meu Drive". O caminho é localizado por
   `pasta_dados_sonda()` no `config` (ou pela variável de ambiente `DADOS_SONDA`).

2. **Arquivos anuais do MD (meteorologia, 10 min).**

   ```powershell
   .\.venv\Scripts\python.exe -m executar.juntar_sonda_por_ano
   ```

   Gera `2026/sonda_unificada/MD/sonda_MD_AAAA.csv` e `.xlsx`, a partir de
   01/12/2023, com a umidade acima de 100 % convertida para 100 % e com as
   falhas do barômetro (~602 mb) trocadas por interpolação linear (coluna
   `press_interpolada`). O
   significado de cada coluna está em `LEIAME_colunas_MD.txt`, na mesma pasta.

3. **Diagnóstico do MD.** Abra `notebooks/02_diagnostico_sonda_md.ipynb`:
   falhas e valores estranhos de cada variável, com mapas da série inteira.

4. **Escalograma.**

   ```powershell
   .\.venv\Scripts\python.exe -m executar.executar_escalograma
   ```

   Hoje calcula a temperatura (`tp_sfc`) com a wavelet Morlet, nos passos de
   10 min (original) e 1 h (média dos registros de cada hora). Para cada passo
   gera quatro figuras: sinal original, escalograma, espectro global e fase
   θ(a, τ). Ficam em `2026/resultados/figuras/wavelet_sonda_md/<variavel>/`
   (cada execução sobrescreve as anteriores). Para outra variável, outra
   wavelet ou outros passos, edite `VARIAVEL`, `WAVELET` e `PASSOS` no início
   do script.

O notebook `notebooks/01_tratamento_sonda.ipynb` é uma exploração anterior
(MD + SD em base horária, `2026/sonda_tratada/`) e não faz parte do fluxo atual.

## Módulos

- `config/caminhos_e_parametros.py`: caminhos e parâmetros padrão da wavelet.
- `src/dados/sonda.py`: leitura dos `.dat`, junção por ano, controle de qualidade.
- `src/wavelet/wavelet_core.py`: transformada e significância (Torrence & Compo, 1998).
- `src/wavelet/analise_wavelet.py`: leitura da variável, preparo da série,
  escalograma e figura.
- `executar/`: scripts que geram os arquivos e figuras.
- `docs/mapa_do_projeto.md`: mapa das pastas e do fluxo.
