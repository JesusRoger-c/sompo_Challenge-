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


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS auditoria (
            auditoria_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora        TEXT DEFAULT (datetime('now')),
            evento           TEXT NOT NULL,
            leitura_id       INTEGER,
            equipamento_id   TEXT,
            status           TEXT NOT NULL,
            detalhes         TEXT,
            modelo_versao    TEXT,
            FOREIGN KEY (leitura_id)
                REFERENCES leituras(leitura_id),
            FOREIGN KEY (equipamento_id)
                REFERENCES equipamentos(equipamento_id)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_auditoria_evento
        ON auditoria(evento)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_auditoria_leitura
        ON auditoria(leitura_id)
    """)

    conn.commit()
    conn.close()

    print("[OK] Tabela de auditoria criada/verificada.")


if __name__ == "__main__":
    main()