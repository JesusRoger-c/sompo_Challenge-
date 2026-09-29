# 👥 Personas — SomPrev Risk

As personas abaixo aprofundam **contexto, dores e cenário prático de uso**.
Cada persona tem um **perfil de acesso e uma visão própria** no dashboard
([`src/somprev/dashboard/app.py`](../src/somprev/dashboard/app.py)). Na Sprint 4 entrou a
quarta persona, o **Técnico de manutenção**, citado no enunciado final.

> Os números citados nos cenários vêm da base simulada da Sprint 4.

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

**Cenário prático de uso.** São 7h30 em Cascavel (PR). Antes de entrar no talhão, João abre
o app e vê um **semáforo grande**: a colheitadeira EQ-021 está com score **97, "Risco Crítico",
operação não recomendada**. O gráfico "por que esse score?" mostra que a umidade do solo (88%)
e a distância da água (140 m) explicam a maior parte do risco, e a recomendação diz o que fazer:
*priorize talhões com solo mais seco; mantenha distância de rios e represas*. Ele marca o alerta
como "reconhecido" e troca de talhão. Sem jargão: só a cor, o número, o porquê e o que fazer.

**Visão do dashboard.** Perfil **Operador**: semáforo, recomendação com ações, contribuição de
cada fator, leitura dos sensores, alertas ativos do equipamento e histórico recente do score.

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

**Cenário prático de uso.** Na segunda de manhã, Fernanda abre o painel. A tendência semanal
mostra que o risco **caiu no Cerrado** (estação seca) e está **subindo em Não-Me-Toque (RS)**
com as chuvas de inverno. Os insights automáticos apontam a **Colheita** como a operação de maior
risco e a distância da água como principal causa. Ela desloca duas colheitadeiras para talhões mais
secos e, na aba **Regras**, registra (com justificativa) um ajuste no gatilho de manutenção.

**Visão do dashboard.** Perfil **Gestor**: KPIs, tendências por região, operação e tipo de
equipamento, mapa região × operação, ranking da frota, alertas com ciclo de vida, edição
versionada das regras e exportação de relatórios.

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

**Cenário prático de uso.** Ricardo abre a visão da seguradora e confirma a **eficácia do
score em dados nunca vistos pelo modelo** (agosto): leituras de risco Baixo viraram sinistro em
**4,9%** dos casos e as de risco Crítico em **93,2%**. O modelo antecipa **82% dos sinistros**,
contra 49% na receita da Sprint 3. Em seguida, clica em **Verificar integridade da auditoria**:
a cadeia de hashes confirma que nenhum evento foi alterado, e cada predição traz a **versão do
modelo (hgb-v2.0) e das regras**.

**Visão do dashboard.** Perfil **Seguradora**: validação do modelo (métricas, calibração, taxa
real por faixa, comparação com a Sprint 3, model card), carteira por região, trilha de auditoria
com verificação criptográfica e painel de qualidade dos dados.

**Benefícios.** Melhor auditoria, decisões mais rápidas e maior confiabilidade dos dados.

---

## 🔧 Carlos Pereira: Técnico de Manutenção (Sprint 4)
**45 anos · oficina da cooperativa · maturidade digital média**

**Contexto.** Carlos cuida da manutenção de toda a frota. Hoje ele descobre que uma máquina
precisa de revisão quando ela quebra no campo, ou por uma planilha desatualizada.

**Dores.**
- Não sabe quais máquinas estão com a revisão vencida sem ligar para cada operador.
- Recebe pedidos de manutenção sem prioridade clara.
- Não tem registro confiável do que foi feito em cada equipamento.

**Cenário prático de uso.** Carlos abre a **fila de manutenção preventiva**. No topo está o EQ-037,
um trator de 21 anos com 590 h desde a última revisão (intervalo de 738 h), com os alertas
"Manutenção vencida" (`Horas desde a última manutenção ≥ 450`) e "Desgaste acumulado"
(`Idade ≥ 15 e horas ≥ 300`). Ele faz a revisão e registra o serviço no próprio painel. Os alertas
de manutenção do equipamento são resolvidos automaticamente, com tudo registrado na auditoria.

**Visão do dashboard.** Perfil **Técnico**: fila priorizada (fórmula de prioridade explícita),
horas desde a manutenção × limite, alertas de manutenção e registro de manutenção.

**Benefícios.** Menos quebras em campo, prioridade objetiva e histórico de manutenção auditável.
