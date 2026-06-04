"""
=============================================================================
 SomPrev Risk  |  Modulo compartilhado de regras de risco
=============================================================================
Centraliza tudo que treino, banco e dashboard precisam compartilhar:
  - listas de variaveis (features) numericas e categoricas;
  - conversao probabilidade -> score 0-100 -> faixa de risco;
  - texto de recomendacao por faixa (experiencia do usuario);
  - explicabilidade: top fatores que mais elevaram o risco de uma leitura.

Manter isso num so lugar evita divergencia de regra entre os modulos: treino,
banco e dashboard usam exatamente a mesma definicao de faixa e de recomendacao.
"""

# As cores das faixas vivem no tema central (tema.py), nao aqui: assim a
# identidade visual tem uma unica fonte de verdade em todo o projeto.
import tema

# Variaveis de entrada do modelo (alinhadas ao gerador de dataset).
# Separamos numericas de categoricas DE PROPOSITO: no treino cada grupo recebe
# um tratamento diferente (padronizacao nas numericas, One-Hot nas categoricas).
FEATURES_NUM = [
    "umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c",
    "declividade_graus", "distancia_corpo_dagua_m",
    "idade_equipamento_anos", "horas_desde_manutencao",
    "horas_operacao_dia", "carga_pct",
]
FEATURES_CAT = ["tipo_solo", "tipo_operacao", "periodo_dia"]
FEATURES = FEATURES_NUM + FEATURES_CAT
ALVO = "houve_sinistro"

# Nomes amigaveis para mostrar ao usuario (explicabilidade).
# Traduzir o nome tecnico da coluna para linguagem humana e o que permite o
# dashboard dizer "Umidade do solo" em vez de "umidade_solo_pct".
ROTULOS = {
    "umidade_solo_pct": "Umidade do solo",
    "precipitacao_24h_mm": "Chuva nas ultimas 24h",
    "temperatura_c": "Temperatura",
    "declividade_graus": "Declividade do terreno",
    "distancia_corpo_dagua_m": "Distância da água",
    "idade_equipamento_anos": "Idade do equipamento",
    "horas_desde_manutencao": "Horas desde a ultima manutencao",
    "horas_operacao_dia": "Horas de operacao no dia",
    "carga_pct": "Carga do equipamento",
    "tipo_solo": "Tipo de solo",
    "tipo_operacao": "Tipo de operacao",
    "periodo_dia": "Periodo do dia",
}


def prob_para_score(prob):
    """Probabilidade de sinistro (0-1) -> score de risco inteiro de 0 a 100.

    Por que converter a probabilidade em um numero de 0 a 100? Porque "score"
    e uma linguagem que o operador e o gestor entendem sem precisar saber o que
    e probabilidade. A informacao e a mesma; muda so a apresentacao.
    """
    return int(round(float(prob) * 100))


# Emojis do semaforo por faixa (a COR vem do tema central, nao e duplicada aqui).
_EMOJI = {"Baixo": "🟢", "Medio": "🟡", "Alto": "🟠", "Critico": "🔴"}


def classificar_risco(score):
    """
    Converte o score em faixa de risco. Retorna (classe, emoji, cor_hex).

    Por que 4 faixas (e nao 2 ou 3)? Duas faixas (liberado/bloqueado) jogam
    fora nuance: o campo precisa do meio-termo "pode operar, mas com cautela".
    Quatro niveis dao acao pratica distinta em cada um (liberar / atencao /
    restringir / suspender) sem virar uma escala dificil de interpretar. Os
    cortes em 25/50/75 dividem o score 0-100 em quartos iguais e estao alinhados
    ao exemplo do enunciado (distancia da agua 500/200/50 m -> baixo a critico).
    """
    if score <= 25:
        classe = "Baixo"
    elif score <= 50:
        classe = "Medio"
    elif score <= 75:
        classe = "Alto"
    else:
        classe = "Critico"
    # A cor sai do tema central -> consistencia garantida com diagrama e app.
    return classe, _EMOJI[classe], tema.RISCO[classe]


def recomendacao(classe):
    """Texto de acao recomendada por faixa - foco na experiencia do usuario.

    A predicao so vira valor quando o usuario sabe O QUE FAZER com ela; por isso
    cada faixa carrega uma instrucao direta, e nao apenas um rotulo de risco.
    """
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

    Por que mostrar os "top 3 fatores"? Um score sozinho e uma caixa-preta:
    dizer "risco 82" nao ajuda o operador a agir. Apontar "umidade alta +
    proximidade de agua" transforma o numero em causa acionavel e gera confianca
    no modelo (a seguradora tambem exige essa rastreabilidade do porque).
    Usamos uma aproximacao por proximidade-do-pior-caso, intencionalmente simples
    e deterministica, para que a explicacao seja sempre reproduzivel e auditavel.

    'linha' = dict/Series com as features.
    """
    # Normaliza cada variavel para [0,1] na direcao do risco (inv=True quando
    # o risco cresce conforme o valor DIMINUI, como a distancia ate a agua).
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
