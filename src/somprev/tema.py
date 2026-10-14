"""
=============================================================================
 SomPrev Risk  |  Tema visual central (paleta de cores)
=============================================================================

Proposito:
    Ponto unico de definicao das cores usadas pelo dashboard, pelos graficos do
    treino e dos relatorios e pelo gerador do diagrama de arquitetura
    (scripts/gerar_arquitetura.py). A centralizacao evita repetir os mesmos
    codigos hexadecimais em varios arquivos e a divergencia de cor entre eles.

Identidade: a marca SomPrev Risk e amarela (amarelo trator) sobre grafite, com
um verde de apoio que vem do broto do simbolo. A escala de risco e separada e
propria (verde->amarelo->laranja->vermelho) e serve so ao SEMAFORO.

REGRA QUE NAO SE QUEBRA
    A cor da marca nunca representa risco. O amarelo institucional so aparece
    na "moldura" do produto -- barra superior, menu lateral, botao primario,
    foco do teclado, assinatura -- nunca dentro de um grafico, de um KPI ou de
    um cartao de alerta. Assim ninguem confunde "isto e da SomPrev" com
    "isto esta em atencao".
"""

# --- Marca ------------------------------------------------------------------
AMARELO_INSTITUCIONAL = "#FFC400"   # amarelo trator: menu lateral, botao primario, marca
AMARELO_ESCURO        = "#E0A500"   # estados :hover/:active e bordas do amarelo
AMBAR_PROFUNDO        = "#A06A00"   # acento escuro legivel sobre fundo claro (texto/linha)
AMARELO_SUAVE         = "#FFF3CC"   # tint do amarelo (fundos de realce)
VERDE_MARCA           = "#1A7048"   # broto do simbolo; apoio em pecas impressas
GRAFITE               = "#17160F"   # tinta principal (texto e simbolo)
GRAFITE_MEDIO         = "#4A463A"   # texto de apoio com bom contraste
BRANCO                = "#FFFFFF"   # cartoes

# --- Neutros de apoio (fundos, bordas, textos secundarios) ------------------
PAPEL          = "#FBFAF5"   # fundo da aplicacao (branco quente, menos ofuscante que #FFF)
CINZA_CLARO    = "#F3F1E9"   # fundo neutro / faixas alternadas
LINHA          = "#E7E3D6"   # linhas e molduras neutras
LINHA_FORTE    = "#D4CFBE"   # moldura de enfase
CINZA_MEDIO    = "#6B6657"   # texto secundario (contraste AA sobre PAPEL)
GRAFITE_SUAVE  = "#EDEBE2"   # preenchimento neutro claro
GRADE          = "#EDEAE0"   # grade dos graficos

# --- Cores das 4 faixas de risco (semaforo) --------------------------------
# Independente da marca: progressao verde (seguro) -> amarelo -> laranja ->
# vermelho (perigo), intuitiva e que dispensa legenda para o operador em campo.
RISCO = {
    "Baixo":   "#2E9E5B",   # 🟢 operacao liberada
    "Medio":   "#E8B800",   # 🟡 operacao com atencao
    "Alto":    "#E8761B",   # 🟠 operacao com restricoes
    "Critico": "#C20A14",   # 🔴 operacao nao recomendada
}

# Tinta a usar SOBRE cada cor de risco. Amarelo e laranja pedem texto escuro:
# texto branco sobre #E8B800 fica em 1.9:1, bem abaixo do minimo legivel.
TINTA_RISCO = {
    "Baixo":   "#FFFFFF",
    "Medio":   "#2A2100",
    "Alto":    "#2A1400",
    "Critico": "#FFFFFF",
}

# Versao escura de cada cor de risco, para ESCREVER sobre fundo claro. As cores
# da escala sao calibradas para preencher um bloco, nao para virar texto: o
# amarelo #E8B800 sobre branco fica em 1,8:1 e e ilegivel.
RISCO_TEXTO = {
    "Baixo":   "#1C6B3E",
    "Medio":   "#8A6700",
    "Alto":    "#9A4A08",
    "Critico": "#A3060F",
}

# --- Aliases legados --------------------------------------------------------
# Os nomes antigos (identidade vermelha) continuam existindo para nao quebrar
# o treino, os relatorios e o gerador do diagrama. Apontam para os tokens novos.
VERMELHO_INSTITUCIONAL = AMBAR_PROFUNDO   # legado: acento da marca em graficos
VERMELHO_ESCURO        = GRAFITE          # legado: titulos
VERMELHO_SUAVE         = AMARELO_SUAVE    # legado: tint da marca

# Agrupador opcional: reune todas as cores nomeadas em um unico dicionario.
PALETA = {
    "amarelo_institucional": AMARELO_INSTITUCIONAL,
    "amarelo_escuro": AMARELO_ESCURO,
    "ambar_profundo": AMBAR_PROFUNDO,
    "amarelo_suave": AMARELO_SUAVE,
    "verde_marca": VERDE_MARCA,
    "grafite": GRAFITE,
    "grafite_medio": GRAFITE_MEDIO,
    "papel": PAPEL,
    "cinza_claro": CINZA_CLARO,
    "branco": BRANCO,
    "linha": LINHA,
    "linha_forte": LINHA_FORTE,
    "cinza_medio": CINZA_MEDIO,
    "grafite_suave": GRAFITE_SUAVE,
    "risco": RISCO,
    "tinta_risco": TINTA_RISCO,
    "risco_texto": RISCO_TEXTO,
    # chaves legadas
    "vermelho_institucional": VERMELHO_INSTITUCIONAL,
    "vermelho_escuro": VERMELHO_ESCURO,
    "vermelho_suave": VERMELHO_SUAVE,
}

# Paleta categorica (series como regioes, operacoes, equipamentos). Ordem fixa e
# validada para daltonismo em pares adjacentes: a mesma serie tem sempre a mesma cor.
CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Escala continua do mapa de calor: do papel ao grafite passando pelo ambar.
ESCALA_CALOR = [[0.0, "#FFFBEA"], [0.35, "#FFD45C"], [0.7, "#E8761B"], [1.0, "#8C1407"]]
