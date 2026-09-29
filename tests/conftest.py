"""
Configuracao dos testes: o sistema inteiro roda em um diretorio TEMPORARIO.

Nenhum teste toca o banco, o modelo ou os dados versionados do repositorio.
O pipeline completo e executado uma vez por sessao de testes (modo rapido de
treino), e cada teste de escrita usa uma copia propria do banco.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="somprev_testes_"))

# Ambiente isolado ANTES de importar o pacote (config le as variaveis no import).
os.environ.update({
    "SOMPREV_DB_PATH": str(TMP / "somprev_teste.db"),
    "SOMPREV_MODELS_DIR": str(TMP / "models"),
    "SOMPREV_DATASETS_DIR": str(TMP / "datasets"),
    "SOMPREV_RELATORIOS_DIR": str(TMP / "relatorios"),
    "SOMPREV_LOG_DIR": str(TMP / "logs"),
    "SOMPREV_REGRAS_PATH": str(TMP / "regras_risco.json"),
    "SOMPREV_API_KEY": "chave-ingestao-de-teste-0123456789",
    "SOMPREV_API_KEY_CONSULTA": "chave-consulta-de-teste-0123456789",
    "SOMPREV_PBKDF2_ITERACOES": "2000",          # rapido nos testes; producao usa 600 mil
    "SOMPREV_OPERADOR_USER": "operador", "SOMPREV_OPERADOR_PASSWORD": "SenhaOperador123",
    "SOMPREV_TECNICO_USER": "tecnico", "SOMPREV_TECNICO_PASSWORD": "SenhaTecnico1234",
    "SOMPREV_GESTOR_USER": "gestor", "SOMPREV_GESTOR_PASSWORD": "SenhaGestor12345",
    "SOMPREV_SEGURADORA_USER": "seguradora", "SOMPREV_SEGURADORA_PASSWORD": "SenhaSeguradora1",
})
(TMP / "models").mkdir(parents=True, exist_ok=True)
shutil.copy(RAIZ / "config" / "regras_risco.json", TMP / "regras_risco.json")
sys.path.insert(0, str(RAIZ / "src"))

import pytest  # noqa: E402

from somprev import config  # noqa: E402


@pytest.fixture(scope="session")
def ambiente():
    """Executa o pipeline completo uma vez e devolve os caminhos do ambiente."""
    from somprev import pipeline
    ok = pipeline.executar(rapido=True)
    assert ok, "o pipeline deveria terminar com todas as verificacoes aprovadas"
    return {"tmp": TMP, "db": config.DB_PATH}


@pytest.fixture()
def banco_isolado(ambiente, tmp_path, monkeypatch):
    """Copia do banco para testes que escrevem (nao contaminam os demais).

    Tambem aponta o cliente HTTP do dashboard (somprev.dashboard.cliente_api) para o
    app FastAPI em processo, com o TestClient do Starlette (o mesmo usado pela fixture
    `cliente_api` abaixo) - o dashboard consome a API de verdade nos testes, sem
    precisar subir um servidor escutando em uma porta real."""
    from starlette.testclient import TestClient

    destino = tmp_path / "copia.db"
    shutil.copy(config.DB_PATH, destino)
    monkeypatch.setattr(config, "DB_PATH", destino)

    from somprev.api import app as modulo_api
    from somprev.dashboard import cliente_api as cliente_dashboard
    modulo_api._janelas.clear()
    monkeypatch.setattr(cliente_dashboard, "_cliente", lambda: TestClient(
        modulo_api.app, base_url="http://apiteste", headers={"X-API-Key": config.API_KEY_CONSULTA}))
    return destino


@pytest.fixture()
def cliente_api(banco_isolado):
    from fastapi.testclient import TestClient

    from somprev.api import app as modulo_api
    return TestClient(modulo_api.app)


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TMP, ignore_errors=True)
