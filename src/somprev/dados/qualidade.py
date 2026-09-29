"""
Qualidade de dados: validacao, limpeza e imputacao da telemetria.

Nenhuma leitura chega ao modelo sem passar por aqui. As regras seguem o
contrato de `esquema.py` e sao aplicadas em DOIS modos com a mesma logica:

  * tratar_lote(...)      -> base historica inteira (pipeline de treino/carga);
  * tratar_registro(...)  -> uma leitura por vez (API em tempo real).

Politica de tratamento (da mais barata para a mais conservadora):

  1. Duplicidade .......... pacote reenviado (linha identica), leitura_id repetido
                             ou mesma maquina no mesmo instante -> mantem a primeira.
  2. Referencia invalida .. equipamento fora do cadastro ou data ilegivel -> quarentena.
  3. Formato .............. "55,3" -> 55.3 ; "Manhã" / " COLHEITA " -> valor canonico.
  4. Fora da faixa fisica . valor impossivel (umidade 140%, carga 9999) vira AUSENTE:
                             e defeito de sensor, nao um dado extremo verdadeiro.
  5. Ausente imputavel .... - idade: recalculada pelo cadastro (fonte mestre);
                             - clima (umidade/chuva/temperatura): mediana da mesma
                               regiao no mesmo dia (o clima e compartilhado);
                             - uso da maquina: ultimo valor conhecido do equipamento;
                             - periodo do dia: derivado do horario da leitura.
  6. Ausente critico ...... declividade, distancia da agua, tipo de solo ou de
                             operacao sem valor -> QUARENTENA (sem eles o score nao
                             seria confiavel; melhor nao pontuar do que pontuar errado).

Toda correcao fica registrada na propria leitura (colunas `qualidade_status` e
`qualidade_obs`) e no relatorio de qualidade - rastreabilidade de ponta a ponta.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd

from ..esquema import (ALVO, CATEGORIAS, CATEGORIAS_CRITICAS, FEATURES, FEATURES_NUM,
                       VARIAVEIS_NUMERICAS, VARIAVEL, normalizar_categoria)
from ..excecoes import DadoInvalido

VARS_CLIMA = ["umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c"]
VARS_USO = ["horas_desde_manutencao", "horas_operacao_dia", "carga_pct"]
NAO_IMPUTAVEIS = ["declividade_graus", "distancia_corpo_dagua_m"] + list(CATEGORIAS_CRITICAS)
TOLERANCIA_IDADE_ANOS = 1.0


# ---------------------------------------------------------------------------
# Primitivas compartilhadas (lote e registro unico)
# ---------------------------------------------------------------------------
def converter_numero(valor) -> float | None:
    """Converte texto/numero para float; aceita decimal com virgula. None se invalido."""
    if valor is None:
        return None
    if isinstance(valor, (int, float, np.integer, np.floating)):
        return None if pd.isna(valor) else float(valor)
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def dentro_da_faixa(variavel: str, valor: float | None) -> bool:
    v = VARIAVEL[variavel]
    return valor is not None and v.minimo <= valor <= v.maximo


def converter_data(valor) -> datetime | None:
    try:
        ts = pd.to_datetime(valor, errors="coerce", format="%Y-%m-%d %H:%M:%S")
        if pd.isna(ts):
            ts = pd.to_datetime(valor, errors="coerce")
        return None if pd.isna(ts) else ts.to_pydatetime()
    except (ValueError, TypeError):
        return None


def periodo_por_hora(hora: int) -> str:
    if 5 <= hora < 12:
        return "Manha"
    if 12 <= hora < 18:
        return "Tarde"
    return "Noite"


def idade_pelo_cadastro(data_fabricacao: str, data_hora: datetime) -> float:
    return round((pd.Timestamp(data_hora) - pd.Timestamp(data_fabricacao)).days / 365.25, 1)


# ---------------------------------------------------------------------------
# Modo LOTE
# ---------------------------------------------------------------------------
@dataclass
class ResultadoLote:
    tratado: pd.DataFrame
    quarentena: pd.DataFrame
    relatorio: dict = field(default_factory=dict)


def tratar_lote(bruto: pd.DataFrame, cadastro: pd.DataFrame) -> ResultadoLote:
    """Aplica a politica de qualidade a uma base inteira de telemetria."""
    df = bruto.copy()
    rel: dict = {"recebidas": int(len(df)), "duplicidades": {}, "correcoes": Counter(),
                 "fora_da_faixa": Counter(), "imputacoes": Counter(), "quarentena": Counter()}
    obs: dict[int, list[str]] = {}

    def anotar(indices, texto):
        for i in indices:
            obs.setdefault(i, []).append(texto)

    # 1. Duplicidades ------------------------------------------------------
    antes = len(df)
    df = df.drop_duplicates()
    rel["duplicidades"]["pacote_reenviado_identico"] = antes - len(df)
    antes = len(df)
    df = df.drop_duplicates(subset="leitura_id", keep="first")
    rel["duplicidades"]["leitura_id_repetido"] = antes - len(df)
    # Reenvio com outro id: mesma maquina no mesmo instante (so para datas validas -
    # duas datas corrompidas iguais nao sao "a mesma leitura", vao para a quarentena).
    antes = len(df)
    df = df.sort_values("leitura_id")
    data_valida = pd.to_datetime(df["data_hora"], errors="coerce", format="%Y-%m-%d %H:%M:%S").notna()
    repetida = df.duplicated(subset=["equipamento_id", "data_hora"], keep="first") & data_valida
    df = df[~repetida]
    rel["duplicidades"]["mesma_maquina_mesmo_instante"] = antes - len(df)
    df = df.reset_index(drop=True)

    quarentena_motivo: dict[int, list[str]] = {}

    def quarentenar(indices, motivo):
        for i in indices:
            quarentena_motivo.setdefault(i, []).append(motivo)
        rel["quarentena"][motivo] += len(indices)

    # 2. Referencias: data e equipamento ------------------------------------
    datas = pd.to_datetime(df["data_hora"], errors="coerce", format="%Y-%m-%d %H:%M:%S")
    quarentenar(df.index[datas.isna()].tolist(), "data_hora inválida")
    df["data_hora_dt"] = datas
    cad = cadastro.set_index("equipamento_id")
    desconhecido = ~df["equipamento_id"].isin(cad.index)
    quarentenar(df.index[desconhecido].tolist(), "equipamento fora do cadastro")

    # 3. Formato: numeros e categorias --------------------------------------
    for col in FEATURES_NUM:
        original = df[col]
        eh_texto = original.map(lambda v: isinstance(v, str))
        if eh_texto.any():
            rel["correcoes"][f"{col}: decimal com vírgula"] += int(eh_texto.sum())
            anotar(df.index[eh_texto], f"{col} convertido de texto")
        df[col] = original.map(converter_numero).astype(float)
    for col in CATEGORIAS:
        original = df[col]
        normal = original.map(lambda v, c=col: normalizar_categoria(c, v))
        mudou = normal.notna() & (normal != original)
        if mudou.any():
            rel["correcoes"][f"{col}: grafia padronizada"] += int(mudou.sum())
            anotar(df.index[mudou], f"{col} padronizado")
        desconhecida = normal.isna() & original.notna() & (original.astype(str).str.strip() != "")
        if desconhecida.any():
            rel["correcoes"][f"{col}: categoria desconhecida"] += int(desconhecida.sum())
            anotar(df.index[desconhecida], f"{col} desconhecido ({original[desconhecida].iloc[0]})")
        df[col] = normal

    # 4. Faixa fisica ------------------------------------------------------
    for v in VARIAVEIS_NUMERICAS:
        fora = df[v.nome].notna() & ~df[v.nome].between(v.minimo, v.maximo)
        if fora.any():
            rel["fora_da_faixa"][v.nome] += int(fora.sum())
            anotar(df.index[fora], f"{v.nome} fora da faixa física")
            df.loc[fora, v.nome] = np.nan

    # 5. Imputacao ---------------------------------------------------------
    valido = ~df.index.isin(list(quarentena_motivo))
    # 5a. idade pelo cadastro (fonte mestre) - tambem corrige divergencias.
    fab = pd.to_datetime(df["equipamento_id"].map(cad["data_fabricacao"]), errors="coerce")
    idade_cad = ((df["data_hora_dt"] - fab).dt.days / 365.25).round(1)
    ausente = df["idade_equipamento_anos"].isna() & idade_cad.notna()
    divergente = (df["idade_equipamento_anos"] - idade_cad).abs() > TOLERANCIA_IDADE_ANOS
    rel["imputacoes"]["idade_equipamento_anos (cadastro)"] += int(ausente.sum())
    rel["correcoes"]["idade divergente do cadastro"] += int(divergente.sum())
    anotar(df.index[ausente], "idade imputada pelo cadastro")
    anotar(df.index[divergente], "idade corrigida pelo cadastro")
    df.loc[ausente | divergente, "idade_equipamento_anos"] = idade_cad[ausente | divergente]

    # 5b. clima: mediana da regiao no mesmo dia.
    df["_dia"] = df["data_hora_dt"].dt.date
    for col in VARS_CLIMA:
        ref = df[col].where(valido).groupby([df["regiao"], df["_dia"]]).transform("median")
        ausente = df[col].isna() & ref.notna()
        rel["imputacoes"][f"{col} (mediana região/dia)"] += int(ausente.sum())
        anotar(df.index[ausente], f"{col} imputado pela mediana da região no dia")
        df.loc[ausente, col] = ref[ausente]

    # 5c. uso da maquina: ultimo valor conhecido do proprio equipamento.
    df = df.sort_values(["equipamento_id", "data_hora_dt"])
    for col in VARS_USO:
        ref = df.groupby("equipamento_id")[col].transform(lambda s: s.ffill().bfill())
        ausente = df[col].isna() & ref.notna()
        rel["imputacoes"][f"{col} (último valor do equipamento)"] += int(ausente.sum())
        anotar(df.index[ausente], f"{col} imputado pelo histórico do equipamento")
        df.loc[ausente, col] = ref[ausente]
    df = df.sort_index()

    # 5d. periodo do dia pelo horario.
    ausente = df["periodo_dia"].isna() & df["data_hora_dt"].notna()
    rel["imputacoes"]["periodo_dia (horário)"] += int(ausente.sum())
    anotar(df.index[ausente], "periodo_dia derivado do horário")
    df.loc[ausente, "periodo_dia"] = df.loc[ausente, "data_hora_dt"].dt.hour.map(periodo_por_hora)

    # 6. Criticos ainda ausentes -> quarentena ------------------------------
    for col in FEATURES:
        faltando = df.index[df[col].isna()].difference(list(quarentena_motivo)).tolist()
        if faltando:
            quarentenar(faltando, f"{col} ausente (não imputável)")

    # Rotulo ausente: leitura valida para pontuar, mas fora do treino.
    df[ALVO] = pd.to_numeric(df[ALVO], errors="coerce")
    rel["rotulo_ausente"] = int(df[ALVO].isna().sum())

    # Montagem das saidas ----------------------------------------------------
    df["qualidade_obs"] = [("; ".join(obs.get(i, [])) or None) for i in df.index]
    df["qualidade_status"] = np.where(df["qualidade_obs"].isna(), "OK", "CORRIGIDO")
    em_quarentena = df.index.isin(list(quarentena_motivo))
    quarentena = bruto.iloc[0:0].copy()
    if em_quarentena.any():
        quarentena = df.loc[em_quarentena].copy()
        quarentena["motivo"] = [" | ".join(quarentena_motivo[i]) for i in quarentena.index]
    tratado = df.loc[~em_quarentena].copy()
    tratado["data_hora"] = tratado["data_hora_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    tratado = tratado.drop(columns=["data_hora_dt", "_dia"]).sort_values("data_hora").reset_index(drop=True)
    tratado["leitura_id"] = tratado["leitura_id"].astype(int)
    if not quarentena.empty:
        quarentena = quarentena.drop(columns=["data_hora_dt", "_dia"], errors="ignore")

    rel["quarentena_total"] = int(len(quarentena))
    rel["aceitas"] = int(len(tratado))
    rel["aceitas_com_correcao"] = int((tratado["qualidade_status"] == "CORRIGIDO").sum())
    rel["taxa_aproveitamento"] = round(len(tratado) / max(rel["recebidas"], 1), 4)
    rel["valores_ausentes_apos_tratamento"] = int(tratado[FEATURES].isna().sum().sum())
    for chave in ("correcoes", "fora_da_faixa", "imputacoes", "quarentena"):
        rel[chave] = {k: int(v) for k, v in rel[chave].items() if v}
    return ResultadoLote(tratado=tratado, quarentena=quarentena, relatorio=rel)


# ---------------------------------------------------------------------------
# Modo REGISTRO UNICO (API)
# ---------------------------------------------------------------------------
Referencia = Callable[[str, dict], "float | str | None"]


@dataclass
class ResultadoRegistro:
    leitura: dict
    avisos: list[str]

    @property
    def status(self) -> str:
        return "CORRIGIDO" if self.avisos else "OK"


def tratar_registro(entrada: dict, cadastro_equip: dict | None,
                    referencia: Referencia | None = None) -> ResultadoRegistro:
    """Valida e trata UMA leitura com a mesma politica do modo lote.

    `cadastro_equip` e a linha do equipamento (ou None se nao existir).
    `referencia(variavel, leitura)` devolve um valor de referencia para imputar
    (mediana da regiao no dia ou ultimo valor do equipamento, vindo do banco).
    Levanta DadoInvalido com a lista de problemas quando nao ha como pontuar.
    """
    erros: list[str] = []
    avisos: list[str] = []
    leitura = dict(entrada)

    dt = converter_data(leitura.get("data_hora"))
    if dt is None:
        erros.append("data_hora ausente ou em formato inválido (use AAAA-MM-DD HH:MM:SS)")
    if cadastro_equip is None:
        erros.append(f"equipamento '{leitura.get('equipamento_id')}' não está no cadastro")
    if erros:
        raise DadoInvalido("Leitura rejeitada", {"erros": erros})
    leitura["data_hora"] = dt.strftime("%Y-%m-%d %H:%M:%S")

    for v in VARIAVEIS_NUMERICAS:
        bruto = leitura.get(v.nome)
        valor = converter_numero(bruto)
        if isinstance(bruto, str) and valor is not None:
            avisos.append(f"{v.nome} convertido de texto ('{bruto}')")
        if valor is not None and not dentro_da_faixa(v.nome, valor):
            avisos.append(f"{v.nome}={valor:g} fora da faixa física {v.minimo:g}-{v.maximo:g} (tratado como ausente)")
            valor = None
        leitura[v.nome] = valor

    for campo in CATEGORIAS:
        bruto = leitura.get(campo)
        valor = normalizar_categoria(campo, bruto)
        if valor is not None and valor != bruto:
            avisos.append(f"{campo} padronizado ('{bruto}' → '{valor}')")
        elif valor is None and bruto not in (None, ""):
            avisos.append(f"{campo} desconhecido ('{bruto}')")
        leitura[campo] = valor

    # Idade: sempre coerente com o cadastro (fonte mestre).
    idade_cad = idade_pelo_cadastro(cadastro_equip["data_fabricacao"], dt)
    idade = leitura.get("idade_equipamento_anos")
    if idade is None:
        avisos.append("idade_equipamento_anos imputada pelo cadastro")
        leitura["idade_equipamento_anos"] = idade_cad
    elif abs(idade - idade_cad) > TOLERANCIA_IDADE_ANOS:
        avisos.append(f"idade_equipamento_anos corrigida pelo cadastro ({idade:g} → {idade_cad:g})")
        leitura["idade_equipamento_anos"] = idade_cad

    if leitura.get("periodo_dia") is None:
        leitura["periodo_dia"] = periodo_por_hora(dt.hour)
        avisos.append("periodo_dia derivado do horário")

    for col in VARS_CLIMA + VARS_USO:
        if leitura.get(col) is None and referencia is not None:
            ref = referencia(col, leitura)
            if ref is not None:
                leitura[col] = float(ref)
                origem = "mediana da região no dia" if col in VARS_CLIMA else "histórico do equipamento"
                avisos.append(f"{col} imputado ({origem})")

    faltando = [c for c in FEATURES if leitura.get(c) is None]
    if faltando:
        raise DadoInvalido("Leitura sem dados suficientes para um score confiável",
                           {"erros": [f"{c} ausente e não imputável" for c in faltando], "avisos": avisos})
    return ResultadoRegistro(leitura=leitura, avisos=avisos)
