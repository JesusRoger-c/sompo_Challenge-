import os
import sqlite3


SRC_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_PATH = os.path.join(
    SRC_DIR,
    "database",
    "somprev_risk.db"
)


with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()

    leituras = cur.execute(
        "SELECT COUNT(*) FROM leituras"
    ).fetchone()[0]

    predicoes = cur.execute(
        "SELECT COUNT(*) FROM predicoes"
    ).fetchone()[0]

    alertas = cur.execute(
        "SELECT COUNT(*) FROM alertas"
    ).fetchone()[0]

    auditoria = cur.execute(
        "SELECT COUNT(*) FROM auditoria"
    ).fetchone()[0]

    sem_predicao = cur.execute("""
        SELECT
            l.leitura_id,
            l.equipamento_id,
            l.data_hora
        FROM leituras l
        LEFT JOIN predicoes p
            ON p.leitura_id = l.leitura_id
        WHERE p.predicao_id IS NULL
        ORDER BY l.leitura_id
    """).fetchall()


print("\nResumo do banco:")
print(f"Leituras:   {leituras}")
print(f"Predições:  {predicoes}")
print(f"Alertas:    {alertas}")
print(f"Auditoria:  {auditoria}")

print("\nLeituras sem predição:")

if sem_predicao:
    for registro in sem_predicao:
        print(registro)
else:
    print("Nenhuma.")

print(f"\nTotal sem predição: {len(sem_predicao)}")