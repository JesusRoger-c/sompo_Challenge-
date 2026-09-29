"""
Trilha de auditoria encadeada por hash (tamper-evident).

Cada evento grava `hash_anterior` (o hash do evento anterior) e `hash_registro`
= SHA-256 do proprio conteudo + hash_anterior. Assim os eventos formam uma
corrente: alterar, inserir ou remover qualquer registro no meio quebra todos os
hashes seguintes, e `verificar_cadeia()` aponta exatamente onde.

Isso complementa os triggers do banco (que bloqueiam UPDATE/DELETE pela
aplicacao): mesmo alguem com acesso direto ao arquivo .db nao consegue
adulterar o historico sem deixar rastro. E o mesmo principio de um livro-razao
- e o que um auditor pede para confiar em "entradas, saidas e decisoes".

Eventos registrados (exemplos):
  CARGA_HISTORICA, TREINO_MODELO, TELEMETRIA_RECEBIDA, TELEMETRIA_REJEITADA,
  PREDICAO_GERADA, ALERTA_GERADO, ALERTA_ATUALIZADO, MANUTENCAO_REGISTRADA,
  LOGIN_SUCESSO, LOGIN_FALHA, CONTA_BLOQUEADA, ACESSO_NEGADO, REGRAS_ALTERADAS,
  RELATORIO_EXPORTADO, VERIFICACAO_AUDITORIA.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

HASH_GENESIS = "0" * 64
_CAMPOS = ("data_hora", "evento", "ator", "perfil", "leitura_id", "equipamento_id",
           "status", "detalhes", "modelo_versao", "hash_anterior")


def _hash_evento(registro: dict) -> str:
    canonico = json.dumps({c: registro.get(c) for c in _CAMPOS}, sort_keys=True,
                          ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def hash_payload(dados: dict) -> str:
    """SHA-256 de um payload (JSON canonico) - prova de integridade da entrada."""
    canonico = json.dumps(dados, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def registrar(conn: sqlite3.Connection, evento: str, ator: str, status: str = "SUCESSO",
              perfil: str | None = None, leitura_id: int | None = None,
              equipamento_id: str | None = None, detalhes: dict | str | None = None,
              modelo_versao: str | None = None) -> str:
    """Insere um evento encadeado. Deve rodar dentro da transacao do chamador.

    Devolve o hash do registro (util para devolver ao cliente como recibo).
    """
    ultimo = conn.execute("SELECT hash_registro FROM auditoria ORDER BY auditoria_id DESC LIMIT 1").fetchone()
    registro = {
        "data_hora": datetime.now().isoformat(timespec="microseconds"),
        "evento": evento,
        "ator": ator,
        "perfil": perfil,
        "leitura_id": leitura_id,
        "equipamento_id": equipamento_id,
        "status": status,
        "detalhes": detalhes if isinstance(detalhes, str) or detalhes is None
        else json.dumps(detalhes, ensure_ascii=False, sort_keys=True, default=str),
        "modelo_versao": modelo_versao,
        "hash_anterior": ultimo[0] if ultimo else HASH_GENESIS,
    }
    registro["hash_registro"] = _hash_evento(registro)
    colunas = list(registro)
    conn.execute(f"INSERT INTO auditoria ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
                 [registro[c] for c in colunas])
    return registro["hash_registro"]


@dataclass
class ResultadoVerificacao:
    integra: bool
    eventos_verificados: int
    primeiro_problema: dict | None = None

    def resumo(self) -> str:
        if self.integra:
            return f"Cadeia íntegra: {self.eventos_verificados} eventos verificados, nenhum adulterado."
        p = self.primeiro_problema or {}
        return (f"ADULTERAÇÃO DETECTADA no evento #{p.get('auditoria_id')} ({p.get('motivo')}). "
                f"{self.eventos_verificados} eventos conferidos até o ponto de quebra.")


def verificar_cadeia(conn: sqlite3.Connection) -> ResultadoVerificacao:
    """Recalcula todos os hashes e confere o encadeamento, do primeiro ao ultimo."""
    anterior = HASH_GENESIS
    n = 0
    cursor = conn.execute(f"SELECT auditoria_id, hash_registro, {', '.join(_CAMPOS)} "
                          "FROM auditoria ORDER BY auditoria_id")
    for linha in cursor:
        registro = dict(linha)
        if registro["hash_anterior"] != anterior:
            return ResultadoVerificacao(False, n, {"auditoria_id": registro["auditoria_id"],
                                                   "motivo": "encadeamento quebrado (evento removido ou inserido)"})
        if _hash_evento(registro) != registro["hash_registro"]:
            return ResultadoVerificacao(False, n, {"auditoria_id": registro["auditoria_id"],
                                                   "motivo": "conteúdo alterado após o registro"})
        anterior = registro["hash_registro"]
        n += 1
    return ResultadoVerificacao(True, n)
