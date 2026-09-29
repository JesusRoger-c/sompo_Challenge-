"""
Logging estruturado do SomPrev Risk.

Por que JSON? Cada linha do arquivo `logs/somprev.log` e um objeto JSON com
horario, nivel, modulo, evento e campos de contexto (leitura_id, usuario,
id_correlacao ...). Isso permite filtrar e auditar os registros com qualquer
ferramenta (jq, pandas, SIEM) sem depender de expressoes regulares.

Os logs complementam a tabela `auditoria` do banco:
  - auditoria  -> eventos de NEGOCIO (entrada, predicao, alerta, login), com
                  encadeamento por hash e retencao permanente;
  - logs       -> eventos TECNICOS (erros, tempos, avisos de qualidade), com
                  rotacao para nao crescer indefinidamente.
Senhas e chaves nunca sao registradas (ver `_CAMPOS_SENSIVEIS`).
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone

from . import config

_CAMPOS_SENSIVEIS = {"senha", "password", "api_key", "x-api-key", "token", "hash_senha"}
_CONFIGURADO = False


class FormatadorJSON(logging.Formatter):
    """Serializa cada registro de log como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "modulo": record.name,
            "mensagem": record.getMessage(),
        }
        contexto = getattr(record, "contexto", None)
        if isinstance(contexto, dict):
            for chave, valor in contexto.items():
                dados[chave] = "***" if chave.lower() in _CAMPOS_SENSIVEIS else valor
        if record.exc_info:
            dados["excecao"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False, default=str)


class FormatadorConsole(logging.Formatter):
    """Console enxuto: so a mensagem (o traceback completo fica no arquivo JSON)."""

    def format(self, record: logging.LogRecord) -> str:
        record.exc_text = None
        copia = logging.makeLogRecord({**record.__dict__, "exc_info": None, "exc_text": None})
        return super().format(copia)


def configurar_logs(nivel: str = "INFO", console: bool = True) -> None:
    """Configura o logger raiz do pacote uma unica vez (idempotente)."""
    global _CONFIGURADO
    if _CONFIGURADO:
        return
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    raiz = logging.getLogger("somprev")
    raiz.setLevel(nivel)
    raiz.propagate = False

    arquivo = logging.handlers.RotatingFileHandler(
        config.LOG_DIR / "somprev.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    arquivo.setFormatter(FormatadorJSON())
    raiz.addHandler(arquivo)

    if console:
        tela = logging.StreamHandler()
        tela.setFormatter(FormatadorConsole("%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"))
        tela.setLevel("WARNING")
        raiz.addHandler(tela)
    _CONFIGURADO = True


def obter_logger(nome: str) -> logging.Logger:
    """Devolve um logger filho de 'somprev' ja configurado."""
    configurar_logs()
    return logging.getLogger(f"somprev.{nome}")


def log_evento(logger: logging.Logger, nivel: int, mensagem: str, **contexto) -> None:
    """Atalho para registrar uma mensagem com campos de contexto estruturados."""
    logger.log(nivel, mensagem, extra={"contexto": contexto})
