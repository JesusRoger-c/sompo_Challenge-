# 🧭 Decisões técnicas ao longo das quatro Sprints

Registro das principais decisões do projeto: o que foi decidido, por quê, e o que mudou quando aprendemos mais. As decisões revistas aparecem de propósito, porque mostram a evolução do projeto.

## Sprint 1: entender o problema

| Decisão | Justificativa |
|---|---|
| Foco em **risco operacional de frotas agrícolas** (atolamento, tombamento, dano mecânico) | Maior parte dos acidentes graves com tratores é capotamento ou tombamento, e ~97% são evitáveis por prevenção ([contextualização](contextualizacao.md)) |
| Mudar a gestão de **reativa para preventiva** com um score antes da operação | A seguradora paga o sinistro. Evitá-lo gera valor para os dois lados |
| Três personas: Operador, Gestor e Seguradora | Cada uma decide algo diferente com o mesmo score |
| Sete User Stories (visualizar risco, alertas, causas, histórico, decisão, facilidade de uso, configurar regras) | Guiaram todas as Sprints seguintes (rastreabilidade no README) |

## Sprint 2: dados e modelo

| Decisão | Justificativa | Revista depois? |
|---|---|---|
| Dados **simulados** com lógica causal documentada | Permitido pelo enunciado. Sem telemetria real das máquinas seguradas | Sim, na Sprint 4 (gerador v2) |
| Score 0–100 = probabilidade × 100 | Linguagem que o operador entende | Mantida; o score ficou calibrado na Sprint 4 |
| Quatro faixas de risco | Cada faixa tem uma ação distinta (liberar / atenção / restringir / suspender) | Cortes redefinidos na Sprint 4 |
| Comparar LR, RF e GB e escolher o RF | Melhor acurácia e importância de variáveis | Sim, na Sprint 4 (critério e algoritmo) |
| Banco relacional (SQLite) com predições versionadas | Histórico consultável e auditável | Ampliado na Sprint 4 |
| Top 3 fatores por leitura | Um score sem motivo é uma caixa-preta | Sim, na Sprint 4 (explicação vinda do modelo) |

## Sprint 3: integração

| Decisão | Justificativa | Revista depois? |
|---|---|---|
| Backend **FastAPI** com `POST /telemetria` | Validação automática (Pydantic) e documentação interativa | Mantida e ampliada |
| API Key no cabeçalho `X-API-Key` | Proteção simples para coletores de campo | Separada em 2 escopos |
| Login no dashboard com perfil fixo | Cada usuário vê só a sua visão | Senhas passaram a ter hash |
| Tabela de auditoria | Rastrear entrada, predição e alerta | Encadeada por hash na Sprint 4 |
| Persistência incremental | Novas leituras sem apagar o histórico | Mantida, agora com transação atômica |

## Sprint 4: consolidação e confiabilidade

| Decisão | Alternativa descartada | Por quê |
|---|---|---|
| Pacote `src/somprev/` com um módulo por responsabilidade e **um comando** (`run.py`) | Scripts soltos com caminhos montados à mão | Fluxo reproduzível, testável e fácil de rodar por quem corrige |
| **Mesmo serviço** de processamento para lote, API e simulador | Lógicas separadas para carga e API | Uma leitura recebe sempre o mesmo score, venha de onde vier |
| Gerador v2: cadastro fixo, clima por região e dia, sazonalidade, manutenção com memória | Manter o gerador v1 | A v1 tinha inconsistências (idade variando) e não gerava tendências |
| Coleta bruta **com falhas injetadas** + qualidade + quarentena | Base limpa desde a origem | O enunciado pede tratar inconsistências. Sem sujeira não há como provar o tratamento |
| Imputação por **fonte de referência** (cadastro, região/dia, histórico da máquina) | Média global | É mais fiel. A chuva da região no dia é exata; a média global erraria |
| Crítico ausente vai para a **quarentena**, não é imputado | Imputar tudo | Declividade e distância da água dependem do talhão. Melhor não pontuar do que pontuar errado |
| **Validação temporal** | Split aleatório | O modelo prevê o futuro; o split aleatório superestima o desempenho |
| **PR-AUC** como critério de seleção | Acurácia | A classe positiva é minoritária e o objetivo é antecipar sinistros |
| **HistGradientBoosting** calibrado | Random Forest (Sprint 2) | Melhor PR-AUC na validação e melhor calibração |
| **Limiar por custo** (score ≥ 15) | 0,5 fixo | Deixar passar um sinistro custa ~10× mais que um alerta. O recall subiu de 49% para 82% |
| Faixas **0–14 / 15–39 / 40–69 / 70–100** | Quartis 25/50/75 | Com o score calibrado, as faixas passam a ter um significado probabilístico |
| Explicação **pelo próprio modelo** (efeito marginal contra a distribuição da frota) | Fórmula fixa da Sprint 2; biblioteca SHAP | Fiel ao modelo, determinística e sem dependência pesada |
| **Gatilhos explícitos** além do modelo | Só o modelo | São interpretáveis, cobrem cenários extremos e funcionam como segunda linha de defesa |
| Agrupamento de alertas (janela de 48 h) | Um alerta por leitura | Evita a fadiga de alerta: o operador deixa de ignorar os avisos |
| Regras em JSON **versionado** e editável pelo Gestor | Constantes no código | Atende à User Story "configurar regras"; cada predição sabe qual regra usou |
| 4º perfil: **Técnico de manutenção** | Manutenção dentro do Gestor | O enunciado cita o técnico, que tem uma tarefa própria (fila da oficina) |
| Auditoria **encadeada por hash** + append-only | Tabela comum | Um auditor precisa provar que o histórico não foi alterado |
| PBKDF2 (biblioteca padrão) | bcrypt/argon2 | Seguro (OWASP) e sem dependência nativa extra para quem corrige |
| Testes com **pipeline completo em diretório temporário** | Testar só funções isoladas | Prova a integração real sem sujar o repositório |
| Manter **atalhos** nos caminhos da Sprint 3 e documentar o de → para | Só mover os arquivos | Quem conhece o repositório anterior encontra tudo; a evolução fica explícita em vez de parecer um projeto novo |
| **Dashboard vira cliente HTTP da própria API** (`dashboard/cliente_api.py`) para tudo que exibe | Manter a leitura direta do banco pelo painel | O feedback da tutoria na Sprint 3 apontou que o painel não passava pela API; a Sprint 4 pede explicitamente "proteção das APIs ou serviços... evitando vulnerabilidades comuns na integração entre sistemas". Seis rotas de consulta novas (`/leituras`, `/equipamentos`, `/manutencoes`, `/quarentena`, `/auditoria`, `/verificacao`), todas com a chave de escopo "consulta" |
| **Escritas do dashboard continuam diretas no banco** (alerta, manutenção, regras, login) | Passar também as escritas pela API | São ações de um usuário já autenticado na própria sessão do dashboard (RBAC por perfil) — uma fronteira de autorização diferente da chave de API máquina-a-máquina, e já adequada; forçar todas as escritas por HTTP não reduziria risco e complicaria a transação atômica |
