"""Compatibilidade com os caminhos da Sprint 3 (pontes) e com o de → para documentado."""

import importlib.util
import re

from somprev import config

RAIZ = config.ROOT_DIR
DE_PARA = RAIZ / "document" / "de_para_sprint3_sprint4.md"


def _carregar(caminho, nome):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_caminho_antigo_do_backend_ainda_expoe_a_api():
    """`src/backend/app.py` da Sprint 3 continua servindo o mesmo objeto FastAPI."""
    ponte = _carregar(RAIZ / "src" / "backend" / "app.py", "ponte_backend")
    from somprev.api.app import app
    assert ponte.app is app


def test_ponte_do_dashboard_existe_e_aponta_para_o_novo():
    texto = (RAIZ / "src" / "dashboards" / "app.py").read_text(encoding="utf-8")
    assert "somprev" in texto and "dashboard" in texto
    assert (RAIZ / "src" / "somprev" / "dashboard" / "app.py").exists()


def test_scripts_antigos_tem_mapa_de_substituicao():
    leia = (RAIZ / "src" / "scripts" / "LEIA-ME.md").read_text(encoding="utf-8")
    for antigo in ("gerar_dataset.py", "popular_banco.py", "treinar_modelo.py", "risco_utils.py",
                   "tema.py", "criar_auditoria.py", "limpar.py", "ver_auditoria.py",
                   "ver_consistencia_banco.py", "_gerar_arquitetura.py"):
        assert antigo in leia, f"{antigo} não aparece no mapa de scripts"


def test_documento_de_para_cita_os_arquivos_novos():
    texto = DE_PARA.read_text(encoding="utf-8")
    for destino in ("somprev/api/app.py", "somprev/servicos/processamento.py", "somprev/regras.py",
                    "somprev/dados/qualidade.py", "somprev/modelo/treino.py", "src/database/schema.sql"):
        assert destino in texto, f"{destino} não aparece no de → para"


def test_arquivos_citados_como_destino_existem():
    """Todo caminho src/... citado no de → para (fora da coluna 'Sprint 3') precisa existir."""
    texto = DE_PARA.read_text(encoding="utf-8")
    inexistentes = []
    for caminho in sorted(set(re.findall(r"`((?:src|config|scripts|tests)/[\w./-]+)`", texto))):
        if not (RAIZ / caminho).exists() and not caminho.startswith(("src/backend/app_backup",)):
            inexistentes.append(caminho)
    # Caminhos da Sprint 3 que deixaram de existir de propósito ficam nesta lista:
    removidos_de_proposito = {"src/scripts/risco_utils.py", "src/scripts/tema.py",
                              "src/scripts/treinar_modelo.py", "src/scripts/popular_banco.py",
                              "src/scripts/criar_auditoria.py", "src/scripts/limpar.py",
                              "src/scripts/ver_auditoria.py", "src/scripts/ver_consistencia_banco.py",
                              "src/scripts/_gerar_arquitetura.py", "src/datasets/gerar_dataset.py",
                              "src/datasets/leituras_agricolas.csv", "src/models/matriz_correlacao.png",
                              "src/dashboards/_dados_dashboard.json", "src/dashboards/preview_dashboard.html",
                              "src/backend/app_backup.py"}
    assert not set(inexistentes) - removidos_de_proposito, f"citados mas inexistentes: {inexistentes}"
