# Critério de mascaramento da umidade do INPE

A base `inpe_2024-08-28_11h_continua_umidade_tratada.csv` já corresponde à
etapa que trata valores de umidade relativa acima de 100 %. O notebook
`notebooks/02_inpe/validar_umidade_inpe.ipynb` registra 592 valores removidos
nessa etapa e produz a base atual com 3.420 linhas.

O número apresentado na Tabela 2.3 não é produzido por esse notebook. Na base
atual, o critério numérico

```text
umidade_relativa < 10.0
```

identifica exatamente 944 valores. A rotina
`executar/mascarar_umidade_inpe_tabela_2_3.py` preserva as 3.420 linhas e
substitui esses valores por `NaN`, deixando 2.476 valores válidos de umidade.

Não foi encontrada, no código ou na documentação disponível, uma lista de
intervalos de falha que substitua esse limiar. Portanto, a reprodução da
Tabela 2.3 é uma máscara numérica explícita, aplicada após o tratamento dos
valores acima de 100 %, e não uma seleção de intervalos documentados.

Saídas geradas em `2026/dados_tratados/`:

- `inpe_2024-08-28_11h_continua_umidade_mascarada_abaixo_10.csv`;
- `inpe_2024-08-28_11h_continua_umidade_mascarada_abaixo_10_relatorio.csv`.
