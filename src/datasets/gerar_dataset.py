"""
=============================================================================
 AgroSentinela  |  Gerador de Dataset Sintetico de Risco Operacional Agricola
 Challenge FIAP + Sompo Seguros  -  Sprint 2
=============================================================================

Por que dados sinteticos?
    O enunciado permite explicitamente o uso de dados simulados. Como ainda
    nao temos telemetria real das maquinas seguradas pela Sompo, geramos um
    dataset que reproduz o COMPORTAMENTO ESTATISTICO esperado em campo: a
    probabilidade de um sinistro cresce de forma coerente com umidade do solo,
    chuva, declividade, proximidade de agua, idade do equipamento etc.

Como o "sinal" e construido (resumo):
    1. Sorteamos cada variavel a partir de uma distribuicao plausivel.
    2. Normalizamos cada variavel para [0, 1] na direcao do risco.
    3. Combinamos tudo em um "logito de risco" (soma ponderada + ruido).
    4. Convertemos o logito em probabilidade (funcao logistica).
    5. Sorteamos o rotulo houve_sinistro ~ Bernoulli(probabilidade).

    Resultado: um modelo de ML consegue APRENDER o padrao (as metricas nao sao
    aleatorias), mas o ruido impede acuracia "perfeita" (irreal). Isso e o que
    queremos para uma validacao estatistica honesta.

Saidas:
    src/datasets/leituras_agricolas.csv  -> base completa para treino (N linhas)
    src/datasets/dataset_exemplo.csv     -> 10 cenarios curados para o README

Uso (a partir da raiz do repositorio):
    python src/datasets/gerar_dataset.py
"""

import os
import numpy as np
import pandas as pd

# Caminhos robustos: as saidas ficam SEMPRE ao lado deste script
# (src/datasets/), independentemente do diretorio de onde ele e chamado.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Reprodutibilidade: mesma seed = mesmo dataset em qualquer maquina.
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

N_LINHAS = 6000            # volume suficiente para treino/teste robustos
N_EQUIPAMENTOS = 40        # frota simulada
DIAS_HISTORICO = 90        # janela temporal das leituras

# Regioes simuladas (nome, estado, bioma) - usadas tambem no banco SQL
REGIOES = [
    ("Sorriso",          "MT", "Cerrado"),
    ("Rio Verde",        "GO", "Cerrado"),
    ("Lucas do Rio Verde","MT", "Cerrado"),
    ("Cascavel",         "PR", "Mata Atlantica"),
    ("Barreiras",        "BA", "Cerrado"),
    ("Nao-Me-Toque",     "RS", "Pampa"),
]

TIPOS_SOLO = ["Arenoso", "Misto", "Argiloso", "Encharcado"]
TIPOS_OPERACAO = ["Plantio", "Pulverizacao", "Colheita", "Transporte"]
PERIODOS = ["Manha", "Tarde", "Noite"]

# Modelos de maquina (so para deixar o cadastro do banco realista)
MODELOS_MAQUINA = [
    ("John Deere 6110J", "Trator"),
    ("Case IH Magnum 340", "Trator"),
    ("New Holland T7", "Trator"),
    ("John Deere S780", "Colheitadeira"),
    ("Case IH Axial-Flow 8250", "Colheitadeira"),
    ("Valtra BH180", "Trator"),
    ("Jacto Uniport 3030", "Pulverizador"),
]


def _norm(x, lo, hi, inverter=False):
    """Normaliza x para [0,1] dentro de [lo,hi]. inverter=True -> menor valor = maior risco."""
    z = np.clip((x - lo) / (hi - lo), 0, 1)
    return 1 - z if inverter else z


def gerar_features(n):
    """Sorteia as variaveis de entrada com distribuicoes plausiveis de campo."""
    df = pd.DataFrame()

    # --- Ambientais -------------------------------------------------------
    df["umidade_solo_pct"] = np.clip(rng.normal(55, 20, n), 5, 100).round(1)
    df["precipitacao_24h_mm"] = np.clip(rng.gamma(2.0, 18, n), 0, 200).round(1)
    df["temperatura_c"] = np.clip(rng.normal(27, 6, n), 5, 45).round(1)
    df["declividade_graus"] = np.clip(rng.gamma(2.2, 5.0, n), 0, 45).round(1)
    df["distancia_corpo_dagua_m"] = np.clip(rng.gamma(2.0, 350, n), 5, 2000).round(0)

    # --- Operacionais / equipamento --------------------------------------
    df["idade_equipamento_anos"] = np.clip(rng.gamma(2.0, 4.0, n), 0, 25).round(0)
    df["horas_desde_manutencao"] = np.clip(rng.gamma(2.0, 90, n), 0, 600).round(0)
    df["horas_operacao_dia"] = np.clip(rng.normal(8, 3, n), 0, 16).round(1)
    df["carga_pct"] = np.clip(rng.normal(80, 18, n), 40, 120).round(0)

    # --- Categoricas ------------------------------------------------------
    df["tipo_solo"] = rng.choice(TIPOS_SOLO, n, p=[0.30, 0.30, 0.28, 0.12])
    df["tipo_operacao"] = rng.choice(TIPOS_OPERACAO, n, p=[0.30, 0.25, 0.30, 0.15])
    df["periodo_dia"] = rng.choice(PERIODOS, n, p=[0.45, 0.40, 0.15])

    return df


def calcular_probabilidade_sinistro(df):
    """
    Constroi o 'logito de risco' como soma ponderada das variaveis normalizadas
    na direcao do risco, aplica ruido e converte em probabilidade.
    Os PESOS refletem a literatura de seguranca agricola (chuva/umidade/declive
    e proximidade de agua sao os principais fatores de atolamento e tombamento).
    """
    # Contribuicoes numericas (cada uma ja em [0,1] na direcao do risco)
    c_umid = _norm(df["umidade_solo_pct"], 0, 100)
    c_chuva = _norm(df["precipitacao_24h_mm"], 0, 200)
    c_decliv = _norm(df["declividade_graus"], 0, 45)
    c_agua = _norm(df["distancia_corpo_dagua_m"], 0, 1500, inverter=True)  # perto = pior
    c_idade = _norm(df["idade_equipamento_anos"], 0, 25)
    c_manut = _norm(df["horas_desde_manutencao"], 0, 600)
    c_horas = _norm(df["horas_operacao_dia"], 0, 16)
    c_carga = _norm(df["carga_pct"], 40, 120)
    # Temperatura: risco leve nos extremos (muito quente cansa, muito frio = solo umido)
    c_temp = _norm(np.abs(df["temperatura_c"] - 27), 0, 18)

    # Contribuicoes categoricas
    mapa_solo = {"Arenoso": 0.05, "Misto": 0.30, "Argiloso": 0.70, "Encharcado": 1.00}
    c_solo = df["tipo_solo"].map(mapa_solo).astype(float)
    mapa_op = {"Plantio": 0.20, "Pulverizacao": 0.35, "Colheita": 0.75, "Transporte": 0.85}
    c_op = df["tipo_operacao"].map(mapa_op).astype(float)
    mapa_per = {"Manha": 0.20, "Tarde": 0.35, "Noite": 0.80}
    c_per = df["periodo_dia"].map(mapa_per).astype(float)

    # Soma ponderada base (efeitos lineares moderados)
    logito = (
        2.0 * c_umid +
        1.8 * c_chuva +
        1.6 * c_decliv +
        1.9 * c_agua +
        1.0 * c_idade +
        1.0 * c_manut +
        0.6 * c_horas +
        0.5 * c_carga +
        0.3 * c_temp +
        1.3 * c_solo +
        1.2 * c_op +
        0.5 * c_per
    )

    # ------------------------------------------------------------------
    # Interacoes / limiares NAO-LINEARES.
    # Sao combinacoes perigosas reais de campo. Modelos de arvore
    # (Random Forest / Gradient Boosting) capturam esses "saltos" de risco;
    # a Regressao Logistica linear nao -> e por isso que o RF vence.
    # ------------------------------------------------------------------
    logito += 3.0 * ((c_solo > 0.6) & (c_chuva > 0.4)).astype(float)   # solo critico + chuva
    logito += 2.5 * ((c_agua > 0.6) & (c_umid > 0.6)).astype(float)    # perto d'agua + solo umido
    logito += 2.2 * ((c_decliv > 0.6) & (c_carga > 0.6)).astype(float) # declive + carga -> tombamento
    logito += 1.8 * ((c_manut > 0.6) & (c_idade > 0.6)).astype(float)  # manutencao atrasada + maquina velha

    # Centraliza para uma taxa-base de sinistro realista (~30%) e adiciona ruido baixo
    logito = logito - 7.4
    logito = logito + rng.normal(0, 0.40, len(df))   # ruido = teto de acuracia realista

    prob = 1 / (1 + np.exp(-logito))
    return prob


def main():
    df = gerar_features(N_LINHAS)
    prob = calcular_probabilidade_sinistro(df)
    df["houve_sinistro"] = (rng.random(N_LINHAS) < prob).astype(int)

    # ---- Cadastro coerente: equipamento, regiao, data/hora --------------
    eq_ids = [f"EQ-{i:03d}" for i in range(1, N_EQUIPAMENTOS + 1)]
    df["equipamento_id"] = rng.choice(eq_ids, N_LINHAS)
    regioes_nome = [r[0] for r in REGIOES]
    df["regiao"] = rng.choice(regioes_nome, N_LINHAS)

    base = pd.Timestamp("2026-05-19 06:00:00")
    minutos = rng.integers(0, DIAS_HISTORICO * 24 * 60, N_LINHAS)
    df["data_hora"] = [base - pd.Timedelta(minutes=int(m)) for m in minutos]
    df = df.sort_values("data_hora").reset_index(drop=True)
    df.insert(0, "leitura_id", range(1, N_LINHAS + 1))

    # Ordena colunas de forma legivel
    colunas = [
        "leitura_id", "data_hora", "equipamento_id", "regiao",
        "umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c",
        "tipo_solo", "declividade_graus", "distancia_corpo_dagua_m",
        "tipo_operacao", "idade_equipamento_anos", "horas_desde_manutencao",
        "horas_operacao_dia", "carga_pct", "periodo_dia",
        "houve_sinistro",
    ]
    df = df[colunas]

    out_base = os.path.join(BASE_DIR, "leituras_agricolas.csv")
    df.to_csv(out_base, index=False)
    print(f"[OK] {out_base}  ({len(df)} linhas)")
    print(f"     Taxa de sinistro: {df['houve_sinistro'].mean():.1%}")

    # ------------------------------------------------------------------
    # Dataset-exemplo curado para o README: 10 cenarios DISTINTOS,
    # cobrindo do risco baixo ao critico (atende ao feedback da Sprint 1).
    # ------------------------------------------------------------------
    exemplos = pd.DataFrame([
        # baixo
        dict(umidade_solo_pct=22, precipitacao_24h_mm=2,  temperatura_c=28, tipo_solo="Arenoso",
             declividade_graus=3,  distancia_corpo_dagua_m=1450, tipo_operacao="Plantio",
             idade_equipamento_anos=2, horas_desde_manutencao=40, horas_operacao_dia=6,
             carga_pct=60, periodo_dia="Manha"),
        dict(umidade_solo_pct=30, precipitacao_24h_mm=0,  temperatura_c=31, tipo_solo="Arenoso",
             declividade_graus=5,  distancia_corpo_dagua_m=1200, tipo_operacao="Pulverizacao",
             idade_equipamento_anos=1, horas_desde_manutencao=20, horas_operacao_dia=5,
             carga_pct=55, periodo_dia="Manha"),
        # medio
        dict(umidade_solo_pct=55, precipitacao_24h_mm=28, temperatura_c=26, tipo_solo="Misto",
             declividade_graus=14, distancia_corpo_dagua_m=620, tipo_operacao="Plantio",
             idade_equipamento_anos=6, horas_desde_manutencao=180, horas_operacao_dia=8,
             carga_pct=78, periodo_dia="Tarde"),
        dict(umidade_solo_pct=64, precipitacao_24h_mm=47, temperatura_c=27, tipo_solo="Misto",
             declividade_graus=22, distancia_corpo_dagua_m=480, tipo_operacao="Pulverizacao",
             idade_equipamento_anos=8, horas_desde_manutencao=240, horas_operacao_dia=9,
             carga_pct=82, periodo_dia="Tarde"),
        dict(umidade_solo_pct=58, precipitacao_24h_mm=33, temperatura_c=24, tipo_solo="Argiloso",
             declividade_graus=18, distancia_corpo_dagua_m=700, tipo_operacao="Colheita",
             idade_equipamento_anos=5, horas_desde_manutencao=150, horas_operacao_dia=10,
             carga_pct=85, periodo_dia="Manha"),
        # alto
        dict(umidade_solo_pct=78, precipitacao_24h_mm=62, temperatura_c=23, tipo_solo="Argiloso",
             declividade_graus=27, distancia_corpo_dagua_m=180, tipo_operacao="Colheita",
             idade_equipamento_anos=11, horas_desde_manutencao=380, horas_operacao_dia=12,
             carga_pct=95, periodo_dia="Tarde"),
        dict(umidade_solo_pct=82, precipitacao_24h_mm=75, temperatura_c=22, tipo_solo="Argiloso",
             declividade_graus=30, distancia_corpo_dagua_m=150, tipo_operacao="Transporte",
             idade_equipamento_anos=12, horas_desde_manutencao=420, horas_operacao_dia=13,
             carga_pct=100, periodo_dia="Noite"),
        # critico
        dict(umidade_solo_pct=91, precipitacao_24h_mm=95, temperatura_c=20, tipo_solo="Encharcado",
             declividade_graus=35, distancia_corpo_dagua_m=60,  tipo_operacao="Colheita",
             idade_equipamento_anos=15, horas_desde_manutencao=520, horas_operacao_dia=14,
             carga_pct=110, periodo_dia="Noite"),
        dict(umidade_solo_pct=95, precipitacao_24h_mm=110,temperatura_c=18, tipo_solo="Encharcado",
             declividade_graus=40, distancia_corpo_dagua_m=40,  tipo_operacao="Transporte",
             idade_equipamento_anos=18, horas_desde_manutencao=560, horas_operacao_dia=15,
             carga_pct=115, periodo_dia="Noite"),
        dict(umidade_solo_pct=88, precipitacao_24h_mm=90, temperatura_c=21, tipo_solo="Encharcado",
             declividade_graus=33, distancia_corpo_dagua_m=80,  tipo_operacao="Colheita",
             idade_equipamento_anos=14, horas_desde_manutencao=480, horas_operacao_dia=14,
             carga_pct=108, periodo_dia="Tarde"),
    ])
    exemplos.insert(0, "id", [f"{i:03d}" for i in range(1, len(exemplos) + 1)])
    out_exemplo = os.path.join(BASE_DIR, "dataset_exemplo.csv")
    exemplos.to_csv(out_exemplo, index=False)
    print(f"[OK] {out_exemplo}    ({len(exemplos)} cenarios curados)")


if __name__ == "__main__":
    main()
