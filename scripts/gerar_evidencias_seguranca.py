#!/usr/bin/env python3
"""
Gera a evidencia de SEGURANCA e RASTREABILIDADE executando cenarios reais contra
uma COPIA temporaria do banco (o banco do repositorio nao e alterado).

Cenarios: chaves da API por escopo (401/403), payload estrito (422), limite de
requisicoes (429), bloqueio de login por forca bruta, permissao negada por
perfil, rastreabilidade completa de uma leitura, amostra do log JSON (com
segredos mascarados) e deteccao de adulteracao da trilha de auditoria.

Uso (a partir da raiz, depois de `python run.py pipeline`):
    python scripts/gerar_evidencias_seguranca.py
Saidas: document/evidencias/seguranca_rastreabilidade.md e amostra_log.jsonl
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="somprev_evid_"))
shutil.copy(RAIZ / "src" / "database" / "somprev_risk.db", TMP / "evidencia.db")
os.environ.update({
    "SOMPREV_DB_PATH": str(TMP / "evidencia.db"), "SOMPREV_LOG_DIR": str(TMP / "logs"),
    "SOMPREV_API_KEY": "chave-ingestao-evidencia-0000000000", "SOMPREV_API_KEY_CONSULTA": "chave-consulta-evidencia-000000000",
})
sys.path.insert(0, str(RAIZ / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from somprev import config  # noqa: E402
from somprev.api import app as modulo_api  # noqa: E402
from somprev.banco.conexao import sessao, transacao  # noqa: E402
from somprev.excecoes import AcessoNegado  # noqa: E402
from somprev.seguranca import auditoria, autenticacao  # noqa: E402

ING = {"X-API-Key": os.environ["SOMPREV_API_KEY"]}
CON = {"X-API-Key": os.environ["SOMPREV_API_KEY_CONSULTA"]}
LEITURA = {"data_hora": "2026-09-15 07:30:00", "equipamento_id": "EQ-021", "regiao_id": 4,
           "umidade_solo_pct": "88,5", "precipitacao_24h_mm": 62.0, "temperatura_c": 17.5, "tipo_solo": "Argiloso",
           "declividade_graus": 12.0, "distancia_corpo_dagua_m": 140, "tipo_operacao": "Colheita",
           "idade_equipamento_anos": None, "horas_desde_manutencao": 310, "horas_operacao_dia": 9.5,
           "carga_pct": 92, "periodo_dia": "Manha"}


def bloco(texto: str) -> str:
    return "```json\n" + texto + "\n```"


def main() -> None:
    cliente = TestClient(modulo_api.app)
    md = ["# Evidência — segurança e rastreabilidade em condição de uso", "",
          "*Gerado por `python scripts/gerar_evidencias_seguranca.py` sobre uma **cópia** do banco final "
          "(chaves de API de demonstração, válidas só nesta execução).*", ""]

    # 1. Chaves da API e payload -------------------------------------------------
    casos = [("Sem chave", cliente.post("/telemetria", json=LEITURA)),
             ("Chave inválida", cliente.post("/telemetria", json=LEITURA, headers={"X-API-Key": "invasor"})),
             ("Chave de CONSULTA tentando ingerir", cliente.post("/telemetria", json=LEITURA, headers=CON)),
             ("Chave de INGESTÃO tentando consultar", cliente.get("/alertas", headers=ING)),
             ("Campo não previsto no payload (`houve_sinistro`)",
              cliente.post("/telemetria", json={**LEITURA, "houve_sinistro": 0}, headers=ING))]
    md += ["## 1. Controle de acesso da API (chaves com escopo) e payload estrito", "",
           "| Tentativa | HTTP | Resposta |", "|---|---|---|"]
    md += [f"| {nome} | **{r.status_code}** | `{r.json().get('erro')}` |" for nome, r in casos]

    config.API_LIMITE_REQ_MINUTO = 5
    modulo_api._janelas.clear()
    codigos = [cliente.get("/alertas?limite=1", headers=CON).status_code for _ in range(7)]
    config.API_LIMITE_REQ_MINUTO = 600
    modulo_api._janelas.clear()
    md += ["", f"**Limite de requisições** (configurado em 5/min para a demonstração): códigos recebidos em 7 "
               f"chamadas seguidas → `{codigos}` (as excedentes recebem **429** com `Retry-After`).", ""]

    # 2. Rastreabilidade de uma leitura ---------------------------------------------
    r = cliente.post("/telemetria", json=LEITURA, headers=ING).json()
    trilha = cliente.get(f"/leituras/{r['leitura_id']}", headers=CON).json()
    md += ["## 2. Rastreabilidade completa de uma leitura (entrada → saída → decisão)", "",
           f"Leitura enviada com umidade `\"88,5\"` (vírgula) e sem a idade da máquina. Resposta resumida:", "",
           bloco(json.dumps({k: r[k] for k in ("leitura_id", "score_risco", "classe_risco", "fatores",
                                                 "avisos_qualidade", "modelo_versao", "regras_versao",
                                                 "recibo_auditoria")}, ensure_ascii=False, indent=2)), "",
           "Alertas gerados, com o critério explícito:", ""]
    md += [f"- **{a['codigo']}** ({a['nivel']}, destino {a['perfil_destino']}): `{a['criterio']}`" for a in r["alertas"]]
    md += ["", f"Trilha de auditoria desta leitura (`GET /leituras/{r['leitura_id']}`):", "",
           "| # | Evento | Ator | Hash do registro |", "|---|---|---|---|"]
    md += [f"| {e['auditoria_id']} | {e['evento']} | `{e['ator']}` | `{e['hash_registro'][:20]}…` |"
           for e in trilha["auditoria"]]
    md += ["", f"Hash SHA-256 do payload gravado na leitura: `{trilha['leitura']['hash_payload']}`", ""]

    # 3. Login: forca bruta e permissoes ------------------------------------------
    with sessao() as conn, transacao(conn):
        autenticacao.criar_usuario(conn, "demo_operador", "SenhaDemo123456", "Operador", ator="evidencia")
    respostas = []
    for tentativa in range(1, config.LOGIN_MAX_TENTATIVAS + 2):
        senha = "SenhaDemo123456" if tentativa == config.LOGIN_MAX_TENTATIVAS + 1 else "senha-errada"
        try:
            with sessao() as conn:
                autenticacao.autenticar(conn, "demo_operador", senha)
            respostas.append((tentativa, senha != "senha-errada", "login aceito"))
        except AcessoNegado as erro:
            respostas.append((tentativa, senha != "senha-errada", str(erro)))
    md += ["## 3. Autenticação do dashboard: força bruta e mensagens genéricas", "",
           "| Tentativa | Senha correta? | Resultado |", "|---|---|---|"]
    md += [f"| {t} | {'sim' if ok else 'não'} | {msg} |" for t, ok, msg in respostas]
    try:
        with sessao() as conn:
            autenticacao.exigir_permissao(conn, "demo_operador", "Operador", "editar_regras")
    except AcessoNegado as erro:
        md += ["", f"**Permissão por perfil:** Operador tentando editar regras → `{erro}` (evento `ACESSO_NEGADO` "
                   "gravado na auditoria).", ""]
    with sessao() as conn:
        hash_senha = conn.execute("SELECT hash_senha FROM usuarios WHERE login = 'demo_operador'").fetchone()[0]
        eventos = conn.execute("""SELECT evento, COUNT(*) FROM auditoria WHERE ator IN ('demo_operador', 'ip:testclient')
                                  GROUP BY evento ORDER BY evento""").fetchall()
    md += [f"Como a senha fica guardada no banco: `{hash_senha[:44]}…` (PBKDF2-SHA256; a senha nunca é gravada).", "",
           "Eventos de segurança registrados nesta execução: " +
           ", ".join(f"`{e}` ×{n}" for e, n in eventos) + ".", ""]

    # 4. Log tecnico ------------------------------------------------------------
    linhas = (TMP / "logs" / "somprev.log").read_text(encoding="utf-8").splitlines()
    amostra = [l for l in linhas if '"Acesso negado' in l][:2] + [l for l in linhas if "Leitura processada" in l][:1] \
        + [l for l in linhas if '"requisicao"' in l][:2]
    (config.EVIDENCIAS_DIR / "amostra_log.jsonl").write_text("\n".join(amostra) + "\n", encoding="utf-8")
    md += ["## 4. Log técnico estruturado (JSON)", "",
           "Cada linha de `logs/somprev.log` é um JSON com horário, nível, módulo e contexto. A chave de API nunca "
           "aparece. Amostra completa em [`amostra_log.jsonl`](amostra_log.jsonl):", "",
           bloco("\n".join(json.dumps(json.loads(l), ensure_ascii=False) for l in amostra[:3])), ""]

    # 5. Adulteracao -------------------------------------------------------------
    with sessao() as conn:
        antes = auditoria.verificar_cadeia(conn)
        try:
            conn.execute("UPDATE auditoria SET status = 'SUCESSO' WHERE auditoria_id = 5")
            bloqueado = "não"
        except Exception as erro:  # trigger append-only
            bloqueado = f"sim — `{erro}`"
        conn.execute("DROP TRIGGER trg_auditoria_sem_update")
        conn.execute("UPDATE auditoria SET detalhes = '{\"adulterado\": true}' WHERE auditoria_id = 5")
        depois = auditoria.verificar_cadeia(conn)
    md += ["## 5. Integridade da trilha de auditoria", "",
           f"1. Verificação antes: **{antes.resumo()}**",
           f"2. `UPDATE` direto na tabela de auditoria foi bloqueado? **{bloqueado}**",
           "3. Simulando um atacante com acesso ao arquivo (remove o trigger e altera o evento #5)…",
           f"4. Verificação depois: **{depois.resumo()}**", "",
           "Conclusão: a trilha é somente-inserção e qualquer adulteração é detectada e localizada.", ""]

    destino = config.EVIDENCIAS_DIR / "seguranca_rastreabilidade.md"
    destino.write_text("\n".join(md), encoding="utf-8")
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"[OK] {destino}\n[OK] {config.EVIDENCIAS_DIR / 'amostra_log.jsonl'}")


if __name__ == "__main__":
    main()
