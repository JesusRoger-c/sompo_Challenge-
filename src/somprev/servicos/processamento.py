"""
Servico de processamento de ponta a ponta de leituras de telemetria.

E o "coracao" do MVP: o MESMO codigo atende a carga historica (lote), a API em
tempo real e o simulador de telemetria. Assim o score de uma leitura e sempre
calculado do mesmo jeito, venha ela de onde vier.

Fluxo de uma leitura:

    entrada -> qualidade (validar/corrigir/imputar ou quarentena)
            -> duplicidade? -> modelo (probabilidade calibrada)
            -> score 0-100 -> faixa -> explicacao (top 3 fatores)
            -> regras de alerta (limiar + gatilhos) -> agrupamento de alertas
            -> persistencia atomica (leitura + predicao + alertas + auditoria)
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime

import pandas as pd

from .. import regras as rg
from ..banco import repositorio as repo
from ..banco.conexao import transacao
from ..dados import qualidade
from ..esquema import FEATURES, ROTULOS
from ..excecoes import DadoInvalido, LeituraDuplicada, RecursoNaoEncontrado
from ..logs import obter_logger
from ..modelo.inferencia import ModeloRisco, carregar_modelo, top_fatores
from ..seguranca import auditoria

log = obter_logger("servicos.processamento")

JANELA_AGRUPAMENTO_H = 48   # repeticoes do mesmo alerta dentro de 48 h viram "ocorrencias"


@dataclass
class ResultadoLeitura:
    leitura_id: int
    equipamento_id: str
    data_hora: str
    score_risco: int
    classe_risco: str
    prob_sinistro: float
    fatores: list[dict]
    recomendacao: str
    alertas: list[dict] = field(default_factory=list)
    qualidade_status: str = "OK"
    avisos_qualidade: list[str] = field(default_factory=list)
    modelo_versao: str = ""
    regras_versao: str = ""
    recibo_auditoria: str | None = None

    def como_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Nucleo compartilhado
# ---------------------------------------------------------------------------
def _horas_entre(a: str, b: str) -> float:
    return abs((pd.Timestamp(a) - pd.Timestamp(b)).total_seconds()) / 3600


def pontuar(modelo: ModeloRisco, leituras: pd.DataFrame, regras_ativas: dict) -> pd.DataFrame:
    """Calcula probabilidade, score, faixa e explicacao para um conjunto de leituras."""
    saida = leituras.copy().reset_index(drop=True)
    probs = modelo.prever(saida[FEATURES])
    explicacoes = modelo.explicar(saida[FEATURES], probs)
    saida["prob_sinistro"] = probs.round(4)
    saida["score_risco"] = [rg.prob_para_score(p) for p in probs]
    saida["classe_risco"] = [rg.classificar(s, regras_ativas) for s in saida["score_risco"]]
    saida["_contrib"] = explicacoes
    saida["_fatores"] = [top_fatores(c) for c in explicacoes]
    return saida


def _persistir(conn: sqlite3.Connection, pontuadas: pd.DataFrame, origem: str, ator: str,
               modelo: ModeloRisco, regras_ativas: dict, auditar_cada: bool,
               cache_alertas: dict | None = None) -> list[ResultadoLeitura]:
    """Grava leituras, predicoes, alertas e auditoria. Deve rodar dentro de uma transacao."""
    repo.inserir_leituras(conn, pontuadas.to_dict("records"))
    resultados: list[ResultadoLeitura] = []
    usar_cache = cache_alertas is not None

    for linha in pontuadas.to_dict("records"):
        fatores = linha["_fatores"]
        contrib = linha["_contrib"]
        predicao_id = repo.inserir_predicao(conn, {
            "leitura_id": linha["leitura_id"], "score_risco": linha["score_risco"],
            "classe_risco": linha["classe_risco"], "prob_sinistro": linha["prob_sinistro"],
            "fator_1": fatores[0], "fator_2": fatores[1], "fator_3": fatores[2],
            "explicacao_json": json.dumps(contrib, ensure_ascii=False),
            "modelo_versao": modelo.versao, "regras_versao": regras_ativas["versao"],
            "criado_em": linha["data_hora"] if origem == "carga_historica" else datetime.now().isoformat(timespec="seconds"),
        })
        alertas_saida = []
        for alerta in rg.avaliar_alertas(linha, linha["score_risco"], linha["classe_risco"], fatores, regras_ativas):
            chave = (linha["equipamento_id"], alerta.codigo)
            aberto = cache_alertas.get(chave) if usar_cache else repo.alerta_aberto(conn, *chave)
            if aberto and _horas_entre(aberto["ultima_ocorrencia"], linha["data_hora"]) <= JANELA_AGRUPAMENTO_H:
                repo.agrupar_ocorrencia(conn, aberto["alerta_id"], linha["data_hora"], alerta.nivel, rg.ORDEM_CLASSE,
                                        alerta.mensagem, alerta.criterio, alerta.recomendacao)
                aberto["ultima_ocorrencia"] = linha["data_hora"]
                alertas_saida.append({**asdict(alerta), "alerta_id": aberto["alerta_id"], "agrupado": True})
                continue
            if aberto:
                # A condicao ficou mais de 48 h sem se repetir: o episodio anterior e
                # encerrado automaticamente e um novo alerta e aberto (sem duplicar ativos).
                repo.encerrar_alerta_expirado(conn, aberto["alerta_id"], linha["data_hora"], JANELA_AGRUPAMENTO_H)
            alerta_id = repo.inserir_alerta(conn, {
                **{k: v for k, v in asdict(alerta).items() if k != "extras"},
                "predicao_id": predicao_id, "leitura_id": linha["leitura_id"],
                "equipamento_id": linha["equipamento_id"], "criado_em": linha["data_hora"],
            })
            if usar_cache:
                cache_alertas[chave] = {"alerta_id": alerta_id, "ultima_ocorrencia": linha["data_hora"]}
            alertas_saida.append({**asdict(alerta), "alerta_id": alerta_id, "agrupado": False})

        resultado = ResultadoLeitura(
            leitura_id=int(linha["leitura_id"]), equipamento_id=linha["equipamento_id"],
            data_hora=linha["data_hora"], score_risco=int(linha["score_risco"]),
            classe_risco=linha["classe_risco"], prob_sinistro=float(linha["prob_sinistro"]),
            fatores=[{"variavel": f, "rotulo": ROTULOS[f], "contribuicao_pontos": contrib[f]} for f in fatores],
            recomendacao=rg.recomendacao(linha["classe_risco"], fatores),
            alertas=[{k: v for k, v in a.items() if k != "extras"} for a in alertas_saida],
            qualidade_status=linha.get("qualidade_status", "OK"),
            avisos_qualidade=[o for o in str(linha.get("qualidade_obs") or "").split("; ") if o],
            modelo_versao=modelo.versao, regras_versao=regras_ativas["versao"],
        )
        if auditar_cada:
            base = {"ator": ator, "leitura_id": resultado.leitura_id, "equipamento_id": resultado.equipamento_id,
                    "modelo_versao": modelo.versao}
            auditoria.registrar(conn, "TELEMETRIA_RECEBIDA", **base,
                                status="AVISO" if resultado.avisos_qualidade else "SUCESSO",
                                detalhes={"origem": origem, "hash_payload": linha.get("hash_payload"),
                                          "qualidade": resultado.qualidade_status,
                                          "avisos": resultado.avisos_qualidade})
            auditoria.registrar(conn, "PREDICAO_GERADA", **base, detalhes={
                "prob": resultado.prob_sinistro, "score": resultado.score_risco, "classe": resultado.classe_risco,
                "fatores": {f: contrib[f] for f in fatores}, "regras": regras_ativas["versao"]})
            for a in resultado.alertas:
                resultado.recibo_auditoria = auditoria.registrar(
                    conn, "ALERTA_AGRUPADO" if a["agrupado"] else "ALERTA_GERADO", **base,
                    detalhes={"alerta_id": a["alerta_id"], "codigo": a["codigo"], "nivel": a["nivel"],
                              "criterio": a["criterio"], "destino": a["perfil_destino"]})
            if resultado.recibo_auditoria is None:
                resultado.recibo_auditoria = conn.execute(
                    "SELECT hash_registro FROM auditoria ORDER BY auditoria_id DESC LIMIT 1").fetchone()[0]
        resultados.append(resultado)
    return resultados


# ---------------------------------------------------------------------------
# Modo LOTE (carga historica)
# ---------------------------------------------------------------------------
def carregar_historico(conn: sqlite3.Connection, tratado: pd.DataFrame, mapa_regioes: dict[str, int],
                       ator: str = "pipeline") -> dict:
    """Pontua e grava a base historica tratada em uma unica transacao."""
    inicio = time.perf_counter()
    modelo = carregar_modelo()
    regras_ativas = rg.carregar_regras()
    df = tratado.copy()
    df["regiao_id"] = df["regiao"].map(mapa_regioes)
    df["origem"] = "carga_historica"
    df["houve_sinistro"] = df["houve_sinistro"].map(lambda v: None if pd.isna(v) else int(v))
    df["qualidade_obs"] = df["qualidade_obs"].map(lambda v: None if pd.isna(v) else str(v))
    df["hash_payload"] = [auditoria.hash_payload({c: r[c] for c in ["leitura_id", "data_hora", "equipamento_id"]
                                                  + FEATURES}) for r in df.to_dict("records")]
    df = df.sort_values("data_hora").reset_index(drop=True)
    pontuadas = pontuar(modelo, df, regras_ativas)
    with transacao(conn):
        resultados = _persistir(conn, pontuadas, "carga_historica", ator, modelo, regras_ativas,
                                auditar_cada=False, cache_alertas={})
        # Alertas historicos sem ocorrencia nos ultimos 3 dias da base sao encerrados.
        fim = pd.Timestamp(df["data_hora"].max())
        encerrados = repo.encerrar_alertas_antigos(conn, (fim - pd.Timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                                                   fim.strftime("%Y-%m-%d %H:%M:%S"))
        resumo = {
            "leituras": len(resultados),
            "por_classe": pontuadas["classe_risco"].value_counts().reindex(rg.CLASSES, fill_value=0).to_dict(),
            "alertas_criados": int(conn.execute("SELECT COUNT(*) FROM alertas").fetchone()[0]),
            "alertas_encerrados_historico": int(encerrados),
            "modelo_versao": modelo.versao, "regras_versao": regras_ativas["versao"],
            "segundos": round(time.perf_counter() - inicio, 1),
        }
        auditoria.registrar(conn, "CARGA_HISTORICA", ator=ator, modelo_versao=modelo.versao, detalhes=resumo)
    return resumo


# ---------------------------------------------------------------------------
# Modo REGISTRO UNICO (API / simulador)
# ---------------------------------------------------------------------------
def processar_leitura(conn: sqlite3.Connection, entrada: dict, origem: str = "api",
                      ator: str = "api") -> ResultadoLeitura:
    """Processa UMA leitura com seguranca transacional e auditoria completa.

    Levanta DadoInvalido / RecursoNaoEncontrado / LeituraDuplicada para erros
    esperados. Leituras rejeitadas vao para a quarentena e ficam auditadas.
    """
    payload_original = dict(entrada)
    hash_entrada = auditoria.hash_payload(payload_original)
    modelo = carregar_modelo()
    regras_ativas = rg.carregar_regras()

    def rejeitar(motivo: str, erro: Exception) -> None:
        with transacao(conn):
            repo.inserir_quarentena(conn, origem, motivo, payload_original, entrada.get("leitura_id"),
                                    entrada.get("equipamento_id"), str(entrada.get("data_hora")))
            auditoria.registrar(conn, "TELEMETRIA_REJEITADA", ator=ator, status="FALHA",
                                equipamento_id=entrada.get("equipamento_id")
                                if repo.obter_equipamento(conn, str(entrada.get("equipamento_id"))) else None,
                                detalhes={"motivo": motivo, "hash_payload": hash_entrada, "origem": origem})
        log.warning("Leitura rejeitada", extra={"contexto": {"motivo": motivo, "origem": origem,
                                                            "equipamento_id": entrada.get("equipamento_id")}})
        raise erro

    regiao = repo.obter_regiao(conn, entrada.get("regiao_id")) if entrada.get("regiao_id") is not None else None
    if regiao is None:
        rejeitar("regiao_id inexistente",
                 RecursoNaoEncontrado(f"Região '{entrada.get('regiao_id')}' não encontrada."))
    equipamento = repo.obter_equipamento(conn, str(entrada.get("equipamento_id")))
    try:
        tratado = qualidade.tratar_registro(
            entrada, equipamento, referencia=lambda var, leit: repo.referencia_imputacao(conn, var, leit))
    except DadoInvalido as erro:
        rejeitar("; ".join(erro.detalhes.get("erros", [erro.mensagem])), erro)

    leitura = tratado.leitura
    leitura_id = leitura.get("leitura_id")
    if leitura_id is not None:
        try:
            leitura_id = int(leitura_id)
            if leitura_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            rejeitar("leitura_id inválido", DadoInvalido("leitura_id deve ser inteiro positivo."))
    duplicada = repo.leitura_existe(conn, leitura_id, leitura["equipamento_id"], leitura["data_hora"])
    if duplicada:
        with transacao(conn):
            auditoria.registrar(conn, "TELEMETRIA_DUPLICADA", ator=ator, status="AVISO",
                                equipamento_id=leitura["equipamento_id"],
                                detalhes={"motivo": duplicada, "hash_payload": hash_entrada})
        raise LeituraDuplicada(f"Leitura duplicada: {duplicada}.")

    with transacao(conn):
        leitura["leitura_id"] = leitura_id or repo.proximo_leitura_id(conn)
        leitura.update({"regiao_id": regiao["regiao_id"], "origem": origem, "hash_payload": hash_entrada,
                        "qualidade_status": tratado.status, "qualidade_obs": "; ".join(tratado.avisos) or None,
                        "houve_sinistro": None})
        pontuadas = pontuar(modelo, pd.DataFrame([leitura]), regras_ativas)
        resultado = _persistir(conn, pontuadas, origem, ator, modelo, regras_ativas, auditar_cada=True)[0]
    log.info("Leitura processada", extra={"contexto": {"leitura_id": resultado.leitura_id,
                                                      "score": resultado.score_risco,
                                                      "classe": resultado.classe_risco,
                                                      "alertas": len(resultado.alertas), "origem": origem}})
    return resultado
