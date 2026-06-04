# 🤖 Documentação da Inteligência Preditiva — AgroSentinela

Detalha a abordagem de IA, as entradas e saídas do modelo e a interpretação dos
resultados. Mantém a rastreabilidade prometida na Sprint 1.

Código de referência: [`src/scripts/treinar_modelo.py`](../src/scripts/treinar_modelo.py) e
[`src/scripts/risco_utils.py`](../src/scripts/risco_utils.py).

## 1. Tipo de problema

Aprendizado **supervisionado de classificação binária**: prever se uma operação
resultará em **sinistro** (`houve_sinistro` = 1) ou não (0). A **probabilidade**
estimada vira o **score de risco (0–100)**, que por sua vez é classificado em quatro
faixas (Baixo, Médio, Alto, Crítico).

## 2. Entradas do modelo (inputs)

12 variáveis — 9 numéricas e 3 categóricas — descritas em
[`document/variaveis.md`](variaveis.md). Resumo:

- **Ambientais:** umidade do solo, precipitação 24h, temperatura, declividade,
  distância de corpo d'água, tipo de solo.
- **Operacionais:** idade do equipamento, horas desde a manutenção, horas de operação
  no dia, carga, tipo de operação, período do dia.

Pré-processamento (via `ColumnTransformer`): **padronização** (StandardScaler) nas
numéricas e **One-Hot Encoding** nas categóricas.

## 3. Saídas do modelo (outputs)

| Saída | Descrição |
|---|---|
| `prob_sinistro` | probabilidade de sinistro (0–1) |
| `score_risco` | `prob_sinistro × 100`, inteiro de 0 a 100 |
| `classe_risco` | Baixo / Médio / Alto / Crítico |
| `fator_1/2/3` | as 3 variáveis que mais elevaram o risco (explicabilidade) |
| recomendação | texto de ação por faixa (liberado → não recomendado) |
| alerta | gerado automaticamente para Alto/Crítico |

## 4. Algoritmo escolhido: Random Forest

Comparamos três algoritmos supervisionados (resultados reais em
[`document/relatorio_validacao.md`](relatorio_validacao.md)):

| Modelo | Acurácia | AUC | Observação |
|---|---|---|---|
| Logistic Regression | 0,747 | 0,841 | baseline linear; recall alto, precisão baixa |
| **Random Forest** ✅ | **0,841** | **0,862** | melhor acurácia + interpretável |
| Gradient Boosting | 0,828 | 0,865 | desempenho quase idêntico ao RF |

**Justificativa técnica:**
- Captura **relações não-lineares e interações** entre variáveis (ex.: solo
  encharcado **e** chuva forte), sem precisarmos criá-las manualmente — algo que a
  Regressão Logística não faz, e que explica a vantagem do RF sobre ela.
- Lida bem com variáveis numéricas e categóricas em escalas diferentes.
- É **robusto a outliers** e reduz overfitting via *bagging* (300 árvores).
- Fornece **importância de variáveis**, sustentando a explicabilidade exigida pelas
  personas Gestor e Seguradora.
- Entrega a **maior acurácia** do comparativo e empata em AUC com o Gradient Boosting,
  com a vantagem de ser mais simples de interpretar.

> O Gradient Boosting (e o XGBoost, sua variante mais conhecida) teve desempenho
> praticamente idêntico e fica registrado como **alternativa natural para produção**.
> Optamos pelo Random Forest nesta etapa pelo equilíbrio entre desempenho,
> interpretabilidade e simplicidade.

## 5. Como o score é interpretado

O score não é só um número: cada predição vem acompanhada dos **três principais
fatores** que a empurraram para cima. Assim, um score 82 não diz apenas "perigo", mas
"perigo **porque** a água está a 30 m, o solo está encharcado e o tipo de solo é
desfavorável". Isso transforma a IA em apoio à decisão, não em caixa-preta.

## 6. Governança do modelo

- Cada predição registra a **versão do modelo** (`rf-v1.0`) na tabela `predicoes`.
- O modelo treinado é serializado em [`src/models/modelo_risco.pkl`](../src/models/) e as
  métricas em [`src/models/metricas.json`](../src/models/), permitindo auditoria e
  reprodutibilidade (seed fixa = 42 em todo o pipeline).
