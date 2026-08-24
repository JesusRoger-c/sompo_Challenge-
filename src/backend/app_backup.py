import os
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Descobre a raiz do projeto a partir de src/backend/app.py
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

DB_PATH = os.path.join(
    BASE_DIR,
    "src",
    "database",
    "somprev_risk.db"
)


app = FastAPI(
    title="SomPrev Risk API",
    description="Backend integrador do SomPrev Risk - Sprint 3",
    version="1.0.0",
)


class Telemetria(BaseModel):
    leitura_id: int = Field(..., description="ID único da leitura")
    data_hora: str
    equipamento_id: str
    regiao_id: int
    umidade_solo_pct: float
    precipitacao_24h_mm: float
    temperatura_c: float
    tipo_solo: str
    declividade_graus: float
    distancia_corpo_dagua_m: float
    tipo_operacao: str
    idade_equipamento_anos: float
    horas_desde_manutencao: float
    horas_operacao_dia: float
    carga_pct: float
    periodo_dia: str


@app.get("/")
def home():
    return {
        "sistema": "SomPrev Risk",
        "status": "online",
        "sprint": 3,
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/telemetria")
def receber_telemetria(dado: Telemetria):

    conn = None

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # 1. Verificar equipamento
        equipamento = cur.execute(
            """
            SELECT equipamento_id
            FROM equipamentos
            WHERE equipamento_id = ?
            """,
            (dado.equipamento_id,)
        ).fetchone()

        if equipamento is None:
            raise HTTPException(
                status_code=404,
                detail=f"Equipamento '{dado.equipamento_id}' não encontrado."
            )

        # 2. Verificar região
        regiao = cur.execute(
            """
            SELECT regiao_id
            FROM regioes
            WHERE regiao_id = ?
            """,
            (dado.regiao_id,)
        ).fetchone()

        if regiao is None:
            raise HTTPException(
                status_code=404,
                detail=f"Região '{dado.regiao_id}' não encontrada."
            )

        # 3. Verificar se a leitura já existe
        existente = cur.execute(
            """
            SELECT leitura_id
            FROM leituras
            WHERE leitura_id = ?
            """,
            (dado.leitura_id,)
        ).fetchone()

        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A leitura_id '{dado.leitura_id}' já existe."
            )

        # 4. Inserir nova leitura
        cur.execute(
            """
            INSERT INTO leituras (
                leitura_id,
                data_hora,
                equipamento_id,
                regiao_id,
                umidade_solo_pct,
                precipitacao_24h_mm,
                temperatura_c,
                tipo_solo,
                declividade_graus,
                distancia_corpo_dagua_m,
                tipo_operacao,
                idade_equipamento_anos,
                horas_desde_manutencao,
                horas_operacao_dia,
                carga_pct,
                periodo_dia,
                houve_sinistro
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dado.leitura_id,
                dado.data_hora,
                dado.equipamento_id,
                dado.regiao_id,
                dado.umidade_solo_pct,
                dado.precipitacao_24h_mm,
                dado.temperatura_c,
                dado.tipo_solo,
                dado.declividade_graus,
                dado.distancia_corpo_dagua_m,
                dado.tipo_operacao,
                dado.idade_equipamento_anos,
                dado.horas_desde_manutencao,
                dado.horas_operacao_dia,
                dado.carga_pct,
                dado.periodo_dia,
                None
            )
        )

        conn.commit()

        return {
            "status": "sucesso",
            "mensagem": "Telemetria recebida e armazenada.",
            "leitura_id": dado.leitura_id,
            "equipamento_id": dado.equipamento_id
        }

    except HTTPException:
        raise

    except sqlite3.Error as erro:
        raise HTTPException(
            status_code=500,
            detail=f"Erro no banco de dados: {erro}"
        )

    finally:
        if conn is not None:
            conn.close()