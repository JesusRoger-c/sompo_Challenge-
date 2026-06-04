# 📊 Relatório de Validação Estatística — SomPrev Risk

Resultados **reais e reprodutíveis** (seed = 42) gerados por
[`src/scripts/treinar_modelo.py`](../src/scripts/treinar_modelo.py) sobre a base de
**6.000 leituras** ([`src/datasets/leituras_agricolas.csv`](../src/datasets/leituras_agricolas.csv)),
com **divisão treino/teste de 75%/25%** e **validação cruzada de 5 folds**.

> Transparência: estes números são os efetivamente produzidos pelo código deste
> repositório. Eles substituem quaisquer métricas ilustrativas anteriores.

## 1. Comparação de modelos

| Modelo | Acurácia | Precisão | Recall | F1 | ROC-AUC | AUC (CV) |
|---|---|---|---|---|---|---|
| Logistic Regression | 0,747 | 0,537 | 0,788 | 0,639 | 0,841 | 0,825 ± 0,014 |
| **Random Forest** ✅ | **0,841** | **0,772** | **0,621** | **0,688** | **0,862** | **0,848 ± 0,011** |
| Gradient Boosting | 0,828 | 0,739 | 0,607 | 0,667 | 0,865 | 0,849 ± 0,012 |

O **Random Forest** foi escolhido pela melhor acurácia e pela interpretabilidade
(importância de variáveis), com AUC estatisticamente empatado ao Gradient Boosting.
Veja a justificativa completa em [`document/modelo_preditivo.md`](modelo_preditivo.md).

Gráficos gerados: comparação de modelos (`src/models/comparacao_modelos.png`) e curva ROC
(`src/models/curva_roc.png`).

## 2. Matriz de confusão (Random Forest, conjunto de teste, n = 1.500)

|  | Previsto: Sem sinistro | Previsto: Com sinistro |
|---|---|---|
| **Real: Sem sinistro** | 997 (VN) | 78 (FP) |
| **Real: Com sinistro** | 161 (FN) | 264 (VP) |

Imagem: `src/models/matriz_confusao.png`.

Leitura: o modelo erra pouco ao liberar operações seguras (apenas 78 falsos
positivos) e ainda há espaço para reduzir os 161 falsos negativos — ver "ajuste de
limiar" na seção 5.

## 3. Validação mais importante: o score separa quem sofre sinistro?

Agrupando as leituras pela faixa de risco prevista e medindo a **taxa real de
sinistro** observada nos dados, obtemos uma separação fortíssima e **monotônica**:

| Faixa prevista | Leituras | Taxa real de sinistro |
|---|---|---|
| 🟢 Baixo | 3.740 | **1,8%** |
| 🟡 Médio | 636 | **15,3%** |
| 🟠 Alto | 703 | **90,3%** |
| 🔴 Crítico | 921 | **97,6%** |

Uma leitura classificada como Baixo tem ~1,8% de chance real de sinistro; uma Crítica,
~97,6%. Essa diferença de **mais de 50×** é a prova prática de que o score é confiável
para apoiar decisões — vale mais que a acurácia isolada. (Query em
[`src/database/queries.sql`](../src/database/queries.sql), consulta 6.)

## 4. Correlação das variáveis com o sinistro

| Variável | \|correlação\| com `houve_sinistro` |
|---|---|
| Umidade do solo | 0,317 |
| Proximidade de corpo d'água | 0,289 |
| Chuva 24h | 0,142 |
| Declividade do terreno | 0,098 |
| Horas desde a manutenção | 0,094 |

Como esperado, **umidade do solo** e **proximidade de água** são os fatores mais
correlacionados, coerentes com a literatura (ver
[`document/contextualizacao.md`](contextualizacao.md)). A importância de variáveis do
Random Forest (`src/models/importancia_variaveis.png`) e a matriz de correlação
(`src/models/matriz_correlacao.png`) confirmam o padrão.

> Observação: correlações lineares individuais são modestas **de propósito** — boa
> parte do sinal está em **interações** (ex.: solo encharcado + chuva), que o Random
> Forest captura e que não aparecem numa correlação simples. Isso explica por que o
> modelo atinge AUC 0,862 mesmo com correlações lineares na casa de 0,3.

## 5. Próximos passos de validação

- **Ajuste de limiar:** para um sistema de segurança, podemos baixar o limiar de
  decisão (hoje 0,5) para **aumentar o recall** (capturar mais sinistros), aceitando
  mais falsos positivos — um trade-off aceitável quando o custo de não alertar é alto.
- **Calibração de probabilidade** (ex.: *isotonic*/Platt) para que o score reflita
  ainda melhor a probabilidade real.
- **Validação com dados reais** de telemetria assim que disponíveis.

## Como reproduzir

```bash
pip install -r config/requirements.txt
python src/datasets/gerar_dataset.py     # gera as 6.000 leituras (seed 42)
python src/scripts/treinar_modelo.py     # treina, valida e salva métricas + gráficos
```
