"""
Regras de negocio do SomPrev Risk (configuraveis).

Tudo o que transforma a probabilidade do modelo em DECISAO fica aqui:
  1. probabilidade -> score 0-100 -> faixa (Baixo / Medio / Alto / Critico);
  2. quando gerar alerta preventivo (limiar do modelo + gatilhos explicitos);
  3. o que recomendar ao usuario, por faixa e por fator de risco;
  4. premissas economicas do "prejuizo evitavel".

As regras vivem em `config/regras_risco.json` (User Story "configurar regras de
risco"): o gestor pode ajustar limiares sem mexer no codigo, cada alteracao gera
uma nova versao e cada predicao grava a versao de regra que a produziu.

Por que gatilhos deterministicos ALEM do modelo? O modelo estatistico e o
motor principal, mas regras explicitas ("solo >= 75% a menos de 200 m da agua")
sao interpretaveis por qualquer usuario, cobrem cenarios extremos com pouca
amostra no historico e funcionam como segunda linha de defesa.
"""

from __future__ import annotations

import copy
import json
import operator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import config
from .esquema import ROTULOS
from .excecoes import DadoInvalido
from .logs import obter_logger

log = obter_logger("regras")

CLASSES = ("Baixo", "Medio", "Alto", "Critico")
ROTULO_CLASSE = {"Baixo": "Baixo", "Medio": "Médio", "Alto": "Alto", "Critico": "Crítico"}
EMOJI_CLASSE = {"Baixo": "🟢", "Medio": "🟡", "Alto": "🟠", "Critico": "🔴"}
ORDEM_CLASSE = {c: i for i, c in enumerate(CLASSES)}

# Regras padrao: usadas se o JSON estiver ausente ou corrompido (falha segura -
# o sistema continua operando com os valores validados da Sprint 4).
REGRAS_PADRAO: dict = {
    "versao": "regras-v2.0-padrao",
    "faixas_score": {"Baixo": [0, 14], "Medio": [15, 39], "Alto": [40, 69], "Critico": [70, 100]},
    "alerta_modelo": {"limiar_score": 15},
    "gatilhos": [],
    "economia": {"custo_medio_sinistro_brl": 85000, "taxa_prevencao": 0.45,
                 "custo_parada_preventiva_brl": 4000},
}

RECOMENDACAO_CLASSE = {
    "Baixo": "Operação liberada. Condições dentro do esperado; siga o plano normal.",
    "Medio": "Operação com atenção. Reduza a velocidade, evite as áreas mais úmidas e reavalie se chover.",
    "Alto": "Operação com restrições. Exija supervisão, afaste a rota de áreas alagadas e declives "
            "e considere adiar trechos críticos.",
    "Critico": "Operação NÃO recomendada. Risco elevado de atolamento, tombamento ou dano mecânico. "
               "Suspenda e reavalie após a melhora das condições.",
}

# Acao especifica por fator de risco: transforma "o que explica o risco" em
# "o que fazer a respeito" (recomendacao acionavel e nao generica).
ACAO_POR_FATOR = {
    "umidade_solo_pct": "priorize talhões com solo mais seco",
    "precipitacao_24h_mm": "aguarde a drenagem após a chuva",
    "declividade_graus": "evite trechos inclinados",
    "distancia_corpo_dagua_m": "mantenha distância de rios e represas",
    "idade_equipamento_anos": "prefira um equipamento mais novo para esta tarefa",
    "horas_desde_manutencao": "antecipe a revisão preventiva",
    "horas_operacao_dia": "reduza a jornada ou faça revezamento de operador",
    "carga_pct": "reduza a carga transportada",
    "tipo_solo": "adapte pneus/lastro ao tipo de solo",
    "tipo_operacao": "reforce a supervisão desta operação",
    "periodo_dia": "evite operar no período noturno",
    "temperatura_c": "faça pausas por causa da temperatura extrema",
}

_OPERADORES = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge,
    "==": operator.eq, "in": lambda a, b: a in b,
}


# ---------------------------------------------------------------------------
# Carga e validacao das regras
# ---------------------------------------------------------------------------
def validar_regras(regras: dict) -> None:
    """Valida a estrutura das regras; levanta DadoInvalido se houver erro."""
    faixas = regras.get("faixas_score", {})
    if set(faixas) != set(CLASSES):
        raise DadoInvalido("As faixas devem ser exatamente: " + ", ".join(CLASSES))
    anterior = -1
    for classe in CLASSES:
        lo, hi = faixas[classe]
        if not (0 <= lo <= hi <= 100) or lo != anterior + 1:
            raise DadoInvalido(f"Faixa '{classe}' inválida ou com lacuna: {lo}-{hi}")
        anterior = hi
    if anterior != 100:
        raise DadoInvalido("As faixas devem cobrir o score de 0 a 100.")
    limiar = regras.get("alerta_modelo", {}).get("limiar_score")
    if not isinstance(limiar, (int, float)) or not 0 < limiar <= 100:
        raise DadoInvalido("O limiar de alerta deve estar entre 1 e 100.")
    for g in regras.get("gatilhos", []):
        for c in g.get("condicoes", []):
            if c.get("operador") not in _OPERADORES:
                raise DadoInvalido(f"Operador inválido no gatilho {g.get('codigo')}: {c.get('operador')}")
    eco = regras.get("economia", {})
    if not 0 <= float(eco.get("taxa_prevencao", 0)) <= 1:
        raise DadoInvalido("taxa_prevencao deve estar entre 0 e 1.")


def carregar_regras(caminho: Path | None = None) -> dict:
    """Le as regras do JSON; em caso de falha usa as regras padrao e registra."""
    caminho = caminho or config.REGRAS_PATH
    try:
        with open(caminho, encoding="utf-8") as arq:
            regras = json.load(arq)
        validar_regras(regras)
        return regras
    except FileNotFoundError:
        log.warning("Arquivo de regras ausente; usando regras padrão", extra={"contexto": {"caminho": str(caminho)}})
    except (json.JSONDecodeError, DadoInvalido, KeyError, TypeError, ValueError) as erro:
        log.error("Regras inválidas; usando regras padrão", extra={"contexto": {"erro": str(erro)}})
    return copy.deepcopy(REGRAS_PADRAO)


def salvar_regras(novas: dict, usuario: str, caminho: Path | None = None) -> dict:
    """Valida, incrementa a versao e grava as regras. Devolve as regras salvas."""
    caminho = caminho or config.REGRAS_PATH
    validar_regras(novas)
    atual = carregar_regras(caminho)
    regras = copy.deepcopy(novas)
    prefixo, _, numero = atual.get("versao", "regras-v2.0").rpartition(".")
    try:
        regras["versao"] = f"{prefixo}.{int(numero) + 1}"
    except ValueError:
        regras["versao"] = f"{atual.get('versao', 'regras')}.1"
    regras["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    regras["atualizado_por"] = usuario
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as arq:
        json.dump(regras, arq, indent=2, ensure_ascii=False)
    return regras


# ---------------------------------------------------------------------------
# Score e faixa
# ---------------------------------------------------------------------------
def prob_para_score(prob: float) -> int:
    """Probabilidade (0-1) -> score inteiro 0-100 (mesma informacao, leitura mais simples)."""
    prob = min(max(float(prob), 0.0), 1.0)
    return int(round(prob * 100))


def classificar(score: int, regras: dict | None = None) -> str:
    """Score -> faixa de risco segundo as faixas configuradas."""
    faixas = (regras or carregar_regras())["faixas_score"]
    for classe in CLASSES:
        lo, hi = faixas[classe]
        if lo <= score <= hi:
            return classe
    return "Critico" if score > 100 else "Baixo"


def recomendacao(classe: str, fatores: list[str] | None = None) -> str:
    """Recomendacao por faixa + acoes especificas dos principais fatores."""
    texto = RECOMENDACAO_CLASSE[classe]
    if classe != "Baixo" and fatores:
        acoes = [ACAO_POR_FATOR[f] for f in fatores[:2] if f in ACAO_POR_FATOR]
        if acoes:
            texto += " Ações sugeridas: " + "; ".join(acoes) + "."
    return texto


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------
@dataclass
class Alerta:
    tipo: str               # RISCO_MODELO | CONDICAO_AMBIENTAL | CONDICAO_OPERACIONAL | MANUTENCAO
    codigo: str
    nivel: str              # Medio | Alto | Critico
    perfil_destino: str
    criterio: str           # a regra exata que disparou o alerta (interpretabilidade)
    mensagem: str
    recomendacao: str
    extras: dict = field(default_factory=dict)


def _condicao_ok(leitura: dict, cond: dict) -> bool:
    valor = leitura.get(cond["variavel"])
    if valor is None:
        return False
    try:
        return bool(_OPERADORES[cond["operador"]](valor, cond["valor"]))
    except TypeError:
        return False


def descrever_condicao(cond: dict) -> str:
    valor = cond["valor"]
    valor_txt = "/".join(valor) if isinstance(valor, list) else f"{valor:g}"
    op = {"in": "∈", ">=": "≥", "<=": "≤"}.get(cond["operador"], cond["operador"])
    return f"{ROTULOS.get(cond['variavel'], cond['variavel'])} {op} {valor_txt}"


def avaliar_alertas(leitura: dict, score: int, classe: str, fatores: list[str],
                    regras: dict | None = None) -> list[Alerta]:
    """Aplica o limiar do modelo e os gatilhos explicitos a uma leitura.

    Retorna a lista de alertas (vazia se nada disparou). Cada alerta carrega o
    CRITERIO textual que o originou, para que o usuario final entenda o motivo.
    """
    regras = regras or carregar_regras()
    alertas: list[Alerta] = []

    limiar = regras["alerta_modelo"]["limiar_score"]
    if score >= limiar:
        nivel = classe if classe != "Baixo" else "Medio"
        alertas.append(Alerta(
            tipo="RISCO_MODELO", codigo="SCORE_ACIMA_LIMIAR", nivel=nivel,
            perfil_destino="Operador" if nivel in ("Medio", "Alto") else "Gestor",
            criterio=f"Score {score} ≥ limiar de alerta {limiar} (regras {regras['versao']})",
            mensagem=f"Risco {ROTULO_CLASSE[classe]} previsto pelo modelo (score {score}/100).",
            recomendacao=recomendacao(classe if classe != "Baixo" else "Medio", fatores),
        ))

    for gatilho in regras.get("gatilhos", []):
        condicoes = gatilho.get("condicoes", [])
        if condicoes and all(_condicao_ok(leitura, c) for c in condicoes):
            alertas.append(Alerta(
                tipo=gatilho["tipo"], codigo=gatilho["codigo"], nivel=gatilho["nivel"],
                perfil_destino=gatilho["perfil_destino"],
                criterio=" e ".join(descrever_condicao(c) for c in condicoes),
                mensagem=gatilho["descricao"] + ".",
                recomendacao=gatilho["recomendacao"],
            ))
    return alertas


# ---------------------------------------------------------------------------
# Economia (prejuizo evitavel)
# ---------------------------------------------------------------------------
def estimar_economia(n_alertas_alto_critico: int, regras: dict | None = None) -> float:
    """nº de alertas Alto/Critico x custo medio do sinistro x taxa de prevencao.

    E uma ESTIMATIVA com premissas explicitas e ajustaveis (config/regras_risco.json),
    nao um valor contabil - traduz o risco tecnico em ordem de grandeza financeira.
    """
    eco = (regras or carregar_regras())["economia"]
    return n_alertas_alto_critico * eco["custo_medio_sinistro_brl"] * eco["taxa_prevencao"]
