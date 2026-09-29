# ✅ Relatório de validação do MVP (Sprint 4)

Este relatório reúne as **evidências de que a solução funciona de ponta a ponta**, de forma reproduzível, com dados íntegros, segurança aplicada e resultados rastreáveis. Cada evidência indica o comando que a reproduz.

| # | Requisito da Sprint 4 | Evidência | Como reproduzir |
|---|---|---|---|
| 1 | Fluxo estável e reproduzível | Pipeline de 7 etapas, 12/12 verificações aprovadas | `python run.py pipeline` |
| 2 | Tratamento de inconsistências, faltantes e duplicidades | Relatório de qualidade (97,2% de aproveitamento, 0 ausentes após o tratamento) | [`src/datasets/relatorio_qualidade.json`](../src/datasets/relatorio_qualidade.json) |
| 3 | Modelo final com métricas justificadas | PR-AUC 0,76, recall 82%, calibrado, validação temporal | [`modelo_preditivo.md`](modelo_preditivo.md) |
| 4 | Integração consistente com a fonte de dados | 200 envios pela API: 0 perdas, 0 erros inesperados | [`evidencias/validacao_integracao.md`](evidencias/validacao_integracao.md) |
| 5 | Controle de acesso, proteção e integridade | Cenários reais: 401/403/422/429, bloqueio, RBAC, adulteração detectada | [`evidencias/seguranca_rastreabilidade.md`](evidencias/seguranca_rastreabilidade.md) |
| 6 | Logs que rastreiam entradas, saídas e decisões | Auditoria encadeada + log JSON ([amostra](evidencias/amostra_log.jsonl)) | `GET /leituras/{id}` |
| 7 | Relatórios de tendência | Por região, operação e equipamento | [`relatorios/relatorio_tendencias.md`](relatorios/relatorio_tendencias.md) |
| 8 | Testes automatizados | 113 testes aprovados | [`evidencias/resultado_testes.txt`](evidencias/resultado_testes.txt) |

---

## 1. Pipeline de ponta a ponta

Saída completa em [`evidencias/execucao_pipeline.txt`](evidencias/execucao_pipeline.txt). Resumo:

```
[1/7] Coleta simulada ........ 40 equipamentos · 5.891 registros brutos · 514 falhas de coleta injetadas
[2/7] Qualidade de dados ..... 5.723 aceitas (314 corrigidas) · 97 duplicadas removidas · 71 em quarentena
[3/7] Modelo preditivo ....... hgb-v2.0 · teste: ROC-AUC 0,881 · PR-AUC 0,760 · recall 82% no limiar 15
[4/7] Banco de dados ......... 6 regiões · 40 equipamentos · 71 em quarentena · 4 usuários
[5/7] Carga + score .......... 5.723 predições com explicação + alertas
[6/7] Relatórios ............. tendências em Markdown + 4 gráficos + 3 CSV
[7/7] Verificação ............ 12/12 verificações aprovadas
```

### As 12 verificações automáticas (`python run.py verificar`)

| Verificação | O que garante |
|---|---|
| `PRAGMA integrity_check` | Arquivo do banco sem corrupção |
| Chaves estrangeiras sem órfãos | Toda leitura aponta para um equipamento e uma região existentes |
| Toda leitura aceita tem predição | **Sem perda** entre entrada e saída |
| Scores e probabilidades dentro da faixa | Nenhum score fora de 0–100 |
| Score coerente com a probabilidade | O score gravado corresponde ao modelo |
| Toda predição rastreável | Versão do modelo e das regras em 100% das predições |
| Sem leituras duplicadas | Reenvios de pacote bloqueados |
| Sem ausentes nas variáveis do modelo | O modelo nunca recebe dado incompleto |
| Trilha de auditoria íntegra | Cadeia de hashes conferida evento a evento |
| Artefato do modelo confere (SHA-256) | O `.pkl` em uso é o mesmo que foi registrado |
| Nenhuma senha sem hash | Só existe hash PBKDF2 no banco |
| Reconciliação da coleta | recebidas = aceitas + quarentena + duplicadas |

---

## 2. Qualidade dos dados

A coleta simulada recebe **falhas típicas de campo** de propósito (514 no total), e a etapa de qualidade precisa tratá-las:

| Falha injetada | Qtde | Tratamento | Resultado |
|---|---:|---|---|
| Pacote reenviado (linha idêntica) | 69 | Remoção de duplicata exata | 69 removidas ✅ |
| Reenvio com novo `leitura_id` | 28 | Mesma máquina no mesmo instante | 28 removidas ✅ |
| Sensor sem leitura (1 sensor: 115; vários: 17) | 132 | Imputação por região/dia, cadastro ou histórico da máquina; declividade e distância da água não são imputáveis | 164 valores imputados no total (inclui os fora da faixa) · 38 leituras em quarentena ✅ |
| Valor fisicamente impossível (umidade 140%, carga 9.999) | 57 | Tratado como ausente e imputado | 57 corrigidas ✅ |
| Decimal com vírgula ("55,3") | 57 | Conversão | 57 convertidas ✅ |
| Grafia diferente ("Manhã", "COLHEITA") | 115 | Padronização | 115 padronizadas ✅ |
| Categoria desconhecida ("Pedregoso") | 11 | Sem tipo de solo não há score confiável | 11 em quarentena ✅ |
| Equipamento fora do cadastro | 11 | Referência inválida | 11 em quarentena ✅ |
| Data corrompida | 11 | Referência inválida | 11 em quarentena ✅ |
| Sinistro ainda não apurado | 23 | Pontuado, mas fora do treino | ✅ |

A imputação foi conferida contra o valor verdadeiro. A **chuva** é compartilhada pela região no dia, então a imputação é exata. A **idade** vem do cadastro e também é exata. A umidade tem erro médio de ~5 p.p. (há variação entre talhões).

---

## 3. Integração com a fonte de dados (tempo real)

O simulador (`python run.py simular`) envia leituras para a API como faria um coletor de campo, com 15% de envios defeituosos, e reconcilia o resultado. Evidência completa: [`evidencias/validacao_integracao.md`](evidencias/validacao_integracao.md).

- enviadas = processadas + rejeitadas (quarentena) + duplicadas bloqueadas, **sem perda**;
- **0 erros inesperados**: nenhuma entrada ruim derrubou a API;
- 100% das leituras aceitas têm predição e trilha de auditoria (conferido pela API de consulta);
- a cadeia de auditoria continua íntegra após a carga.

---

## 4. Testes automatizados

`python run.py testes` roda **113 testes** em um ambiente temporário isolado (o pipeline completo é refeito do zero dentro do teste). Resultado: [`evidencias/resultado_testes.txt`](evidencias/resultado_testes.txt).

| Arquivo | O que cobre | Testes |
|---|---|---:|
| `test_regras.py` | faixas, limiar, gatilhos explícitos, recomendação, versionamento das regras | 19 |
| `test_qualidade.py` | conversões, reconciliação, imputação fiel, quarentena, registro único | 26 |
| `test_seguranca.py` | hash de senha, política, bloqueio, RBAC, append-only, **detecção de adulteração** | 22 |
| `test_modelo.py` | versão, validação temporal, métricas mínimas, **supera a Sprint 3**, faixas monotônicas, explicação | 11 |
| `test_api.py` | 401/403 por escopo, 201/409/422/404, lote misto, erro 500 sem vazamento, **limite 429** | 14 |
| `test_integracao.py` | artefatos, 12 verificações, alertas sem duplicidade, **simulador sem perda**, sazonalidade | 7 |
| `test_dashboard.py` | login inválido, cada perfil vê a sua tela, operador sem acesso às regras | 6 |
| `test_compatibilidade.py` | caminhos da Sprint 3 ainda funcionam; o mapa de → para está correto | 5 |

> **Um teste encontrou um bug real de segurança durante a Sprint 4.** Quando o login falhava, o erro saía de dentro da transação, e o `ROLLBACK` apagava justamente o registro da tentativa suspeita. Resultado: o bloqueio por força bruta nunca disparava. A correção grava a tentativa (`COMMIT`) antes de sinalizar o erro. O teste de regressão `test_falha_de_login_fica_gravada_mesmo_com_erro` impede que o problema volte.

A integração contínua (`.github/workflows/testes.yml`) roda a suíte em Python 3.10 e 3.12 a cada push.

---

## 5. Casos de uso demonstrados

| User Story | Demonstração |
|---|---|
| Visualizar risco operacional | Operador: semáforo com score, faixa e recomendação ([print](prints/sprint4/02_operador.png)) |
| Receber alertas preventivos | Alertas com critério explícito, destino por perfil e ciclo de vida |
| Entender fatores de risco | Gráfico "por que esse score?" com a contribuição de cada fator |
| Analisar histórico operacional | Tendências por região, operação e equipamento + trilha de auditoria |
| Melhorar a tomada de decisão | Ações específicas por fator + fila priorizada de manutenção |
| Facilidade de uso | Uma tela por perfil, linguagem simples, cores sempre acompanhadas de rótulo |
| Configurar regras de risco | Gestor ajusta limiar e premissas; cada mudança vira uma nova versão auditada |
