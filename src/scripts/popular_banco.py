"""
=============================================================================
 AgroSentinela  |  Construcao e Populacao do Banco de Dados
 Challenge FIAP + Sompo Seguros  -  Sprint 2
=============================================================================

Fluxo (integracao ponta a ponta dos modulos):
    CSV de leituras  ->  banco SQL  ->  modelo de IA  ->  predicoes  ->  alertas

Passos:
  1. Cria o banco a partir de database/schema.sql.
  2. Popula 'regioes' e 'equipamentos' (cadastro) de forma coerente com os dados.
  3. Carrega todas as 'leituras' do CSV.
  4. Carrega o modelo treinado (models/modelo_risco.pkl) e gera, para cada
     leitura: probabilidade -> score 0-100 -> classe de risco -> top 3 fatores.
  5. Grava em 'predicoes' (com versao do modelo = rastreabilidade).
  6. Gera 'alertas' preventivos para as predicoes Alto/Critico.

Uso (a partir da raiz do repositorio):
    python src/scripts/popular_banco.py
"""

import os
import sqlite3
import pandas as pd
import joblib

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import risco_utils as ru

# Caminhos robustos relativos a src/: o script vive em src/scripts/.
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SRC_DIR, "database", "agrosentinela.db")
CSV_PATH = os.path.join(SRC_DIR, "datasets", "leituras_agricolas.csv")
SCHEMA_PATH = os.path.join(SRC_DIR, "database", "schema.sql")
MODELO_PATH = os.path.join(SRC_DIR, "models", "modelo_risco.pkl")
METRICAS_PATH = os.path.join(SRC_DIR, "models", "metricas.json")

REGIOES = [
    ("Sorriso", "MT", "Cerrado"),
    ("Rio Verde", "GO", "Cerrado"),
    ("Lucas do Rio Verde", "MT", "Cerrado"),
    ("Cascavel", "PR", "Mata Atlantica"),
    ("Barreiras", "BA", "Cerrado"),
    ("Nao-Me-Toque", "RS", "Pampa"),
]
MODELOS_MAQUINA = [
    ("John Deere 6110J", "Trator"),
    ("Case IH Magnum 340", "Trator"),
    ("New Holland T7", "Trator"),
    ("John Deere S780", "Colheitadeira"),
    ("Case IH Axial-Flow 8250", "Colheitadeira"),
    ("Valtra BH180", "Trator"),
    ("Jacto Uniport 3030", "Pulverizador"),
]


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    df = pd.read_csv(CSV_PATH)
    modelo = joblib.load(MODELO_PATH)
    with open(METRICAS_PATH, encoding="utf-8") as f:
        import json
        versao = json.load(f).get("versao_modelo", "rf-v1.0")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        cur.executescript(f.read())
    print("[OK] Esquema criado.")

    # ---- regioes ---------------------------------------------------------
    cur.executemany("INSERT INTO regioes (nome, estado, bioma) VALUES (?,?,?)", REGIOES)
    conn.commit()
    mapa_regiao = {nome: rid for rid, nome in cur.execute(
        "SELECT regiao_id, nome FROM regioes").fetchall()}

    # ---- equipamentos (cadastro coerente com os dados) -------------------
    import random
    random.seed(42)
    equip_ids = sorted(df["equipamento_id"].unique())
    # regiao-base = regiao mais frequente daquele equipamento nas leituras
    regiao_base = (df.groupby("equipamento_id")["regiao"]
                     .agg(lambda s: s.value_counts().index[0]).to_dict())
    idade_med = df.groupby("equipamento_id")["idade_equipamento_anos"].median().to_dict()
    equip_rows = []
    for eq in equip_ids:
        modelo_maq, tipo = random.choice(MODELOS_MAQUINA)
        ano = int(2026 - round(idade_med.get(eq, 5)))
        equip_rows.append((eq, modelo_maq, tipo, ano, mapa_regiao[regiao_base[eq]]))
    cur.executemany(
        "INSERT INTO equipamentos (equipamento_id, modelo, tipo, ano_fabricacao, regiao_base_id)"
        " VALUES (?,?,?,?,?)", equip_rows)
    conn.commit()
    print(f"[OK] {len(REGIOES)} regioes e {len(equip_rows)} equipamentos cadastrados.")

    # ---- leituras --------------------------------------------------------
    df_leit = df.copy()
    df_leit["regiao_id"] = df_leit["regiao"].map(mapa_regiao)
    cols = ["leitura_id", "data_hora", "equipamento_id", "regiao_id",
            "umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c", "tipo_solo",
            "declividade_graus", "distancia_corpo_dagua_m", "tipo_operacao",
            "idade_equipamento_anos", "horas_desde_manutencao", "horas_operacao_dia",
            "carga_pct", "periodo_dia", "houve_sinistro"]
    df_leit[cols].to_sql("leituras", conn, if_exists="append", index=False)
    print(f"[OK] {len(df_leit)} leituras inseridas.")

    # ---- predicoes (rodando o modelo de IA) ------------------------------
    X = df[ru.FEATURES]
    probs = modelo.predict_proba(X)[:, 1]

    pred_rows, alerta_rows = [], []
    for i, prob in enumerate(probs):
        score = ru.prob_para_score(prob)
        classe, _, _ = ru.classificar_risco(score)
        fatores = ru.top_fatores(df.iloc[i])
        pred_rows.append((
            int(df.iloc[i]["leitura_id"]), score, classe, round(float(prob), 4),
            fatores[0], fatores[1], fatores[2], versao))

    cur.executemany(
        "INSERT INTO predicoes (leitura_id, score_risco, classe_risco, prob_sinistro,"
        " fator_1, fator_2, fator_3, modelo_versao) VALUES (?,?,?,?,?,?,?,?)", pred_rows)
    conn.commit()
    print(f"[OK] {len(pred_rows)} predicoes gravadas.")

    # ---- alertas (apenas Alto/Critico) -----------------------------------
    rows = cur.execute(
        "SELECT predicao_id, classe_risco FROM predicoes "
        "WHERE classe_risco IN ('Alto','Critico')").fetchall()
    for pid, classe in rows:
        alerta_rows.append((
            pid, classe,
            f"Risco {classe} detectado para a operacao.",
            ru.recomendacao(classe), "aberto"))
    cur.executemany(
        "INSERT INTO alertas (predicao_id, nivel, mensagem, recomendacao, status)"
        " VALUES (?,?,?,?,?)", alerta_rows)
    conn.commit()
    print(f"[OK] {len(alerta_rows)} alertas preventivos gerados.")

    # ---- resumo ----------------------------------------------------------
    print("\nDistribuicao por classe de risco:")
    for classe, qtd in cur.execute(
        "SELECT classe_risco, COUNT(*) FROM predicoes GROUP BY classe_risco "
        "ORDER BY CASE classe_risco WHEN 'Baixo' THEN 1 WHEN 'Medio' THEN 2 "
        "WHEN 'Alto' THEN 3 ELSE 4 END").fetchall():
        print(f"   {classe:<8} {qtd}")

    conn.close()
    print(f"\n[OK] Banco pronto: {DB_PATH}")


if __name__ == "__main__":
    main()
