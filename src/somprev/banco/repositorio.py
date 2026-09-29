"""
Repositorio: todas as consultas SQL do sistema em um so lugar.

Os demais modulos nunca escrevem SQL solto - chamam funcoes daqui. Isso
padroniza o acesso ao banco, usa sempre parametros (`?`, nunca concatenacao ->
protecao contra SQL injection) e facilita testar e auditar as consultas.
"""

from __future__ import annotations

import json
import sqlite3

import pandas as pd

# ---------------------------------------------------------------------------
# Cadastros
# ---------------------------------------------------------------------------


def inserir_regioes(conn: sqlite3.Connection, regioes: list[dict]) -> dict[str, int]:
    conn.executemany("INSERT INTO regioes (nome, estado, bioma, regime) VALUES (:nome, :estado, :bioma, :regime)",
                     regioes)
    return mapa_regioes(conn)


def mapa_regioes(conn: sqlite3.Connection) -> dict[str, int]:
    return {r["nome"]: r["regiao_id"] for r in conn.execute("SELECT regiao_id, nome FROM regioes")}


def inserir_equipamentos(conn: sqlite3.Connection, equipamentos: list[dict]) -> None:
    conn.executemany(
        """INSERT INTO equipamentos (equipamento_id, modelo, tipo, ano_fabricacao, data_fabricacao,
                                     regiao_base_id, intervalo_manutencao_h)
           VALUES (:equipamento_id, :modelo, :tipo, :ano_fabricacao, :data_fabricacao,
                   :regiao_base_id, :intervalo_manutencao_h)""", equipamentos)


def obter_equipamento(conn: sqlite3.Connection, equipamento_id: str) -> dict | None:
    linha = conn.execute("SELECT * FROM equipamentos WHERE equipamento_id = ?", (equipamento_id,)).fetchone()
    return dict(linha) if linha else None


def obter_regiao(conn: sqlite3.Connection, regiao_id: int) -> dict | None:
    linha = conn.execute("SELECT * FROM regioes WHERE regiao_id = ?", (regiao_id,)).fetchone()
    return dict(linha) if linha else None


def listar_equipamentos(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("""SELECT e.*, r.nome AS regiao_base FROM equipamentos e
                          JOIN regioes r ON r.regiao_id = e.regiao_base_id ORDER BY e.equipamento_id""", conn)


# ---------------------------------------------------------------------------
# Leituras
# ---------------------------------------------------------------------------
COLUNAS_LEITURA_BANCO = [
    "leitura_id", "data_hora", "equipamento_id", "regiao_id", "umidade_solo_pct", "precipitacao_24h_mm",
    "temperatura_c", "tipo_solo", "declividade_graus", "distancia_corpo_dagua_m", "tipo_operacao",
    "idade_equipamento_anos", "horas_desde_manutencao", "horas_operacao_dia", "carga_pct", "periodo_dia",
    "houve_sinistro", "origem", "qualidade_status", "qualidade_obs", "hash_payload",
]


def leitura_existe(conn: sqlite3.Connection, leitura_id: int | None, equipamento_id: str, data_hora: str) -> str | None:
    """Devolve o motivo da duplicidade (ou None se a leitura e nova)."""
    if leitura_id is not None and conn.execute("SELECT 1 FROM leituras WHERE leitura_id = ?",
                                               (leitura_id,)).fetchone():
        return f"leitura_id {leitura_id} já recebido"
    if conn.execute("SELECT 1 FROM leituras WHERE equipamento_id = ? AND data_hora = ?",
                    (equipamento_id, data_hora)).fetchone():
        return f"já existe leitura de {equipamento_id} em {data_hora} (reenvio)"
    return None


def proximo_leitura_id(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COALESCE(MAX(leitura_id), 0) + 1 FROM leituras").fetchone()[0])


def inserir_leituras(conn: sqlite3.Connection, linhas: list[dict]) -> None:
    placeholders = ", ".join(f":{c}" for c in COLUNAS_LEITURA_BANCO)
    conn.executemany(f"INSERT INTO leituras ({', '.join(COLUNAS_LEITURA_BANCO)}) VALUES ({placeholders})",
                     [{c: linha.get(c) for c in COLUNAS_LEITURA_BANCO} for linha in linhas])


def inserir_quarentena(conn: sqlite3.Connection, origem: str, motivo: str, payload: dict,
                       leitura_id=None, equipamento_id=None, data_hora=None) -> int:
    cur = conn.execute(
        """INSERT INTO leituras_quarentena (origem, leitura_id, equipamento_id, data_hora, motivo, payload_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (origem, leitura_id, equipamento_id, data_hora, motivo,
         json.dumps(payload, ensure_ascii=False, default=str)))
    return int(cur.lastrowid)


# Obs.: `variavel` so entra no SQL depois de conferida contra uma lista fixa de
# nomes de coluna (abaixo); valores do usuario vao sempre como parametro `?`.
def referencia_imputacao(conn: sqlite3.Connection, variavel: str, leitura: dict) -> float | None:
    """Valor de referencia para imputar uma variavel ausente em tempo real.

    Clima -> mediana da mesma regiao no dia (ou nas 24 h anteriores); uso da maquina -> ultimo valor
    conhecido do equipamento antes desta leitura. Mesma politica do modo lote.
    """
    if variavel in ("umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c"):
        # Mesmo dia da regiao; se ainda nao houver leitura no dia, as 24 h anteriores
        # (o clima de uma regiao muda pouco de um dia para o outro).
        dh = str(leitura.get("data_hora"))
        valores = [r[0] for r in conn.execute(
            f"SELECT {variavel} FROM leituras WHERE regiao_id = ? AND (substr(data_hora, 1, 10) = ? "
            "OR data_hora BETWEEN datetime(?, '-24 hours') AND ?)",
            (leitura.get("regiao_id"), dh[:10], dh, dh))]
        return float(pd.Series(valores).median()) if valores else None
    if variavel in ("horas_desde_manutencao", "horas_operacao_dia", "carga_pct"):
        linha = conn.execute(
            f"SELECT {variavel} FROM leituras WHERE equipamento_id = ? AND data_hora < ? "
            "ORDER BY data_hora DESC LIMIT 1", (leitura.get("equipamento_id"), leitura.get("data_hora"))).fetchone()
        return float(linha[0]) if linha else None
    return None


# ---------------------------------------------------------------------------
# Predicoes e alertas
# ---------------------------------------------------------------------------
def inserir_predicao(conn: sqlite3.Connection, p: dict) -> int:
    cur = conn.execute(
        """INSERT INTO predicoes (leitura_id, score_risco, classe_risco, prob_sinistro, fator_1, fator_2, fator_3,
                                  explicacao_json, modelo_versao, regras_versao, criado_em)
           VALUES (:leitura_id, :score_risco, :classe_risco, :prob_sinistro, :fator_1, :fator_2, :fator_3,
                   :explicacao_json, :modelo_versao, :regras_versao, :criado_em)""", p)
    return int(cur.lastrowid)


def alerta_aberto(conn: sqlite3.Connection, equipamento_id: str, codigo: str) -> dict | None:
    linha = conn.execute(
        """SELECT alerta_id, ultima_ocorrencia, nivel FROM alertas
           WHERE equipamento_id = ? AND codigo = ? AND status IN ('aberto', 'reconhecido')
           ORDER BY alerta_id DESC LIMIT 1""", (equipamento_id, codigo)).fetchone()
    return dict(linha) if linha else None


def inserir_alerta(conn: sqlite3.Connection, a: dict) -> int:
    cur = conn.execute(
        """INSERT INTO alertas (predicao_id, leitura_id, equipamento_id, tipo, codigo, nivel, perfil_destino,
                                criterio, mensagem, recomendacao, status, criado_em, ultima_ocorrencia)
           VALUES (:predicao_id, :leitura_id, :equipamento_id, :tipo, :codigo, :nivel, :perfil_destino,
                   :criterio, :mensagem, :recomendacao, 'aberto', :criado_em, :criado_em)""", a)
    return int(cur.lastrowid)


def agrupar_ocorrencia(conn: sqlite3.Connection, alerta_id: int, data_hora: str, nivel: str,
                       ordem_nivel: dict, mensagem: str, criterio: str, recomendacao: str) -> None:
    """Soma uma ocorrencia ao alerta ativo.

    Se a nova ocorrencia for igual ou mais grave, o alerta passa a exibir o nivel,
    a mensagem, o criterio e a recomendacao mais recentes (o usuario sempre ve a
    situacao atual, e o historico completo fica na trilha de auditoria).
    """
    atual = conn.execute("SELECT nivel FROM alertas WHERE alerta_id = ?", (alerta_id,)).fetchone()["nivel"]
    if ordem_nivel[nivel] >= ordem_nivel[atual]:
        conn.execute("UPDATE alertas SET ocorrencias = ocorrencias + 1, ultima_ocorrencia = ?, nivel = ?, "
                     "mensagem = ?, criterio = ?, recomendacao = ? WHERE alerta_id = ?",
                     (data_hora, nivel, mensagem, criterio, recomendacao, alerta_id))
    else:
        conn.execute("UPDATE alertas SET ocorrencias = ocorrencias + 1, ultima_ocorrencia = ? WHERE alerta_id = ?",
                     (data_hora, alerta_id))


def atualizar_status_alerta(conn: sqlite3.Connection, alerta_id: int, novo_status: str, usuario: str,
                            comentario: str | None, quando: str) -> dict:
    linha = conn.execute("SELECT * FROM alertas WHERE alerta_id = ?", (alerta_id,)).fetchone()
    if linha is None:
        from ..excecoes import RecursoNaoEncontrado
        raise RecursoNaoEncontrado(f"Alerta {alerta_id} não encontrado.")
    ordem = {"aberto": 0, "reconhecido": 1, "resolvido": 2}
    if ordem[novo_status] <= ordem[linha["status"]]:
        from ..excecoes import DadoInvalido
        raise DadoInvalido(f"Transição inválida: {linha['status']} → {novo_status}.")
    conn.execute("UPDATE alertas SET status = ?, atualizado_em = ?, atualizado_por = ?, comentario = ? "
                 "WHERE alerta_id = ?", (novo_status, quando, usuario, comentario, alerta_id))
    return dict(linha)


def encerrar_alerta_expirado(conn: sqlite3.Connection, alerta_id: int, quando: str, janela_h: int) -> None:
    conn.execute(
        """UPDATE alertas SET status = 'resolvido', atualizado_em = ?, atualizado_por = 'sistema',
                  comentario = ? WHERE alerta_id = ? AND status != 'resolvido'""",
        (quando, f"Encerrado automaticamente: condição não se repetiu em {janela_h} h.", alerta_id))


def encerrar_alertas_antigos(conn: sqlite3.Connection, antes_de: str, quando: str) -> int:
    """Encerra alertas historicos sem nova ocorrencia desde `antes_de` (carga historica)."""
    cur = conn.execute(
        """UPDATE alertas SET status = 'resolvido', atualizado_em = ?, atualizado_por = 'sistema',
                  comentario = 'Encerrado na carga histórica: sem novas ocorrências no período.'
           WHERE status = 'aberto' AND ultima_ocorrencia < ?""", (quando, antes_de))
    return cur.rowcount


def registrar_manutencao(conn: sqlite3.Connection, equipamento_id: str, tecnico: str, descricao: str,
                         alerta_id: int | None, quando: str) -> int:
    cur = conn.execute("INSERT INTO manutencoes (equipamento_id, alerta_id, realizada_em, tecnico, descricao) "
                       "VALUES (?, ?, ?, ?, ?)", (equipamento_id, alerta_id, quando, tecnico, descricao))
    return int(cur.lastrowid)


def registrar_versao_modelo(conn: sqlite3.Connection, versao: str, algoritmo: str, treinado_em: str,
                            hash_artefato: str, metricas: dict) -> None:
    conn.execute("UPDATE modelo_versoes SET ativo = 0")
    conn.execute("""INSERT INTO modelo_versoes (versao, algoritmo, treinado_em, hash_artefato, metricas_json, ativo)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(versao) DO UPDATE SET treinado_em = excluded.treinado_em,
                        hash_artefato = excluded.hash_artefato, metricas_json = excluded.metricas_json, ativo = 1""",
                 (versao, algoritmo, treinado_em, hash_artefato, json.dumps(metricas, ensure_ascii=False)))


# ---------------------------------------------------------------------------
# Consultas analiticas (dashboard / relatorios / API)
# ---------------------------------------------------------------------------
def carregar_leituras_risco(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM vw_leituras_risco", conn)
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    return df


def carregar_alertas(conn: sqlite3.Connection, status: tuple[str, ...] | None = None) -> pd.DataFrame:
    sql = """SELECT a.*, e.tipo AS equip_tipo, r.nome AS regiao_nome, p.score_risco, l.data_hora AS data_leitura
             FROM alertas a
             JOIN equipamentos e ON e.equipamento_id = a.equipamento_id
             JOIN leituras l ON l.leitura_id = a.leitura_id
             JOIN regioes r ON r.regiao_id = l.regiao_id
             JOIN predicoes p ON p.predicao_id = a.predicao_id"""
    params: tuple = ()
    if status:
        sql += f" WHERE a.status IN ({', '.join('?' * len(status))})"
        params = status
    return pd.read_sql(sql + " ORDER BY a.ultima_ocorrencia DESC", conn, params=params)


def carregar_auditoria(conn: sqlite3.Connection, limite: int = 500) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM auditoria ORDER BY auditoria_id DESC LIMIT ?", conn, params=(limite,))


def carregar_quarentena(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM leituras_quarentena ORDER BY quarentena_id DESC", conn)


def carregar_manutencoes(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM manutencoes ORDER BY realizada_em DESC", conn)


def contagens(conn: sqlite3.Connection) -> dict[str, int]:
    tabelas = ["regioes", "equipamentos", "leituras", "leituras_quarentena", "predicoes", "alertas",
               "manutencoes", "usuarios", "auditoria", "modelo_versoes"]
    return {t: int(conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in tabelas}
