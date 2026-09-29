"""Dashboard: login, perfis e permissoes (Streamlit AppTest, sem navegador)."""

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from somprev import config
from somprev.dashboard import cliente_api

APP = str(config.ROOT_DIR / "src" / "somprev" / "dashboard" / "app.py")


def _entrar(login, senha):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.text_input[0].input(login)
    at.text_input[1].input(senha)
    at.button[0].click()
    at.run()
    return at


def test_login_invalido_mostra_erro_generico(banco_isolado):
    at = _entrar("gestor", "senha-errada")
    assert any("Usuário ou senha inválidos" in e.value for e in at.error)


@pytest.mark.parametrize("login,senha,titulo", [
    ("operador", "SenhaOperador123", "Posso operar agora?"),
    ("tecnico", "SenhaTecnico1234", "Fila de manutenção preventiva"),
    ("gestor", "SenhaGestor12345", "Gestão da frota"),
    ("seguradora", "SenhaSeguradora1", "Seguradora — validação, carteira e auditoria"),
])
def test_cada_perfil_ve_sua_visao(banco_isolado, login, senha, titulo):
    at = _entrar(login, senha)
    assert not at.exception, at.exception
    textos = " ".join(m.value for m in at.markdown)
    assert titulo in textos


def test_operador_nao_ve_edicao_de_regras(banco_isolado):
    at = _entrar("operador", "SenhaOperador123")
    textos = " ".join(m.value for m in at.markdown)
    assert "Ajustar parâmetros" not in textos and "Gestão da frota" not in textos


def test_dashboard_nao_le_mais_o_banco_direto(banco_isolado):
    """O dashboard e cliente da API (rotas de consulta) - nao ha `repositorio` nem
    `sessao(somente_leitura=True)` para dados exibidos, so para acoes de escrita."""
    import ast

    arvore = ast.parse((config.ROOT_DIR / "src" / "somprev" / "dashboard" / "app.py").read_text(encoding="utf-8"))
    chamadas_repo = [n for n in ast.walk(arvore) if isinstance(n, ast.Attribute) and n.attr not in
                     ("atualizar_status_alerta", "registrar_manutencao") and
                     isinstance(n.value, ast.Name) and n.value.id == "repo"]
    assert not chamadas_repo, [c.attr for c in chamadas_repo]


def test_api_indisponivel_vira_mensagem_amigavel(monkeypatch):
    """Se a API estiver fora do ar, o dashboard nao deve mostrar um traceback cru."""
    def _falha():
        raise httpx.ConnectError("recusado")
    monkeypatch.setattr(cliente_api, "_cliente", lambda: _FalhaAoEntrar(_falha))
    with pytest.raises(cliente_api.ApiIndisponivel, match="python run.py api"):
        cliente_api.leituras_risco()


class _FalhaAoEntrar:
    """Client falso cujo __enter__ dispara a excecao de rede que o teste quer simular."""

    def __init__(self, disparar):
        self._disparar = disparar

    def __enter__(self):
        self._disparar()

    def __exit__(self, *_):
        return False
