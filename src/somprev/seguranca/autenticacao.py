"""
Autenticacao e controle de acesso (RBAC) do SomPrev Risk.

Boas praticas aplicadas (Sprint 4):
  * Senha NUNCA armazenada: somente hash PBKDF2-HMAC-SHA256 com salt aleatorio
    de 16 bytes e 600 mil iteracoes (recomendacao OWASP). Formato autodescritivo
    `pbkdf2_sha256$iteracoes$salt$hash`, o que permite aumentar o custo no futuro.
  * Comparacao em tempo constante (hmac.compare_digest) - evita timing attack.
  * Bloqueio temporario apos N tentativas invalidas (forca bruta).
  * Mensagem de erro generica ("usuario ou senha invalidos") - nao revela se o
    login existe.
  * Politica minima de senha (12+ caracteres, letras e numeros).
  * Controle de acesso por perfil: cada perfil tem uma lista explicita de
    permissoes; tudo o que nao esta na lista e negado (privilegio minimo).
  * Todo login (sucesso, falha, bloqueio) vai para a auditoria encadeada.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timedelta

from .. import config
from ..banco.conexao import transacao
from ..excecoes import AcessoNegado, DadoInvalido
from . import auditoria

# ---------------------------------------------------------------------------
# Permissoes por perfil (privilegio minimo)
# ---------------------------------------------------------------------------
PERMISSOES: dict[str, frozenset[str]] = {
    "Operador": frozenset({"ver_operacao", "reconhecer_alerta"}),
    "Tecnico": frozenset({"ver_operacao", "ver_manutencao", "reconhecer_alerta", "resolver_alerta",
                          "registrar_manutencao"}),
    "Gestor": frozenset({"ver_operacao", "ver_manutencao", "ver_frota", "ver_tendencias",
                         "reconhecer_alerta", "resolver_alerta", "editar_regras", "exportar_relatorio"}),
    "Seguradora": frozenset({"ver_frota", "ver_tendencias", "ver_validacao_modelo", "ver_auditoria",
                             "verificar_auditoria", "exportar_relatorio"}),
}


def tem_permissao(perfil: str, permissao: str) -> bool:
    return permissao in PERMISSOES.get(perfil, frozenset())


def exigir_permissao(conn: sqlite3.Connection | None, usuario: str, perfil: str, permissao: str) -> None:
    """Levanta AcessoNegado (e audita, em transacao propria) se o perfil nao tiver a permissao."""
    if tem_permissao(perfil, permissao):
        return
    if conn is not None:
        with transacao(conn):
            auditoria.registrar(conn, "ACESSO_NEGADO", ator=usuario, perfil=perfil, status="NEGADO",
                                detalhes={"permissao": permissao})
    raise AcessoNegado(f"O perfil {perfil} não tem permissão para '{permissao}'.")


# ---------------------------------------------------------------------------
# Hash de senha
# ---------------------------------------------------------------------------
def _b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def gerar_hash_senha(senha: str, iteracoes: int | None = None) -> str:
    iteracoes = iteracoes or config.PBKDF2_ITERACOES
    salt = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iteracoes)
    return f"pbkdf2_sha256${iteracoes}${_b64(salt)}${_b64(derivado)}"


def conferir_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        algoritmo, iteracoes, salt_b64, hash_b64 = hash_armazenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"),
                                       base64.b64decode(salt_b64), int(iteracoes))
        return hmac.compare_digest(derivado, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


# Hash "fantasma" usado quando o login nao existe: o tempo de resposta fica igual
# ao de um login existente, sem revelar quais usuarios estao cadastrados.
_HASH_FANTASMA = None


def _hash_fantasma() -> str:
    global _HASH_FANTASMA
    if _HASH_FANTASMA is None:
        _HASH_FANTASMA = gerar_hash_senha(secrets.token_hex(16))
    return _HASH_FANTASMA


def validar_politica_senha(senha: str) -> None:
    if len(senha) < 12 or not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        raise DadoInvalido("A senha deve ter ao menos 12 caracteres, com letras e números.")


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
def criar_usuario(conn: sqlite3.Connection, login: str, senha: str, perfil: str,
                  nome: str | None = None, ator: str = "pipeline") -> None:
    """Cadastra (ou redefine) um usuario. Deve rodar dentro de uma transacao."""
    if perfil not in config.PERFIS:
        raise DadoInvalido(f"Perfil inválido: {perfil}. Use um de {', '.join(config.PERFIS)}.")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,40}", login):
        raise DadoInvalido("Login deve ter 3-40 caracteres (letras, números, ponto, hífen ou _).")
    validar_politica_senha(senha)
    conn.execute(
        """INSERT INTO usuarios (login, nome, perfil, hash_senha) VALUES (?, ?, ?, ?)
           ON CONFLICT(login) DO UPDATE SET perfil = excluded.perfil, hash_senha = excluded.hash_senha,
                  nome = excluded.nome, tentativas_falhas = 0, bloqueado_ate = NULL, ativo = 1""",
        (login, nome or login, perfil, gerar_hash_senha(senha)))
    auditoria.registrar(conn, "USUARIO_CADASTRADO", ator=ator, detalhes={"login": login, "perfil": perfil})


def autenticar(conn: sqlite3.Connection, login: str, senha: str) -> dict:
    """Valida credenciais. Devolve {login, nome, perfil} ou levanta AcessoNegado.

    Abre a PROPRIA transacao e so levanta o erro depois do COMMIT: assim o
    contador de falhas, o bloqueio e os eventos de auditoria de uma tentativa
    invalida ficam gravados (se o erro saisse de dentro da transacao, o
    ROLLBACK apagaria justamente o registro da tentativa suspeita).
    """
    agora = datetime.now()
    erro: str | None = None
    with transacao(conn):
        linha = conn.execute("SELECT * FROM usuarios WHERE login = ?", (login,)).fetchone()
        if linha is None or not linha["ativo"]:
            conferir_senha(senha, _hash_fantasma())
            auditoria.registrar(conn, "LOGIN_FALHA", ator=login[:40] or "-", status="NEGADO",
                                detalhes={"motivo": "usuario inexistente ou inativo"})
            erro = "Usuário ou senha inválidos."
        elif linha["bloqueado_ate"] and datetime.fromisoformat(linha["bloqueado_ate"]) > agora:
            auditoria.registrar(conn, "LOGIN_FALHA", ator=login, perfil=linha["perfil"], status="NEGADO",
                                detalhes={"motivo": "conta bloqueada"})
            minutos = int((datetime.fromisoformat(linha["bloqueado_ate"]) - agora).total_seconds() // 60) + 1
            erro = (f"Conta temporariamente bloqueada por excesso de tentativas. "
                    f"Tente novamente em {minutos} min.")
        elif not conferir_senha(senha, linha["hash_senha"]):
            falhas = linha["tentativas_falhas"] + 1
            bloqueio = None
            if falhas >= config.LOGIN_MAX_TENTATIVAS:
                bloqueio = (agora + timedelta(minutes=config.LOGIN_BLOQUEIO_MINUTOS)).isoformat(timespec="seconds")
                falhas = 0
                auditoria.registrar(conn, "CONTA_BLOQUEADA", ator=login, perfil=linha["perfil"], status="NEGADO",
                                    detalhes={"minutos": config.LOGIN_BLOQUEIO_MINUTOS})
            conn.execute("UPDATE usuarios SET tentativas_falhas = ?, bloqueado_ate = ? WHERE login = ?",
                         (falhas, bloqueio, login))
            auditoria.registrar(conn, "LOGIN_FALHA", ator=login, perfil=linha["perfil"], status="NEGADO",
                                detalhes={"motivo": "senha incorreta"})
            erro = "Usuário ou senha inválidos."
        else:
            conn.execute("UPDATE usuarios SET tentativas_falhas = 0, bloqueado_ate = NULL, ultimo_login = ? "
                         "WHERE login = ?", (agora.isoformat(timespec="seconds"), login))
            auditoria.registrar(conn, "LOGIN_SUCESSO", ator=login, perfil=linha["perfil"])
    if erro:
        raise AcessoNegado(erro)
    return {"login": linha["login"], "nome": linha["nome"], "perfil": linha["perfil"]}


# ---------------------------------------------------------------------------
# Chaves da API
# ---------------------------------------------------------------------------
def identificar_chave_api(chave: str | None) -> str | None:
    """Devolve o escopo da chave ('ingestao' ou 'consulta') ou None se invalida.

    A comparacao e feita em tempo constante contra cada chave configurada.
    """
    if not chave:
        return None
    escopo = None
    for nome, esperada in (("ingestao", config.API_KEY_INGESTAO), ("consulta", config.API_KEY_CONSULTA)):
        if esperada and hmac.compare_digest(chave.encode(), esperada.encode()):
            escopo = nome
    return escopo


def impressao_digital(chave: str) -> str:
    """Identificador nao reversivel da chave para logs/auditoria (nunca a chave em si)."""
    return hashlib.sha256(chave.encode()).hexdigest()[:10]
