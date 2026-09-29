# Evidência — validação da integração com a fonte de dados (telemetria)

*Execução: 2026-09-21T13:16:37 · comando `python run.py simular` contra a API em execução (modelo hgb-v2.0, regras regras-v2.0).*

## Reconciliação (sem perda nem duplicação de dados)

| Enviadas | Processadas | Rejeitadas (quarentena) | Duplicadas bloqueadas | Erros inesperados | Fecha? |
|---|---|---|---|---|---|
| 200 | 185 | 11 | 4 | 0 | ✅ sim |

- Respostas conforme o esperado para cada tipo de envio: **200/200**
- Leituras aceitas sem predição ou sem trilha de auditoria: **0**
- Integridade da trilha de auditoria após a carga: **Cadeia íntegra: 486 eventos verificados, nenhum adulterado.**
- Latência da API por leitura (inclui validação, modelo, explicação, alertas e auditoria): p50 **126.7 ms**, p95 **144.2 ms**
- Alertas gerados/agrupados nas leituras aceitas: **92**

## Comportamento por tipo de envio

| Tipo de envio | Enviadas | HTTP esperado | Conformes |
|---|---|---|---|
| distância da água vazia → quarentena | 1 | 422 | 1/1 |
| data inválida → quarentena | 5 | 422 | 5/5 |
| EQ-999 → quarentena | 5 | 422 | 5/5 |
| umidade 140% → tratada como ausente e imputada | 5 | 201 | 5/5 |
| "COLHEITA" → padronizado | 3 | 201 | 3/3 |
| leitura correta | 174 | 201 | 174/174 |
| mesmo pacote → bloqueado | 4 | 409 | 4/4 |
| "55,3" → convertido | 3 | 201 | 3/3 |

Nenhuma leitura com defeito derrubou a API ou interrompeu o fluxo: cada uma recebeu o tratamento previsto e ficou registrada (processada, em quarentena ou bloqueada como duplicada).
