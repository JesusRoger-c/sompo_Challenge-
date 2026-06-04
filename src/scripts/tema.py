"""
=============================================================================
 SomPrev Risk  |  Tema visual central (paleta de cores)
=============================================================================

Por que este arquivo existe?
    Antes, os mesmos codigos de cor (hex) apareciam repetidos no gerador do
    diagrama de arquitetura e no app Streamlit. Espalhar cor pelo codigo tem
    dois problemas: (1) trocar a identidade visual vira uma cacada por hex
    soltos em varios arquivos e (2) corre-se o risco de o diagrama ficar com
    uma cor e o dashboard com outra. Centralizar aqui significa que mudar a
    marca passa a ser editar UM lugar so, com garantia de consistencia.

    Observacao: o protótipo HTML (preview_dashboard.html) tem seu proprio
    ponto central equivalente — as variaveis CSS em :root —, porque um arquivo
    estatico de navegador nao consegue importar este modulo Python. A divisao
    e proposital: Python (diagrama + app) le daqui; o HTML le do seu :root.

Identidade: cores institucionais da Sompo (vermelho) para a MARCA; uma escala
de risco propria (verde->amarelo->laranja->vermelho) para o SEMAFORO. As duas
sao mantidas separadas DE PROPOSITO: a cor de marca nunca representa risco, para
o operador nunca confundir "isto e da Sompo" com "isto e perigoso".
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

# Agrupador opcional: util para quem prefere acessar tudo por um unico dict.
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
