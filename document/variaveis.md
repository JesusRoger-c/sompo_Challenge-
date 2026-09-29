# 🧾 Dicionário de Variáveis — SomPrev Risk

Este documento descreve **todas as variáveis** usadas pelo modelo preditivo, com
**tipo, unidade, faixa típica e impacto no risco**. Ele substitui a antiga seção
"Variáveis Utilizadas" e atende ao ponto do feedback da Sprint 1.

As variáveis são geradas pelo simulador [`src/somprev/dados/gerador.py`](../src/somprev/dados/gerador.py),
validadas pelo **contrato de dados** [`src/somprev/esquema.py`](../src/somprev/esquema.py) e persistidas
na tabela `leituras` ([`src/database/schema.sql`](../src/database/schema.sql)).

## Contrato de dados (Sprint 4)

Cada variável tem uma **faixa física aceita**. Um valor fora dela é defeito de sensor: vira ausente e
segue a política de imputação. Variáveis **críticas** sem valor (e sem como imputar) levam a leitura
para a **quarentena**.

| Variável | Faixa aceita | Crítica? | Se ausente |
|---|---|:---:|---|
| `umidade_solo_pct` | 0 – 100 | sim | mediana da região no dia |
| `precipitacao_24h_mm` | 0 – 400 | sim | mediana da região no dia |
| `temperatura_c` | -10 – 55 | não | mediana da região no dia |
| `declividade_graus` | 0 – 60 | sim | **quarentena** (depende do talhão) |
| `distancia_corpo_dagua_m` | 0 – 5000 | sim | **quarentena** (depende do talhão) |
| `idade_equipamento_anos` | 0 – 50 | não | recalculada pelo **cadastro** (também corrige divergências) |
| `horas_desde_manutencao` | 0 – 3000 | não | último valor do equipamento |
| `horas_operacao_dia` | 0 – 24 | não | último valor do equipamento |
| `carga_pct` | 0 – 150 | não | último valor do equipamento |
| `tipo_solo` | 4 categorias | sim | **quarentena** |
| `tipo_operacao` | 4 categorias | sim | **quarentena** |
| `periodo_dia` | 3 categorias | não | derivado do horário da leitura |

Grafias alternativas são padronizadas ("Manhã", " MANHA " → `Manha`; "pulverização" → `Pulverizacao`),
e números com vírgula decimal ("55,3") são convertidos.

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
| `prob_sinistro` | contínua | 0 – 1 | Probabilidade **calibrada** estimada pelo modelo (HistGradientBoosting). |
| `fator_1`, `fator_2`, `fator_3` | texto | — | As 3 variáveis que mais elevaram o risco **segundo o próprio modelo**. |
| `explicacao_json` | JSON | — | Contribuição (em pontos de score) de cada uma das 12 variáveis. |
| `modelo_versao` | texto | ex.: `hgb-v2.0` | Versão do modelo que gerou a predição (rastreabilidade). |
| `regras_versao` | texto | ex.: `regras-v2.0` | Versão das regras (faixas/limiar/gatilhos) usada na decisão. |

## Faixas de risco (sistema de 4 níveis) — revisadas na Sprint 4

Com o score calibrado (score ≈ probabilidade real × 100), os cortes passaram a ter significado
probabilístico. Eles ficam em [`config/regras_risco.json`](../config/regras_risco.json) e podem ser
ajustados pelo Gestor (cada ajuste gera uma nova versão).

| Score | Classe | Ação | Sinistros reais no teste |
|---|---|---|---:|
| 0 – 14 | 🟢 Baixo | Operação liberada | 4,9% |
| 15 – 39 | 🟡 Médio | Operação com atenção (alerta ao operador) | 19,0% |
| 40 – 69 | 🟠 Alto | Operação com restrições / supervisão | 54,5% |
| 70 – 100 | 🔴 Crítico | Operação não recomendada | 93,2% |

O corte 15 é o **limiar de alerta de menor custo** (ver [`modelo_preditivo.md`](modelo_preditivo.md)).
Nas Sprints 2 e 3 os cortes eram 25/50/75 (quartos iguais do score).
