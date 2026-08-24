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


conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

rows = cur.execute("""
    SELECT
        auditoria_id,
        evento,
        leitura_id,
        equipamento_id,
        status,
        modelo_versao
    FROM auditoria
    WHERE leitura_id = 6007
    ORDER BY auditoria_id
""").fetchall()

print("\nAuditoria da leitura 6007:\n")

for row in rows:
    print(row)

print(f"\nTotal de eventos: {len(rows)}")

conn.close()