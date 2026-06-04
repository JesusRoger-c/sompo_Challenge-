"""
Gera o diagrama de arquitetura do AgroSentinela (SVG + PNG).
Uso (a partir da raiz do repositorio): python src/scripts/_gerar_arquitetura.py
As saidas sao gravadas em document/ (template FIAP).
"""
import os
import cairosvg

# Raiz do repositorio: este script vive em src/scripts/.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCUMENT_DIR = os.path.join(ROOT_DIR, "document")
os.makedirs(DOCUMENT_DIR, exist_ok=True)

# Paleta agritech
INK = "#13241C"; PAPER = "#F6F4EC"; LINE = "#C9C2AE"
G_DARK = "#0B3D2E"; G = "#0B6E4F"; G_SOFT = "#E3EFE7"
AMBER = "#C77D34"; AMBER_SOFT = "#F3E4CF"
BLUE = "#3E6E8E"; BLUE_SOFT = "#E0EAF0"
RISKS = {"Baixo": "#1B9E4B", "Medio": "#E8B800", "Alto": "#E8761B", "Critico": "#D62828"}

W, H = 1180, 660

def box(x, y, w, h, fill, stroke, title, sub, tcol=INK, r=12):
    return f'''
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>
    <text x="{x+16}" y="{y+26}" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="15" font-weight="700" fill="{tcol}">{title}</text>
    <text x="{x+16}" y="{y+46}" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="11.5" fill="{tcol}" opacity="0.78">{sub}</text>
  </g>'''

def chip(x, y, w, label, fill, stroke):
    return f'''
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>
    <text x="{x+w/2}" y="{y+19}" text-anchor="middle" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="11.5" font-weight="600" fill="{INK}">{label}</text>
  </g>'''

def col_label(x, w, text, color):
    return f'''
  <g>
    <rect x="{x}" y="104" width="{w}" height="30" rx="8" fill="{color}"/>
    <text x="{x+w/2}" y="124" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="12" font-weight="700" fill="#ffffff" letter-spacing="1.5">{text}</text>
  </g>'''

def arrow(x1, y1, x2, y2):
    return f'<path d="M {x1} {y1} L {x2} {y2}" stroke="{G}" stroke-width="2.4" fill="none" marker-end="url(#arrow)"/>'

svg = [f'''<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arrow" markerWidth="11" markerHeight="11" refX="8" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="{G}"/>
    </marker>
    <linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{G_DARK}"/><stop offset="1" stop-color="{G}"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="{W}" height="{H}" fill="{PAPER}"/>

  <!-- Header -->
  <rect x="0" y="0" width="{W}" height="74" fill="url(#hdr)"/>
  <circle cx="40" cy="37" r="15" fill="none" stroke="#fff" stroke-width="2.4"/>
  <path d="M40 27 L40 47 M31 37 L49 37" stroke="#fff" stroke-width="2.4"/>
  <text x="66" y="33" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="20" font-weight="800" fill="#fff">AgroSentinela &#8212; Arquitetura da Solucao</text>
  <text x="66" y="54" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="12.5" fill="#CFE8DC">Pipeline de risco agricola | Sensores/APIs &#8594; Processamento (IA) &#8594; Dashboards/Alertas | Challenge FIAP + Sompo</text>
''']

# Column labels
svg.append(col_label(40, 250, "1 - CAMPO (COLETA)", G_DARK))
svg.append(col_label(330, 215, "2 - CONECTIVIDADE", AMBER))
svg.append(col_label(585, 260, "3 - NUVEM (IA + DADOS)", G))
svg.append(col_label(885, 255, "4 - APLICACAO", BLUE))

# ---- Column 1: Campo (devices) ----
svg.append(box(40, 150, 250, 56, G_SOFT, G, "Sensor de umidade do solo", "Umidade % + temperatura"))
svg.append(box(40, 216, 250, 56, G_SOFT, G, "GPS / Geolocalizacao", "Posicao, distancia de corpos d'agua"))
svg.append(box(40, 282, 250, 56, G_SOFT, G, "Inclinometro", "Declividade do terreno (graus)"))
svg.append(box(40, 348, 250, 56, G_SOFT, G, "Horimetro / sensor de carga", "Horas de operacao, carga, manutencao"))
svg.append(box(40, 430, 250, 56, AMBER_SOFT, AMBER, "API de Clima (externa)", "Precipitacao, previsao (ex.: OpenWeather)"))

# ---- Column 2: Conectividade ----
svg.append(box(330, 216, 215, 66, "#fff", AMBER, "Gateway de borda", "LoRaWAN / 4G | bufferiza e envia"))
svg.append(box(330, 348, 215, 66, "#fff", AMBER, "Coletor / MQTT", "Padroniza pacotes de telemetria"))

# ---- Column 3: Nuvem ----
svg.append(box(585, 150, 260, 70, "#fff", G, "Ingestao / ETL (Python)", "Limpeza, validacao, feature engineering"))
# SQL cylinder
cx, cy, cw, ch = 585, 250, 260, 96
svg.append(f'''
  <g>
    <path d="M{cx} {cy+14} a{cw/2} 14 0 0 1 {cw} 0 v{ch-28} a{cw/2} 14 0 0 1 -{cw} 0 z" fill="{G_DARK}"/>
    <ellipse cx="{cx+cw/2}" cy="{cy+14}" rx="{cw/2}" ry="14" fill="{G}"/>
    <text x="{cx+cw/2}" y="{cy+50}" text-anchor="middle" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="15" font-weight="700" fill="#fff">Banco de Dados SQL</text>
    <text x="{cx+cw/2}" y="{cy+70}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="10.5" fill="#CFE8DC">regioes . equipamentos . leituras</text>
    <text x="{cx+cw/2}" y="{cy+85}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="10.5" fill="#CFE8DC">predicoes . alertas (historico/auditoria)</text>
  </g>''')
svg.append(box(585, 378, 260, 108, G_DARK, G_DARK,
               "Motor de IA - Random Forest", "Classifica sinistro e gera o score 0-100", tcol="#fff"))
svg.append(chip(601, 432, 110, "Score 0-100", "#fff", G))
svg.append(chip(719, 432, 110, "Top 3 fatores", "#fff", G))

# ---- Column 4: Aplicacao (personas) ----
svg.append(box(885, 150, 255, 78, BLUE_SOFT, BLUE, "App do Operador (mobile)", "Semaforo de risco + recomendacao simples"))
svg.append(box(885, 236, 255, 78, BLUE_SOFT, BLUE, "Dashboard do Gestor (web)", "Mapa de calor, ranking da frota, KPIs"))
svg.append(box(885, 322, 255, 78, BLUE_SOFT, BLUE, "Portal da Seguradora", "Score auditavel, historico, relatorios"))
svg.append(box(885, 430, 255, 56, "#FCE9E9", RISKS["Critico"], "Motor de Alertas", "Notificacoes preventivas Alto/Critico", tcol=INK))

# ---- Arrows (flow) ----
svg.append(arrow(290, 178, 328, 230))
svg.append(arrow(290, 244, 328, 244))
svg.append(arrow(290, 310, 328, 372))
svg.append(arrow(290, 376, 328, 388))
svg.append(arrow(290, 458, 583, 410))
svg.append(arrow(545, 248, 583, 200))
svg.append(arrow(545, 380, 583, 320))
svg.append(arrow(845, 185, 883, 188))     # ingestao -> ... (visual)
svg.append(arrow(845, 300, 883, 270))     # banco -> gestor/seguradora
svg.append(arrow(845, 430, 883, 360))     # IA -> portal
svg.append(arrow(845, 440, 883, 188))     # IA -> operador
svg.append(arrow(845, 460, 883, 455))     # IA -> alertas

# Internal nuvem arrows
svg.append(f'<path d="M715 220 L715 250" stroke="{G}" stroke-width="2.4" marker-end="url(#arrow)"/>')
svg.append(f'<path d="M715 346 L715 378" stroke="{G}" stroke-width="2.4" marker-end="url(#arrow)"/>')

# ---- Footer caption ----
svg.append(f'''
  <rect x="40" y="520" width="1100" height="110" rx="12" fill="#fff" stroke="{LINE}"/>
  <text x="60" y="548" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="13" font-weight="700" fill="{INK}">Governanca e Seguranca</text>
  <text x="60" y="572" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="11.5" fill="{INK}" opacity="0.82">Controle de acesso por perfil . Validacao de integridade na ingestao . Versao do modelo registrada em cada predicao . Historico imutavel para auditoria.</text>
  <text x="60" y="600" font-family="IBM Plex Mono, monospace" font-size="11" fill="{G_DARK}" font-weight="700">FLUXO:  Sensores/APIs  &#8594;  Gateway  &#8594;  ETL  &#8594;  Banco SQL  &#8594;  Random Forest  &#8594;  Score/Alertas  &#8594;  Dashboards por persona</text>
  <text x="60" y="620" font-family="IBM Plex Sans, Segoe UI, sans-serif" font-size="10.5" fill="{INK}" opacity="0.6">Tecnologias: Python . scikit-learn . SQLite/SQL . Streamlit . GitHub</text>
''')

svg.append("</svg>")
svg_str = "\n".join(svg)

svg_out = os.path.join(DOCUMENT_DIR, "arquitetura.svg")
png_out = os.path.join(DOCUMENT_DIR, "arquitetura.png")
with open(svg_out, "w", encoding="utf-8") as f:
    f.write(svg_str)
cairosvg.svg2png(bytestring=svg_str.encode("utf-8"),
                 write_to=png_out, output_width=W*2, output_height=H*2)
print(f"[OK] {svg_out} e {png_out} gerados.")
