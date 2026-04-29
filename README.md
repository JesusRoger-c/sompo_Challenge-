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

- Karina Garta Szewczuk  RM569309
- Maria Sabrina Feitosa da Silva  RM568714
- Nicolas Lima Apolinário  RM570741
- Roger Gabriel de Souza Jesus Costa  RM573659

---

## 👩‍🏫 Professores  

### Tutora  
- Sabrina Otoni  

### Coordenador  
- André Godói  

---

## 📜 Descrição  

## ⚠️ Problema  

A operação de equipamentos agrícolas ocorre em ambientes altamente variáveis e imprevisíveis. Fatores como clima, tipo de solo, umidade e proximidade com recursos hídricos impactam diretamente a segurança e a eficiência das atividades.

Atualmente, a tomada de decisão é predominantemente **reativa**, ou seja, ações são tomadas apenas após a ocorrência de incidentes, como:

- Atolamento de máquinas 🚜  
- Colisões em terrenos irregulares 💥  
- Falhas mecânicas em condições adversas ⚙️  

Esse cenário gera impactos relevantes:

- 💸 Aumento de custos operacionais  
- ⏱️ Redução da produtividade  
- ⚠️ Riscos à segurança dos operadores  
- 📉 Baixa previsibilidade de perdas  

Além disso, existe uma subutilização de dados que já estão disponíveis, mas que não são integrados de forma estruturada para apoiar decisões.

Diante disso, torna-se necessário um sistema capaz de **antecipar riscos e apoiar decisões preventivas**.

---

## 💡 Solução Proposta  

A proposta consiste no desenvolvimento de um **sistema preditivo de risco agrícola**, baseado em análise de dados e Inteligência Artificial.

O sistema será responsável por transformar dados ambientais e operacionais em informações acionáveis, permitindo a identificação antecipada de riscos.

### 🔍 Principais capacidades

- Análise integrada de múltiplas variáveis  
- Classificação do nível de risco antes da operação  
- Geração de alertas preventivos 🚨  
- Recomendações baseadas em dados históricos  
- Visualização por meio de dashboards 📊 e relatórios  

---

## 📤 Saídas do Sistema  

- 🎯 Score de risco (baixo, médio, alto)  
- 🚨 Alertas preventivos  
- 📌 Recomendações operacionais  
- 📊 Relatórios analíticos por região e período  

---

## 👥 Personas  

### 🚜 Operador  
Responsável pela execução das atividades. Necessita de informações rápidas para decidir se deve operar.

### 📊 Gestor  
Responsável pelo planejamento e acompanhamento. Busca reduzir custos e otimizar operações.

### 🏢 Seguradora  
Focada na avaliação de riscos e previsibilidade de prejuízos.

---

## 🗂️ Estruturação dos Dados  

A solução é baseada na análise de variáveis ambientais e operacionais.

### 📊 Exemplo de Dataset  

| chuva_24h | tipo_solo | umidade | proximidade_agua | tipo_operacao | historico_falha | risco |
|----------|----------|--------|------------------|--------------|----------------|------|
| alta     | argila   | alta   | sim              | campo        | sim            | alto |
| baixa    | areia    | baixa  | não              | transporte   | não            | baixo |

### 🧾 Variáveis  

- **chuva_24h**: precipitação recente  
- **tipo_solo**: classificação do solo  
- **umidade**: nível de umidade  
- **proximidade_agua**: presença de água próxima  
- **tipo_operacao**: tipo de atividade  
- **historico_falha**: registros anteriores  
- **risco**: variável alvo  

---

## 🤖 Modelo Preditivo  

Será utilizado um modelo de classificação supervisionada.

### 📥 Entradas  

- Dados climáticos  
- Condições do solo  
- Tipo de operação  
- Localização  
- Histórico  

### 📤 Saída  

Classificação do risco em:

- 🟢 Baixo  
- 🟡 Médio  
- 🔴 Alto  

### ⭐ Diferencial  

O modelo será interpretável, permitindo identificar os fatores que influenciam cada previsão.

---

## 🏗️ Arquitetura da Solução  

### 🔄 Fluxo  

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

### 🧩 Componentes  

- Entrada: APIs, sensores ou dados simulados  
- Processamento: limpeza e transformação dos dados  
- Modelo: responsável pelas previsões  
- Saída: dashboards 📊, alertas 🚨 e relatórios  

---

## ⚙️ Funcionalidades  

- 📊 Dashboard por operação ou equipamento  
- 🚨 Alertas preventivos  
- 📌 Recomendações automáticas  
- 📄 Relatórios por período e região  
- ⚙️ Configuração de limites de risco  

---

## 🔗 Atendimento às User Stories  

| Necessidade        | Solução                   |
|------------------|--------------------------|
| Visualizar risco   | Dashboard com score       |
| Entender causas    | Explicação dos fatores    |
| Receber alertas    | Alertas preventivos       |
| Melhorar decisões  | Recomendações automáticas |
| Analisar histórico | Relatórios                |
| Facilidade de uso  | Interface intuitiva       |
| Configurar regras  | Limites de risco          |

---

## 🗓️ Próximas Etapas  

### 🚀 Sprint 2 — Estruturação e Modelagem  

- Criação e organização do dataset  
- Tratamento e padronização dos dados  
- Treinamento inicial do modelo  
- Validação preliminar  

---

### 🚀 Sprint 3 — Desenvolvimento e Integração  

- Desenvolvimento do dashboard 📊  
- Integração entre modelo e interface  
- Implementação de alertas 🚨  
- Testes de usabilidade  

---

### 🚀 Sprint 4 — Refinamento e Validação  

- Otimização do modelo  
- Testes com cenários mais complexos  
- Ajustes de interface  
- Documentação final  
- Preparação para apresentação  

---

## 🧑‍💻 Divisão de Tarefas  

- Roger: Dados e dataset  
- Maria Sabrina: Modelo de IA  
- Karina: Arquitetura  
- Nicolas: Documentação e apresentação  

---

## 🎥 Vídeo Demonstrativo  

Link: [Chanllenge Sompo  ](https://youtu.be/hF9JeH9Zwjk)

---

## 🗃 Histórico de lançamentos

* 0.1.0 - 29/04/2024
  
    *Lancamento do Planejamento

---

## 📝 Considerações Finais  

A solução proposta busca transformar a gestão de risco agrícola, migrando de um modelo reativo para um modelo preditivo.

Os principais benefícios esperados são:

- 💰 Redução de custos  
- 🛡️ Aumento da segurança  
- 📈 Melhoria na tomada de decisão  
- 🔍 Maior previsibilidade operacional

O uso de dados e Inteligência Artificial permite gerar valor estratégico para operadores, gestores e seguradoras.



## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
