"""
Compatibilidade com a Sprint 3.

O backend ficava neste arquivo (585 linhas com rota, regra de negócio e SQL
juntos). Na Sprint 4 ele foi separado em:

    src/somprev/api/app.py .................. rotas, chaves de API e proteções
    src/somprev/servicos/processamento.py ... fluxo de uma leitura (qualidade →
                                              modelo → score → alertas → auditoria)
    src/somprev/banco/repositorio.py ........ todo o SQL

Este arquivo continua existindo só para não quebrar quem aponta para o caminho
antigo: ele expõe o mesmo objeto `app` do FastAPI.

Forma recomendada de subir a API:  python scripts/run.py api
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from somprev.api.app import app  # noqa: E402,F401  (reexportado de propósito)
