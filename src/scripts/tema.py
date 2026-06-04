"""
=============================================================================
 SomPrev Risk  |  Tema visual central (paleta de cores)
=============================================================================

Por que este arquivo existe?
    Antes, os mesmos codigos de cor (hex) apareciam repetidos no gerador do
    diagrama de arquitetura e no app Streamlit. Espalhar cor pelo codigo tem
    dois problemas: (1) trocar a identidade visual vira uma cacada por hex
    soltos em varios arquivos e (2) corre-se o risco de o diagrama ficar com
    um verde e o dashboard com outro. Centralizar aqui significa que mudar a
    marca passa a ser editar UM lugar so, com garantia de consistencia.

    Observacao: o protótipo HTML (preview_dashboard.html) tem seu proprio
    ponto central equivalente — as variaveis CSS em :root —, porque um arquivo
    estatico de navegador nao consegue importar este modulo Python. A divisao
    e proposital: Python (diagrama + app) le daqui; o HTML le do seu :root.
"""

# --- Cores de marca (nomeadas para leitura humana) -------------------------
# Sao a base da identidade visual agritech do produto.
VERDE_ESCURO = "#0B3D2E"   # verde escuro: cabecalhos, fundos de destaque
VERDE        = "#0B6E4F"   # verde principal: bordas, setas, enfase
AMBAR        = "#C77D34"   # ambar: camada de conectividade / acento quente
OFF_WHITE    = "#F6F4EC"   # off-white: fundo "papel" das telas
TINTA        = "#13241C"   # tinta: cor de texto principal (quase preto esverdeado)

# --- Tons de apoio do diagrama (neutros e variacoes suaves) ----------------
# Mantidos junto da marca para que o diagrama tambem tenha fonte unica de cor.
LINHA        = "#C9C2AE"   # linhas/molduras neutras
VERDE_SUAVE  = "#E3EFE7"   # preenchimento suave de blocos "campo"
AMBAR_SUAVE  = "#F3E4CF"   # preenchimento suave da camada de conectividade
AZUL         = "#3E6E8E"   # azul: camada de aplicacao (personas)
AZUL_SUAVE   = "#E0EAF0"   # preenchimento suave dos blocos de aplicacao

# --- Cores das 4 faixas de risco -------------------------------------------
# Semaforo do produto: a mesma escala vale no diagrama, no app e no HTML.
# Verde (seguro) -> amarelo -> laranja -> vermelho (perigo), uma progressao
# intuitiva que dispensa legenda para o operador em campo.
RISCO = {
    "Baixo":   "#1B9E4B",   # 🟢 operacao liberada
    "Medio":   "#E8B800",   # 🟡 operacao com atencao
    "Alto":    "#E8761B",   # 🟠 operacao com restricoes
    "Critico": "#D62828",   # 🔴 operacao nao recomendada
}

# Agrupador opcional: util para quem prefere acessar tudo por um unico dict.
PALETA = {
    "verde_escuro": VERDE_ESCURO,
    "verde": VERDE,
    "ambar": AMBAR,
    "off_white": OFF_WHITE,
    "tinta": TINTA,
    "linha": LINHA,
    "verde_suave": VERDE_SUAVE,
    "ambar_suave": AMBAR_SUAVE,
    "azul": AZUL,
    "azul_suave": AZUL_SUAVE,
    "risco": RISCO,
}
