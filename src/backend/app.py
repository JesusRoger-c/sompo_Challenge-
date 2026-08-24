import json
import os
import secrets
import sqlite3
import sys

import joblib
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

load_dotenv(os.path.join(BASE_DIR, ".env"))



SRC_DIR = os.path.join(BASE_DIR, "src")

DB_PATH = os.path.join(
    SRC_DIR,
    "database",
    "somprev_risk.db"
)

MODELO_PATH = os.path.join(
    SRC_DIR,
    "models",
    "modelo_risco.pkl"
)

METRICAS_PATH = os.path.join(
    SRC_DIR,
    "models",
    "metricas.json"
)

SCRIPTS_PATH = os.path.join(
    SRC_DIR,
    "scripts"
)


# Permite reutilizar risco_utils.py e tema.py
if SCRIPTS_PATH not in sys.path:
    sys.path.append(SCRIPTS_PATH)

import risco_utils as ru


# ---------------------------------------------------------------------------
# Carregamento do modelo
# ---------------------------------------------------------------------------

modelo = joblib.load(MODELO_PATH)

with open(METRICAS_PATH, encoding="utf-8") as arquivo:
    metricas = json.load(arquivo)

VERSAO_MODELO = metricas.get(
    "versao_modelo",
    "rf-v1.0"
)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SomPrev Risk API",
    description="Backend integrador do SomPrev Risk - Sprint 3",
    version="1.0.0",
)



API_KEY = os.getenv("SOMPREV_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "SOMPREV_API_KEY não definida no arquivo .env."
    )


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


def validar_api_key(
    chave_recebida: str = Depends(api_key_header)
):
    if not chave_recebida:
        raise HTTPException(
            status_code=401,
            detail="API Key não informada."
        )

    if not secrets.compare_digest(
        chave_recebida,
        API_KEY
    ):
        raise HTTPException(
            status_code=401,
            detail="API Key inválida."
        )

    return chave_recebida

# ---------------------------------------------------------------------------
# Estrutura dos dados recebidos
# ---------------------------------------------------------------------------

class Telemetria(BaseModel):
    leitura_id: int = Field(
        ...,
        gt=0,
        description="ID único da leitura"
    )

    data_hora: str
    equipamento_id: str
    regiao_id: int

    umidade_solo_pct: float = Field(
        ...,
        ge=0,
        le=100
    )

    precipitacao_24h_mm: float = Field(
        ...,
        ge=0
    )

    temperatura_c: float

    tipo_solo: str

    declividade_graus: float = Field(
        ...,
        ge=0
    )

    distancia_corpo_dagua_m: float = Field(
        ...,
        ge=0
    )

    tipo_operacao: str

    idade_equipamento_anos: float = Field(
        ...,
        ge=0
    )

    horas_desde_manutencao: float = Field(
        ...,
        ge=0
    )

    horas_operacao_dia: float = Field(
        ...,
        ge=0
    )

    carga_pct: float = Field(
        ...,
        ge=0
    )

    periodo_dia: str


# ---------------------------------------------------------------------------
# Endpoints básicos
# ---------------------------------------------------------------------------

def registrar_auditoria(
    cur,
    evento,
    leitura_id,
    equipamento_id,
    status,
    detalhes
):
    cur.execute(
        """
        INSERT INTO auditoria (
            evento,
            leitura_id,
            equipamento_id,
            status,
            detalhes,
            modelo_versao
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            evento,
            leitura_id,
            equipamento_id,
            status,
            detalhes,
            VERSAO_MODELO,
        )
    )

@app.get("/")
def home():
    return {
        "sistema": "SomPrev Risk",
        "status": "online",
        "sprint": 3,
        "modelo": VERSAO_MODELO,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "banco": os.path.exists(DB_PATH),
        "modelo": os.path.exists(MODELO_PATH),
        "versao_modelo": VERSAO_MODELO,
    }


# ---------------------------------------------------------------------------
# Entrada e processamento da telemetria
# ---------------------------------------------------------------------------

@app.post("/telemetria")
def receber_telemetria(
    dado: Telemetria,
    _: str = Depends(validar_api_key)
):

    conn = None

    try:
        conn = sqlite3.connect(DB_PATH)

        # Ativa as chaves estrangeiras também nesta conexão.
        conn.execute("PRAGMA foreign_keys = ON")

        cur = conn.cursor()

        # ------------------------------------------------------------------
        # 1. Verificar equipamento
        # ------------------------------------------------------------------

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
                detail=(
                    f"Equipamento "
                    f"'{dado.equipamento_id}' não encontrado."
                )
            )

        # ------------------------------------------------------------------
        # 2. Verificar região
        # ------------------------------------------------------------------

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
                detail=(
                    f"Região "
                    f"'{dado.regiao_id}' não encontrada."
                )
            )

        # ------------------------------------------------------------------
        # 3. Impedir leitura duplicada
        # ------------------------------------------------------------------

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
                detail=(
                    f"A leitura_id "
                    f"'{dado.leitura_id}' já existe."
                )
            )

        # ------------------------------------------------------------------
        # 4. Preparar os dados para o Random Forest
        # ------------------------------------------------------------------

        linha_modelo = {
            feature: getattr(dado, feature)
            for feature in ru.FEATURES
        }

        X = pd.DataFrame(
            [linha_modelo],
            columns=ru.FEATURES
        )

        # ------------------------------------------------------------------
        # 5. Executar o modelo
        # ------------------------------------------------------------------

        probabilidade = float(
            modelo.predict_proba(X)[0][1]
        )

        score = ru.prob_para_score(
            probabilidade
        )

        classe, _, _ = ru.classificar_risco(
            score
        )

        fatores = ru.top_fatores(
            linha_modelo
        )

        # ------------------------------------------------------------------
        # 6. Salvar a leitura
        # ------------------------------------------------------------------

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
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
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
                None,
            )
        )
        registrar_auditoria(
            cur=cur,
            evento="TELEMETRIA_RECEBIDA",
            leitura_id=dado.leitura_id,
            equipamento_id=dado.equipamento_id,
            status="SUCESSO",
            detalhes=json.dumps(
                {
                    "regiao_id": dado.regiao_id,
                    "umidade_solo_pct": dado.umidade_solo_pct,
                    "precipitacao_24h_mm": dado.precipitacao_24h_mm,
                },
                ensure_ascii=False
            )
        )

        # ------------------------------------------------------------------
        # 7. Salvar a predição
        # ------------------------------------------------------------------

        cur.execute(
            """
            INSERT INTO predicoes (
                leitura_id,
                score_risco,
                classe_risco,
                prob_sinistro,
                fator_1,
                fator_2,
                fator_3,
                modelo_versao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dado.leitura_id,
                score,
                classe,
                round(probabilidade, 4),
                fatores[0],
                fatores[1],
                fatores[2],
                VERSAO_MODELO,
            )
        )

        predicao_id = cur.lastrowid


        registrar_auditoria(
            cur=cur,
            evento="PREDICAO_GERADA",
            leitura_id=dado.leitura_id,
            equipamento_id=dado.equipamento_id,
            status="SUCESSO",
            detalhes=json.dumps(
                {
                    "probabilidade": round(probabilidade, 4),
                    "score": score,
                    "classe": classe,
                    "fatores": fatores,
                },
                ensure_ascii=False
            )
        )

        # ------------------------------------------------------------------
        # 8. Gerar alerta preventivo
        # ------------------------------------------------------------------

        alerta_gerado = False
        alerta_id = None

        if classe in ("Alto", "Critico"):

            cur.execute(
                """
                INSERT INTO alertas (
                    predicao_id,
                    nivel,
                    mensagem,
                    recomendacao,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    predicao_id,
                    classe,
                    (
                        f"Risco {classe} detectado "
                        f"para a operação."
                    ),
                    ru.recomendacao(classe),
                    "aberto",
                )
            )

            alerta_id = cur.lastrowid
            alerta_gerado = True

            registrar_auditoria(
      
            cur=cur,
            evento="ALERTA_GERADO",
            leitura_id=dado.leitura_id,
            equipamento_id=dado.equipamento_id,
            status="SUCESSO",
            detalhes=json.dumps(
        {
            "alerta_id": alerta_id,
            "nivel": classe,
            "recomendacao": ru.recomendacao(classe),
        },
        ensure_ascii=False
    )
)

        # ------------------------------------------------------------------
        # 9. Confirmar tudo no banco
        # ------------------------------------------------------------------

        conn.commit()

        # ------------------------------------------------------------------
        # 10. Resposta da API
        # ------------------------------------------------------------------

        return {
            "status": "sucesso",
            "mensagem": (
                "Telemetria processada com sucesso."
            ),
            "leitura_id": dado.leitura_id,
            "equipamento_id": dado.equipamento_id,
            "predicao": {
                "predicao_id": predicao_id,
                "probabilidade_sinistro": round(
                    probabilidade,
                    4
                ),
                "score_risco": score,
                "classe_risco": classe,
                "fatores_principais": fatores,
                "modelo_versao": VERSAO_MODELO,
            },
            "alerta": {
                "gerado": alerta_gerado,
                "alerta_id": alerta_id,
                "recomendacao": (
                    ru.recomendacao(classe)
                ),
            },
        }

    except HTTPException:
        if conn is not None:
            conn.rollback()

        raise

    except Exception as erro:
        if conn is not None:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar telemetria: {erro}"
        )

    finally:
        if conn is not None:
            conn.close()