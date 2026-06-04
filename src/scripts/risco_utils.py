"""
=============================================================================
 AgroSentinela  |  Modulo compartilhado de regras de risco
=============================================================================
Centraliza tudo que treino, banco e dashboard precisam compartilhar:
  - listas de variaveis (features) numericas e categoricas;
  - conversao probabilidade -> score 0-100 -> faixa de risco;
  - texto de recomendacao por faixa (experiencia do usuario);
  - explicabilidade: top fatores que mais elevaram o risco de uma leitura.

Manter isso num so lugar evita divergencia de regra entre os modulos.
"""

# Variaveis de entrada do modelo (alinhadas ao gerador de dataset)
FEATURES_NUM = [
    "umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c",
    "declividade_graus", "distancia_corpo_dagua_m",
    "idade_equipamento_anos", "horas_desde_manutencao",
    "horas_operacao_dia", "carga_pct",
]
FEATURES_CAT = ["tipo_solo", "tipo_operacao", "periodo_dia"]
FEATURES = FEATURES_NUM + FEATURES_CAT
ALVO = "houve_sinistro"

# Nomes amigaveis para mostrar ao usuario (explicabilidade)
ROTULOS = {
    "umidade_solo_pct": "Umidade do solo",
    "precipitacao_24h_mm": "Chuva nas ultimas 24h",
    "temperatura_c": "Temperatura",
    "declividade_graus": "Declividade do terreno",
    "distancia_corpo_dagua_m": "Proximidade de corpo d'agua",
    "idade_equipamento_anos": "Idade do equipamento",
    "horas_desde_manutencao": "Horas desde a ultima manutencao",
    "horas_operacao_dia": "Horas de operacao no dia",
    "carga_pct": "Carga do equipamento",
    "tipo_solo": "Tipo de solo",
    "tipo_operacao": "Tipo de operacao",
    "periodo_dia": "Periodo do dia",
}


def prob_para_score(prob):
    """Probabilidade de sinistro (0-1) -> score de risco inteiro de 0 a 100."""
    return int(round(float(prob) * 100))


def classificar_risco(score):
    """
    Converte o score em faixa de risco. Sistema de 4 niveis, alinhado ao
    exemplo do enunciado (distancia da agua: 500/200/50 m -> baixo a critico).
    Retorna (classe, emoji, cor_hex).
    """
    if score <= 25:
        return "Baixo", "🟢", "#1B9E4B"
    elif score <= 50:
        return "Medio", "🟡", "#E8B800"
    elif score <= 75:
        return "Alto", "🟠", "#E8761B"
    else:
        return "Critico", "🔴", "#D62828"


def recomendacao(classe):
    """Texto de acao recomendada por faixa - foco na experiencia do usuario."""
    return {
        "Baixo":  "Operacao liberada. Condicoes dentro do esperado; siga o plano normal.",
        "Medio":  "Operacao com atencao. Reduza a velocidade, evite as areas mais umidas "
                  "e reavalie se chover.",
        "Alto":   "Operacao com restricoes. Exija supervisao, replaneje a rota para longe "
                  "de areas alagadas/declives e considere adiar trechos criticos.",
        "Critico":"Operacao NAO recomendada. Risco elevado de atolamento, tombamento ou "
                  "dano mecanico. Suspenda e reavalie apos a melhora das condicoes.",
    }[classe]


def top_fatores(linha, n=3):
    """
    Explicabilidade simples e transparente (atende a User Story 'entender causas').
    Calcula, para UMA leitura, o quanto cada variavel se aproxima do pior caso e
    devolve os n fatores que mais puxaram o risco para cima, em linguagem humana.

    'linha' = dict/Series com as features.
    """
    def n_(v, lo, hi, inv=False):
        z = max(0.0, min(1.0, (float(v) - lo) / (hi - lo)))
        return (1 - z) if inv else z

    contrib = {
        "umidade_solo_pct":        1.8 * n_(linha["umidade_solo_pct"], 0, 100),
        "precipitacao_24h_mm":     1.6 * n_(linha["precipitacao_24h_mm"], 0, 200),
        "declividade_graus":       1.5 * n_(linha["declividade_graus"], 0, 45),
        "distancia_corpo_dagua_m": 1.7 * n_(linha["distancia_corpo_dagua_m"], 0, 1500, inv=True),
        "idade_equipamento_anos":  0.9 * n_(linha["idade_equipamento_anos"], 0, 25),
        "horas_desde_manutencao":  0.9 * n_(linha["horas_desde_manutencao"], 0, 600),
        "horas_operacao_dia":      0.6 * n_(linha["horas_operacao_dia"], 0, 16),
        "carga_pct":               0.5 * n_(linha["carga_pct"], 40, 120),
    }
    mapa_solo = {"Arenoso": 0.05, "Misto": 0.30, "Argiloso": 0.70, "Encharcado": 1.00}
    mapa_op = {"Plantio": 0.20, "Pulverizacao": 0.35, "Colheita": 0.75, "Transporte": 0.85}
    contrib["tipo_solo"] = 1.2 * mapa_solo.get(linha["tipo_solo"], 0.3)
    contrib["tipo_operacao"] = 1.1 * mapa_op.get(linha["tipo_operacao"], 0.3)

    ordenado = sorted(contrib.items(), key=lambda kv: kv[1], reverse=True)
    return [ROTULOS[k] for k, _ in ordenado[:n]]
