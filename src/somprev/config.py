"""
Configuracao central do SomPrev Risk.

Todos os caminhos e parametros ficam aqui para que nenhum modulo monte caminhos
"na mao". Isso garante que o sistema rode igual a partir de qualquer diretorio
e que um teste consiga redirecionar banco e artefatos para uma pasta temporaria
apenas trocando variaveis de ambiente (SOMPREV_DB_PATH, SOMPREV_LOG_DIR ...).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Raiz do repositorio: src/somprev/config.py -> sobe 3 niveis.
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"

# O .env e opcional: sem ele o sistema ainda sobe, mas as rotas protegidas
# recusam acesso (falha segura) ate que as credenciais sejam configuradas.
load_dotenv(ROOT_DIR / ".env", override=False)


def _caminho(env: str, padrao: Path) -> Path:
    """Permite sobrescrever qualquer caminho por variavel de ambiente."""
    valor = os.getenv(env)
    return Path(valor).expanduser().resolve() if valor else padrao


# ---------------------------------------------------------------------------
# Diretorios de dados e artefatos (estrutura do template FIAP preservada).
# ---------------------------------------------------------------------------
DATASETS_DIR = _caminho("SOMPREV_DATASETS_DIR", SRC_DIR / "datasets")
DADOS_BRUTOS_CSV = DATASETS_DIR / "coleta_bruta.csv"          # telemetria "como chegou"
DADOS_TRATADOS_CSV = DATASETS_DIR / "leituras_tratadas.csv"   # apos limpeza/validacao
CADASTRO_EQUIP_CSV = DATASETS_DIR / "cadastro_equipamentos.csv"
DATASET_EXEMPLO_CSV = DATASETS_DIR / "dataset_exemplo.csv"
RELATORIO_QUALIDADE_JSON = DATASETS_DIR / "relatorio_qualidade.json"

DATABASE_DIR = SRC_DIR / "database"
DB_PATH = _caminho("SOMPREV_DB_PATH", DATABASE_DIR / "somprev_risk.db")
SCHEMA_PATH = DATABASE_DIR / "schema.sql"

MODELS_DIR = _caminho("SOMPREV_MODELS_DIR", SRC_DIR / "models")
MODELO_PATH = MODELS_DIR / "modelo_risco.pkl"
METRICAS_PATH = MODELS_DIR / "metricas.json"
MODEL_CARD_PATH = MODELS_DIR / "model_card.json"

CONFIG_DIR = ROOT_DIR / "config"
REGRAS_PATH = _caminho("SOMPREV_REGRAS_PATH", CONFIG_DIR / "regras_risco.json")

DOCUMENT_DIR = ROOT_DIR / "document"
RELATORIOS_DIR = _caminho("SOMPREV_RELATORIOS_DIR", DOCUMENT_DIR / "relatorios")
EVIDENCIAS_DIR = DOCUMENT_DIR / "evidencias"

LOG_DIR = _caminho("SOMPREV_LOG_DIR", ROOT_DIR / "logs")

# ---------------------------------------------------------------------------
# Parametros de reprodutibilidade
# ---------------------------------------------------------------------------
SEED = int(os.getenv("SOMPREV_SEED", "42"))

# ---------------------------------------------------------------------------
# Seguranca
# ---------------------------------------------------------------------------
API_KEY_INGESTAO = os.getenv("SOMPREV_API_KEY", "")
API_KEY_CONSULTA = os.getenv("SOMPREV_API_KEY_CONSULTA", "")

# Endereco da API que o dashboard consome (rotas de consulta, ver src/somprev/dashboard/cliente_api.py).
# O dashboard nao le mais o banco diretamente: qualquer sistema que precise dos mesmos dados passa
# pela mesma porta protegida (chave de escopo "consulta", limite de requisicoes, auditoria de acesso negado).
API_BASE_URL = os.getenv("SOMPREV_API_URL", "http://127.0.0.1:8000")

# Limite de requisicoes por chave (janela deslizante de 60 s) - protege a API
# contra abuso ou um sensor com defeito disparando leituras em loop.
API_LIMITE_REQ_MINUTO = int(os.getenv("SOMPREV_API_LIMITE_REQ_MINUTO", "600"))

# Bloqueio de conta apos tentativas de login invalidas (forca bruta).
LOGIN_MAX_TENTATIVAS = int(os.getenv("SOMPREV_LOGIN_MAX_TENTATIVAS", "5"))
LOGIN_BLOQUEIO_MINUTOS = int(os.getenv("SOMPREV_LOGIN_BLOQUEIO_MINUTOS", "15"))

# Custo do hash de senha (PBKDF2-HMAC-SHA256). 600 mil iteracoes segue a
# recomendacao OWASP (2023) para PBKDF2-SHA256.
PBKDF2_ITERACOES = int(os.getenv("SOMPREV_PBKDF2_ITERACOES", "600000"))

# Usuarios de demonstracao lidos do .env (senha em texto so no .env, nunca no
# banco: la fica apenas o hash). Formato: perfil -> (usuario, senha).
PERFIS = ("Operador", "Tecnico", "Gestor", "Seguradora")
ROTULO_PERFIL = {"Operador": "Operador de máquinas", "Tecnico": "Técnico de manutenção",
                 "Gestor": "Gestor de frota", "Seguradora": "Analista da seguradora"}


def usuarios_iniciais() -> dict[str, tuple[str, str]]:
    """Le do ambiente os usuarios que o pipeline cadastra no primeiro setup."""
    mapa = {
        "Operador": ("SOMPREV_OPERADOR_USER", "SOMPREV_OPERADOR_PASSWORD"),
        "Tecnico": ("SOMPREV_TECNICO_USER", "SOMPREV_TECNICO_PASSWORD"),
        "Gestor": ("SOMPREV_GESTOR_USER", "SOMPREV_GESTOR_PASSWORD"),
        "Seguradora": ("SOMPREV_SEGURADORA_USER", "SOMPREV_SEGURADORA_PASSWORD"),
    }
    saida = {}
    for perfil, (env_user, env_senha) in mapa.items():
        usuario, senha = os.getenv(env_user, ""), os.getenv(env_senha, "")
        if usuario and senha:
            saida[perfil] = (usuario, senha)
    return saida


def garantir_diretorios() -> None:
    """Cria os diretorios de saida (idempotente)."""
    for pasta in (DATASETS_DIR, DATABASE_DIR, MODELS_DIR, RELATORIOS_DIR,
                  EVIDENCIAS_DIR, LOG_DIR, DB_PATH.parent):
        pasta.mkdir(parents=True, exist_ok=True)
