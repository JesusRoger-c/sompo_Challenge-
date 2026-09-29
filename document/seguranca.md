# 🔐 Segurança e rastreabilidade (Sprint 4)

> Evidência executada (respostas reais da API, bloqueio de login, trilha de uma leitura e detecção de adulteração): [`evidencias/seguranca_rastreabilidade.md`](evidencias/seguranca_rastreabilidade.md). Para gerar de novo: `python scripts/gerar_evidencias_seguranca.py`.

O SomPrev Risk trata dados operacionais de clientes da seguradora e gera decisões que afetam a operação ("pode operar ou não"). Por isso, a segurança foi desenhada em **camadas**: controle de acesso, proteção de dados, integridade e rastreabilidade de ponta a ponta.

## 1. Controle de acesso

| Camada | Controle | Onde está |
|---|---|---|
| Dashboard | Login com usuário e senha; perfil fixo por usuário | `seguranca/autenticacao.py`, `dashboard/app.py` |
| Dashboard | **Permissões explícitas por perfil** (privilégio mínimo): o que não está na lista é negado | `autenticacao.PERMISSOES` |
| Dashboard | Bloqueio de 15 min após 5 senhas erradas (força bruta) | `autenticar()` |
| Dashboard | Mensagem genérica ("usuário ou senha inválidos") e tempo de resposta igual para login inexistente | hash "fantasma" |
| Dashboard | Sessão expira após 30 min de inatividade | `sessao_valida()` |
| API | **Duas chaves com escopos separados**: ingestão (coletores) e consulta (BI/seguradora). Uma não serve para a outra (403) | `api/app.py` |
| API | Comparação de chave em tempo constante (`hmac.compare_digest`) | `identificar_chave_api()` |
| API | Limite de requisições por chave/IP (HTTP 429 + `Retry-After`) | `_limitar_taxa()` |
| API | Corpo limitado a 1 MB (413); payload estrito, com campos desconhecidos recusados (422) | middleware + Pydantic |

### Matriz de permissões

| Permissão | Operador | Técnico | Gestor | Seguradora |
|---|:---:|:---:|:---:|:---:|
| Ver a operação do equipamento | ✅ | ✅ | ✅ | |
| Reconhecer alerta | ✅ | ✅ | ✅ | |
| Resolver alerta | | ✅ | ✅ | |
| Registrar manutenção | | ✅ | | |
| Ver frota e tendências | | | ✅ | ✅ |
| Editar regras de risco | | | ✅ | |
| Exportar relatório | | | ✅ | ✅ |
| Ver validação do modelo e auditoria | | | | ✅ |
| Verificar a integridade da auditoria | | | | ✅ |

## 2. Proteção de dados

- **Senhas nunca são armazenadas.** No banco fica só o hash PBKDF2-HMAC-SHA256, com salt aleatório de 16 bytes e **600 mil iterações** (recomendação OWASP 2023), no formato `pbkdf2_sha256$iterações$salt$hash`.
- **Política de senha:** mínimo de 12 caracteres, com letras e números.
- **Segredos fora do código:** chaves e senhas iniciais ficam só no `.env` (ignorado pelo git, com permissão 600). O comando `python run.py configurar` gera segredos aleatórios fortes.
- **Logs sem segredos:** o formatador JSON mascara campos sensíveis (`senha`, `api_key`, `token`...), e a chave de API aparece só como uma impressão digital não reversível (SHA-256 truncado).
- **Erros sem vazamento:** um erro inesperado devolve HTTP 500 genérico com `id_requisicao`. O detalhe técnico fica só no log (há teste que garante isso).
- **Minimização (LGPD):** a telemetria não tem dados pessoais. O único dado pessoal é o login dos usuários, usado para auditoria.

## 3. Integridade das informações

| Mecanismo | O que impede |
|---|---|
| `CHECK` no banco (faixas físicas, domínios, score 0–100) | Gravar valor impossível, mesmo por fora da aplicação |
| `FOREIGN KEY` + `UNIQUE(equipamento_id, data_hora)` | Leitura órfã ou medição duplicada |
| Transação atômica por leitura (`BEGIN IMMEDIATE`) | Leitura gravada sem predição ou sem auditoria ("pela metade") |
| **Hash SHA-256 do payload** em cada leitura | Alteração da entrada depois do recebimento |
| **Hash SHA-256 do modelo** registrado em `modelo_versoes` | Troca silenciosa do arquivo `.pkl` |
| Qualidade de dados + quarentena | Dado inconsistente chegando ao modelo |

## 4. Rastreabilidade: entradas, saídas e decisões

### 4.1 Trilha de auditoria encadeada (tamper-evident)

Cada evento grava `hash_anterior` e `hash_registro = SHA-256(conteúdo + hash_anterior)`. Os eventos formam uma corrente, como em um livro-razão:

- **triggers** do SQLite impedem `UPDATE` e `DELETE` na tabela `auditoria` (append-only);
- se alguém com acesso direto ao arquivo remover os triggers e alterar ou apagar um evento, a verificação (`GET /auditoria/verificar`, botão na visão da Seguradora ou `python run.py verificar`) aponta **exatamente** o evento adulterado. Há testes automatizados para os dois casos.

### 4.2 Eventos registrados

| Grupo | Eventos |
|---|---|
| Entrada | `TELEMETRIA_RECEBIDA` (com hash do payload e avisos de qualidade), `TELEMETRIA_REJEITADA`, `TELEMETRIA_DUPLICADA`, `CARGA_HISTORICA`, `QUALIDADE_DADOS` |
| Saída / decisão | `PREDICAO_GERADA` (probabilidade, score, faixa, fatores com contribuição, versão das regras), `ALERTA_GERADO`, `ALERTA_AGRUPADO` (com o critério que disparou) |
| Ação humana | `ALERTA_ATUALIZADO` (quem, de → para, comentário), `MANUTENCAO_REGISTRADA`, `REGRAS_ALTERADAS` (versões e justificativa obrigatória), `RELATORIO_EXPORTADO` |
| Segurança | `LOGIN_SUCESSO`, `LOGIN_FALHA`, `CONTA_BLOQUEADA`, `LOGOUT`, `ACESSO_NEGADO`, `API_ACESSO_NEGADO`, `USUARIO_CADASTRADO` |
| Sistema | `MODELO_REGISTRADO`, `VERIFICACAO_SISTEMA`, `VERIFICACAO_AUDITORIA` |

### 4.3 Explicabilidade do score (por que o sistema decidiu isso?)

`GET /leituras/{id}` devolve, para uma leitura:

1. a **entrada** exatamente como ficou gravada (com status de qualidade e hash);
2. a **saída**: probabilidade, score, faixa, versão do modelo e das regras, e a contribuição de cada variável;
3. os **alertas** com o critério textual (ex.: `Distância da água < 200 e Umidade do solo ≥ 75`);
4. a **trilha de auditoria** daquela leitura, com os hashes.

### 4.4 Logs técnicos

`logs/somprev.log` tem uma linha JSON por evento técnico (requisição, rota, status, duração, `id_requisicao`, avisos de qualidade, erros com traceback). A rotação é automática (5 × 2 MB). Os logs complementam a auditoria: a auditoria guarda **o que o sistema decidiu** e os logs guardam **como ele se comportou**.

## 5. Limitações conhecidas (MVP)

- O HTTPS deve ficar num proxy reverso (nginx, API Gateway) na implantação. O MVP roda em `localhost`.
- O limite de taxa é por processo, em memória. Com vários processos, deve ir para um Redis ou para o gateway.
- O SQLite atende o MVP. Em produção, o recomendado é PostgreSQL com usuários de banco separados (leitura × escrita) e backup.
