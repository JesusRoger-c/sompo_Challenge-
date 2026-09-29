# 🔁 De → para: o que mudou de lugar entre a Sprint 3 e a Sprint 4

A Sprint 4 pede para **refinar o que já existe**: organizar a arquitetura, modularizar o código e padronizar funções. Nada foi jogado fora: cada arquivo da Sprint 3 continua no histórico do git e teve a sua responsabilidade levada para um módulo com um dono claro.

Este documento existe para que ninguém precise procurar: mostra **onde cada coisa foi parar** e **por que mudou**.

## 1. Código Python

| Sprint 3 (no GitHub) | Sprint 4 (onde está agora) | Por que mudou |
|---|---|---|
| `src/backend/app.py` (585 linhas, tudo junto) | `src/somprev/api/app.py` (rotas e proteções) + `src/somprev/servicos/processamento.py` (fluxo da leitura) + `src/somprev/banco/repositorio.py` (SQL) | O arquivo misturava rota HTTP, regra de negócio e SQL. Separado em três responsabilidades, o mesmo fluxo passou a servir também à carga em lote e ao simulador |
| `src/backend/app_backup.py` | removido | Era cópia de segurança de uma versão anterior; o histórico do git já cumpre esse papel |
| `src/dashboards/app.py` | `src/somprev/dashboard/app.py` (4 perfis) + `src/somprev/dashboard/componentes.py` (estilo e gráficos) | Entrou o perfil Técnico, o ciclo de vida dos alertas, as tendências e a edição de regras |
| `src/dashboards/preview_dashboard.html` | `document/other/historico/prototipo_dashboard_sprint2.html` | Protótipo estático da Sprint 2: virou material histórico |
| `src/dashboards/_dados_dashboard.json` | removido | Dados de exemplo do protótipo; o dashboard lê o banco |
| `src/scripts/risco_utils.py` | `src/somprev/regras.py` + `src/somprev/esquema.py` | As regras (faixas, alertas, recomendações) ficaram configuráveis em `config/regras_risco.json`; o contrato de dados virou um módulo próprio |
| `src/scripts/tema.py` | `src/somprev/tema.py` | Mesma paleta, agora com as cores categóricas dos gráficos |
| `src/scripts/treinar_modelo.py` | `src/somprev/modelo/treino.py` | Ganhou validação temporal, busca de hiperparâmetros, calibração, limiar por custo e model card |
| `src/scripts/popular_banco.py` | `src/somprev/pipeline.py` (etapas 4 e 5) + `servicos/processamento.py` | A carga passou a usar o mesmo caminho da API, com transação atômica e auditoria |
| `src/datasets/gerar_dataset.py` | `src/somprev/dados/gerador.py` | Gerador v2: cadastro fixo, clima por região e dia, sazonalidade e falhas de coleta |
| `src/scripts/criar_auditoria.py` | `src/database/schema.sql` + `src/somprev/seguranca/auditoria.py` | A tabela nasce com o schema; a auditoria virou cadeia de hashes |
| `src/scripts/limpar.py` | `src/somprev/dados/qualidade.py` | Era uma limpeza pontual de 2 leituras órfãs; virou uma etapa de qualidade com política, quarentena e relatório |
| `src/scripts/ver_auditoria.py` | `python scripts/run.py verificar` · `GET /auditoria/verificar` · aba Auditoria do dashboard · `queries.sql` (consulta 6 e 7) | Consulta com `leitura_id` fixo no código virou ferramenta de verdade |
| `src/scripts/ver_consistencia_banco.py` | `src/somprev/servicos/verificacao.py` (12 verificações) | De 1 conferência para 12, com saída padronizada e usada nos testes |
| `src/scripts/_gerar_arquitetura.py` | `scripts/gerar_arquitetura.py` | Saiu de `src/` (não é código do sistema) e passou a desenhar a arquitetura final |

## 2. Banco de dados

| Sprint 3 | Sprint 4 | Por que |
|---|---|---|
| `src/database/schema.sql` (6 tabelas) | `src/database/schema.sql` (10 tabelas, mesmo caminho) | Entraram quarentena, manutenções, usuários e versões de modelo; e restrições `CHECK`, `UNIQUE` e gatilhos que deixam a auditoria somente-inserção |
| `src/database/queries.sql` | `src/database/queries.sql` (mesmo caminho) | Consultas reescritas para o schema novo (tendências, fila de manutenção, rastreabilidade, consistência) |
| `src/database/somprev_risk.db` | mesmo caminho | Recriado pelo pipeline com os dados tratados |

## 3. Dados e modelo

| Sprint 3 | Sprint 4 | Por que |
|---|---|---|
| `src/datasets/leituras_agricolas.csv` | `src/datasets/coleta_bruta.csv` → `leituras_tratadas.csv` (+ `relatorio_qualidade.json`, `cadastro_equipamentos.csv`) | Agora há a base **como ela chega** (com defeitos) e a base **tratada**, com o relatório do que foi corrigido |
| `src/models/modelo_risco.pkl` (`rf-v1.0`) | mesmo caminho (`hgb-v2.0`) | Modelo reajustado, calibrado e com `model_card.json` e hash SHA-256 |
| `src/models/metricas.json` | mesmo caminho | Métricas do teste temporal, comparação com a receita da Sprint 3 e análise do limiar |
| `src/models/matriz_correlacao.png` | removido | Substituído por gráficos mais úteis: calibração, precisão × recall, análise do limiar e taxa real por faixa |

## 4. Documentação e evidências

| Sprint 3 | Sprint 4 |
|---|---|
| `document/arquitetura.png` / `.svg` | Atualizados. As versões antigas ficaram em `document/other/historico/` |
| `document/prints/sprint3_*.png` | Organizados em `document/prints/sprint3/`; os novos estão em `document/prints/sprint4/` |
| `document/prints/dashboard_*.png` (Sprint 2) | `document/prints/sprint2/` |
| — | **Novos:** `decisoes_tecnicas.md`, `seguranca.md`, `de_para_sprint3_sprint4.md`, `evidencias/` e `relatorios/` |

## 5. O que passou a existir e não existia

| Novo | Para quê |
|---|---|
| `scripts/run.py` | Um único comando para tudo: `configurar`, `pipeline`, `api`, `dashboard`, `simular`, `verificar`, `usuario`, `testes` |
| `src/somprev/dados/qualidade.py` | Duplicidades, valores impossíveis, grafias, imputação e quarentena |
| `src/somprev/seguranca/` | Senhas com hash, bloqueio, permissões por perfil e auditoria encadeada |
| `src/somprev/servicos/verificacao.py` e `simulador.py` | As 12 verificações e o teste de confiabilidade da coleta |
| `src/somprev/relatorios/tendencias.py` | Tendências por região, operação e equipamento |
| `config/regras_risco.json` | Regras de risco versionadas e editáveis pelo Gestor |
| `src/tests/` (113 testes) e `.github/workflows/testes.yml` | Validação automatizada e integração contínua |

## 6. Compatibilidade com os caminhos antigos

Para quem conhece o repositório da Sprint 3, os dois caminhos principais continuam funcionando, agora como atalhos para o código novo:

| Caminho antigo | O que acontece hoje |
|---|---|
| `src/backend/app.py` | Continua expondo o objeto `app` do FastAPI (importa `somprev.api.app`) |
| `src/dashboards/app.py` | Continua subindo o dashboard (chama `somprev/dashboard/app.py`) |
| `src/scripts/` | `LEIA-ME.md` aponta cada script antigo para o comando equivalente do `scripts/run.py` |

O caminho recomendado, porém, é sempre o `scripts/run.py`.
