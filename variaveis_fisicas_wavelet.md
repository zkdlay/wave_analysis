# Variaveis fisicas da analise wavelet

Este arquivo descreve as principais variaveis usadas no pipeline de
`waveanalise.py`. Entre parenteses aparece, quando aplicavel, o nome classico
usado em muitos codigos de wavelet e o nome mais descritivo usado neste projeto.

## Variaveis de entrada e preparacao

| Variavel no codigo | Unidade fisica | Significado |
| --- | --- | --- |
| `Temperatura_Avg` | graus Celsius (degC), se a planilha estiver nessa unidade | Temperatura media do ar no intervalo original de amostragem. |
| `Umidade_Avg` | porcentagem (%) | Umidade relativa media do ar no intervalo original de amostragem. |
| `dados_diarios["data"]` | dia calendario | Data associada a cada media diaria. |
| `umidade_media_diaria` | porcentagem (%) | Serie temporal da umidade relativa media diaria. |
| `umidade_anomalia` | porcentagem (%) | Desvio da umidade diaria em relacao a media da propria serie. |
| `variancia_umidade` | porcentagem ao quadrado (%^2) | Variancia da serie de anomalia de umidade. |
| `passo_tempo` (`dt`) | dias | Intervalo temporal entre duas amostras consecutivas. Para dados horarios, `dt = 1/24` dia. |
| `escala` (`scale`) | dias, aproximadamente | Escala temporal usada pela transformada wavelet. Ela e convertida em periodo por um fator que depende da wavelet mae. |
| `periodo` (`period`) | dias | Periodo equivalente de cada escala, isto e, a duracao fisica das oscilacoes analisadas. |
| `coeficientes_wavelet` (`wave`) | mesma unidade da serie, aqui % | Coeficientes complexos da transformada wavelet. Eles indicam amplitude e fase das oscilacoes em cada tempo e periodo. |
| `cone_influencia` (`coi`) | dias | Limite temporal-periodico a partir do qual os efeitos de borda passam a afetar fortemente a interpretacao. |

## `power` (`espectro_potencia`)

`power` e o espectro de potencia local da wavelet:

```text
power = abs(wave)^2
```

Fisicamente, ele mede a intensidade da variabilidade da serie em cada instante
e em cada periodo. Como a serie analisada e umidade relativa em %, a unidade de
`power` e aproximadamente %^2.

Valores altos de `power` indicam que, naquele intervalo de tempo, existe uma
oscilacao forte associada ao periodo correspondente. Por exemplo, potencia alta
em periodo de 8 dias significa que a umidade apresentou variacoes intensas nessa
escala temporal durante aquele trecho da serie.

## `global_ws` (`espectro_wavelet_global`)

`global_ws` e o espectro global de wavelet. Ele e calculado pela media temporal
do espectro de potencia:

```text
global_ws = mean(power, ao longo do tempo)
```

Fisicamente, ele resume quais periodos concentram mais variancia na serie
inteira. Enquanto `power` mostra onde e quando uma oscilacao aparece,
`global_ws` responde quais periodos sao mais importantes considerando todo o
registro temporal.

A unidade tambem e %^2 quando a variavel analisada e umidade relativa em %.

## `scale_avg` (`media_escala`)

`scale_avg` e a media de escala, isto e, uma serie temporal que soma a potencia
wavelet dentro de uma faixa de periodos escolhida. No script, a faixa analisada
e aproximadamente de 2 a 8 dias:

```text
2 <= scale < 8
```

Fisicamente, `scale_avg` mostra como a variancia associada a essa banda de
periodos muda ao longo do tempo. Se `media_escala` aumenta, significa que as
oscilacoes entre 2 e 8 dias ficaram mais fortes naquele trecho da serie.

Sua unidade fisica e a unidade da variavel ao quadrado, aqui %^2.

## `sig95` (`significancia_95`)

`sig95` representa a razao entre a potencia observada e a potencia minima
necessaria para significancia estatistica de 95%:

```text
sig95 = power / significancia_teorica
```

Ela e adimensional, pois e uma razao entre duas potencias com a mesma unidade.
Quando `sig95 > 1`, a potencia wavelet local e considerada estatisticamente
significativa ao nivel de 95%, de acordo com o modelo de ruido vermelho definido
por `lag1`.

No grafico, o contorno preto marca aproximadamente as regioes onde `sig95 = 1`.

## COI (`cone_influencia`)

COI significa `cone of influence`, ou cone de influencia. Ele delimita a regiao
do espectro wavelet afetada por efeitos de borda.

Como a transformada wavelet usa janelas temporais finitas, os pontos perto do
inicio e do fim da serie nao possuem informacao completa para escalas longas.
Nessas regioes, a potencia pode ser artificialmente reduzida ou distorcida.

Fisicamente, o COI indica ate quais periodos a interpretacao e mais confiavel em
cada instante. Fora da regiao confiavel, especialmente em periodos longos perto
das bordas da serie, os resultados devem ser interpretados com cautela.

A unidade do COI e dias, a mesma unidade de `periodo`.

## Papel de `dj`

`dj` controla a resolucao entre escalas consecutivas da transformada wavelet.
As escalas sao construidas em potencias de 2:

```text
scale_j = s0 * 2^(j * dj)
```

Assim, `dj` define quantos pontos de escala existem dentro de cada oitava. Uma
oitava representa dobrar a escala ou o periodo. No codigo atual:

```text
dj = 0.25
```

Isso significa 4 subescalas por oitava, porque `1 / 0.25 = 4`.

Fisicamente, `dj` nao muda a unidade da serie; ele muda o detalhamento com que
os periodos sao amostrados. Um `dj` menor gera mais escalas, mais suavidade no
grafico e maior custo computacional. Um `dj` maior gera menos escalas, menos
detalhe e graficos mais discretos.

Para series meteorologicas horarias, `dj = 0.25` e uma escolha adequada e bem
comum. Ela oferece boa resolucao para identificar variabilidade sinotica,
intrassazonal e sazonal sem deixar a analise excessivamente pesada.

## Papel de `s0`

`s0` e a menor escala analisada pela wavelet. Ele define o ponto de partida da
grade de escalas:

```text
scale_0 = s0
```

No codigo atual, usando a base horaria:

```text
s0 = 2 * dt
dt = 1/24 dia
```

Como a serie e horaria, `dt = 1/24` representa uma hora em unidade de dias.
Assim, `s0 = 2 * dt` corresponde a 2 horas, ou aproximadamente 0,0833 dia.
Isso permite que a analise inclua variabilidade subdiaria e ciclo diario.

Importante: escala e periodo nao sao exatamente a mesma coisa. A conversao
depende da wavelet mae. Para a wavelet `PAUL` com parametro 4, usada no codigo,
o fator de Fourier e aproximadamente:

```text
periodo = 1.396 * escala
```

Portanto, com `s0 = 2 * dt`, o menor periodo analisado fica perto de:

```text
periodo_minimo = 1.396 * 0.0833 = 0.116 dia = 2.79 horas
```

Para dados meteorologicos horarios, isso e adequado quando o interesse inclui
variabilidade horaria, ciclo diario e tambem variacoes de varios dias.

## Papel de `j1`

`j1` controla quantas escalas serao calculadas a partir de `s0`. Ele define o
limite superior da grade de escalas. No codigo atual, esse valor nao fica mais
fixo como `7 / dj`; ele e calculado automaticamente a partir do periodo maximo
desejado:

```text
j1 = floor(log2(scale_max / s0) / dj)
```

Para a configuracao atual:

```text
periodo_maximo = 365 dias
scale_max = periodo_maximo / fator_fourier
```

Como a escala cresce por `2^(j * dj)`, o codigo usa quantas escalas forem
necessarias para ir de cerca de 2,8 horas ate aproximadamente 365 dias.

Isso inclui variabilidade subdiaria, ciclo diario, escala sinotica,
intrassazonal e quase anual.

## Os parametros atuais sao adequados para series meteorologicas?

Para series meteorologicas horarias, os parametros atuais sao uma boa primeira
configuracao:

| Parametro | Valor atual | Avaliacao |
| --- | --- | --- |
| `dt` | 1/24 dia | Adequado para base horaria. |
| `dj` | 0.25 | Adequado; fornece 4 subescalas por oitava. |
| `s0` | `2 * dt` | Adequado para incluir variabilidade horaria e ciclo diario. |
| `j1` | automatico | Calculado para cobrir ate `PERIODO_MAX_ANALISE_DIAS`, atualmente 365 dias. |
| `mother` | `PAUL` | Pode ser usado, mas `MORLET` costuma ser mais comum para interpretar ciclos oscilatorios em geofisica. |
| `lag1` | estimado por variavel | Mais adequado do que usar um valor fixo para todas as series. |

A configuracao atual e especialmente adequada se o objetivo for estudar
variabilidade desde poucas horas ate cerca de 1 ano. Isso combina bem com
temperatura, umidade relativa e radiacao de onda curta em base horaria.

Ha, porem, tres cuidados importantes:

1. Se a serie tiver varios anos e o interesse incluir variabilidade interanual,
   `PERIODO_MAX_ANALISE_DIAS = 365` pode ser curto. Nesse caso, convem aumentar
   esse limite, por exemplo para 730 dias ou mais.

2. Se a interpretacao de ciclos for central, a wavelet `MORLET` geralmente e
   mais intuitiva que `PAUL`, porque ela representa melhor oscilacoes suaves e
   periodicas. A `PAUL` e mais localizada no tempo e pode destacar eventos mais
   abruptos.

3. O `lag1` influencia diretamente a significancia estatistica. Agora ele e
   estimado separadamente para cada variavel pela autocorrelacao de atraso 1 da
   serie preparada.

Uma configuracao recomendada para comecar, mantendo o codigo atual, e:

```text
dt = 1/24
dj = 0.25
s0 = 2 * dt
periodo_maximo = 365 dias
lag1 = estimado separadamente para cada variavel
mother = "PAUL" ou "MORLET"
```

Para uma analise mais robusta, especialmente em artigo ou relatorio final, a
proxima melhoria seria testar a sensibilidade dos resultados a `mother`,
`PERIODO_MAX_ANALISE_DIAS` e ao intervalo escolhido para a media de escala.
