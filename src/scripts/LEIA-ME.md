# Scripts da Sprint 3: para onde foram

Os scripts soltos desta pasta viraram módulos com dono claro dentro de
`src/somprev/`, e o que se rodava à mão virou comando do `run.py`.

| Script da Sprint 3 | Hoje |
|---|---|
| `gerar_dataset.py` | `somprev/dados/gerador.py` — etapa 1 de `python run.py pipeline` |
| `popular_banco.py` | `somprev/pipeline.py` (etapas 4 e 5), usando o mesmo serviço da API |
| `treinar_modelo.py` | `somprev/modelo/treino.py` — etapa 3 de `python run.py pipeline` |
| `risco_utils.py` | `somprev/regras.py` (regras configuráveis) e `somprev/esquema.py` (contrato de dados) |
| `tema.py` | `somprev/tema.py` |
| `criar_auditoria.py` | `src/database/schema.sql` + `somprev/seguranca/auditoria.py` |
| `limpar.py` | `somprev/dados/qualidade.py` (limpeza, imputação e quarentena) |
| `ver_auditoria.py` | `python run.py verificar`, `GET /auditoria/verificar`, aba Auditoria do dashboard |
| `ver_consistencia_banco.py` | `somprev/servicos/verificacao.py` (12 verificações) |
| `_gerar_arquitetura.py` | `scripts/gerar_arquitetura.py` (fora de `src/`, porque não é código do sistema) |

Detalhes e justificativas: [`document/de_para_sprint3_sprint4.md`](../../document/de_para_sprint3_sprint4.md).
