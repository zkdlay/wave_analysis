# Mapa do projeto

> Lista oficial do que está em uso. **Regra:** o que não aparece aqui não faz
> parte do fluxo e vai para `_lixo/` (fora do git, mas consultável na pasta).
>
> Hoje a única fonte é a estação SONDA de Cachoeira Paulista (pasta **"Dados
> SONDA"** do Google Drive). Há séries prontas de temperatura e de umidade do
> MD e de radiação de onda curta (`glo`) e onda longa (`lw_calc`) do SD, lidas
> direto dos `.dat` (o SD ainda não foi juntado por ano). Na umidade, as falhas de mar–mai/2025 foram preenchidas com 100 % de forma
> **provisória** (ar saturado, a confirmar com o grupo; ver
> `02_dados/series_prontas/LEIAME_umidade_falhas_saturacao.txt`).

## Ideia geral

```text
TRATAMENTO (um por fonte)          FRONTEIRA                 MOTOR (um só, genérico)
notebooks/<fonte>/ + src/dados/  -> 02_dados/series_prontas/  -> notebooks/wavelet/ + src/wavelet/
  - lê o dado bruto                  <fonte>_<var>_<passo>.csv   - descobre o passo pelas datas
  - controle de qualidade            colunas: tempo, valor       - recusa série irregular ou com falha
  - muda o passo (10 min -> 1 h)     datas regulares, sem NaN    - normaliza, lag-1, transformada
  - preenche falhas                                              - testes e gráficos escolhidos por lista
```

O motor **não sabe** de onde a série veio e **não altera** o dado. Tudo que
mexe no dado fica no tratamento.

## Para que serve cada arquivo

| Arquivo | Para que serve | Quem usa |
|---|---|---|
| `README_EXECUCAO.md` | como rodar cada etapa | você |
| `requirements.txt` | versões das bibliotecas, para recriar o `.venv` | `pip install -r` |
| `config/caminhos_e_parametros.py` | pastas e parâmetros padrão da wavelet | todos |
| `src/dados/sonda.py` | ler os `.dat`, juntar por ano, corrigir umidade/pressão, ler o MD, ler uma variável do SD | `executar/`, `notebooks/sonda/` |
| `src/dados/comum.py` | mudar passo, achar/preencher falhas, salvar série pronta (qualquer fonte) | notebooks de tratamento |
| `src/wavelet/wavelet_core.py` | a conta: transformada e significância (Torrence & Compo, 1998) | `motor.py`, `significancia.py` |
| `src/wavelet/motor.py` | valida a série, passo, normalização, lag-1, faixa de períodos, transformada | notebook do motor |
| `src/wavelet/significancia.py` | testes de significância (`TESTES_DISPONIVEIS`) | `motor.py` |
| `src/wavelet/graficos.py` | gráficos (`GRAFICOS_DISPONIVEIS`), títulos, salvar figuras | notebook do motor |
| `executar/juntar_sonda_por_ano.py` | `.dat` brutos -> um arquivo por ano (MD, 10 min) | rodado à mão |
| `notebooks/sonda/01_diagnostico.ipynb` | mostra falhas e valores estranhos do MD (não altera nada) | você |
| `notebooks/sonda/02_tratamento.ipynb` | gera as séries prontas da SONDA (`TIPO` = MD ou SD) | você |
| `notebooks/wavelet/rodar_wavelet.ipynb` | roda o motor numa série e gera as figuras | você |

## Como estender

| Quero... | Onde |
|---|---|
| trocar wavelet-mãe, testes, gráficos, faixa de períodos, textos dos títulos | célula de configuração de `rodar_wavelet.ipynb` |
| um gráfico novo | `plotar_<nome>(serie_preparada, resultado, info, opcoes)` em `graficos.py` + `GRAFICOS_DISPONIVEIS` |
| um teste de significância novo | `teste_<nome>(serie_preparada, resultado, nivel)` em `significancia.py` + `TESTES_DISPONIVEIS` |
| uma fonte nova (INPE, NASA...) | `src/dados/<fonte>.py` + `notebooks/<fonte>/` gravando em `series_prontas/` |

## Fora do repositório

```text
Google Drive/
└── Dados SONDA/                     ENTRADA: arquivos brutos .dat (2023–2026)

Iniciação Cientifica - INPE/
├── 01_codigo/wave_analysis/         ESTE projeto
├── 02_dados/
│   ├── sonda_unificada/MD/          SAÍDA de juntar_sonda_por_ano.py
│   │   ├── sonda_MD_2023 ... sonda_MD_2026 (.csv e .xlsx); 2023 só a partir de 01/12/2023
│   │   ├── LEIAME_colunas_MD.txt    significado de cada coluna e cuidados
│   │   └── diagnostico/             tabelas do notebook 01_diagnostico
│   ├── series_prontas/              SAÍDA do tratamento, ENTRADA do motor
│   │   └── LEIAME_umidade_falhas_saturacao.txt   regra provisória das falhas da umidade
│   └── resultados/wavelet/<fonte>/<variavel>/<wavelet>_<passo>/   SAÍDA do motor
├── 03_referencias/  04_producao/  05_administrativo/  06_anotacoes/
└── 99_arquivo/                      projeto antigo, dados e resultados do fluxo anterior
                                     (LEIAME_reorganizacao_2026-11.md: caminho antigo -> novo)
```

## Escolhas do motor

| Item | Como está | Antes (fluxo antigo) |
|---|---|---|
| Passo de tempo | deduzido das datas; série irregular é recusada | escrito à mão no código |
| Falhas | o motor recusa NaN; o tratamento interpola falhas de até 60 min e para nas maiores | interpolava tudo sem avisar (ou `dropna`) |
| Grade de períodos (dj) | 1/8: 8 escalas por oitava | 1/4: o ciclo diário aparecia como "22 h" |
| Faixa de períodos | automática: de 2 passos até o limite do COI (sem passar da duração da série); `PERIODO_MIN`/`PERIODO_MAX` opcionais | fixa até 365 d |
| Eixo de período | marcas escolhidas pela faixa, em min, h, d, meses, anos | marcas fixas de 1 h a 256 d |
| Lag-1 do ruído vermelho | valor real (0,9978 na temperatura de 10 min) | limitado a 0,99 |
| Memória | guarda só potência e fase (float32) | todos os coeficientes complexos |
| Significância na figura | contorno preto nas regiões significativas (`ESMAECER` esmaece as outras) | contornos brancos |
| Espectro global | média da potência no tempo; `N − escala/dt` graus de liberdade | — |
| Títulos | `FONTE`, `LOCAL`, `VARIAVEL`, `UNIDADE`, `TEXTO_EXTRA` vindos do notebook | fixos no código |
| Arquivos de figura | sobrescreve | criava cópias `_01`, `_02`... |

Conferência da reorganização (01/11/2026): com a temperatura em 10 min e 1 h,
Morlet e `PERIODO_MAX = "365D"`, potência, fase, períodos, COI e significância
saíram idênticos aos do motor antigo.

Ainda por fazer: novos testes de significância (média de escala, `sigtest=2`,
com as constantes de reconstrução Morlet 0,776, Paul 1,132, DOG 3,541; teste
por área; Monte Carlo).

## Convenções dos dados SONDA

- Horário em **UTC** (hora local = UTC−3); o `TIMESTAMP` marca o **fim** do intervalo de 10 min.
- Troca do datalogger CR3000 → CR1000X em **01/12/2023**; antes disso o MD não
  tem chuva nem vento.
- Dúvidas em aberto sobre os dados: checklist "Checklist - dúvidas sobre os dados SONDA-CPA".
