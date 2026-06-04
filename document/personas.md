# 👥 Personas — AgroSentinela

As personas abaixo aprofundam **contexto, dores e cenário prático de uso**,
atendendo ao feedback da Sprint 1. Cada persona está conectada a uma **visão
específica do dashboard** ([`src/dashboards/preview_dashboard.html`](../src/dashboards/preview_dashboard.html)),
reforçando o foco na experiência do usuário.

---

## 🚜 João Batista — Operador Agrícola
**42 anos · Mato Grosso · 18 anos de experiência · maturidade digital baixa**

**Contexto.** João opera tratores e colheitadeiras há quase duas décadas. Conhece o
campo "de cor", mas decide pela intuição: olha o céu, sente o solo e segue. Usa um
celular simples e desconfia de telas cheias de gráficos.

**Dores.**
- Não tem previsibilidade das condições do solo antes de entrar no talhão.
- Já ficou atolado em períodos de chuva intensa, parando a operação por horas.
- Sofre pressão por produtividade e teme errar a decisão.

**Cenário prático de uso.** São 6h. Antes de ligar a máquina, João abre o app e vê um
**semáforo grande**: para o equipamento EQ-009 o score está **82 — vermelho, "Operação
não recomendada"**, porque a água está a 30 m, o solo está encharcado e choveu na
véspera. Em vez de arriscar, ele aciona o supervisor e troca de talhão. Sem jargão,
sem gráfico — só a cor, o número e o que fazer.

**Visão do dashboard.** Aba **Operador**: semáforo, leitura dos sensores, recomendação
direta e os 3 fatores que explicam o risco.

**Benefícios.** Mais segurança, menos incidentes e confiança para decidir.

---

## 📊 Fernanda Almeida — Gestora de Frota Agrícola
**36 anos · 10 anos em gestão operacional · maturidade digital média**

**Contexto.** Fernanda coordena dezenas de máquinas espalhadas por várias regiões.
Cada parada vira prejuízo, e ela precisa enxergar o todo para planejar manutenção,
deslocamento e prioridades — hoje, com planilhas dispersas.

**Dores.**
- Alto custo com incidentes e máquinas paradas.
- Dificuldade de monitorar regiões diferentes ao mesmo tempo.
- Falta de previsibilidade para planejar a semana.

**Cenário prático de uso.** Na segunda de manhã, Fernanda abre o painel e vê que
**Sorriso (MT)** lidera o risco médio e que há **1.624 leituras em risco Alto/Crítico**.
No ranking, **EQ-017** aparece com mais leituras críticas — ela agenda manutenção
preventiva antes que vire pane. Na curva de tendência, percebe um pico de risco
chegando com a frente de chuva e antecipa o replanejamento das rotas.

**Visão do dashboard.** Aba **Gestor**: KPIs da frota, mapa de calor por região,
ranking de equipamentos, distribuição por faixa e tendência de 14 dias.

**Benefícios.** Redução de custos, melhor planejamento e mais produtividade.

---

## 🏢 Ricardo Mendes — Analista de Risco da Seguradora (Sompo)
**39 anos · seguradora agrícola · maturidade digital alta**

**Contexto.** Ricardo precifica apólices e avalia carteiras. Trabalha com grandes
volumes e exige rastreabilidade: toda decisão tem de ser auditável e baseada em
evidência, não em achismo.

**Dores.**
- Baixa previsibilidade dos sinistros e dados inconsistentes.
- Pouca rastreabilidade operacional para auditoria.
- Dificuldade de justificar preço/risco com base sólida.

**Cenário prático de uso.** Ricardo abre a visão da seguradora e confirma a **eficácia
do score**: leituras de risco Baixo viraram sinistro em apenas **1,8%** dos casos, e as
de risco Crítico em **97,6%** — uma separação que sustenta decisões de subscrição. Em
seguida, consulta a **trilha de auditoria**, onde cada alerta registra equipamento,
score, fatores e **versão do modelo (rf-v1.0)**, garantindo reprodutibilidade.

**Visão do dashboard.** Aba **Seguradora**: validação por faixa de risco, causas
predominantes e trilha de auditoria com versionamento.

**Benefícios.** Melhor auditoria, decisões mais rápidas e maior confiabilidade dos dados.
