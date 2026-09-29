"""
Excecoes de dominio do SomPrev Risk.

Separar erros ESPERADOS (dado invalido, equipamento inexistente, leitura
duplicada) de erros INESPERADOS (bug, disco cheio) permite que a API devolva o
codigo HTTP correto e uma mensagem util, sem vazar detalhes internos, e que o
pipeline em lote siga processando as demais leituras em vez de parar.
"""


class SomPrevErro(Exception):
    """Base de todos os erros previsiveis do sistema."""

    codigo_http = 400

    def __init__(self, mensagem: str, detalhes: dict | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.detalhes = detalhes or {}


class DadoInvalido(SomPrevErro):
    """A leitura nao pode ser processada (campo critico ausente ou impossivel)."""

    codigo_http = 422


class RecursoNaoEncontrado(SomPrevErro):
    """Equipamento, regiao ou registro referenciado nao existe."""

    codigo_http = 404


class LeituraDuplicada(SomPrevErro):
    """A mesma leitura ja foi recebida (reenvio de pacote pelo sensor)."""

    codigo_http = 409


class ModeloIndisponivel(SomPrevErro):
    """Artefato do modelo ausente ou incompativel - rode o pipeline de treino."""

    codigo_http = 503


class AcessoNegado(SomPrevErro):
    """Credencial invalida, conta bloqueada ou perfil sem permissao."""

    codigo_http = 403
