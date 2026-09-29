"""Integracao de ponta a ponta: pipeline, consistencia do banco, simulador e relatorios."""

from somprev import config
from somprev.banco import repositorio as repo
from somprev.banco.conexao import sessao
from somprev.relatorios import tendencias
from somprev.servicos import simulador
from somprev.servicos.verificacao import verificar_sistema


def test_pipeline_gera_todos_os_artefatos(ambiente):
    for caminho in (config.DADOS_BRUTOS_CSV, config.DADOS_TRATADOS_CSV, config.CADASTRO_EQUIP_CSV,
                    config.RELATORIO_QUALIDADE_JSON, config.MODELO_PATH, config.METRICAS_PATH,
                    config.MODEL_CARD_PATH, config.DB_PATH, config.RELATORIOS_DIR / "relatorio_tendencias.md"):
        assert caminho.exists(), caminho


def test_todas_as_verificacoes_do_sistema_passam(ambiente):
    with sessao() as conn:
        itens = verificar_sistema(conn)
    falhas = [i for i in itens if not i["ok"]]
    assert not falhas, falhas


def test_alertas_ativos_nao_se_duplicam(ambiente):
    with sessao() as conn:
        dup = conn.execute("""SELECT equipamento_id, codigo, COUNT(*) FROM alertas
                              WHERE status != 'resolvido' GROUP BY 1, 2 HAVING COUNT(*) > 1""").fetchall()
    assert dup == []


def test_toda_predicao_tem_explicacao_e_versoes(ambiente):
    with sessao() as conn:
        n = conn.execute("""SELECT COUNT(*) FROM predicoes WHERE explicacao_json IS NULL OR fator_1 IS NULL
                            OR modelo_versao IS NULL OR regras_versao IS NULL""").fetchone()[0]
    assert n == 0


def test_simulador_reconcilia_sem_perda(cliente_api):
    resumo = simulador.executar(cliente_api, quantidade=80, taxa_falhas=0.35, seed=11)
    assert resumo["reconciliacao_ok"]
    assert resumo["erros_inesperados"] == 0
    assert resumo["leituras_aceitas_sem_rastro"] == 0
    assert resumo["respostas_conforme_esperado"] == resumo["enviadas"]
    assert resumo["cadeia_auditoria"]["integra"] is True
    with sessao() as conn:
        assert conn.execute("SELECT COUNT(*) FROM leituras WHERE origem = 'api'").fetchone()[0] == resumo["processadas"]
        itens = verificar_sistema(conn)
    assert all(i["ok"] for i in itens if "Reconciliação" not in i["verificacao"])


def test_tendencias_por_dimensao(ambiente):
    with sessao() as conn:
        df = repo.carregar_leituras_risco(conn)
        alertas = repo.carregar_alertas(conn)
    for dim in ("regiao_nome", "tipo_operacao", "equipamento_id"):
        tab = tendencias.tendencia(df, dim)
        assert not tab.empty and tab["score_medio"].between(0, 100).all()
    var = tendencias.variacao_recente(df, "regiao_nome")
    assert set(var["tendencia"]) <= {"subindo", "caindo", "estável"}
    rank = tendencias.ranking_equipamentos(df, alertas)
    assert rank["score_medio"].is_monotonic_decreasing
    assert tendencias.insights(df, alertas)


def test_sazonalidade_regional_capturada(ambiente):
    """Cerrado seca no inverno (risco cai); Sul chove mais (risco sobe) - tendencia real nos dados."""
    with sessao() as conn:
        df = repo.carregar_leituras_risco(conn)
    df["mes"] = df["data_hora"].dt.month
    cerrado = df[df["regime"] == "cerrado"].groupby("mes")["score_risco"].mean()
    sul = df[df["regime"] == "sul"].groupby("mes")["score_risco"].mean()
    assert cerrado[3] > cerrado[8] + 15
    assert sul[8] > cerrado[8] + 20
