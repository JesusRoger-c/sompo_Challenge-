"""
Backend FastAPI do SomPrev Risk (Sprint 4).

Endpoints
---------
Publicos
    GET  /                         identificacao do servico
    GET  /health                   saude (banco, modelo, regras)
Ingestao (X-API-Key de ingestao - usada pelos coletores de telemetria)
    POST /telemetria               processa UMA leitura (score, explicacao, alertas)
    POST /telemetria/lote          processa ate 500 leituras, com resultado por item
Consulta (X-API-Key de consulta - usada por sistemas da seguradora/BI e pelo PROPRIO dashboard)
    GET  /leituras/{id}            leitura + predicao + alertas + trilha de auditoria
    GET  /leituras                 todas as leituras com score (o dashboard le daqui, nao do banco)
    GET  /equipamentos/{id}/risco  ultimo score do equipamento e alertas abertos
    GET  /equipamentos             cadastro da frota
    GET  /alertas                  alertas filtrados por status/perfil/equipamento
    GET  /manutencoes              manutencoes registradas
    GET  /quarentena               leituras rejeitadas pela qualidade de dados
    GET  /auditoria                eventos da trilha (filtro por tipo)
    GET  /relatorios/tendencias    tendencia de risco por regiao/operacao/equipamento
    GET  /modelo                   model card da versao ativa
    GET  /auditoria/verificar      verificacao criptografica da trilha de auditoria
    GET  /verificacao              as 12 verificacoes de integridade e consistencia do sistema

O dashboard (Streamlit) e um CLIENTE desta API, igual a qualquer sistema externo: ele nao
abre o banco por fora, so consome estas rotas de consulta com a mesma chave e os mesmos
limites de taxa e auditoria de acesso negado. Quem grava (reconhecer alerta, registrar
manutencao, editar regras) e o proprio dashboard, sob a sessao do usuario logado - isso e um
limite de autorizacao diferente (perfil humano com RBAC), nao a integracao entre sistemas.

Protecoes
---------
* Duas chaves com escopos separados (ingestao x consulta) - privilegio minimo;
  comparacao em tempo constante; a chave nunca e logada (so uma impressao digital).
* Limite de requisicoes por chave/IP (HTTP 429 + Retry-After).
* Limite de tamanho do corpo da requisicao (HTTP 413).
* Payload estrito: campos desconhecidos sao recusados (evita "mass assignment").
* Erros esperados -> codigo HTTP correto e mensagem util; erros inesperados ->
  HTTP 500 generico com id da requisicao (detalhe tecnico so no log).
* Cabecalhos de seguranca e X-Request-ID em todas as respostas.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import defaultdict, deque
from typing import Literal, Optional, Union

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__, config, regras
from ..banco import repositorio as repo
from ..banco.conexao import banco_existe, sessao, transacao
from ..excecoes import ModeloIndisponivel, RecursoNaoEncontrado, SomPrevErro
from ..logs import configurar_logs, obter_logger
from ..modelo.inferencia import carregar_modelo
from ..relatorios import tendencias
from ..seguranca import auditoria, autenticacao
from ..servicos import processamento

configurar_logs()
log = obter_logger("api")

TAMANHO_MAXIMO_CORPO = 1_000_000   # 1 MB
MAX_LOTE = 500

app = FastAPI(
    title="SomPrev Risk API",
    version=__version__,
    description="Backend do SomPrev Risk — telemetria → qualidade → modelo → score → alertas → auditoria. "
                "Challenge FIAP + Sompo Seguros (Sprint 4).",
)

Numero = Optional[Union[float, str]]


class TelemetriaEntrada(BaseModel):
    """Leitura de telemetria. Campos de sensor aceitam nulo (sensor sem leitura) e
    texto com virgula decimal ("55,3"): a etapa de qualidade trata, imputa ou rejeita."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "leitura_id": 900001, "data_hora": "2026-09-01 07:30:00", "equipamento_id": "EQ-021", "regiao_id": 4,
        "umidade_solo_pct": "88,5", "precipitacao_24h_mm": 62.0, "temperatura_c": 17.5, "tipo_solo": "Argiloso",
        "declividade_graus": 12.0, "distancia_corpo_dagua_m": 140, "tipo_operacao": "Colheita",
        "idade_equipamento_anos": None, "horas_desde_manutencao": 310, "horas_operacao_dia": 9.5,
        "carga_pct": 92, "periodo_dia": "Manha"}})

    leitura_id: Optional[int] = Field(None, gt=0, description="Opcional: gerado pelo sistema se ausente")
    data_hora: str = Field(..., max_length=32, description="AAAA-MM-DD HH:MM:SS")
    equipamento_id: str = Field(..., max_length=16)
    regiao_id: int = Field(..., gt=0)
    umidade_solo_pct: Numero = None
    precipitacao_24h_mm: Numero = None
    temperatura_c: Numero = None
    tipo_solo: Optional[str] = Field(None, max_length=32)
    declividade_graus: Numero = None
    distancia_corpo_dagua_m: Numero = None
    tipo_operacao: Optional[str] = Field(None, max_length=32)
    idade_equipamento_anos: Numero = None
    horas_desde_manutencao: Numero = None
    horas_operacao_dia: Numero = None
    carga_pct: Numero = None
    periodo_dia: Optional[str] = Field(None, max_length=16)


class LoteEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    leituras: list[TelemetriaEntrada] = Field(..., min_length=1, max_length=MAX_LOTE)


# ---------------------------------------------------------------------------
# Seguranca: chaves, escopos e limite de taxa
# ---------------------------------------------------------------------------
_cabecalho_chave = APIKeyHeader(name="X-API-Key", auto_error=False)
_janelas: dict[str, deque] = defaultdict(deque)
_trava_taxa = threading.Lock()


def _limitar_taxa(identidade: str) -> None:
    agora = time.monotonic()
    with _trava_taxa:
        janela = _janelas[identidade]
        while janela and agora - janela[0] > 60:
            janela.popleft()
        if len(janela) >= config.API_LIMITE_REQ_MINUTO:
            espera = int(60 - (agora - janela[0])) + 1
            raise HTTPException(429, "Limite de requisições excedido. Tente novamente em instantes.",
                                headers={"Retry-After": str(espera)})
        janela.append(agora)


def _exigir_escopo(escopo: Literal["ingestao", "consulta"]):
    def dependencia(request: Request, chave: Optional[str] = Depends(_cabecalho_chave)) -> str:
        ip = request.client.host if request.client else "desconhecido"
        _limitar_taxa(f"ip:{ip}" if not chave else f"chave:{autenticacao.impressao_digital(chave)}")
        escopo_chave = autenticacao.identificar_chave_api(chave)
        if escopo_chave != escopo:
            motivo = "chave ausente" if not chave else "chave inválida" if escopo_chave is None \
                else f"chave de {escopo_chave} sem permissão de {escopo}"
            with sessao() as conn, transacao(conn):
                auditoria.registrar(conn, "API_ACESSO_NEGADO", ator=f"ip:{ip}", status="NEGADO",
                                    detalhes={"rota": request.url.path, "motivo": motivo})
            log.warning("Acesso negado na API", extra={"contexto": {"rota": request.url.path, "motivo": motivo,
                                                                    "ip": ip}})
            raise HTTPException(401 if escopo_chave is None else 403,
                                "API Key não informada." if not chave else
                                "API Key inválida." if escopo_chave is None else
                                "Esta chave não tem permissão para este recurso.")
        return f"api:{escopo}:{autenticacao.impressao_digital(chave)}"
    return dependencia


# ---------------------------------------------------------------------------
# Middleware: id de requisicao, tamanho do corpo, log e cabecalhos
# ---------------------------------------------------------------------------
@app.middleware("http")
async def middleware_padrao(request: Request, call_next):
    id_req = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.id_req = id_req
    inicio = time.perf_counter()
    tamanho = request.headers.get("content-length")
    if tamanho and tamanho.isdigit() and int(tamanho) > TAMANHO_MAXIMO_CORPO:
        resposta = JSONResponse({"erro": "Corpo da requisição muito grande.", "id_requisicao": id_req},
                                status_code=413)
    else:
        resposta = await call_next(request)
    resposta.headers["X-Request-ID"] = id_req
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Cache-Control"] = "no-store"
    log.info("requisicao", extra={"contexto": {
        "id_requisicao": id_req, "metodo": request.method, "rota": request.url.path,
        "status": resposta.status_code, "ms": round((time.perf_counter() - inicio) * 1000, 1)}})
    return resposta


@app.exception_handler(SomPrevErro)
async def tratar_erro_dominio(request: Request, erro: SomPrevErro):
    return JSONResponse({"erro": erro.mensagem, "detalhes": erro.detalhes,
                         "id_requisicao": getattr(request.state, "id_req", None)}, status_code=erro.codigo_http)


@app.exception_handler(StarletteHTTPException)
async def tratar_http(request: Request, erro: StarletteHTTPException):
    return JSONResponse({"erro": erro.detail, "id_requisicao": getattr(request.state, "id_req", None)},
                        status_code=erro.status_code, headers=getattr(erro, "headers", None))


@app.exception_handler(RequestValidationError)
async def tratar_validacao(request: Request, erro: RequestValidationError):
    problemas = [f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in erro.errors()]
    return JSONResponse({"erro": "Payload inválido.", "detalhes": {"erros": problemas},
                         "id_requisicao": getattr(request.state, "id_req", None)}, status_code=422)


@app.exception_handler(Exception)
async def tratar_inesperado(request: Request, erro: Exception):
    id_req = getattr(request.state, "id_req", None)
    log.exception("Erro inesperado na API", extra={"contexto": {"id_requisicao": id_req, "rota": request.url.path}})
    return JSONResponse({"erro": "Erro interno ao processar a requisição. Informe o id_requisicao ao suporte.",
                         "id_requisicao": id_req}, status_code=500)


# ---------------------------------------------------------------------------
# Rotas publicas
# ---------------------------------------------------------------------------
@app.get("/", tags=["Sistema"])
def raiz():
    return {"sistema": "SomPrev Risk", "versao_api": __version__, "sprint": 4, "documentacao": "/docs"}


@app.get("/health", tags=["Sistema"])
def health():
    estado = {"banco": banco_existe(), "modelo": None, "regras": regras.carregar_regras()["versao"]}
    try:
        estado["modelo"] = carregar_modelo().versao
    except ModeloIndisponivel:
        estado["modelo"] = None
    estado["status"] = "ok" if estado["banco"] and estado["modelo"] else "degradado"
    return JSONResponse(estado, status_code=200 if estado["status"] == "ok" else 503)


# ---------------------------------------------------------------------------
# Ingestao
# ---------------------------------------------------------------------------
@app.post("/telemetria", status_code=201, tags=["Ingestão"])
def receber_telemetria(dado: TelemetriaEntrada, ator: str = Depends(_exigir_escopo("ingestao"))):
    """Valida, trata, pontua e persiste uma leitura. Devolve score, faixa, fatores,
    recomendacao, alertas e o recibo (hash) da trilha de auditoria."""
    with sessao() as conn:
        resultado = processamento.processar_leitura(conn, dado.model_dump(), origem="api", ator=ator)
    return {"status": "processada", **resultado.como_dict()}


@app.post("/telemetria/lote", tags=["Ingestão"])
def receber_lote(lote: LoteEntrada, ator: str = Depends(_exigir_escopo("ingestao"))):
    """Processa varias leituras; uma leitura com problema NAO interrompe as demais."""
    itens, contagem = [], defaultdict(int)
    with sessao() as conn:
        for i, dado in enumerate(lote.leituras):
            try:
                r = processamento.processar_leitura(conn, dado.model_dump(), origem="api", ator=ator)
                itens.append({"indice": i, "status": "processada", "leitura_id": r.leitura_id,
                              "score_risco": r.score_risco, "classe_risco": r.classe_risco,
                              "alertas": len(r.alertas), "qualidade": r.qualidade_status})
                contagem["processadas"] += 1
            except SomPrevErro as erro:
                status = {409: "duplicada", 404: "rejeitada", 422: "rejeitada"}.get(erro.codigo_http, "erro")
                itens.append({"indice": i, "status": status, "erro": erro.mensagem, "detalhes": erro.detalhes})
                contagem[status] += 1
    return {"recebidas": len(lote.leituras), **contagem, "itens": itens}


# ---------------------------------------------------------------------------
# Consulta
# ---------------------------------------------------------------------------
@app.get("/leituras/{leitura_id}", tags=["Consulta"])
def consultar_leitura(leitura_id: int, _: str = Depends(_exigir_escopo("consulta"))):
    """Rastreabilidade completa de uma leitura: entrada, saida, decisao e auditoria."""
    with sessao(somente_leitura=True) as conn:
        linha = conn.execute("SELECT * FROM vw_leituras_risco WHERE leitura_id = ?", (leitura_id,)).fetchone()
        if linha is None:
            raise RecursoNaoEncontrado(f"Leitura {leitura_id} não encontrada.")
        leitura = dict(linha)
        leitura["explicacao"] = json.loads(leitura.pop("explicacao_json") or "{}")
        alertas = [dict(a) for a in conn.execute("SELECT * FROM alertas WHERE leitura_id = ?", (leitura_id,))]
        eventos = [dict(e) for e in conn.execute(
            "SELECT auditoria_id, data_hora, evento, ator, status, detalhes, hash_registro FROM auditoria "
            "WHERE leitura_id = ? ORDER BY auditoria_id", (leitura_id,))]
    return {"leitura": leitura, "alertas": alertas, "auditoria": eventos}


@app.get("/equipamentos/{equipamento_id}/risco", tags=["Consulta"])
def risco_equipamento(equipamento_id: str, _: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        if repo.obter_equipamento(conn, equipamento_id) is None:
            raise RecursoNaoEncontrado(f"Equipamento {equipamento_id} não encontrado.")
        ultima = conn.execute("SELECT * FROM vw_leituras_risco WHERE equipamento_id = ? ORDER BY data_hora DESC "
                              "LIMIT 1", (equipamento_id,)).fetchone()
        abertos = [dict(a) for a in conn.execute(
            "SELECT alerta_id, codigo, nivel, criterio, recomendacao, status, ocorrencias, ultima_ocorrencia "
            "FROM alertas WHERE equipamento_id = ? AND status != 'resolvido' ORDER BY alerta_id DESC",
            (equipamento_id,))]
    ultima = dict(ultima) if ultima else {}
    return {"equipamento_id": equipamento_id, "ultima_leitura": ultima.get("data_hora"),
            "score_risco": ultima.get("score_risco"), "classe_risco": ultima.get("classe_risco"),
            "recomendacao": regras.recomendacao(ultima["classe_risco"], [ultima["fator_1"], ultima["fator_2"]])
            if ultima else None, "alertas_abertos": abertos}


@app.get("/alertas", tags=["Consulta"])
def listar_alertas(status: Optional[Literal["aberto", "reconhecido", "resolvido"]] = None,
                   perfil_destino: Optional[Literal["Operador", "Tecnico", "Gestor", "Seguradora"]] = None,
                   equipamento_id: Optional[str] = None, limite: int = Query(100, ge=1, le=5000),
                   _: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        df = repo.carregar_alertas(conn, (status,) if status else None)
    if perfil_destino:
        df = df[df["perfil_destino"] == perfil_destino]
    if equipamento_id:
        df = df[df["equipamento_id"] == equipamento_id]
    return {"total": int(len(df)), "alertas": json.loads(df.head(limite).to_json(orient="records", force_ascii=False))}


@app.get("/leituras", tags=["Consulta"])
def listar_leituras(dias: int = Query(3650, ge=1, le=3650), _: str = Depends(_exigir_escopo("consulta"))):
    """Leituras com score/predicao (join ja pronto - vw_leituras_risco), para paineis e BI.

    E a mesma consulta que alimenta o dashboard: nao ha mais leitura direta do banco por fora
    da API. `dias` filtra pela data da leitura mais recente da base (default cobre tudo hoje)."""
    with sessao(somente_leitura=True) as conn:
        df = repo.carregar_leituras_risco(conn)
    if not df.empty:
        df = df[df["data_hora"] > df["data_hora"].max() - pd.Timedelta(days=dias)]
    return {"total": int(len(df)),
            "leituras": json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso"))}


@app.get("/equipamentos", tags=["Consulta"])
def listar_equipamentos(_: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        df = repo.listar_equipamentos(conn)
    return {"total": int(len(df)), "equipamentos": json.loads(df.to_json(orient="records", force_ascii=False))}


@app.get("/manutencoes", tags=["Consulta"])
def listar_manutencoes(_: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        df = repo.carregar_manutencoes(conn)
    return {"total": int(len(df)),
            "manutencoes": json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso"))}


@app.get("/quarentena", tags=["Consulta"])
def listar_quarentena(_: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        df = repo.carregar_quarentena(conn)
    return {"total": int(len(df)),
            "quarentena": json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso"))}


@app.get("/auditoria", tags=["Consulta"])
def listar_auditoria(evento: Optional[str] = None, limite: int = Query(1000, ge=1, le=5000),
                     _: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        df = repo.carregar_auditoria(conn, limite=limite)
    if evento:
        df = df[df["evento"] == evento]
    return {"total": int(len(df)),
            "eventos": json.loads(df.to_json(orient="records", force_ascii=False, date_format="iso"))}


@app.get("/relatorios/tendencias", tags=["Consulta"])
def relatorio_tendencias(dimensao: Literal["regiao_nome", "tipo_operacao", "equipamento_id", "equip_tipo"] =
                         "regiao_nome", dias: int = Query(90, ge=7, le=365),
                         _: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        df = repo.carregar_leituras_risco(conn)
    df = df[df["data_hora"] > df["data_hora"].max() - pd.Timedelta(days=dias)]
    serie = tendencias.tendencia(df, dimensao)
    serie["periodo"] = serie["periodo"].dt.strftime("%Y-%m-%d")
    return {"dimensao": dimensao, "dias": dias,
            "variacao_recente": json.loads(tendencias.variacao_recente(df, dimensao).to_json(orient="records",
                                                                                                force_ascii=False)),
            "serie_semanal": json.loads(serie.to_json(orient="records", force_ascii=False))}


@app.get("/modelo", tags=["Consulta"])
def model_card(_: str = Depends(_exigir_escopo("consulta"))):
    if not config.MODEL_CARD_PATH.exists():
        raise ModeloIndisponivel("Model card não encontrado. Rode: python scripts/run.py pipeline")
    return json.loads(config.MODEL_CARD_PATH.read_text(encoding="utf-8"))


@app.get("/auditoria/verificar", tags=["Consulta"])
def verificar_auditoria(_: str = Depends(_exigir_escopo("consulta"))):
    with sessao(somente_leitura=True) as conn:
        resultado = auditoria.verificar_cadeia(conn)
    return {"integra": resultado.integra, "eventos_verificados": resultado.eventos_verificados,
            "resumo": resultado.resumo(), "primeiro_problema": resultado.primeiro_problema}


@app.get("/verificacao", tags=["Consulta"])
def verificacao_sistema(_: str = Depends(_exigir_escopo("consulta"))):
    """As mesmas 12 verificacoes de integridade e consistencia do `python scripts/run.py verificar`."""
    from ..servicos.verificacao import verificar_sistema
    with sessao(somente_leitura=True) as conn:
        itens = verificar_sistema(conn)
    return {"ok": all(i["ok"] for i in itens), "verificacoes": itens}
