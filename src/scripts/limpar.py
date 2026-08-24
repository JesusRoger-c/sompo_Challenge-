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


IDS_TESTE = (6001, 6002)


with sqlite3.connect(DB_PATH) as conn:
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    print("\nLeituras que serão verificadas:")

    registros = cur.execute(
        """
        SELECT
            l.leitura_id,
            l.equipamento_id,
            l.data_hora
        FROM leituras l
        LEFT JOIN predicoes p
            ON p.leitura_id = l.leitura_id
        WHERE l.leitura_id IN (?, ?)
          AND p.predicao_id IS NULL
        """,
        IDS_TESTE
    ).fetchall()

    if not registros:
        print("Nenhuma leitura órfã encontrada.")
    else:
        for registro in registros:
            print(registro)

        cur.execute(
            """
            DELETE FROM leituras
            WHERE leitura_id IN (?, ?)
              AND NOT EXISTS (
                  SELECT 1
                  FROM predicoes p
                  WHERE p.leitura_id = leituras.leitura_id
              )
            """,
            IDS_TESTE
        )

        removidas = cur.rowcount

        conn.commit()

        print(
            f"\n[OK] {removidas} leitura(s) órfã(s) removida(s)."
        )