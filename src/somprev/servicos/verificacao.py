"""
Verificacoes de integridade e consistencia do sistema (evidencia de validacao).

Cada verificacao devolve um item {nome, ok, detalhe}. O conjunto e executado
ao final do pipeline, pelo comando `python run.py verificar`, pelos testes
automatizados e pela visao da Seguradora no dashboard.
"""

from __future__ import annotations

import json
import sqlite3

from .. import config
from ..modelo.treino import sha256_arquivo
from ..seguranca.auditoria import verificar_cadeia


def _item(nome: str, ok: bool, detalhe: str) -> dict:
    return {"verificacao": nome, "ok": bool(ok), "detalhe": detalhe}


def verificar_sistema(conn: sqlite3.Connection) -> list[dict]:
    itens = []

    integridade = conn.execute("PRAGMA integrity_check").fetchone()[0]
    itens.append(_item("Integridade física do banco (PRAGMA integrity_check)", integridade == "ok", integridade))

    fks = conn.execute("PRAGMA foreign_key_check").fetchall()
    itens.append(_item("Chaves estrangeiras sem órfãos", not fks, f"{len(fks)} violações"))

    sem_pred = conn.execute("""SELECT COUNT(*) FROM leituras l LEFT JOIN predicoes p ON p.leitura_id = l.leitura_id
                               WHERE p.predicao_id IS NULL""").fetchone()[0]
    itens.append(_item("Toda leitura aceita tem predição (sem perda)", sem_pred == 0,
                       f"{sem_pred} leituras sem predição"))

    fora = conn.execute("SELECT COUNT(*) FROM predicoes WHERE score_risco NOT BETWEEN 0 AND 100 "
                        "OR prob_sinistro NOT BETWEEN 0 AND 1").fetchone()[0]
    itens.append(_item("Scores e probabilidades dentro da faixa", fora == 0, f"{fora} fora da faixa"))

    incoerente = conn.execute("SELECT COUNT(*) FROM predicoes WHERE ABS(score_risco - ROUND(prob_sinistro * 100)) > 1"
                              ).fetchone()[0]
    itens.append(_item("Score coerente com a probabilidade gravada", incoerente == 0, f"{incoerente} divergências"))

    sem_versao = conn.execute("SELECT COUNT(*) FROM predicoes WHERE modelo_versao IS NULL OR regras_versao IS NULL"
                              ).fetchone()[0]
    itens.append(_item("Toda predição rastreável (versão do modelo e das regras)", sem_versao == 0,
                       f"{sem_versao} sem versão"))

    dup = conn.execute("SELECT COUNT(*) FROM (SELECT equipamento_id, data_hora FROM leituras "
                       "GROUP BY 1, 2 HAVING COUNT(*) > 1)").fetchone()[0]
    itens.append(_item("Sem leituras duplicadas (mesma máquina, mesmo instante)", dup == 0, f"{dup} duplicidades"))

    nulos = conn.execute("""SELECT COUNT(*) FROM leituras WHERE umidade_solo_pct IS NULL OR precipitacao_24h_mm IS NULL
                            OR declividade_graus IS NULL OR distancia_corpo_dagua_m IS NULL OR tipo_solo IS NULL
                            OR tipo_operacao IS NULL""").fetchone()[0]
    itens.append(_item("Sem valores ausentes nas variáveis do modelo", nulos == 0, f"{nulos} leituras incompletas"))

    cadeia = verificar_cadeia(conn)
    itens.append(_item("Trilha de auditoria íntegra (cadeia de hashes)", cadeia.integra, cadeia.resumo()))

    ativo = conn.execute("SELECT versao, hash_artefato FROM modelo_versoes WHERE ativo = 1").fetchone()
    if ativo and config.MODELO_PATH.exists():
        confere = sha256_arquivo(config.MODELO_PATH) == ativo["hash_artefato"]
        itens.append(_item("Artefato do modelo confere com a versão registrada (SHA-256)", confere,
                           f"versão ativa {ativo['versao']}"))
    else:
        itens.append(_item("Artefato do modelo confere com a versão registrada (SHA-256)", False,
                           "modelo ou registro de versão ausente"))

    senhas = conn.execute("SELECT COUNT(*) FROM usuarios WHERE hash_senha NOT LIKE 'pbkdf2_sha256$%'").fetchone()[0]
    itens.append(_item("Nenhuma senha armazenada sem hash", senhas == 0, f"{senhas} senhas fora do padrão"))

    if config.RELATORIO_QUALIDADE_JSON.exists():
        rel = json.loads(config.RELATORIO_QUALIDADE_JSON.read_text(encoding="utf-8"))
        duplicadas = sum(rel["duplicidades"].values())
        fecha = rel["recebidas"] == rel["aceitas"] + rel["quarentena_total"] + duplicadas
        historico = conn.execute("SELECT COUNT(*) FROM leituras WHERE origem = 'carga_historica'").fetchone()[0]
        quarent = conn.execute("SELECT COUNT(*) FROM leituras_quarentena WHERE origem = 'carga_historica'"
                               ).fetchone()[0]
        ok = fecha and historico == rel["aceitas"] and quarent == rel["quarentena_total"]
        itens.append(_item("Reconciliação da coleta: recebidas = aceitas + quarentena + duplicadas", ok,
                           f"{rel['recebidas']} = {rel['aceitas']} + {rel['quarentena_total']} + {duplicadas}; "
                           f"banco: {historico} aceitas, {quarent} em quarentena"))
    return itens
