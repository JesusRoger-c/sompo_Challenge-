"""
Gerador de telemetria simulada - versao 2 (Sprint 4).

O enunciado permite dados simulados. Na Sprint 4 o gerador foi refeito para
eliminar inconsistencias da versao anterior e aproximar o comportamento de uma
frota real:

  * CADASTRO FIXO por equipamento: tipo, modelo, ano de fabricacao e regiao-base
    nao mudam entre leituras (na v1 a idade de uma mesma maquina variava a cada
    leitura - inconsistencia apontada na revisao da Sprint 4).
  * CLIMA COMPARTILHADO por regiao e dia: todas as maquinas de uma regiao no
    mesmo dia veem a mesma chuva; a umidade do solo segue um balanco hidrico
    simples (acumula com a chuva e seca com o tempo).
  * SAZONALIDADE REGIONAL: no Cerrado (MT, GO, BA) as chuvas se concentram em
    marco/abril e quase somem no inverno seco; no Sul (PR, RS) chove o ano todo,
    com mais volume no inverno. Isso gera TENDENCIAS reais de risco por regiao.
  * FRENTES DE CHUVA: eventos de alguns dias com precipitacao intensa.
  * MANUTENCAO COM MEMORIA: as horas desde a ultima manutencao crescem com o uso
    e zeram na revisao; alguns equipamentos tem manutencao negligenciada.
  * OPERACAO COERENTE com o tipo de maquina (pulverizador pulveriza, colheitadeira
    colhe) e com o calendario agricola (colheita do milho safrinha no inverno).

Em seguida, `simular_coleta_bruta` injeta as FALHAS TIPICAS de uma coleta de
campo (pacote reenviado, sensor sem leitura, valor fora da faixa, grafia
diferente, equipamento desconhecido, data corrompida). A etapa de qualidade
(`dados/qualidade.py`) precisa trata-las antes do modelo.

O rotulo `houve_sinistro` segue a mesma logica causal documentada desde a
Sprint 2 (soma ponderada dos fatores + interacoes perigosas + ruido), agora
aplicada a dados coerentes no tempo e no espaco.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import config
from ..esquema import COLUNAS_LEITURA

# ---------------------------------------------------------------------------
# Parametros da simulacao
# ---------------------------------------------------------------------------
N_EQUIPAMENTOS = 40
DATA_INICIO = pd.Timestamp("2026-03-01")
DATA_FIM = pd.Timestamp("2026-08-31")
PROB_OPERAR_NO_DIA = 0.55


@dataclass(frozen=True)
class Regiao:
    nome: str
    estado: str
    bioma: str
    regime: str               # "cerrado" (verao chuvoso / inverno seco) ou "sul"
    solos: tuple[float, float, float]   # prob. Arenoso, Misto, Argiloso
    relevo: float             # escala da declividade tipica (gamma)


REGIOES = (
    Regiao("Sorriso", "MT", "Cerrado", "cerrado", (0.25, 0.40, 0.35), 3.5),
    Regiao("Rio Verde", "GO", "Cerrado", "cerrado", (0.30, 0.40, 0.30), 4.5),
    Regiao("Lucas do Rio Verde", "MT", "Cerrado", "cerrado", (0.25, 0.45, 0.30), 3.5),
    Regiao("Cascavel", "PR", "Mata Atlantica", "sul", (0.10, 0.35, 0.55), 6.5),
    Regiao("Barreiras", "BA", "Cerrado", "cerrado", (0.50, 0.35, 0.15), 3.0),
    Regiao("Não-Me-Toque", "RS", "Pampa", "sul", (0.15, 0.40, 0.45), 6.0),
)

MODELOS_POR_TIPO = {
    "Trator": ("John Deere 6110J", "Case IH Magnum 340", "New Holland T7", "Valtra BH180"),
    "Colheitadeira": ("John Deere S780", "Case IH Axial-Flow 8250", "New Holland CR8.90"),
    "Pulverizador": ("Jacto Uniport 3030", "John Deere M4040"),
}


# ---------------------------------------------------------------------------
# 1. Cadastro da frota
# ---------------------------------------------------------------------------
def gerar_cadastro(rng: np.random.Generator) -> pd.DataFrame:
    """Cadastro fixo de equipamentos (uma linha por maquina)."""
    tipos = rng.choice(list(MODELOS_POR_TIPO), N_EQUIPAMENTOS, p=[0.55, 0.25, 0.20])
    linhas = []
    for i, tipo in enumerate(tipos, start=1):
        idade = float(np.clip(rng.gamma(2.2, 3.6), 0.5, 24))
        fabricacao = DATA_INICIO - pd.Timedelta(days=int(idade * 365.25))
        # 20% da frota tem manutencao negligenciada (intervalo bem maior que o manual).
        negligente = rng.random() < 0.20
        intervalo = int(rng.uniform(620, 820) if negligente else rng.uniform(250, 420))
        linhas.append({
            "equipamento_id": f"EQ-{i:03d}",
            "modelo": str(rng.choice(MODELOS_POR_TIPO[tipo])),
            "tipo": str(tipo),
            "ano_fabricacao": int(fabricacao.year),
            "data_fabricacao": fabricacao.date().isoformat(),
            "regiao_base": REGIOES[int(rng.integers(len(REGIOES)))].nome,
            "intervalo_manutencao_h": intervalo,
            "horas_iniciais": int(rng.uniform(0, intervalo)),
        })
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 2. Clima diario por regiao
# ---------------------------------------------------------------------------
def _chuva_media_diaria(regime: str, dia_do_ano: np.ndarray) -> np.ndarray:
    """Chuva media esperada (mm/dia) conforme o regime climatico e a epoca."""
    if regime == "cerrado":
        # ~9 mm/dia no inicio de marco caindo para ~0,3 mm/dia em julho/agosto.
        return 0.3 + 8.7 / (1 + np.exp((dia_do_ano - 120) / 12))
    # Sul: chuva bem distribuida, um pouco maior no inverno (junho-agosto).
    return 4.0 + 2.2 * np.exp(-((dia_do_ano - 190) / 45) ** 2)


def gerar_clima(rng: np.random.Generator) -> pd.DataFrame:
    """Serie diaria de chuva, umidade do solo e temperatura para cada regiao."""
    dias = pd.date_range(DATA_INICIO, DATA_FIM, freq="D")
    doy = dias.dayofyear.to_numpy()
    tabelas = []
    for reg in REGIOES:
        media = _chuva_media_diaria(reg.regime, doy)
        # Dia chuvoso ~ Bernoulli; volume ~ gamma (poucos dias com muita chuva).
        chove = rng.random(len(dias)) < np.clip(media / 9, 0.05, 0.75)
        chuva = np.where(chove, rng.gamma(1.6, np.maximum(media, 0.5) * 1.9), 0.0)
        # Frentes de chuva: 3 a 5 episodios de 2-4 dias com chuva forte.
        for _ in range(int(rng.integers(3, 6))):
            ini = int(rng.integers(0, len(dias) - 4))
            dur = int(rng.integers(2, 5))
            fator = 1.0 if reg.regime == "sul" or doy[ini] < 140 else 0.35
            chuva[ini:ini + dur] += rng.gamma(3.0, 16.0, dur) * fator
        chuva_24h = np.clip(chuva, 0, 220)

        # Balanco hidrico: o excesso de umidade decai ~10%/dia e sobe com a chuva.
        umidade = np.empty(len(dias))
        u = 70.0 if reg.regime == "cerrado" else 60.0
        base = 22.0 if reg.regime == "cerrado" else 34.0
        for t in range(len(dias)):
            u = base + (u - base) * 0.90 + 0.42 * chuva_24h[t]
            u = min(u, 98.0)
            umidade[t] = u
        # Temperatura: sul esfria no inverno; cerrado fica quente e seco.
        if reg.regime == "sul":
            temp = 24 - 9 * np.exp(-((doy - 195) / 40) ** 2)
        else:
            temp = 28 - 3 * np.exp(-((doy - 180) / 35) ** 2)
        tabelas.append(pd.DataFrame({
            "data": dias.date, "regiao": reg.nome,
            "precipitacao_24h_mm": chuva_24h.round(1),
            "umidade_base": umidade,
            "temperatura_base": temp,
        }))
    return pd.concat(tabelas, ignore_index=True)


# ---------------------------------------------------------------------------
# 3. Leituras de telemetria
# ---------------------------------------------------------------------------
def _operacao(tipo: str, doy: int, rng: np.random.Generator) -> str:
    if tipo == "Pulverizador":
        return "Pulverizacao"
    if tipo == "Colheitadeira":
        return "Colheita" if rng.random() < 0.85 else "Transporte"
    # Trator: plantio concentrado no inicio do periodo (safrinha), transporte o ano todo.
    p_plantio = 0.55 if doy < 110 else 0.20
    return str(rng.choice(["Plantio", "Transporte", "Colheita"],
                          p=[p_plantio, 0.75 - p_plantio, 0.25]))


def gerar_leituras(cadastro: pd.DataFrame, clima: pd.DataFrame,
                   rng: np.random.Generator) -> pd.DataFrame:
    """Percorre o calendario de cada maquina gerando as leituras de operacao."""
    clima_idx = clima.set_index(["data", "regiao"])
    regioes = {r.nome: r for r in REGIOES}
    nomes_regioes = list(regioes)
    dias = pd.date_range(DATA_INICIO, DATA_FIM, freq="D")
    linhas = []

    for eq in cadastro.itertuples(index=False):
        horas_manut = float(eq.horas_iniciais)
        fabricacao = pd.Timestamp(eq.data_fabricacao)
        efeito_operador = rng.normal(0, 0.25)   # habilidade/cuidado (nao observado)
        for dia in dias:
            if rng.random() > PROB_OPERAR_NO_DIA:
                continue
            nome_reg = eq.regiao_base if rng.random() < 0.9 else str(rng.choice(nomes_regioes))
            reg = regioes[nome_reg]
            cli = clima_idx.loc[(dia.date(), nome_reg)]
            n_turnos = 1 if rng.random() < 0.55 else 2
            periodos = rng.choice(["Manha", "Tarde", "Noite"], n_turnos, replace=False,
                                  p=[0.45, 0.40, 0.15])
            for periodo in periodos:
                hora = {"Manha": 6, "Tarde": 13, "Noite": 19}[periodo] + int(rng.integers(0, 5))
                data_hora = dia + pd.Timedelta(hours=hora, minutes=int(rng.integers(0, 60)))
                umidade = float(np.clip(cli.umidade_base + rng.normal(0, 6), 5, 100))
                solo = str(rng.choice(["Arenoso", "Misto", "Argiloso"], p=reg.solos))
                if umidade >= 85 and solo != "Arenoso" and rng.random() < 0.6:
                    solo = "Encharcado"
                horas_dia = float(np.clip(rng.normal(8, 2.5), 1, 16))
                operacao = _operacao(eq.tipo, dia.dayofyear, rng)
                carga = float(np.clip(rng.normal(88 if operacao in ("Colheita", "Transporte") else 72, 14),
                                      40, 120))
                linhas.append({
                    "data_hora": data_hora,
                    "equipamento_id": eq.equipamento_id,
                    "regiao": nome_reg,
                    "umidade_solo_pct": round(umidade, 1),
                    "precipitacao_24h_mm": float(cli.precipitacao_24h_mm),
                    "temperatura_c": round(float(cli.temperatura_base + rng.normal(0, 3.5)), 1),
                    "tipo_solo": solo,
                    "declividade_graus": round(float(np.clip(rng.gamma(2.0, reg.relevo), 0, 45)), 1),
                    "distancia_corpo_dagua_m": float(np.clip(round(rng.gamma(2.0, 380)), 5, 2500)),
                    "tipo_operacao": operacao,
                    "idade_equipamento_anos": round((data_hora - fabricacao).days / 365.25, 1),
                    "horas_desde_manutencao": round(horas_manut),
                    "horas_operacao_dia": round(horas_dia, 1),
                    "carga_pct": round(carga),
                    "periodo_dia": str(periodo),
                    "_efeito_operador": efeito_operador,
                })
                horas_manut += horas_dia / n_turnos
            # Revisao: ao passar do intervalo, a maquina vai para a oficina.
            if horas_manut >= eq.intervalo_manutencao_h and rng.random() < 0.5:
                horas_manut = 0.0
    df = pd.DataFrame(linhas).sort_values(["data_hora", "equipamento_id"]).reset_index(drop=True)
    return df


def _norm(x, lo, hi, inverter=False):
    z = np.clip((np.asarray(x, dtype=float) - lo) / (hi - lo), 0, 1)
    return 1 - z if inverter else z


def calcular_probabilidade_sinistro(df: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Logica causal do sinistro (mesma estrutura documentada desde a Sprint 2)."""
    c_umid = _norm(df["umidade_solo_pct"], 0, 100)
    c_chuva = _norm(df["precipitacao_24h_mm"], 0, 200)
    c_decliv = _norm(df["declividade_graus"], 0, 45)
    c_agua = _norm(df["distancia_corpo_dagua_m"], 0, 1500, inverter=True)
    c_idade = _norm(df["idade_equipamento_anos"], 0, 25)
    c_manut = _norm(df["horas_desde_manutencao"], 0, 600)
    c_horas = _norm(df["horas_operacao_dia"], 0, 16)
    c_carga = _norm(df["carga_pct"], 40, 120)
    c_temp = _norm(np.abs(df["temperatura_c"] - 27), 0, 18)
    c_solo = df["tipo_solo"].map({"Arenoso": 0.05, "Misto": 0.30, "Argiloso": 0.70,
                                  "Encharcado": 1.00}).to_numpy(float)
    c_op = df["tipo_operacao"].map({"Plantio": 0.20, "Pulverizacao": 0.35, "Colheita": 0.75,
                                    "Transporte": 0.85}).to_numpy(float)
    c_per = df["periodo_dia"].map({"Manha": 0.20, "Tarde": 0.35, "Noite": 0.80}).to_numpy(float)

    logito = (2.0 * c_umid + 1.8 * c_chuva + 1.6 * c_decliv + 1.9 * c_agua + 1.0 * c_idade
              + 1.0 * c_manut + 0.6 * c_horas + 0.5 * c_carga + 0.3 * c_temp
              + 1.3 * c_solo + 1.2 * c_op + 0.5 * c_per)
    # Interacoes perigosas de campo (saltos nao lineares de risco).
    logito += 3.0 * ((c_solo > 0.6) & (c_chuva > 0.25))
    logito += 2.5 * ((c_agua > 0.6) & (c_umid > 0.6))
    logito += 2.2 * ((c_decliv > 0.6) & (c_carga > 0.6))
    logito += 1.8 * ((c_manut > 0.6) & (c_idade > 0.5))
    logito += df["_efeito_operador"].to_numpy(float)
    logito = logito - 6.9 + rng.normal(0, 0.40, len(df))
    return 1 / (1 + np.exp(-logito))


def gerar_base(seed: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gera (cadastro, leituras limpas com rotulo). Mesma seed = mesma base."""
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    cadastro = gerar_cadastro(rng)
    clima = gerar_clima(rng)
    leituras = gerar_leituras(cadastro, clima, rng)
    prob = calcular_probabilidade_sinistro(leituras, rng)
    leituras["houve_sinistro"] = (rng.random(len(leituras)) < prob).astype(int)
    leituras = leituras.drop(columns="_efeito_operador")
    leituras.insert(0, "leitura_id", np.arange(1, len(leituras) + 1))
    leituras["data_hora"] = leituras["data_hora"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return cadastro, leituras[COLUNAS_LEITURA]


# ---------------------------------------------------------------------------
# 4. Falhas de coleta (dados "como chegam do campo")
# ---------------------------------------------------------------------------
FALHAS = {
    "pacote_reenviado": 0.012,        # linha duplicada identica (retransmissao)
    "reenvio_novo_id": 0.005,         # mesma leitura com outro leitura_id
    "sensor_sem_leitura": 0.020,      # um sensor numerico vazio
    "multiplos_sensores_vazios": 0.003,
    "valor_fora_da_faixa": 0.010,     # ex.: umidade 140%, chuva negativa, codigo 9999
    "grafia_categoria": 0.020,        # "Manhã", " COLHEITA", "pulverização"
    "categoria_desconhecida": 0.002,
    "equipamento_desconhecido": 0.002,
    "data_corrompida": 0.002,
    "decimal_com_virgula": 0.010,     # "55,3" (padrao brasileiro vindo do coletor)
    "rotulo_ausente": 0.004,          # sinistro ainda nao apurado
}

_GRAFIAS = {
    "periodo_dia": {"Manha": ["Manhã", "manha", "MANHÃ"], "Tarde": ["tarde", " TARDE "],
                    "Noite": ["noite", "NOITE"]},
    "tipo_operacao": {"Colheita": ["COLHEITA", " colheita"], "Pulverizacao": ["Pulverização", "pulverizacao"],
                      "Plantio": ["plantio "], "Transporte": ["TRANSPORTE"]},
    "tipo_solo": {"Misto": [" misto "], "Argiloso": ["ARGILOSO"], "Arenoso": ["arenoso"],
                  "Encharcado": ["encharcado"]},
}


def simular_coleta_bruta(leituras: pd.DataFrame, seed: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Aplica falhas realistas de coleta. Devolve (bruto, contagem de falhas injetadas)."""
    rng = np.random.default_rng((config.SEED if seed is None else seed) + 1)
    bruto = leituras.copy().astype(object)
    n = len(bruto)
    injetadas: dict[str, int] = {}

    def sortear(taxa: float) -> np.ndarray:
        return rng.choice(n, size=max(1, int(n * taxa)), replace=False)

    numericas = ["umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c", "declividade_graus",
                 "distancia_corpo_dagua_m", "horas_desde_manutencao", "horas_operacao_dia", "carga_pct",
                 "idade_equipamento_anos"]

    idx = sortear(FALHAS["sensor_sem_leitura"])
    for i in idx:
        bruto.at[i, str(rng.choice(numericas))] = np.nan
    injetadas["sensor_sem_leitura"] = len(idx)

    idx = sortear(FALHAS["multiplos_sensores_vazios"])
    for i in idx:
        for col in rng.choice(["declividade_graus", "distancia_corpo_dagua_m", "umidade_solo_pct"], 2, replace=False):
            bruto.at[i, str(col)] = np.nan
    injetadas["multiplos_sensores_vazios"] = len(idx)

    idx = sortear(FALHAS["valor_fora_da_faixa"])
    for i in idx:
        col, valor = [("umidade_solo_pct", 140.0), ("precipitacao_24h_mm", -3.0),
                      ("carga_pct", 9999.0), ("temperatura_c", -99.0),
                      ("horas_operacao_dia", 31.0)][int(rng.integers(5))]
        bruto.at[i, col] = valor
    injetadas["valor_fora_da_faixa"] = len(idx)

    idx = sortear(FALHAS["grafia_categoria"])
    for i in idx:
        campo = str(rng.choice(list(_GRAFIAS)))
        atual = bruto.at[i, campo]
        opcoes = _GRAFIAS[campo].get(atual)
        if opcoes:
            bruto.at[i, campo] = str(rng.choice(opcoes))
    injetadas["grafia_categoria"] = len(idx)

    idx = sortear(FALHAS["categoria_desconhecida"])
    for i in idx:
        bruto.at[i, "tipo_solo"] = "Pedregoso"
    injetadas["categoria_desconhecida"] = len(idx)

    idx = sortear(FALHAS["equipamento_desconhecido"])
    for i in idx:
        bruto.at[i, "equipamento_id"] = "EQ-999"
    injetadas["equipamento_desconhecido"] = len(idx)

    idx = sortear(FALHAS["data_corrompida"])
    for i in idx:
        bruto.at[i, "data_hora"] = str(rng.choice(["2026-13-45 99:00:00", "", "ontem"]))
    injetadas["data_corrompida"] = len(idx)

    idx = sortear(FALHAS["decimal_com_virgula"])
    for i in idx:
        valor = bruto.at[i, "umidade_solo_pct"]
        if isinstance(valor, float) and not np.isnan(valor):
            bruto.at[i, "umidade_solo_pct"] = f"{valor:.1f}".replace(".", ",")
    injetadas["decimal_com_virgula"] = len(idx)

    idx = sortear(FALHAS["rotulo_ausente"])
    for i in idx:
        bruto.at[i, "houve_sinistro"] = np.nan
    injetadas["rotulo_ausente"] = len(idx)

    # Duplicidades por ultimo (duplicam linhas ja com eventuais defeitos).
    idx = sortear(FALHAS["pacote_reenviado"])
    duplicadas = bruto.iloc[idx].copy()
    injetadas["pacote_reenviado"] = len(idx)
    idx = sortear(FALHAS["reenvio_novo_id"])
    reenvios = bruto.iloc[idx].copy()
    reenvios["leitura_id"] = np.arange(n + 1, n + 1 + len(reenvios))
    injetadas["reenvio_novo_id"] = len(idx)

    bruto = pd.concat([bruto, duplicadas, reenvios], ignore_index=True)
    bruto = bruto.sample(frac=1.0, random_state=int(rng.integers(1_000_000))).reset_index(drop=True)
    return bruto, injetadas


def cenarios_exemplo() -> pd.DataFrame:
    """10 cenarios curados (do risco baixo ao critico) usados no README e nos testes."""
    base = dict(equipamento_id="EQ-001", regiao_id=1)
    cen = [
        dict(umidade_solo_pct=22, precipitacao_24h_mm=2, temperatura_c=28, tipo_solo="Arenoso", declividade_graus=3,
             distancia_corpo_dagua_m=1450, tipo_operacao="Plantio", idade_equipamento_anos=2,
             horas_desde_manutencao=40, horas_operacao_dia=6, carga_pct=60, periodo_dia="Manha"),
        dict(umidade_solo_pct=30, precipitacao_24h_mm=0, temperatura_c=31, tipo_solo="Arenoso", declividade_graus=5,
             distancia_corpo_dagua_m=1200, tipo_operacao="Pulverizacao", idade_equipamento_anos=1,
             horas_desde_manutencao=20, horas_operacao_dia=5, carga_pct=55, periodo_dia="Manha"),
        dict(umidade_solo_pct=55, precipitacao_24h_mm=28, temperatura_c=26, tipo_solo="Misto", declividade_graus=14,
             distancia_corpo_dagua_m=620, tipo_operacao="Plantio", idade_equipamento_anos=6,
             horas_desde_manutencao=180, horas_operacao_dia=8, carga_pct=78, periodo_dia="Tarde"),
        dict(umidade_solo_pct=64, precipitacao_24h_mm=47, temperatura_c=27, tipo_solo="Misto", declividade_graus=22,
             distancia_corpo_dagua_m=480, tipo_operacao="Pulverizacao", idade_equipamento_anos=8,
             horas_desde_manutencao=240, horas_operacao_dia=9, carga_pct=82, periodo_dia="Tarde"),
        dict(umidade_solo_pct=58, precipitacao_24h_mm=33, temperatura_c=24, tipo_solo="Argiloso", declividade_graus=18,
             distancia_corpo_dagua_m=700, tipo_operacao="Colheita", idade_equipamento_anos=5,
             horas_desde_manutencao=150, horas_operacao_dia=10, carga_pct=85, periodo_dia="Manha"),
        dict(umidade_solo_pct=78, precipitacao_24h_mm=62, temperatura_c=23, tipo_solo="Argiloso", declividade_graus=27,
             distancia_corpo_dagua_m=180, tipo_operacao="Colheita", idade_equipamento_anos=11,
             horas_desde_manutencao=380, horas_operacao_dia=12, carga_pct=95, periodo_dia="Tarde"),
        dict(umidade_solo_pct=82, precipitacao_24h_mm=75, temperatura_c=22, tipo_solo="Argiloso", declividade_graus=30,
             distancia_corpo_dagua_m=150, tipo_operacao="Transporte", idade_equipamento_anos=12,
             horas_desde_manutencao=420, horas_operacao_dia=13, carga_pct=100, periodo_dia="Noite"),
        dict(umidade_solo_pct=91, precipitacao_24h_mm=95, temperatura_c=20, tipo_solo="Encharcado", declividade_graus=35,
             distancia_corpo_dagua_m=60, tipo_operacao="Colheita", idade_equipamento_anos=15,
             horas_desde_manutencao=520, horas_operacao_dia=14, carga_pct=110, periodo_dia="Noite"),
        dict(umidade_solo_pct=95, precipitacao_24h_mm=110, temperatura_c=18, tipo_solo="Encharcado",
             declividade_graus=40, distancia_corpo_dagua_m=40, tipo_operacao="Transporte", idade_equipamento_anos=18,
             horas_desde_manutencao=560, horas_operacao_dia=15, carga_pct=115, periodo_dia="Noite"),
        dict(umidade_solo_pct=88, precipitacao_24h_mm=90, temperatura_c=21, tipo_solo="Encharcado",
             declividade_graus=33, distancia_corpo_dagua_m=80, tipo_operacao="Colheita", idade_equipamento_anos=14,
             horas_desde_manutencao=480, horas_operacao_dia=14, carga_pct=108, periodo_dia="Tarde"),
    ]
    df = pd.DataFrame([{**base, **c} for c in cen])
    df.insert(0, "cenario", [f"{i:03d}" for i in range(1, len(df) + 1)])
    df["faixa_esperada"] = ["Baixo", "Baixo", "Medio", "Medio", "Medio", "Alto", "Alto",
                            "Critico", "Critico", "Critico"]
    return df
