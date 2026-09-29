"""Seguranca: senhas, bloqueio, controle de acesso e auditoria encadeada."""

import sqlite3

import pytest

from somprev import config
from somprev.banco.conexao import sessao
from somprev.excecoes import AcessoNegado, DadoInvalido
from somprev.seguranca import auditoria, autenticacao


def test_hash_de_senha_nao_guarda_a_senha():
    h = autenticacao.gerar_hash_senha("SenhaMuitoForte123")
    assert "SenhaMuitoForte123" not in h and h.startswith("pbkdf2_sha256$")
    assert autenticacao.conferir_senha("SenhaMuitoForte123", h)
    assert not autenticacao.conferir_senha("senhamuitoforte123", h)
    # Mesmo texto -> hashes diferentes (salt aleatorio).
    assert h != autenticacao.gerar_hash_senha("SenhaMuitoForte123")


@pytest.mark.parametrize("senha", ["curta1", "semnumerosnenhum", "123456789012"])
def test_politica_de_senha(senha):
    with pytest.raises(DadoInvalido):
        autenticacao.validar_politica_senha(senha)


def test_login_correto_e_incorreto(banco_isolado):
    with sessao() as conn:
        u = autenticacao.autenticar(conn, "gestor", "SenhaGestor12345")
    assert u["perfil"] == "Gestor"
    with pytest.raises(AcessoNegado) as erro, sessao() as conn:
        autenticacao.autenticar(conn, "gestor", "errada")
    assert str(erro.value) == "Usuário ou senha inválidos."


def test_falha_de_login_fica_gravada_mesmo_com_erro(banco_isolado):
    """Regressao: o erro de login nao pode desfazer (ROLLBACK) o registro da tentativa."""
    _tentar("gestor", "errada")
    with sessao() as conn:
        falhas = conn.execute("SELECT tentativas_falhas FROM usuarios WHERE login = 'gestor'").fetchone()[0]
        eventos = conn.execute("SELECT COUNT(*) FROM auditoria WHERE evento = 'LOGIN_FALHA'").fetchone()[0]
    assert falhas == 1 and eventos == 1


def test_usuario_inexistente_recebe_mesma_mensagem(banco_isolado):
    with pytest.raises(AcessoNegado) as erro, sessao() as conn:
        autenticacao.autenticar(conn, "nao_existe", "qualquer")
    assert str(erro.value) == "Usuário ou senha inválidos."


def _tentar(login, senha):
    try:
        with sessao() as conn:
            autenticacao.autenticar(conn, login, senha)
        return "ok"
    except AcessoNegado as e:
        return str(e)


def test_bloqueio_apos_tentativas_invalidas(banco_isolado):
    for _ in range(config.LOGIN_MAX_TENTATIVAS):
        _tentar("operador", "errada")
    # Mesmo com a senha certa, a conta fica bloqueada temporariamente.
    assert "bloqueada" in _tentar("operador", "SenhaOperador123")
    with sessao() as conn:
        eventos = [r[0] for r in conn.execute("SELECT evento FROM auditoria WHERE ator = 'operador'")]
    assert "CONTA_BLOQUEADA" in eventos and eventos.count("LOGIN_FALHA") >= config.LOGIN_MAX_TENTATIVAS


def test_banco_so_tem_hashes(banco_isolado):
    with sessao() as conn:
        hashes = [r[0] for r in conn.execute("SELECT hash_senha FROM usuarios")]
    assert len(hashes) == 4 and all(h.startswith("pbkdf2_sha256$") for h in hashes)
    assert not any("Senha" in h for h in hashes)


@pytest.mark.parametrize("perfil,permissao,esperado", [
    ("Operador", "editar_regras", False), ("Operador", "reconhecer_alerta", True),
    ("Tecnico", "registrar_manutencao", True), ("Tecnico", "ver_auditoria", False),
    ("Gestor", "editar_regras", True), ("Seguradora", "verificar_auditoria", True),
    ("Seguradora", "resolver_alerta", False), ("Invasor", "ver_frota", False)])
def test_permissoes_por_perfil(perfil, permissao, esperado):
    assert autenticacao.tem_permissao(perfil, permissao) is esperado


def test_acesso_negado_e_auditado(banco_isolado):
    with pytest.raises(AcessoNegado), sessao() as conn:
        autenticacao.exigir_permissao(conn, "operador", "Operador", "editar_regras")
    with sessao() as conn:
        n = conn.execute("SELECT COUNT(*) FROM auditoria WHERE evento = 'ACESSO_NEGADO'").fetchone()[0]
    assert n == 1


def test_chaves_de_api_tem_escopos_separados():
    assert autenticacao.identificar_chave_api(config.API_KEY_INGESTAO) == "ingestao"
    assert autenticacao.identificar_chave_api(config.API_KEY_CONSULTA) == "consulta"
    assert autenticacao.identificar_chave_api("chave-falsa") is None
    assert autenticacao.identificar_chave_api(None) is None


def test_auditoria_e_somente_insercao(banco_isolado):
    with sessao() as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("UPDATE auditoria SET status = 'SUCESSO' WHERE auditoria_id = 1")
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM auditoria WHERE auditoria_id = 1")


def test_cadeia_integra_e_deteccao_de_adulteracao(banco_isolado):
    with sessao() as conn:
        assert auditoria.verificar_cadeia(conn).integra
        # Simula um atacante com acesso direto ao arquivo: remove a protecao e altera um evento.
        conn.execute("DROP TRIGGER trg_auditoria_sem_update")
        conn.execute("UPDATE auditoria SET detalhes = '{\"adulterado\": true}' WHERE auditoria_id = 2")
        resultado = auditoria.verificar_cadeia(conn)
    assert not resultado.integra
    assert resultado.primeiro_problema["auditoria_id"] == 2
    assert "alterado" in resultado.primeiro_problema["motivo"]


def test_remocao_de_evento_quebra_a_cadeia(banco_isolado):
    with sessao() as conn:
        conn.execute("DROP TRIGGER trg_auditoria_sem_delete")
        conn.execute("DELETE FROM auditoria WHERE auditoria_id = 3")
        resultado = auditoria.verificar_cadeia(conn)
    assert not resultado.integra and "quebrado" in resultado.primeiro_problema["motivo"]
