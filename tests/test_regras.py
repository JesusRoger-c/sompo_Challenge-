"""Regras de negocio: score, faixas, alertas explicitos e versionamento das regras."""

import copy

import pytest

from somprev import regras
from somprev.excecoes import DadoInvalido


@pytest.fixture()
def r():
    return regras.carregar_regras()


def test_prob_para_score_limita_e_arredonda():
    assert regras.prob_para_score(0.0) == 0
    assert regras.prob_para_score(0.504) == 50
    assert regras.prob_para_score(1.7) == 100
    assert regras.prob_para_score(-0.2) == 0


@pytest.mark.parametrize("score,classe", [(0, "Baixo"), (14, "Baixo"), (15, "Medio"), (39, "Medio"),
                                          (40, "Alto"), (69, "Alto"), (70, "Critico"), (100, "Critico")])
def test_fronteiras_das_faixas(r, score, classe):
    assert regras.classificar(score, r) == classe


def test_faixas_com_lacuna_sao_recusadas(r):
    ruim = copy.deepcopy(r)
    ruim["faixas_score"]["Medio"] = [16, 39]
    with pytest.raises(DadoInvalido):
        regras.validar_regras(ruim)


def test_limiar_invalido_e_recusado(r):
    ruim = copy.deepcopy(r)
    ruim["alerta_modelo"]["limiar_score"] = 0
    with pytest.raises(DadoInvalido):
        regras.validar_regras(ruim)


def test_regras_corrompidas_usam_padrao_seguro(tmp_path):
    arq = tmp_path / "regras.json"
    arq.write_text("{ isto nao e json", encoding="utf-8")
    assert regras.carregar_regras(arq)["versao"].endswith("padrao")


def _leitura(**kw):
    base = dict(umidade_solo_pct=40, precipitacao_24h_mm=5, temperatura_c=25, tipo_solo="Arenoso",
                declividade_graus=5, distancia_corpo_dagua_m=900, tipo_operacao="Plantio",
                idade_equipamento_anos=3, horas_desde_manutencao=100, horas_operacao_dia=8, carga_pct=70,
                periodo_dia="Manha")
    base.update(kw)
    return base


def test_score_baixo_sem_gatilho_nao_gera_alerta(r):
    assert regras.avaliar_alertas(_leitura(), 5, "Baixo", [], r) == []


def test_score_no_limiar_gera_alerta_com_criterio_explicito(r):
    limiar = r["alerta_modelo"]["limiar_score"]
    alertas = regras.avaliar_alertas(_leitura(), limiar, regras.classificar(limiar, r), ["umidade_solo_pct"], r)
    assert len(alertas) == 1
    assert alertas[0].tipo == "RISCO_MODELO"
    assert f"≥ limiar de alerta {limiar}" in alertas[0].criterio


def test_gatilho_area_alagavel_dispara_mesmo_com_score_baixo(r):
    alertas = regras.avaliar_alertas(_leitura(distancia_corpo_dagua_m=80, umidade_solo_pct=90), 5, "Baixo", [], r)
    codigos = {a.codigo for a in alertas}
    assert "AREA_ALAGAVEL" in codigos
    alerta = next(a for a in alertas if a.codigo == "AREA_ALAGAVEL")
    assert "Distância da água < 200" in alerta.criterio and alerta.perfil_destino == "Operador"


def test_gatilho_de_manutencao_vai_para_o_tecnico(r):
    alertas = regras.avaliar_alertas(_leitura(horas_desde_manutencao=500), 5, "Baixo", [], r)
    manut = [a for a in alertas if a.tipo == "MANUTENCAO"]
    assert manut and all(a.perfil_destino == "Tecnico" for a in manut)


def test_recomendacao_inclui_acao_do_fator_principal():
    texto = regras.recomendacao("Alto", ["declividade_graus", "carga_pct"])
    assert "evite trechos inclinados" in texto and "reduza a carga" in texto
    assert "Ações sugeridas" not in regras.recomendacao("Baixo", ["declividade_graus"])


def test_salvar_regras_incrementa_versao(tmp_path, r):
    arq = tmp_path / "regras.json"
    arq.write_text(__import__("json").dumps(r), encoding="utf-8")
    novas = copy.deepcopy(r)
    novas["alerta_modelo"]["limiar_score"] = 20
    salvas = regras.salvar_regras(novas, "gestor", arq)
    assert salvas["versao"] != r["versao"] and salvas["atualizado_por"] == "gestor"
    assert regras.carregar_regras(arq)["alerta_modelo"]["limiar_score"] == 20


def test_economia_estimada():
    r = regras.carregar_regras()
    eco = r["economia"]
    assert regras.estimar_economia(10, r) == pytest.approx(10 * eco["custo_medio_sinistro_brl"] * eco["taxa_prevencao"])
