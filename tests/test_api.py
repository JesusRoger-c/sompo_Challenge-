"""API: autenticacao por escopo, processamento, erros tratados, rastreabilidade e limites."""

import pytest

from somprev import config
from somprev.banco.conexao import sessao

ING = {"X-API-Key": "chave-ingestao-de-teste-0123456789"}
CON = {"X-API-Key": "chave-consulta-de-teste-0123456789"}
LEITURA = {"data_hora": "2026-09-10 07:30:00", "equipamento_id": "EQ-004", "regiao_id": 4,
           "umidade_solo_pct": 90, "precipitacao_24h_mm": 70, "temperatura_c": 18, "tipo_solo": "Argiloso",
           "declividade_graus": 12, "distancia_corpo_dagua_m": 120, "tipo_operacao": "Colheita",
           "idade_equipamento_anos": None, "horas_desde_manutencao": 300, "horas_operacao_dia": 9,
           "carga_pct": 90, "periodo_dia": "Manha"}


def test_health(cliente_api):
    r = cliente_api.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.parametrize("headers,codigo", [({}, 401), ({"X-API-Key": "falsa"}, 401), (CON, 403)])
def test_ingestao_exige_chave_de_ingestao(cliente_api, headers, codigo):
    r = cliente_api.post("/telemetria", json=LEITURA, headers=headers)
    assert r.status_code == codigo
    assert "erro" in r.json() and "X-Request-ID" in r.headers


def test_consulta_nao_aceita_chave_de_ingestao(cliente_api):
    assert cliente_api.get("/alertas", headers=ING).status_code == 403


def test_leitura_valida_ponta_a_ponta(cliente_api):
    r = cliente_api.post("/telemetria", json=LEITURA, headers=ING)
    assert r.status_code == 201
    corpo = r.json()
    assert 0 <= corpo["score_risco"] <= 100 and corpo["classe_risco"] in ("Baixo", "Medio", "Alto", "Critico")
    assert len(corpo["fatores"]) == 3 and corpo["recomendacao"]
    assert corpo["modelo_versao"] and corpo["regras_versao"] and len(corpo["recibo_auditoria"]) == 64
    assert "idade_equipamento_anos imputada pelo cadastro" in corpo["avisos_qualidade"]
    assert any(a["codigo"] == "AREA_ALAGAVEL" for a in corpo["alertas"])

    trilha = cliente_api.get(f"/leituras/{corpo['leitura_id']}", headers=CON).json()
    eventos = [e["evento"] for e in trilha["auditoria"]]
    assert eventos[:2] == ["TELEMETRIA_RECEBIDA", "PREDICAO_GERADA"]
    assert trilha["leitura"]["hash_payload"] and trilha["leitura"]["origem"] == "api"


def test_reenvio_e_bloqueado(cliente_api):
    assert cliente_api.post("/telemetria", json=LEITURA, headers=ING).status_code == 201
    r = cliente_api.post("/telemetria", json=LEITURA, headers=ING)
    assert r.status_code == 409 and "duplicada" in r.json()["erro"].lower()


def test_leitura_sem_critico_vai_para_quarentena(cliente_api):
    r = cliente_api.post("/telemetria", json={**LEITURA, "declividade_graus": None}, headers=ING)
    assert r.status_code == 422
    with sessao() as conn:
        q = conn.execute("SELECT motivo FROM leituras_quarentena WHERE origem = 'api'").fetchall()
        rej = conn.execute("SELECT COUNT(*) FROM auditoria WHERE evento = 'TELEMETRIA_REJEITADA'").fetchone()[0]
    assert q and "declividade_graus" in q[-1][0] and rej == 1


def test_campo_desconhecido_e_recusado(cliente_api):
    r = cliente_api.post("/telemetria", json={**LEITURA, "houve_sinistro": 1}, headers=ING)
    assert r.status_code == 422


def test_regiao_inexistente(cliente_api):
    assert cliente_api.post("/telemetria", json={**LEITURA, "regiao_id": 99}, headers=ING).status_code == 404


def test_lote_misto_nao_interrompe(cliente_api):
    lote = {"leituras": [
        {**LEITURA, "data_hora": "2026-09-11 07:00:00"},
        {**LEITURA, "data_hora": "2026-09-11 08:00:00", "equipamento_id": "EQ-999"},
        {**LEITURA, "data_hora": "2026-09-11 07:00:00"},
        {**LEITURA, "data_hora": "2026-09-11 09:00:00", "umidade_solo_pct": "77,5"}]}
    r = cliente_api.post("/telemetria/lote", json=lote, headers=ING).json()
    assert [i["status"] for i in r["itens"]] == ["processada", "rejeitada", "duplicada", "processada"]
    assert r["processadas"] == 2


def test_erro_inesperado_nao_vaza_detalhes(cliente_api, monkeypatch):
    from somprev.servicos import processamento

    def quebrar(*a, **k):
        raise RuntimeError("detalhe-interno-secreto")
    monkeypatch.setattr(processamento, "processar_leitura", quebrar)
    from fastapi.testclient import TestClient

    from somprev.api.app import app
    r = TestClient(app, raise_server_exceptions=False).post("/telemetria", json=LEITURA, headers=ING)
    assert r.status_code == 500
    assert "detalhe-interno-secreto" not in r.text and r.json()["id_requisicao"]


def test_limite_de_requisicoes(cliente_api, monkeypatch):
    monkeypatch.setattr(config, "API_LIMITE_REQ_MINUTO", 3)
    codigos = [cliente_api.get("/alertas?limite=1", headers=CON).status_code for _ in range(5)]
    assert codigos[:3] == [200, 200, 200] and codigos[3] == 429


def test_consultas_de_relatorio_e_modelo(cliente_api):
    r = cliente_api.get("/relatorios/tendencias?dimensao=tipo_operacao&dias=30", headers=CON)
    assert r.status_code == 200 and r.json()["serie_semanal"]
    assert cliente_api.get("/modelo", headers=CON).json()["versao"]
    assert cliente_api.get("/auditoria/verificar", headers=CON).json()["integra"] is True
    risco = cliente_api.get("/equipamentos/EQ-001/risco", headers=CON).json()
    assert risco["classe_risco"] in ("Baixo", "Medio", "Alto", "Critico")
    assert cliente_api.get("/equipamentos/EQ-999/risco", headers=CON).status_code == 404


def test_rotas_de_consulta_que_alimentam_o_dashboard(cliente_api):
    """O dashboard nao le mais o banco por fora: estas sao as rotas que ele consome
    (somprev/dashboard/cliente_api.py). Todas exigem a chave de escopo "consulta"."""
    for rota in ("/leituras", "/equipamentos", "/manutencoes", "/quarentena", "/auditoria", "/verificacao"):
        assert cliente_api.get(rota, headers=ING).status_code == 403, rota
        assert cliente_api.get(rota).status_code == 401, rota

    leituras = cliente_api.get("/leituras", headers=CON).json()
    assert leituras["total"] > 0 and leituras["leituras"][0]["score_risco"] is not None

    equipamentos = cliente_api.get("/equipamentos", headers=CON).json()
    assert equipamentos["total"] > 0 and "regiao_base" in equipamentos["equipamentos"][0]

    # manutencoes e quarentena podem estar vazias na base simulada, mas a rota precisa responder
    assert cliente_api.get("/manutencoes", headers=CON).json()["total"] >= 0
    assert cliente_api.get("/quarentena", headers=CON).json()["total"] >= 0

    eventos = cliente_api.get("/auditoria?limite=5", headers=CON).json()
    assert 0 < eventos["total"] <= 5

    verificacao = cliente_api.get("/verificacao", headers=CON).json()
    assert verificacao["ok"] is True and len(verificacao["verificacoes"]) == 12
