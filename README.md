# wave_analysis

Projeto de Iniciação Científica (PIBIC/INPE): **análise wavelet contínua** de dados
meteorológicos de superfície da estação **SONDA de Cachoeira Paulista** (INPE). O
**NASA POWER** do mesmo ponto é usado como comparação. A transformada e os testes de
significância seguem **Torrence & Compo (1998)**.

## Como o projeto funciona

```text
tratamento por fonte  ->  série pronta  ->  motor wavelet  ->  figuras
(notebooks/<fonte>/)      (tempo, valor;    (notebooks/wavelet/
                           sem falhas)       + src/wavelet/)
```

- O **tratamento** lê o dado bruto, faz o controle de qualidade, muda o passo (10 min → 1 h) e
  preenche as falhas curtas.
- O **motor** não altera o dado. Ele recusa séries irregulares ou com falha, normaliza a série,
  estima o lag-1 do ruído vermelho, calcula a transformada e roda os testes de significância a 95 %.

## Por onde começar a ler

| Onde | O que tem |
|---|---|
| `docs/mapa_do_projeto.md` | lista oficial dos arquivos em uso, escolhas do motor e convenções dos dados |
| `src/wavelet/` | o motor: `wavelet_core.py` (a conta), `motor.py`, `significancia.py`, `graficos.py` |
| `src/dados/` | leitura e tratamento: `sonda.py`, `nasa_power.py`, `comum.py` |
| `notebooks/sonda/` | diagnóstico (`01`) e tratamento (`02`) da SONDA |
| `notebooks/nasa_power/` | diagnóstico (`01`) e tratamento (`02`) do NASA POWER |
| `notebooks/visualizacao/ciclo_diario.ipynb` | ciclo diário médio de temperatura, umidade, onda curta e onda longa (SONDA e NASA POWER) |
| `notebooks/wavelet/rodar_wavelet.ipynb` | roda o motor numa série pronta |

## Situação atual e questões em aberto

- **Séries prontas:**
  - SONDA: temperatura e umidade (10 min e 1 h) e radiação de onda curta e de onda longa;
  - NASA POWER: temperatura (1 h).
- **Onda longa da SONDA (`lw_calc`):** o ciclo diurno médio parece fisicamente incoerente (mínimo
  perto das 10 h e máximo perto das 19 h locais). A causa ainda não foi confirmada.
- **Umidade da SONDA:** as falhas de mar–mai/2025 foram preenchidas com 100 % de forma provisória
  (sensor saturado), a confirmar com o grupo.
- **Por fazer no motor:**
  - teste de significância da média de escalas (`sigtest = 2`);
  - teste por área;
  - Monte Carlo.

## Dados e execução

Os dados **não estão neste repositório**. Ficam fora dele, na pasta `02_dados/` da IC: os brutos
da SONDA, o CSV do NASA POWER, as séries prontas e as figuras. As figuras de diagnóstico e de
ciclo diário aparecem nas saídas dos notebooks. Para rodar cada etapa, veja
[`README_EXECUCAO.md`](README_EXECUCAO.md).
