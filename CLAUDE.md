# CLAUDE.md — wave_analysis

Projeto de Iniciação Científica (PIBIC/INPE) de Sarah: análise wavelet contínua de
dados meteorológicos de superfície da estação SONDA (INPE Cachoeira Paulista).
Alimenta um artigo, um relatório e o TCC (a partir de março/2027).

**Antes de qualquer tarefa, leia `docs/mapa_do_projeto.md`.** Ele é a lista oficial
do que está em uso. Para rodar cada etapa, veja `README_EXECUCAO.md`.

## Como trabalhar comigo

- Responda em português.
- Meu objetivo é aprender: quero entender o que cada parte do código faz, por que é
  necessária e como se liga ao resto.
- Vá passo a passo, sem despejar muita informação de uma vez.
- Quando houver erro, me ajude a investigar a causa antes de propor a correção.
- Prefira código legível e simples. Siga os nomes e o estilo já usados no projeto
  (em português).
- Diferencie o que é resultado matemático, evidência computacional e interpretação física.

## Estrutura (resumo; detalhes no mapa)

- `src/dados/` → leitura e tratamento dos dados SONDA (`sonda.py`, `comum.py`)
- `src/wavelet/` → motor da transformada (Torrence & Compo, 1998): `wavelet_core.py`,
  `motor.py`, `significancia.py`, `graficos.py`
- `notebooks/sonda/` → diagnóstico e tratamento; `notebooks/wavelet/rodar_wavelet.ipynb` → roda o motor
- `config/caminhos_e_parametros.py` → caminhos e parâmetros padrão
- `_lixo/` → fora do fluxo; não use nem edite, a menos que eu peça

Fora do repositório, na pasta da IC (`../../`):
- `02_dados/sonda_unificada/MD/` → dados unidos por ano (10 min); colunas em `LEIAME_colunas_MD.txt`
- `02_dados/series_prontas/` → séries limpas (colunas `tempo`, `valor`), entrada do motor
- `02_dados/resultados/` → saídas do motor
- `99_arquivo/` → versões antigas; não use, a menos que eu peça

## Regras

- **Nunca altere os dados brutos** nem os arquivos de `02_dados/sonda_unificada/`.
- Tudo que mexe no dado fica no **tratamento**; o **motor** não altera o dado e recusa
  séries irregulares ou com NaN. Não quebre essa separação.
- Use só dados da SONDA.
- Horários da SONDA em **UTC** (hora local = UTC−3); o `TIMESTAMP` marca o **fim** do
  intervalo de 10 min.
- Troca de datalogger em **01/12/2023**: antes disso não há chuva nem vento no MD.
- Ao mudar o motor, confira se os resultados antigos continuam iguais (potência, fase,
  COI, significância), como foi feito na reorganização de 01/11/2026.
