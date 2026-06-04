# 🎓 FIAP - Faculdade de Informática e Administração Paulista

# 🚜 Challenge Sompo Seguros

# 🌱 Sistema Preditivo de Risco Agrícola

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="assets/logo-fiap.png" alt="FIAP" width="40%">
  </a>
</p>

---

# 🌱 AgroSentinela — Sistema Preditivo de Risco Agrícola

### 🎓 FIAP — Faculdade de Informática e Administração Paulista · 🚜 Challenge Sompo Seguros

Inteligência preditiva que transforma a gestão de risco de frotas agrícolas de uma
atuação **reativa** para **preventiva**, gerando um **score de risco (0–100)** por
equipamento/região, **alertas automáticos** e **recomendações acionáveis** — com foco
total na experiência de três personas: operador, gestor e seguradora.

---

## 👨‍🎓 Integrantes

| Integrante | RM |
|---|---|
| Karina Garta Szewczuk | RM569309 |
| Maria Sabrina Feitosa da Silva | RM568714 |
| Nicolas Lima Apolinário | RM570741 |
| Roger Gabriel de Souza Jesus Costa | RM573659 |

**👩‍🏫 Tutora:** Sabrina Otoni · **Coordenador:** André Godói

---

## 🎥 Vídeo demonstrativo

📌 **Link do vídeo (não listado):** _adicionar aqui o link do YouTube_

---

## 🔎 O que evoluiu desde a Sprint 1

Esta entrega sai do plano conceitual e passa para a **implementação funcional ponta a
ponta**. Em resposta direta ao feedback recebido:

| Ponto do feedback | O que fizemos nesta Sprint |
|---|---|
| Personas em uma linha | Aprofundamos contexto, dor e **cenário prático de uso** → [`docs/personas.md`](docs/personas.md) |
| Dataset com poucas linhas | Geramos **6.000 leituras** + 10 cenários curados, com **dicionário completo de variáveis** → [`docs/variaveis.md`](docs/variaveis.md) |
| Arquitetura só textual | Criamos um **diagrama de arquitetura** com dispositivos, integrações e componentes (abaixo) |
| Algoritmo sem justificativa | **Random Forest** comparado a Logistic Regression e Gradient Boosting, com inputs/outputs estruturados → [`docs/modelo_preditivo.md`](docs/modelo_preditivo.md) |
| Contexto sem dados/fontes | Adicionamos **números de mercado, sinistralidade e fontes referenciadas** → [`docs/contextualizacao.md`](docs/contextualizacao.md) |
| Métricas sem evidência | Substituímos por **métricas reais e reprodutíveis** geradas pelo código → [`docs/relatorio_validacao.md`](docs/relatorio_validacao.md) |

---

## 🌎 Contextualização (resumo)

O seguro rural brasileiro cobriu cerca de **6,3 milhões de hectares** e **~R$ 45 bilhões**
em valor segurado em 2024 (Mapa/Agência Gov). Ao mesmo tempo, o Brasil tem o **maior
número de fatalidades com tratores** do mundo — cerca de **3 mil mortes/ano** (Canal
Rural) — e um estudo no RS aponta que **96,8% desses acidentes seriam evitáveis por
prevenção** (Tecno-Lógica, 2021). Esse é exatamente o espaço da nossa solução.
Detalhes e fontes em [`docs/contextualizacao.md`](docs/contextualizacao.md).

---

## 🏗️ Arquitetura da Solução

![Arquitetura do AgroSentinela](docs/arquitetura.png)

**Fluxo:** Sensores/APIs → Gateway de borda → Ingestão/ETL (Python) → Banco SQL →
Motor de IA (Random Forest) → Score/Alertas → Dashboards por persona.

- **Campo (coleta):** sensores de umidade do solo, GPS (distância de corpos d'água),
  inclinômetro (declividade), horímetro/carga e **API de clima externa**.
- **Conectividade:** gateway LoRaWAN/4G + coletor MQTT.
- **Nuvem:** ETL em Python, banco relacional SQL e o motor de IA.
- **Aplicação:** app do operador (semáforo), dashboard do gestor, portal da seguradora
  e o motor de alertas.

> O diagrama é gerado por [`docs/_gerar_arquitetura.py`](docs/_gerar_arquitetura.py)
> (saídas: `docs/arquitetura.svg` e `docs/arquitetura.png`).

---

## 🤖 Modelo Preditivo (resumo)

Problema de **classificação binária supervisionada** (`houve_sinistro`); a
probabilidade vira o **score 0–100**, classificado em 4 faixas.

| Faixa | Score | Ação |
|---|---|---|
| 🟢 Baixo | 0–25 | Operação liberada |
| 🟡 Médio | 26–50 | Operação com atenção |
| 🟠 Alto | 51–75 | Operação com restrições / supervisão |
| 🔴 Crítico | 76–100 | Operação não recomendada |

**Algoritmo escolhido: Random Forest** (300 árvores). Justificativa: captura
interações não-lineares (ex.: solo encharcado **+** chuva), lida com variáveis mistas,
é robusto e **interpretável** (importância de variáveis → explicabilidade). Comparação
completa em [`docs/modelo_preditivo.md`](docs/modelo_preditivo.md).

---

## 📈 Resultados reais (validação)

Base de **6.000 leituras**, split 75/25, validação cruzada de 5 folds. **Métricas reais
do código** (seed 42):

| Modelo | Acurácia | Precisão | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0,747 | 0,537 | 0,788 | 0,639 | 0,841 |
| **Random Forest** ✅ | **0,841** | **0,772** | **0,621** | **0,688** | **0,862** |
| Gradient Boosting | 0,828 | 0,739 | 0,607 | 0,667 | 0,865 |

**Prova de eficácia — o score separa quem sofre sinistro?** Taxa real de sinistro por
faixa prevista:

| Faixa | 🟢 Baixo | 🟡 Médio | 🟠 Alto | 🔴 Crítico |
|---|---|---|---|---|
| Sinistro real | **1,8%** | **15,3%** | **90,3%** | **97,6%** |

Uma diferença de **mais de 50×** entre as pontas. Relatório completo (matriz de
confusão, correlações, gráficos) em [`docs/relatorio_validacao.md`](docs/relatorio_validacao.md).

---

## 📱 Dashboards por persona

Front-end funcional com três visões sob medida (prints em [`docs/prints/`](docs/prints/)):

| Persona | Visão | Destaque |
|---|---|---|
| 🚜 Operador | semáforo + recomendação | número grande e ação clara, sem jargão |
| 📊 Gestor | mapa de calor + ranking + KPIs + tendência | onde agir na frota |
| 🏢 Seguradora | validação + trilha de auditoria | rastreabilidade e versionamento |

![Visão do Operador](docs/prints/dashboard_operador.png)

Há duas formas de visualizar:
- **Protótipo estático:** abra [`dashboards/preview_dashboard.html`](dashboards/preview_dashboard.html) no navegador.
- **App funcional (lê o banco ao vivo):** `streamlit run dashboards/app.py`.

---

## 🗄️ Banco de Dados

Modelo **relacional** com 5 tabelas e histórico auditável
([`database/schema.sql`](database/schema.sql)):

`regioes` · `equipamentos` · `leituras` (telemetria) · `predicoes` (score, classe,
fatores, **versão do modelo**) · `alertas`.

Consultas analíticas prontas em [`database/queries.sql`](database/queries.sql)
(risco por região, ranking da frota, alertas abertos, tendência, validação do modelo,
faixas de distância da água).

---

## ▶️ Como executar

```bash
# 1) Instalar dependências
pip install -r requirements.txt

# 2) Gerar o dataset (6.000 leituras, seed 42)
python datasets/gerar_dataset.py

# 3) Treinar o modelo, validar e gerar gráficos + métricas
python scripts/treinar_modelo.py

# 4) Criar e popular o banco (roda o modelo e gera predições/alertas)
python scripts/popular_banco.py

# 5a) Abrir o dashboard estático
#     abra dashboards/preview_dashboard.html no navegador
# 5b) Ou rodar o app funcional
streamlit run dashboards/app.py
```

---

## 📂 Estrutura do Repositório

```
.
├── README.md
├── requirements.txt
├── datasets/
│   ├── gerar_dataset.py          # gerador sintético (seed 42)
│   ├── leituras_agricolas.csv    # base completa (6.000 linhas)
│   └── dataset_exemplo.csv       # 10 cenários curados
├── scripts/
│   ├── risco_utils.py            # faixas, recomendações, explicabilidade
│   ├── treinar_modelo.py         # treino + validação + gráficos
│   └── popular_banco.py          # cria/popula o banco e roda predições
├── models/
│   ├── modelo_risco.pkl          # modelo treinado
│   ├── metricas.json             # métricas reais
│   └── *.png                     # matriz de confusão, ROC, importância, etc.
├── database/
│   ├── schema.sql                # esquema relacional (5 tabelas)
│   ├── queries.sql               # 7 consultas analíticas
│   └── agrosentinela.db          # banco SQLite populado
├── dashboards/
│   ├── preview_dashboard.html    # protótipo estático (3 personas)
│   └── app.py                    # app Streamlit funcional
└── docs/
    ├── personas.md               # personas aprofundadas
    ├── variaveis.md              # dicionário de variáveis
    ├── contextualizacao.md       # dados + fontes
    ├── modelo_preditivo.md       # inteligência preditiva
    ├── relatorio_validacao.md    # validação estatística
    ├── arquitetura.svg / .png    # diagrama de arquitetura
    └── prints/                   # capturas de tela dos dashboards
```

---

## 🔐 Segurança e Governança

Controle de acesso por perfil (operador/gestor/seguradora), validação de integridade
na ingestão, **versão do modelo registrada em cada predição** (rastreabilidade) e
histórico para auditoria.

---

## ⚙️ Tecnologias

Python · Pandas · NumPy · scikit-learn · Matplotlib/Seaborn · SQL (SQLite) ·
Streamlit · GitHub.

---

## 🧑‍💻 Divisão de Tarefas

| Integrante | Responsabilidade |
|---|---|
| Roger | Dados e dataset |
| Maria Sabrina | Modelo de IA |
| Karina | Arquitetura |
| Nicolas | Documentação e apresentação |

---

## 🗃️ Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 0.1.0 | 29/04/2026 | Estrutura inicial do projeto |
| 0.2.0 | 19/05/2026 | Integração da Sprint 2 |
| 0.3.0 | — | Implementação funcional ponta a ponta (IA + SQL + dashboards) |

---

## 📄 Licença

Projeto acadêmico desenvolvido para fins educacionais no Challenge FIAP + Sompo Seguros.
Dados operacionais **simulados** (uso permitido pelo enunciado). MODELO GIT FIAP por
FIAP, licenciado sob Attribution 4.0 International.
