# Mapa do projeto

> A única fonte de dados é a estação SONDA de Cachoeira Paulista (pasta
> **"Dados SONDA"** do Google Drive). No momento a análise wavelet cobre só a
> temperatura do MD; a umidade aguarda a resposta do grupo sobre as falhas de
> mar–mai/2025.

## Estrutura

```text
wave_analysis-1/
├── README_EXECUCAO.md               como executar cada etapa
├── config/
│   └── caminhos_e_parametros.py     caminhos e parâmetros padrão da wavelet
├── src/
│   ├── dados/
│   │   └── sonda.py                 leitura dos .dat, junção por ano, controle de qualidade
│   └── wavelet/
│       ├── wavelet_core.py          transformada e significância (Torrence & Compo, 1998)
│       └── analise_wavelet.py       leitura da variável, preparo, escalograma e figura
├── executar/
│   ├── juntar_sonda_por_ano.py      .dat brutos -> um arquivo por ano (MD, 10 min)
│   └── executar_escalograma.py      sinal, escalograma, espectro global e fase (Morlet; 10 min e 1 h)
├── notebooks/
│   ├── 01_tratamento_sonda.ipynb    exploração anterior: MD + SD em base horária
│   └── 02_diagnostico_sonda_md.ipynb  falhas e valores estranhos do MD, com mapas
├── docs/
│   └── mapa_do_projeto.md           este arquivo
└── _lixo/                           material antigo, fora do fluxo (pode ser consultado)
```

## Fora do repositório

```text
Google Drive/
└── Dados SONDA/                     ENTRADA: arquivos brutos .dat (2023–2026)

Iniciação Cientifica - INPE/2026/
├── sonda_unificada/MD/              SAÍDA de juntar_sonda_por_ano.py
│   ├── sonda_MD_2023 ... sonda_MD_2026 (.csv e .xlsx); 2023 só a partir de 01/12/2023
│   ├── LEIAME_colunas_MD.txt        significado de cada coluna e cuidados
│   └── diagnostico/                 tabelas do notebook 02
├── resultados/figuras/
│   ├── wavelet_sonda_md/            SAÍDA de executar_escalograma.py
│   ├── sonda_tratamento/            figuras do notebook 01
│   └── (demais pastas)              resultados antigos, das bases antigas
├── sonda_tratada/                   saída do notebook 01 (base horária)
├── dados_brutos/                    cópia local antiga (SONDA e NASA POWER), não usada
└── dados_tratados/                  bases antigas (NASA, INPE, SONDA), não usadas
```

## Fluxo atual

```text
Dados SONDA/AAAA/CPA_AAAA_DDD_a_DDD_MD.dat     (10 min, UTC)
        │  executar/juntar_sonda_por_ano.py
        ▼
2026/sonda_unificada/MD/sonda_MD_AAAA.csv      (desde 01/12/2023; umidade > 100 % -> 100 %; pressão ~602 mb interpolada)
        │                     │
        │                     └─ notebooks/02_diagnostico_sonda_md.ipynb (falhas e valores estranhos)
        │  executar/executar_escalograma.py
        ▼
2026/resultados/figuras/wavelet_sonda_md/<variavel>/
    sinal_<variavel>_<passo>.png
    escalograma_<variavel>_<wavelet>_<passo>.png
    espectro_global_<variavel>_<wavelet>_<passo>.png
    fase_<variavel>_<wavelet>_<passo>.png          (<passo> = 10min ou 1h)
```

## Escalograma: escolhas e correções

| Item | Como está | Antes (fluxo antigo) |
|---|---|---|
| Passo de tempo | 10 min (135.792 pontos) | 1 h |
| Grade de períodos (dj) | 1/8: 8 escalas por oitava, ~21 min a ~1 ano | 1/4: o ciclo diário aparecia como "22 h" |
| Falhas | interpola só falhas de até 60 min; maiores interrompem a análise com a lista | interpolava tudo sem avisar (ou `dropna`, que quebrava a série) |
| Lag-1 do ruído vermelho | valor real (0,9978 na temperatura) | limitado a 0,99, subestimando o ruído nos períodos longos |
| Memória | guarda só a potência (float32, ~64 MB) | guardava todos os coeficientes complexos |
| Passo de tempo | 10 min e 1 h (média horária; o horário marca o fim da hora) | só 1 h |
| Significância na figura | cores inteiras com contorno preto nas regiões significativas (`esmaecer=True` também esmaece as não significativas) | contornos brancos que viravam manchas em séries longas |
| Espectro global | média da potência no tempo; significância com `N − escala/dt` graus de liberdade | — |
| Fase | θ(a, τ) = arg W(a, τ), mapa de cores cíclico | — |
| Arquivos de figura | sobrescreve | criava cópias `_01`, `_02`... |
| `wave_signif` com `sigtest=1` | aceita `dof` escalar | quebrava com `dof` escalar |
| Configuração | parâmetros passados como argumentos | variáveis globais sobrescritas pelos executores |

Ainda por fazer quando for retomada: média de escala (constante de
reconstrução de cada wavelet: Morlet 0,776, Paul 1,132, DOG 3,541).

## Convenções dos dados SONDA

- Horário em **UTC** (hora local = UTC−3); o `TIMESTAMP` marca o **fim** do intervalo de 10 min.
- Troca do datalogger CR3000 → CR1000X em **01/12/2023**; antes disso o MD não
  tem chuva nem vento.
- Dúvidas em aberto sobre os dados: checklist "Checklist - dúvidas sobre os dados SONDA-CPA".
