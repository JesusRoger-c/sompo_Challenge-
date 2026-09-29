"""
Contrato de dados do SomPrev Risk.

Define, em um unico lugar, o que e uma leitura valida de telemetria:
  - quais variaveis o modelo consome (numericas x categoricas);
  - a faixa FISICAMENTE possivel de cada sensor (fora dela = defeito de coleta);
  - quais variaveis sao CRITICAS (sem elas nao ha score confiavel);
  - os valores aceitos para cada categoria e os sinonimos que a coleta real
    costuma produzir ("Manhã", "manha", "MANHA" -> "Manha").

O mesmo contrato e usado pelo tratamento em lote (dados/qualidade.py), pela API
(validacao de cada POST) e pelos testes - uma regra, tres consumidores.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Variavel:
    nome: str
    rotulo: str            # nome amigavel exibido ao usuario
    unidade: str
    minimo: float          # limite fisico inferior aceito
    maximo: float          # limite fisico superior aceito
    critica: bool          # sem ela a leitura vai para a quarentena
    origem: str            # "ambiente" (regiao/dia) ou "equipamento"


VARIAVEIS_NUMERICAS: tuple[Variavel, ...] = (
    Variavel("umidade_solo_pct", "Umidade do solo", "%", 0, 100, True, "ambiente"),
    Variavel("precipitacao_24h_mm", "Chuva nas últimas 24h", "mm", 0, 400, True, "ambiente"),
    Variavel("temperatura_c", "Temperatura", "°C", -10, 55, False, "ambiente"),
    Variavel("declividade_graus", "Declividade do terreno", "graus", 0, 60, True, "ambiente"),
    Variavel("distancia_corpo_dagua_m", "Distância da água", "m", 0, 5000, True, "ambiente"),
    Variavel("idade_equipamento_anos", "Idade do equipamento", "anos", 0, 50, False, "equipamento"),
    Variavel("horas_desde_manutencao", "Horas desde a última manutenção", "h", 0, 3000, False, "equipamento"),
    Variavel("horas_operacao_dia", "Horas de operação no dia", "h", 0, 24, False, "equipamento"),
    Variavel("carga_pct", "Carga do equipamento", "%", 0, 150, False, "equipamento"),
)

CATEGORIAS: dict[str, tuple[str, ...]] = {
    "tipo_solo": ("Arenoso", "Misto", "Argiloso", "Encharcado"),
    "tipo_operacao": ("Plantio", "Pulverizacao", "Colheita", "Transporte"),
    "periodo_dia": ("Manha", "Tarde", "Noite"),
}
ROTULOS_CATEGORIAS = {
    "tipo_solo": "Tipo de solo",
    "tipo_operacao": "Tipo de operação",
    "periodo_dia": "Período do dia",
}
# Categoricas criticas: sem tipo de solo ou de operacao nao ha score confiavel.
CATEGORIAS_CRITICAS = ("tipo_solo", "tipo_operacao")

FEATURES_NUM = [v.nome for v in VARIAVEIS_NUMERICAS]
FEATURES_CAT = list(CATEGORIAS)
FEATURES = FEATURES_NUM + FEATURES_CAT
ALVO = "houve_sinistro"

ROTULOS = {v.nome: v.rotulo for v in VARIAVEIS_NUMERICAS} | ROTULOS_CATEGORIAS
VARIAVEL = {v.nome: v for v in VARIAVEIS_NUMERICAS}

# Colunas de identificacao/contexto de cada leitura (nao entram no modelo).
COLUNAS_ID = ["leitura_id", "data_hora", "equipamento_id", "regiao"]
COLUNAS_LEITURA = COLUNAS_ID + FEATURES + [ALVO]


# Rotulos de exibicao para valores canonicos (o banco guarda sem acento, a tela mostra com).
ROTULO_VALOR = {"Manha": "Manhã", "Pulverizacao": "Pulverização", "Medio": "Médio", "Critico": "Crítico"}


def rotulo_valor(valor) -> str:
    return ROTULO_VALOR.get(valor, str(valor))


def _sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in base if not unicodedata.combining(c))


def normalizar_categoria(campo: str, valor) -> str | None:
    """Converte variacoes de grafia para o valor canonico; None se desconhecido.

    Exemplos: "Manhã" -> "Manha", " COLHEITA " -> "Colheita",
    "pulverização" -> "Pulverizacao". Um valor fora da lista retorna None e e
    tratado como ausente (e registrado no relatorio de qualidade).
    """
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "null"}:
        return None
    chave = _sem_acento(texto).lower()
    for canonico in CATEGORIAS[campo]:
        if _sem_acento(canonico).lower() == chave:
            return canonico
    return None
