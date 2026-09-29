"""Qualidade de dados: conversoes, limpeza em lote, imputacao e quarentena."""

import numpy as np
import pandas as pd
import pytest

from somprev.dados import gerador, qualidade
from somprev.esquema import FEATURES, normalizar_categoria
from somprev.excecoes import DadoInvalido


@pytest.mark.parametrize("entrada,esperado", [("55,3", 55.3), (" 12 ", 12.0), (7, 7.0), ("abc", None),
                                              (None, None), (float("nan"), None), ("", None)])
def test_converter_numero(entrada, esperado):
    assert qualidade.converter_numero(entrada) == esperado


@pytest.mark.parametrize("campo,entrada,esperado", [
    ("periodo_dia", "Manhã", "Manha"), ("periodo_dia", " MANHA ", "Manha"),
    ("tipo_operacao", "pulverização", "Pulverizacao"), ("tipo_operacao", "COLHEITA", "Colheita"),
    ("tipo_solo", "Pedregoso", None), ("tipo_solo", None, None)])
def test_normalizar_categoria(campo, entrada, esperado):
    assert normalizar_categoria(campo, entrada) == esperado


@pytest.fixture(scope="module")
def base():
    cadastro, leituras = gerador.gerar_base(seed=123)
    bruto, falhas = gerador.simular_coleta_bruta(leituras, seed=123)
    return cadastro, leituras, bruto, falhas, qualidade.tratar_lote(bruto, cadastro)


def test_gerador_e_reprodutivel():
    _, a = gerador.gerar_base(seed=5)
    _, b = gerador.gerar_base(seed=5)
    pd.testing.assert_frame_equal(a, b)


def test_cadastro_fixo_idade_coerente(base):
    cadastro, leituras, *_ = base
    # Na v1 a idade de uma mesma maquina variava por leitura; agora cresce com o tempo.
    for eq, grupo in leituras.groupby("equipamento_id"):
        idades = grupo.sort_values("data_hora")["idade_equipamento_anos"]
        assert idades.is_monotonic_increasing, eq
        assert idades.max() - idades.min() < 0.6


def test_reconciliacao_do_lote(base):
    *_, res = base
    rel = res.relatorio
    assert rel["recebidas"] == rel["aceitas"] + rel["quarentena_total"] + sum(rel["duplicidades"].values())


def test_saida_sem_ausentes_nem_duplicadas(base):
    *_, res = base
    t = res.tratado
    assert t[FEATURES].isna().sum().sum() == 0
    assert not t.duplicated(["equipamento_id", "data_hora"]).any()
    assert t["leitura_id"].is_unique


def test_valores_fisicamente_impossiveis_nao_passam(base):
    *_, res = base
    t = res.tratado
    assert t["umidade_solo_pct"].between(0, 100).all()
    assert (t["precipitacao_24h_mm"] >= 0).all()
    assert t["carga_pct"].between(0, 150).all()
    assert t["tipo_solo"].isin(["Arenoso", "Misto", "Argiloso", "Encharcado"]).all()


def test_falhas_injetadas_foram_tratadas(base):
    *_, falhas, res = base
    rel = res.relatorio
    assert rel["duplicidades"]["pacote_reenviado_identico"] == falhas["pacote_reenviado"]
    assert rel["duplicidades"]["mesma_maquina_mesmo_instante"] == falhas["reenvio_novo_id"]
    assert rel["quarentena"]["equipamento fora do cadastro"] == falhas["equipamento_desconhecido"]
    assert rel["quarentena"]["data_hora inválida"] == falhas["data_corrompida"]
    assert rel["taxa_aproveitamento"] > 0.95


def test_imputacao_climatica_e_fiel(base):
    _, leituras, _, _, res = base
    comp = res.tratado.merge(leituras, on="leitura_id", suffixes=("", "_real"))
    # A chuva e compartilhada pela regiao no dia: a imputacao pela mediana e exata.
    assert np.allclose(comp["precipitacao_24h_mm"], comp["precipitacao_24h_mm_real"])
    # A idade vem do cadastro (fonte mestre).
    assert np.allclose(comp["idade_equipamento_anos"], comp["idade_equipamento_anos_real"], atol=0.11)


def test_toda_correcao_fica_registrada(base):
    *_, res = base
    corrigidas = res.tratado[res.tratado["qualidade_status"] == "CORRIGIDO"]
    assert len(corrigidas) > 0 and corrigidas["qualidade_obs"].notna().all()
    assert res.quarentena["motivo"].notna().all()


CADASTRO_EQ = {"equipamento_id": "EQ-001", "data_fabricacao": "2020-01-01"}
REGISTRO = dict(data_hora="2026-09-01 08:00:00", equipamento_id="EQ-001", regiao_id=1, umidade_solo_pct=50,
                precipitacao_24h_mm=10, temperatura_c=25, tipo_solo="Misto", declividade_graus=8,
                distancia_corpo_dagua_m=600, tipo_operacao="Plantio", idade_equipamento_anos=6.7,
                horas_desde_manutencao=120, horas_operacao_dia=8, carga_pct=70, periodo_dia="Manha")


def test_registro_valido_passa_sem_avisos():
    r = qualidade.tratar_registro(REGISTRO, CADASTRO_EQ)
    assert r.status == "OK" and r.avisos == []


def test_registro_fora_da_faixa_e_imputado_com_aviso():
    r = qualidade.tratar_registro({**REGISTRO, "umidade_solo_pct": 140}, CADASTRO_EQ, referencia=lambda v, l: 61.0)
    assert r.leitura["umidade_solo_pct"] == 61.0
    assert any("fora da faixa" in a for a in r.avisos)


def test_registro_idade_divergente_e_corrigida_pelo_cadastro():
    r = qualidade.tratar_registro({**REGISTRO, "idade_equipamento_anos": 20}, CADASTRO_EQ)
    assert r.leitura["idade_equipamento_anos"] == pytest.approx(6.7, abs=0.1)


def test_registro_sem_critico_e_rejeitado():
    with pytest.raises(DadoInvalido) as erro:
        qualidade.tratar_registro({**REGISTRO, "declividade_graus": None}, CADASTRO_EQ)
    assert "declividade_graus ausente e não imputável" in erro.value.detalhes["erros"]


def test_registro_equipamento_desconhecido_e_data_invalida():
    with pytest.raises(DadoInvalido) as erro:
        qualidade.tratar_registro({**REGISTRO, "data_hora": "ontem"}, None)
    assert len(erro.value.detalhes["erros"]) == 2
