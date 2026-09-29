"""Modelo: artefato, metricas, calibracao, explicacao e comparacao com a Sprint 3."""

import json

import numpy as np
import pandas as pd
import pytest

from somprev import config, regras
from somprev.dados import gerador
from somprev.esquema import FEATURES
from somprev.excecoes import ModeloIndisponivel
from somprev.modelo.inferencia import ModeloRisco, carregar_modelo, top_fatores


@pytest.fixture(scope="module")
def metricas(ambiente):
    return json.loads(config.METRICAS_PATH.read_text(encoding="utf-8"))


def test_artefato_versionado_e_rastreavel(ambiente, metricas):
    m = carregar_modelo()
    assert m.versao == metricas["versao_modelo"] and m.versao.endswith("v2.0")
    card = json.loads(config.MODEL_CARD_PATH.read_text(encoding="utf-8"))
    assert card["hash_artefato_sha256"] == metricas["hash_artefato_sha256"]
    assert card["limitacoes"]


def test_validacao_e_temporal(metricas):
    d = metricas["divisao_temporal"]
    assert d["treino"]["periodo"].split(" a ")[1] < d["validacao"]["periodo"].split(" a ")[0]
    assert d["validacao"]["periodo"].split(" a ")[1] < d["teste"]["periodo"].split(" a ")[0]


def test_metricas_minimas_no_teste(metricas):
    final = metricas["modelo_final_teste"]
    assert final["roc_auc"] > 0.80
    assert final["pr_auc"] > 0.60
    assert final["recall"] >= 0.70


def test_supera_a_receita_da_sprint3_em_recall_e_custo(metricas):
    s3 = metricas["comparacao"]["Receita Sprint 3"]
    assert metricas["modelo_final_teste"]["recall"] > s3["teste_limiar"]["recall"]
    custos = metricas["analise_limiar"]["custo_esperado_teste_brl"]
    assert custos["modelo_final"] < custos["receita_sprint3"] < custos["sem_modelo"]


def test_taxa_real_cresce_com_a_faixa(metricas):
    taxas = [f["taxa_real_sinistro"] for f in metricas["taxa_real_por_faixa_teste"] if f["leituras"] >= 10]
    assert taxas == sorted(taxas), "faixas mais graves devem ter mais sinistros reais"


def test_probabilidades_validas(ambiente):
    df = pd.read_csv(config.DADOS_TRATADOS_CSV).head(300)
    p = carregar_modelo().prever(df)
    assert ((p >= 0) & (p <= 1)).all()


def test_cenarios_curados_ordenados(ambiente):
    cen = gerador.cenarios_exemplo()
    scores = [regras.prob_para_score(p) for p in carregar_modelo().prever(cen)]
    baixos, criticos = scores[:2], scores[-3:]
    assert max(baixos) < min(criticos)
    assert all(regras.classificar(s) == "Baixo" for s in baixos)
    assert all(regras.classificar(s) in ("Alto", "Critico") for s in criticos)


def test_explicacao_aponta_causas_plausiveis(ambiente):
    cen = gerador.cenarios_exemplo()
    critico = cen.iloc[[8]]      # solo encharcado, 40 m da agua, chuva forte
    contrib = carregar_modelo().explicar(critico)[0]
    top = top_fatores(contrib)
    assert set(top) & {"umidade_solo_pct", "distancia_corpo_dagua_m", "precipitacao_24h_mm", "tipo_solo"}
    assert contrib[top[0]] > 0


def test_explicacao_e_deterministica(ambiente):
    cen = gerador.cenarios_exemplo().iloc[[5]]
    m = carregar_modelo()
    assert m.explicar(cen) == m.explicar(cen)


def test_modelo_ausente_gera_erro_claro(tmp_path):
    with pytest.raises(ModeloIndisponivel):
        carregar_modelo(tmp_path / "nao_existe.pkl")


def test_artefato_incompativel_e_recusado():
    with pytest.raises(ModeloIndisponivel):
        ModeloRisco({"modelo": None, "versao": "x", "features": FEATURES[:-1], "referencia": {}})
