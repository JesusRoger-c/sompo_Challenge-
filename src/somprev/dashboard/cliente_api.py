"""
Cliente HTTP da API para o dashboard (Sprint 4).

O dashboard NAO abre o banco de dados diretamente. Ele e um cliente da API, exatamente como
qualquer sistema externo (BI, seguradora) seria: usa a chave de escopo "consulta", passa pelo
mesmo limite de requisicoes e, se a chave faltar ou for recusada, o evento fica na trilha de
auditoria (API_ACESSO_NEGADO) como qualquer outra tentativa. Isso fecha o ponto que a Sprint 3
deixou em aberto: "o painel le o banco direto em vez de consumir a API".

Quem grava dados a partir do dashboard (reconhecer alerta, registrar manutencao, editar regras)
continua indo direto no banco, dentro de uma transacao - mas ali quem autoriza e o login do
usuario (RBAC por perfil), um limite de autorizacao diferente do par de chaves da API. Ver a
nota no topo de somprev/api/app.py.
"""

from __future__ import annotations

import httpx
import pandas as pd

from .. import config
from ..excecoes import SomPrevErro


class ApiIndisponivel(SomPrevErro):
    """A API do SomPrev Risk nao respondeu. Rode: python run.py api"""

    codigo_http = 503

    def __init__(self, causa: str):
        super().__init__(f"Não foi possível falar com a API em {config.API_BASE_URL} ({causa}). "
                         "Rode `python run.py api` em outro terminal e recarregue a página.")


def _cliente() -> httpx.Client:
    """Isolado em funcao para os testes trocarem por um transporte ASGI em memoria
    (sem precisar subir um servidor de verdade) - ver tests/conftest.py."""
    return httpx.Client(base_url=config.API_BASE_URL, headers={"X-API-Key": config.API_KEY_CONSULTA}, timeout=15.0)


def _get(caminho: str, **params) -> dict:
    try:
        with _cliente() as cli:
            resp = cli.get(caminho, params=params or None)
    except httpx.ConnectError as erro:
        raise ApiIndisponivel("conexão recusada") from erro
    except httpx.TimeoutException as erro:
        raise ApiIndisponivel("tempo esgotado") from erro
    if resp.status_code >= 400:
        try:
            detalhe = resp.json().get("erro", resp.text)
        except ValueError:
            detalhe = resp.text
        raise ApiIndisponivel(f"HTTP {resp.status_code} em {caminho}: {detalhe}")
    return resp.json()


def _df(chave: str, caminho: str, colunas_data: tuple[str, ...] = (), **params) -> pd.DataFrame:
    df = pd.DataFrame(_get(caminho, **params)[chave])
    for coluna in colunas_data:
        if coluna in df.columns and not df.empty:
            df[coluna] = pd.to_datetime(df[coluna])
    return df


def leituras_risco(dias: int = 3650) -> pd.DataFrame:
    return _df("leituras", "/leituras", colunas_data=("data_hora",), dias=dias)


def alertas(limite: int = 5000) -> pd.DataFrame:
    return _df("alertas", "/alertas", limite=limite)


def equipamentos() -> pd.DataFrame:
    return _df("equipamentos", "/equipamentos")


def manutencoes() -> pd.DataFrame:
    return _df("manutencoes", "/manutencoes", colunas_data=("realizada_em",))


def quarentena() -> pd.DataFrame:
    return _df("quarentena", "/quarentena", colunas_data=("recebido_em",))


def auditoria(limite: int = 2000, evento: str | None = None) -> pd.DataFrame:
    params = {"limite": limite}
    if evento:
        params["evento"] = evento
    return _df("eventos", "/auditoria", colunas_data=("data_hora",), **params)


def verificar_auditoria() -> dict:
    return _get("/auditoria/verificar")


def verificacao_sistema() -> list[dict]:
    return _get("/verificacao")["verificacoes"]
