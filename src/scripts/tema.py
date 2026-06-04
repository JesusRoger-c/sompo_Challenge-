"""
=============================================================================
 SomPrev Risk  |  Tema visual central (paleta de cores)
=============================================================================

Proposito:
    Ponto unico de definicao das cores usadas pelo gerador do diagrama de
    arquitetura e pelo app Streamlit. A centralizacao evita a repeticao dos
    mesmos codigos hexadecimais em varios arquivos e a divergencia de cor entre
    o diagrama e o dashboard.

    O protótipo HTML (preview_dashboard.html) possui um ponto central
    equivalente — as variaveis CSS em :root —, ja que um arquivo estatico de
    navegador nao importa este modulo Python. A divisao e intencional: o lado
    Python (diagrama e app) deriva as cores deste modulo; o HTML deriva do seu
    proprio :root.

Identidade: cores institucionais da Sompo (vermelho) para a MARCA e uma escala
de risco propria (verde->amarelo->laranja->vermelho) para o SEMAFORO. As duas
permanecem separadas de proposito: a cor de marca nunca representa risco, o que
evita confundir "pertence a Sompo" com "indica perigo".
"""

# --- Cores institucionais (marca Sompo) ------------------------------------
VERMELHO_INSTITUCIONAL = "#E1251B"   # destaques, marca, links, acentos
VERMELHO_ESCURO        = "#A4161A"   # cabecalhos e titulos
GRAFITE                = "#1A1A1A"   # texto principal
CINZA_CLARO            = "#F5F5F5"   # fundo neutro
BRANCO                 = "#FFFFFF"   # cartoes

# --- Neutros de apoio (bordas, textos secundarios, tints do diagrama) ------
# Mantidos junto da marca para que o diagrama tambem tenha fonte unica de cor.
LINHA          = "#E2E2E2"   # linhas/molduras neutras
CINZA_MEDIO    = "#6B6B6B"   # texto secundario / colunas neutras do diagrama
VERMELHO_SUAVE = "#FBE3E1"   # preenchimento suave (tint do vermelho da marca)
GRAFITE_SUAVE  = "#EDEDED"   # preenchimento neutro claro

# --- Cores das 4 faixas de risco (semaforo) --------------------------------
# Independente da marca: progressao verde (seguro) -> amarelo -> laranja ->
# vermelho (perigo), intuitiva e que dispensa legenda para o operador em campo.
RISCO = {
    "Baixo":   "#2E9E5B",   # 🟢 operacao liberada
    "Medio":   "#E8B800",   # 🟡 operacao com atencao
    "Alto":    "#E8761B",   # 🟠 operacao com restricoes
    "Critico": "#C20A14",   # 🔴 operacao nao recomendada
}

# Agrupador opcional: reune todas as cores nomeadas em um unico dicionario.
PALETA = {
    "vermelho_institucional": VERMELHO_INSTITUCIONAL,
    "vermelho_escuro": VERMELHO_ESCURO,
    "grafite": GRAFITE,
    "cinza_claro": CINZA_CLARO,
    "branco": BRANCO,
    "linha": LINHA,
    "cinza_medio": CINZA_MEDIO,
    "vermelho_suave": VERMELHO_SUAVE,
    "grafite_suave": GRAFITE_SUAVE,
    "risco": RISCO,
}
