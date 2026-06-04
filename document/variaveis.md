# 🧾 Dicionário de Variáveis — AgroSentinela

Este documento descreve **todas as variáveis** usadas pelo modelo preditivo, com
**tipo, unidade, faixa típica e impacto no risco**. Ele substitui a antiga seção
"Variáveis Utilizadas" e atende ao ponto do feedback da Sprint 1.

As variáveis são geradas pelo script [`src/datasets/gerar_dataset.py`](../src/datasets/gerar_dataset.py)
e persistidas na tabela `leituras` do banco ([`src/database/schema.sql`](../src/database/schema.sql)).

## Variáveis numéricas (sensores e telemetria)

| Variável | Tipo | Unidade | Faixa típica | Impacto no risco |
|---|---|---|---|---|
| `umidade_solo_pct` | contínua | % | 5 – 100 | **Alto (↑)**. Solo encharcado reduz tração e favorece atolamento. |
| `precipitacao_24h_mm` | contínua | mm | 0 – 200 | **Alto (↑)**. Chuva recente satura o solo e eleva o risco. |
| `temperatura_c` | contínua | °C | 5 – 45 | Baixo. Atua nos extremos (calor = fadiga; frio = solo úmido). |
| `declividade_graus` | contínua | graus | 0 – 45 | **Alto (↑)**. Terreno inclinado aumenta risco de tombamento. |
| `distancia_corpo_dagua_m` | contínua | metros | 5 – 2000 | **Alto (↓ distância = ↑ risco)**. Perto d'água o solo é mais instável. |
| `idade_equipamento_anos` | contínua | anos | 0 – 25 | Médio (↑). Máquinas antigas falham mais. |
| `horas_desde_manutencao` | contínua | horas | 0 – 600 | Médio (↑). Manutenção atrasada eleva risco mecânico. |
| `horas_operacao_dia` | contínua | horas | 0 – 16 | Médio (↑). Jornadas longas aumentam fadiga e desgaste. |
| `carga_pct` | contínua | % | 40 – 120 | Médio (↑). Sobrecarga agrava o risco em declives. |

## Variáveis categóricas

| Variável | Tipo | Valores possíveis | Impacto no risco |
|---|---|---|---|
| `tipo_solo` | categórica | Arenoso, Misto, Argiloso, Encharcado | **Alto**. Argiloso/Encharcado retêm água e elevam o risco. |
| `tipo_operacao` | categórica | Plantio, Pulverização, Colheita, Transporte | Médio. Colheita/Transporte (máquinas pesadas) puxam o risco para cima. |
| `periodo_dia` | categórica | Manhã, Tarde, Noite | Baixo. Operação noturna eleva levemente o risco. |

## Variável-alvo (o que o modelo aprende a prever)

| Variável | Tipo | Valores | Descrição |
|---|---|---|---|
| `houve_sinistro` | binária | 0 / 1 | Indica se a operação resultou em sinistro (atolamento, tombamento ou dano mecânico). É o **rótulo histórico** usado no treino supervisionado. |

## Saídas geradas pelo modelo (tabela `predicoes`)

| Campo | Tipo | Faixa | Descrição |
|---|---|---|---|
| `score_risco` | inteiro | 0 – 100 | Probabilidade de sinistro × 100. |
| `classe_risco` | categórica | Baixo / Médio / Alto / Crítico | Faixa derivada do score (ver abaixo). |
| `prob_sinistro` | contínua | 0 – 1 | Probabilidade bruta estimada pelo Random Forest. |
| `fator_1`, `fator_2`, `fator_3` | texto | — | As 3 variáveis que mais elevaram o risco da leitura (explicabilidade). |
| `modelo_versao` | texto | ex.: `rf-v1.0` | Versão do modelo que gerou a predição (rastreabilidade). |

## Faixas de risco (sistema de 4 níveis)

Inspirado no exemplo do enunciado (distância de corpos d'água: > 500 m baixo,
200–500 m médio, 50–200 m alto, < 50 m crítico), generalizamos para o **score**:

| Score | Classe | Ação |
|---|---|---|
| 0 – 25 | 🟢 Baixo | Operação liberada |
| 26 – 50 | 🟡 Médio | Operação com atenção |
| 51 – 75 | 🟠 Alto | Operação com restrições / supervisão |
| 76 – 100 | 🔴 Crítico | Operação não recomendada |
