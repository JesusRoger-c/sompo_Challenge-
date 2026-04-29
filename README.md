# 🎓 FIAP - Faculdade de Informática e Administração Paulista

# 🚜 Challenge Sompo

## 🌱 Sistema Preditivo de Risco Agrícola

<p align="center">
<a href="https://www.fiap.com.br/">
<img src="assets/logo-fiap.png" alt="FIAP" width="40%">
</a>
</p>

---

## 👨‍🎓 Integrantes

* Felipe de Sá Gomes Bruno
* Karina Garta Szewczuk
* Maria Sabrina Feitosa da Silva
* Nicolas Lima Apolinário
* Roger Gabriel de Souza Jesus Costa

---

## 👩‍🏫 Professores

### 📚 Tutora

* Sabrina Otoni

### 🎯 Coordenador

* André Godói

---

## 📜 Descrição

## ⚠️ Problema

Equipamentos agrícolas operam em ambientes com alta exposição a riscos 🌧️🌱, principalmente em condições adversas como:

* Solo úmido
* Proximidade com água
* Variações climáticas

Atualmente, muitas decisões são tomadas de forma **reativa**, ou seja, após incidentes como:

* Atolamentos 🚜
* Colisões 💥
* Falhas mecânicas ⚙️

Isso gera:

* 💸 Prejuízos financeiros
* ⏱️ Perda de produtividade
* ⚠️ Riscos à segurança

👉 Surge então a necessidade de uma solução capaz de **antecipar riscos e apoiar decisões preventivas**.

---

## 💡 Solução Proposta

Desenvolvimento de um **sistema inteligente baseado em dados e IA 🤖** capaz de prever riscos antes da operação agrícola.

### 🔍 O sistema será capaz de:

* Identificar padrões de risco
* Gerar alertas preventivos 🚨
* Oferecer recomendações práticas
* Apresentar dashboards 📊 e relatórios

---

### 📤 Saídas do Sistema

* 🎯 Score de risco (baixo, médio, alto)
* 🚨 Alertas em tempo real
* 📌 Recomendações de ação
* 📊 Relatórios por região/operação

---

## 👥 Perfis de Usuário

### 🚜 Operador

* Atua diretamente com o equipamento
* Precisa saber se é seguro operar
* Recebe alertas antes da execução

### 📊 Gestor

* Responsável pela operação
* Busca reduzir custos e evitar perdas
* Analisa relatórios e riscos

### 🏢 Seguradora

* Avalia riscos operacionais
* Prevê possíveis prejuízos
* Apoia decisões estratégicas

---

## 🗂️ Estruturação dos Dados

A solução utiliza variáveis ambientais e operacionais para prever riscos.

### 📊 Exemplo de Dataset

| chuva_24h | tipo_solo | umidade | proximidade_agua | tipo_operacao | historico_falha | risco |
| --------- | --------- | ------- | ---------------- | ------------- | --------------- | ----- |
| alta      | argila    | alta    | sim              | campo         | sim             | alto  |
| baixa     | areia     | baixa   | não              | transporte    | não             | baixo |

---

### 🧾 Variáveis

* chuva_24h: nível de chuva nas últimas 24h 🌧️
* tipo_solo: classificação do solo
* umidade: nível de umidade
* proximidade_agua: presença de água
* tipo_operacao: campo ou transporte
* historico_falha: ocorrências anteriores
* risco: saída do modelo

---

## 🤖 Modelo Preditivo (IA)

Modelo de classificação capaz de prever o nível de risco.

### 📥 Entradas

* Dados climáticos
* Condições do solo
* Tipo de operação
* Localização
* Histórico

### 📤 Saída

* Classificação de risco:

  * 🟢 Baixo
  * 🟡 Médio
  * 🔴 Alto

### ⭐ Diferencial

O modelo explica **quais fatores influenciam o risco**, aumentando a transparência e a confiança.

---

## 🏗️ Arquitetura da Solução

### 🔄 Fluxo do Sistema

Coleta de Dados 🌐
↓
Armazenamento 💾
↓
Processamento ⚙️
↓
Modelo de IA 🤖
↓
Geração de Insights 📊
↓
Interface (Dashboard / Alertas) 📱

---

### 🧩 Componentes

* Entrada: APIs, sensores ou dados simulados
* Processamento: tratamento dos dados
* IA: modelo preditivo
* Saída:

  * Alertas 🚨
  * Dashboard 📊
  * Relatórios 📄

---

## ⚙️ Funcionalidades

* 📊 Dashboard por equipamento/operação
* 🚨 Alertas preventivos
* 📌 Recomendações inteligentes
* 📄 Relatórios por período/região
* ⚙️ Configuração de limites de risco

---

## 🔗 Atendimento às User Stories

| Necessidade        | Solução                   |
| ------------------ | ------------------------- |
| Visualizar risco   | Dashboard com score       |
| Entender causas    | Explicação dos fatores    |
| Receber alertas    | Alertas preventivos       |
| Melhorar decisões  | Recomendações automáticas |
| Analisar histórico | Relatórios                |
| Facilidade de uso  | Interface simples         |
| Configurar regras  | Limites de risco          |

---

## 🗓️ Próximas Etapas

### 🚀 Sprint 2

* Dataset
* Modelo de IA
* Testes iniciais

### 🚀 Sprint 3

* Dashboard
* Integração

### 🚀 Sprint 4

* Ajustes finais
* Validação

---

## 🧑‍💻 Divisão de Tarefas

* Roger: Dados e dataset
* Maria Sabrina: IA
* Karina: Arquitetura
* Nicolas: Documentação e apresentação

---

# 🎥 Vídeo Demonstrativo

📌 Link do vídeo: *        *


## 📝 Considerações Finais

A solução proposta busca **transformar a gestão de riscos agrícolas 🌱**, promovendo:

* Mais segurança
* Redução de custos
* Maior eficiência operacional

Tudo isso através do uso de **dados + Inteligência Artificial 🤖📊**.

---

