# Evidência — segurança e rastreabilidade em condição de uso

*Gerado por `python scripts/gerar_evidencias_seguranca.py` sobre uma **cópia** do banco final (chaves de API de demonstração, válidas só nesta execução).*

## 1. Controle de acesso da API (chaves com escopo) e payload estrito

| Tentativa | HTTP | Resposta |
|---|---|---|
| Sem chave | **401** | `API Key não informada.` |
| Chave inválida | **401** | `API Key inválida.` |
| Chave de CONSULTA tentando ingerir | **403** | `Esta chave não tem permissão para este recurso.` |
| Chave de INGESTÃO tentando consultar | **403** | `Esta chave não tem permissão para este recurso.` |
| Campo não previsto no payload (`houve_sinistro`) | **422** | `Payload inválido.` |

**Limite de requisições** (configurado em 5/min para a demonstração): códigos recebidos em 7 chamadas seguidas → `[200, 200, 200, 200, 200, 429, 429]` (as excedentes recebem **429** com `Retry-After`).

## 2. Rastreabilidade completa de uma leitura (entrada → saída → decisão)

Leitura enviada com umidade `"88,5"` (vírgula) e sem a idade da máquina. Resposta resumida:

```json
{
  "leitura_id": 5980,
  "score_risco": 97,
  "classe_risco": "Critico",
  "fatores": [
    {
      "variavel": "umidade_solo_pct",
      "rotulo": "Umidade do solo",
      "contribuicao_pontos": 11.46
    },
    {
      "variavel": "distancia_corpo_dagua_m",
      "rotulo": "Distância da água",
      "contribuicao_pontos": 9.75
    },
    {
      "variavel": "precipitacao_24h_mm",
      "rotulo": "Chuva nas últimas 24h",
      "contribuicao_pontos": 4.78
    }
  ],
  "avisos_qualidade": [
    "umidade_solo_pct convertido de texto ('88,5')",
    "idade_equipamento_anos imputada pelo cadastro"
  ],
  "modelo_versao": "hgb-v2.0",
  "regras_versao": "regras-v2.0",
  "recibo_auditoria": "6b4d5873b3d592175480853b1925ac069f1dc2a93c99232faa890c5ce346abe9"
}
```

Alertas gerados, com o critério explícito:

- **SCORE_ACIMA_LIMIAR** (Critico, destino Gestor): `Score 97 ≥ limiar de alerta 15 (regras regras-v2.0)`
- **AREA_ALAGAVEL** (Alto, destino Operador): `Distância da água < 200 e Umidade do solo ≥ 75`

Trilha de auditoria desta leitura (`GET /leituras/5980`):

| # | Evento | Ator | Hash do registro |
|---|---|---|---|
| 497 | TELEMETRIA_RECEBIDA | `api:ingestao:0b4796f176` | `edf832f738c571e281c0…` |
| 498 | PREDICAO_GERADA | `api:ingestao:0b4796f176` | `eb89395732c99ffe5519…` |
| 499 | ALERTA_GERADO | `api:ingestao:0b4796f176` | `a01cead18fec6a4097e5…` |
| 500 | ALERTA_GERADO | `api:ingestao:0b4796f176` | `6b4d5873b3d592175480…` |

Hash SHA-256 do payload gravado na leitura: `b3f908704501f23cde6a7f3c00eefb44d42c397d99be84f796fe4f82a1cf4317`

## 3. Autenticação do dashboard: força bruta e mensagens genéricas

| Tentativa | Senha correta? | Resultado |
|---|---|---|
| 1 | não | Usuário ou senha inválidos. |
| 2 | não | Usuário ou senha inválidos. |
| 3 | não | Usuário ou senha inválidos. |
| 4 | não | Usuário ou senha inválidos. |
| 5 | não | Usuário ou senha inválidos. |
| 6 | sim | Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em 15 min. |

**Permissão por perfil:** Operador tentando editar regras → `O perfil Operador não tem permissão para 'editar_regras'.` (evento `ACESSO_NEGADO` gravado na auditoria).

Como a senha fica guardada no banco: `pbkdf2_sha256$600000$wL7WIhNLzmMP0b8Sm4tsyA=…` (PBKDF2-SHA256; a senha nunca é gravada).

Eventos de segurança registrados nesta execução: `ACESSO_NEGADO` ×1, `API_ACESSO_NEGADO` ×4, `CONTA_BLOQUEADA` ×1, `LOGIN_FALHA` ×6.

## 4. Log técnico estruturado (JSON)

Cada linha de `logs/somprev.log` é um JSON com horário, nível, módulo e contexto. A chave de API nunca aparece. Amostra completa em [`amostra_log.jsonl`](amostra_log.jsonl):

```json
{"ts": "2026-09-21T16:55:35.272+00:00", "nivel": "WARNING", "modulo": "somprev.api", "mensagem": "Acesso negado na API", "rota": "/telemetria", "motivo": "chave ausente", "ip": "testclient"}
{"ts": "2026-09-21T16:55:35.280+00:00", "nivel": "WARNING", "modulo": "somprev.api", "mensagem": "Acesso negado na API", "rota": "/telemetria", "motivo": "chave inválida", "ip": "testclient"}
{"ts": "2026-09-21T16:55:38.933+00:00", "nivel": "INFO", "modulo": "somprev.servicos.processamento", "mensagem": "Leitura processada", "leitura_id": 5980, "score": 97, "classe": "Critico", "alertas": 2, "origem": "api"}
```

## 5. Integridade da trilha de auditoria

1. Verificação antes: **Cadeia íntegra: 509 eventos verificados, nenhum adulterado.**
2. `UPDATE` direto na tabela de auditoria foi bloqueado? **sim — `auditoria e somente-insercao (append-only)`**
3. Simulando um atacante com acesso ao arquivo (remove o trigger e altera o evento #5)…
4. Verificação depois: **ADULTERAÇÃO DETECTADA no evento #5 (conteúdo alterado após o registro). 4 eventos conferidos até o ponto de quebra.**

Conclusão: a trilha é somente-inserção e qualquer adulteração é detectada e localizada.
