"""
Orquestracao do fluxo completo do SomPrev Risk (reprodutivel de ponta a ponta).

    [1] coleta simulada ......... cadastro da frota + telemetria bruta com falhas
    [2] qualidade de dados ...... limpeza, imputacao, quarentena, relatorio
    [3] modelo .................. treino, calibracao, limiar, metricas, model card
    [4] banco de dados .......... schema, cadastros, usuarios, versao do modelo
    [5] carga + score ........... predicoes, explicacoes e alertas do historico
    [6] relatorios .............. tendencias por regiao, operacao e equipamento
    [7] verificacao ............. integridade, consistencia e trilha de auditoria

Mesma seed -> mesmos dados, mesmo modelo, mesmos numeros em qualquer maquina.
Cada etapa e isolada em uma funcao e falhas sao reportadas com a etapa exata.
"""

from __future__ import annotations

import json
import time

import pandas as pd

from . import config, regras
from .banco import repositorio as repo
from .banco.conexao import criar_schema, sessao, transacao
from .dados import gerador, qualidade
from .logs import configurar_logs, obter_logger
from .modelo import treino
from .modelo.inferencia import carregar_modelo
from .relatorios import tendencias
from .seguranca import auditoria, autenticacao
from .servicos import processamento, verificacao

log = obter_logger("pipeline")


def _etapa(numero: int, titulo: str) -> float:
    print(f"\n[{numero}/7] {titulo}")
    return time.perf_counter()


def _ok(inicio: float, texto: str) -> None:
    print(f"      ✔ {texto}  ({time.perf_counter() - inicio:.1f}s)")


def etapa_coleta() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    t = _etapa(1, "Coleta simulada de telemetria")
    cadastro, leituras = gerador.gerar_base()
    bruto, falhas = gerador.simular_coleta_bruta(leituras)
    cadastro.to_csv(config.CADASTRO_EQUIP_CSV, index=False)
    bruto.to_csv(config.DADOS_BRUTOS_CSV, index=False)
    gerador.cenarios_exemplo().to_csv(config.DATASET_EXEMPLO_CSV, index=False)
    _ok(t, f"{len(cadastro)} equipamentos · {len(bruto)} registros brutos · "
           f"{sum(falhas.values())} falhas de coleta injetadas")
    return cadastro, bruto, falhas


def etapa_qualidade(cadastro: pd.DataFrame, bruto: pd.DataFrame, falhas: dict) -> qualidade.ResultadoLote:
    t = _etapa(2, "Qualidade de dados (validação, limpeza, imputação, quarentena)")
    resultado = qualidade.tratar_lote(bruto, cadastro)
    resultado.relatorio["falhas_injetadas_na_simulacao"] = falhas
    resultado.tratado.to_csv(config.DADOS_TRATADOS_CSV, index=False)
    config.RELATORIO_QUALIDADE_JSON.write_text(json.dumps(resultado.relatorio, indent=2, ensure_ascii=False),
                                               encoding="utf-8")
    r = resultado.relatorio
    _ok(t, f"{r['aceitas']} aceitas ({r['aceitas_com_correcao']} corrigidas) · "
           f"{sum(r['duplicidades'].values())} duplicadas removidas · {r['quarentena_total']} em quarentena · "
           f"aproveitamento {r['taxa_aproveitamento']:.1%}")
    return resultado


def etapa_modelo(tratado: pd.DataFrame, rapido: bool) -> dict:
    t = _etapa(3, "Modelo preditivo (seleção temporal, calibração, limiar por custo)")
    metricas = treino.treinar(tratado, rapido=rapido)
    final = metricas["modelo_final_teste"]
    limiar_cfg = regras.carregar_regras()["alerta_modelo"]["limiar_score"]
    _ok(t, f"{metricas['versao_modelo']} · teste: ROC-AUC {final['roc_auc']:.3f} · PR-AUC {final['pr_auc']:.3f} · "
           f"recall {final['recall']:.0%} no limiar {metricas['analise_limiar']['limiar_score']}")
    if metricas["analise_limiar"]["limiar_score"] != limiar_cfg:
        print(f"      ⚠ limiar recomendado ({metricas['analise_limiar']['limiar_score']}) difere do configurado "
              f"({limiar_cfg}) em config/regras_risco.json — revise com o gestor.")
    return metricas


def etapa_banco(cadastro: pd.DataFrame, resultado: qualidade.ResultadoLote, metricas: dict) -> None:
    t = _etapa(4, "Banco de dados (schema, cadastros, usuários, versão do modelo)")
    for sufixo in ("", "-wal", "-shm"):
        caminho = config.DB_PATH.with_name(config.DB_PATH.name + sufixo)
        if caminho.exists():
            caminho.unlink()
    with sessao() as conn:
        criar_schema(conn)
        with transacao(conn):
            regioes = [{"nome": r.nome, "estado": r.estado, "bioma": r.bioma, "regime": r.regime}
                       for r in gerador.REGIOES]
            mapa = repo.inserir_regioes(conn, regioes)
            cad = cadastro.assign(regiao_base_id=cadastro["regiao_base"].map(mapa))
            repo.inserir_equipamentos(conn, cad.to_dict("records"))
            for linha in resultado.quarentena.to_dict("records"):
                repo.inserir_quarentena(conn, "carga_historica", linha["motivo"],
                                        {k: v for k, v in linha.items() if k != "motivo"},
                                        linha.get("leitura_id"), linha.get("equipamento_id"),
                                        str(linha.get("data_hora")))
            modelo = carregar_modelo()
            repo.registrar_versao_modelo(conn, modelo.versao, modelo.algoritmo, modelo.treinado_em,
                                         treino.sha256_arquivo(config.MODELO_PATH), metricas["modelo_final_teste"])
            auditoria.registrar(conn, "QUALIDADE_DADOS", ator="pipeline", detalhes={
                k: resultado.relatorio[k] for k in ("recebidas", "aceitas", "quarentena_total", "duplicidades")})
            auditoria.registrar(conn, "MODELO_REGISTRADO", ator="pipeline", modelo_versao=modelo.versao,
                                detalhes={"hash": treino.sha256_arquivo(config.MODELO_PATH),
                                          "teste": metricas["modelo_final_teste"]})
            usuarios = config.usuarios_iniciais()
            for perfil, (login, senha) in usuarios.items():
                autenticacao.criar_usuario(conn, login, senha, perfil, nome=f"{config.ROTULO_PERFIL[perfil]} (demo)")
    faltando = set(config.PERFIS) - set(usuarios)
    _ok(t, f"{len(mapa)} regiões · {len(cadastro)} equipamentos · {len(resultado.quarentena)} em quarentena · "
           f"{len(usuarios)} usuários")
    if faltando:
        print(f"      ⚠ sem credenciais no .env para: {', '.join(sorted(faltando))} "
              "(rode: python run.py configurar)")


def etapa_carga(tratado: pd.DataFrame) -> dict:
    t = _etapa(5, "Carga histórica + score + explicação + alertas")
    # Recebe o DataFrame já tratado em memória (etapa 2) em vez de reler o CSV do
    # disco: o CSV em config.DADOS_TRATADOS_CSV é só a evidência exigida pelo enunciado
    # (pipeline de dados tratados), nunca a fonte de leitura do pipeline ou da API/dashboard.
    with sessao() as conn:
        resumo = processamento.carregar_historico(conn, tratado, repo.mapa_regioes(conn))
    classes = " · ".join(f"{regras.ROTULO_CLASSE[c]} {n}" for c, n in resumo["por_classe"].items())
    _ok(t, f"{resumo['leituras']} predições ({classes}) · {resumo['alertas_criados']} alertas")
    return resumo


def etapa_relatorios() -> dict:
    t = _etapa(6, "Relatórios de tendência")
    with sessao() as conn:
        df = repo.carregar_leituras_risco(conn)
        alertas = repo.carregar_alertas(conn)
        arquivos = tendencias.gerar_relatorio(df, alertas)
        with transacao(conn):
            auditoria.registrar(conn, "RELATORIO_EXPORTADO", ator="pipeline", detalhes=arquivos)
    _ok(t, f"document/relatorios/{arquivos['markdown']} + {len(arquivos['graficos'])} gráficos + "
           f"{len(arquivos['csv'])} CSV")
    return arquivos


def etapa_verificacao() -> list[dict]:
    t = _etapa(7, "Verificação de integridade e consistência")
    with sessao() as conn:
        itens = verificacao.verificar_sistema(conn)
        with transacao(conn):
            auditoria.registrar(conn, "VERIFICACAO_SISTEMA", ator="pipeline",
                                status="SUCESSO" if all(i["ok"] for i in itens) else "FALHA",
                                detalhes={i["verificacao"]: i["ok"] for i in itens})
    for i in itens:
        print(f"      {'✔' if i['ok'] else '✖'} {i['verificacao']} — {i['detalhe']}")
    _ok(t, f"{sum(i['ok'] for i in itens)}/{len(itens)} verificações aprovadas")
    return itens


def executar(rapido: bool = False, pular_treino: bool = False) -> bool:
    """Roda o pipeline completo. Devolve True se todas as verificacoes passaram."""
    configurar_logs()
    config.garantir_diretorios()
    inicio = time.perf_counter()
    print("=" * 72)
    print(" SomPrev Risk — pipeline de ponta a ponta (Sprint 4)")
    print("=" * 72)
    cadastro, bruto, falhas = etapa_coleta()
    resultado = etapa_qualidade(cadastro, bruto, falhas)
    if pular_treino and config.METRICAS_PATH.exists() and config.MODELO_PATH.exists():
        print("\n[3/7] Modelo preditivo — reaproveitando o artefato existente (--pular-treino)")
        metricas = json.loads(config.METRICAS_PATH.read_text(encoding="utf-8"))
    else:
        metricas = etapa_modelo(resultado.tratado, rapido)
    etapa_banco(cadastro, resultado, metricas)
    etapa_carga(resultado.tratado)
    etapa_relatorios()
    itens = etapa_verificacao()
    ok = all(i["ok"] for i in itens)
    print("\n" + "=" * 72)
    print(f" {'CONCLUÍDO' if ok else 'CONCLUÍDO COM FALHAS'} em {time.perf_counter() - inicio:.0f}s · "
          f"banco: {config.DB_PATH.relative_to(config.ROOT_DIR) if config.DB_PATH.is_relative_to(config.ROOT_DIR) else config.DB_PATH}")
    print("=" * 72)
    log.info("Pipeline concluido", extra={"contexto": {"ok": ok}})
    return ok
