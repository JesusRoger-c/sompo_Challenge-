"""
Componentes visuais reutilizaveis do dashboard (estilo, cartoes e graficos).

Padroes de visualizacao adotados:
  * Cores de RISCO (verde -> vermelho) sao reservadas as faixas de risco e
    sempre acompanhadas do rotulo escrito (nunca so a cor).
  * O amarelo da marca vive apenas na moldura do produto (menu lateral, botao
    primario, foco, assinatura). Dentro de grafico, KPI ou alerta ele nunca
    aparece, para nao ser confundido com a faixa "Medio" do semaforo.
  * Series categoricas (regioes, operacoes) usam uma paleta fixa, na mesma
    ordem sempre: a mesma regiao tem a mesma cor em todos os graficos.
  * Um unico eixo Y por grafico; linhas de 2 px; grade discreta; tooltip ao
    passar o mouse; legenda sempre presente quando ha mais de uma serie.
"""

from __future__ import annotations

import zlib

import plotly.graph_objects as go
import streamlit as st

from .. import regras, tema
from ..esquema import rotulo_valor
from . import fontes, marca

# Paleta categorica validada (ordem fixa, segura para daltonismo em pares adjacentes).
CATEGORICA = tema.CATEGORICA
ORDEM_REGIOES = ["Sorriso", "Rio Verde", "Lucas do Rio Verde", "Cascavel", "Barreiras", "Não-Me-Toque"]
ORDEM_OPERACOES = ["Plantio", "Pulverizacao", "Colheita", "Transporte"]
ORDEM_TIPOS = ["Trator", "Colheitadeira", "Pulverizador"]

FONTE_TEXTO = "'IBM Plex Sans', 'Segoe UI', Arial, sans-serif"
FONTE_TITULO = "'Manrope', 'IBM Plex Sans', Arial, sans-serif"
FONTE_NUM = "'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace"


def cor_serie(nome: str) -> str:
    for ordem in (ORDEM_REGIOES, ORDEM_OPERACOES, ORDEM_TIPOS):
        if nome in ordem:
            return CATEGORICA[ordem.index(nome)]
    return CATEGORICA[zlib.crc32(str(nome).encode()) % len(CATEGORICA)]   # estavel entre execucoes


def aplicar_estilo() -> None:
    st.markdown(f"""
    <style>
      {fontes.CSS}

      :root {{
        --sp-amarelo: {tema.AMARELO_INSTITUCIONAL};
        --sp-amarelo-escuro: {tema.AMARELO_ESCURO};
        --sp-ambar: {tema.AMBAR_PROFUNDO};
        --sp-grafite: {tema.GRAFITE};
        --sp-grafite-medio: {tema.GRAFITE_MEDIO};
        --sp-cinza: {tema.CINZA_MEDIO};
        --sp-papel: {tema.PAPEL};
        --sp-linha: {tema.LINHA};
        --sp-linha-forte: {tema.LINHA_FORTE};
        --sp-raio: 12px;
        --sp-saida: cubic-bezier(.23, 1, .32, 1);
        --sp-sombra: 0 1px 2px rgba(23,22,15,.05), 0 8px 20px -14px rgba(23,22,15,.28);
      }}

      /* ---------- base ---------- */
      .stApp {{ background: var(--sp-papel); }}
      html, body, [class*="css"], .stMarkdown, .stText, input, button, textarea, select {{
        font-family: {FONTE_TEXTO};
        -webkit-font-smoothing: antialiased;
      }}
      h1, h2, h3, h4 {{ font-family: {FONTE_TITULO}; letter-spacing: -.018em; color: var(--sp-grafite);
                        font-weight: 800; }}
      .stMarkdown h2, .stMarkdown h3 {{ font-weight: 800; }}
      h3 {{ font-size: 1.22rem; }}
      strong, b {{ font-weight: 600; }}
      a {{ color: var(--sp-ambar); text-underline-offset: 3px; }}
      .block-container {{ padding-top: 2.1rem; padding-bottom: 4rem; max-width: 1440px; }}
      [data-testid="stHeader"] {{ background: transparent; }}
      hr {{ border-color: var(--sp-linha); }}
      ::selection {{ background: {tema.AMARELO_SUAVE}; color: var(--sp-grafite); }}

      /* ---------- menu lateral: a marca mora aqui ---------- */
      [data-testid="stSidebar"] {{
        background: var(--sp-amarelo);
        border-right: 1px solid rgba(23,22,15,.14);
      }}
      [data-testid="stSidebar"] * {{ color: var(--sp-grafite); }}
      [data-testid="stSidebar"] hr {{ border-color: rgba(23,22,15,.18); }}
      [data-testid="stSidebar"] .stButton button {{
        background: var(--sp-grafite); color: var(--sp-amarelo); border: 0; font-weight: 600;
        border-radius: 10px; width: 100%;
      }}
      [data-testid="stSidebar"] .stButton button:hover {{ background: #2A2819; color: #fff; }}
      [data-testid="stSidebar"] .stButton button * {{ color: inherit; }}
      .sp-marca {{ display: block; width: 86%; max-width: 184px; height: auto; margin: 4px 0 22px; }}
      .sp-marca-emp {{ display: block; width: 100%; max-width: 236px; height: auto; margin: 0 auto 6px; }}

      .sp-usuario {{
        display: flex; align-items: center; gap: 11px;
        background: rgba(255,255,255,.52); border: 1px solid rgba(23,22,15,.12);
        border-radius: 12px; padding: 11px 13px; margin-bottom: 12px;
      }}
      .sp-avatar {{
        width: 38px; height: 38px; border-radius: 10px; background: var(--sp-grafite);
        color: var(--sp-amarelo); display: flex; align-items: center; justify-content: center;
        font-family: {FONTE_TITULO}; font-weight: 800; font-size: 17px; flex: 0 0 38px;
      }}
      .sp-usuario .nome {{ font-weight: 700; font-size: 14.5px; line-height: 1.2; }}
      .sp-usuario .papel {{ font-size: 12px; color: rgba(23,22,15,.68); line-height: 1.3; margin-top: 2px; }}
      .sp-secao {{
        font-size: 11px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
        color: rgba(23,22,15,.6); margin: 18px 0 8px;
      }}
      .sp-chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
      .sp-chip {{
        font-family: {FONTE_NUM}; font-size: 11.5px; padding: 3px 9px; border-radius: 7px;
        background: rgba(23,22,15,.09); border: 1px solid rgba(23,22,15,.1);
      }}
      .sp-meta {{ font-size: 11.5px; line-height: 1.55; color: rgba(23,22,15,.68); }}

      /* ---------- titulo da tela ---------- */
      .sp-titulo h1 {{ font-size: 2.05rem; margin: 0 0 2px; line-height: 1.1; font-weight: 800; }}
      .sp-titulo .sub {{ color: var(--sp-cinza); font-size: 15px; max-width: 76ch; }}
      .sp-titulo {{ margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--sp-linha); }}

      /* ---------- cartoes ---------- */
      .sp-cartao {{
        background: #fff; border: 1px solid var(--sp-linha); border-radius: var(--sp-raio);
        padding: 15px 17px 16px; min-height: 108px; box-shadow: var(--sp-sombra);
      }}
      .sp-rotulo {{
        font-size: 11.5px; color: var(--sp-cinza); text-transform: uppercase; letter-spacing: .07em;
        font-weight: 600;
      }}
      .sp-valor {{
        font-family: {FONTE_NUM}; font-size: 27px; white-space: nowrap; font-weight: 600;
        color: var(--sp-grafite); line-height: 1.2; margin-top: 5px; font-variant-numeric: tabular-nums;
      }}
      .sp-sub {{ font-size: 12.5px; color: var(--sp-cinza); }}
      .sp-pill {{
        display: inline-block; padding: 3px 11px; border-radius: 999px; font-weight: 700;
        font-size: 12.5px; letter-spacing: .01em;
      }}

      /* ---------- alertas ---------- */
      .sp-alerta {{
        border: 1px solid var(--sp-linha); border-left: 3px solid; border-radius: var(--sp-raio);
        background: #fff; padding: 12px 15px; margin-bottom: 9px; box-shadow: var(--sp-sombra);
      }}
      .sp-alerta .acao {{ margin: 6px 0 2px; color: var(--sp-grafite-medio); }}
      .sp-estado {{
        font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 6px;
        background: var(--sp-papel); border: 1px solid var(--sp-linha); color: var(--sp-cinza);
      }}
      .sp-criterio {{
        font-family: {FONTE_NUM}; font-size: 11.5px; color: var(--sp-cinza); margin-top: 6px;
        padding-top: 6px; border-top: 1px dashed var(--sp-linha);
      }}

      /* ---------- semaforo ----------
         A cor de risco fica concentrada na "luz". Assim o sinal se lê de longe
         sem transformar a tela inteira em um bloco vermelho no caso Crítico. */
      .sp-semaforo {{
        display: flex; gap: 20px; align-items: center;
        background: #fff; border: 1px solid var(--sp-linha); border-radius: 16px;
        padding: 20px 22px; box-shadow: var(--sp-sombra);
        /* mesma altura do gráfico ao lado, para os dois blocos fecharem na mesma linha */
        min-height: 300px; box-sizing: border-box;
      }}
      .sp-semaforo .luz {{
        flex: 0 0 116px; width: 116px; height: 116px; border-radius: 20px;
        display: flex; align-items: center; justify-content: center;
        transition: background 260ms var(--sp-saida);
      }}
      .sp-semaforo .luz .num {{
        font-family: {FONTE_NUM}; font-size: 52px; font-weight: 600; line-height: 1;
        font-variant-numeric: tabular-nums; letter-spacing: -.03em;
      }}
      .sp-semaforo .corpo {{ min-width: 0; padding-top: 2px; }}
      .sp-semaforo .cap {{
        font-size: 11.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
        color: var(--sp-cinza);
      }}
      .sp-semaforo .classe {{ font-family: {FONTE_TITULO}; font-size: 22px; font-weight: 800; margin: 3px 0 9px; }}
      .sp-semaforo .rec {{ font-size: 15.5px; line-height: 1.5; color: var(--sp-grafite-medio); }}

      /* versão sólida (bloco inteiro colorido), mantida para quem preferir */
      .sp-semaforo.sp-solido {{
        display: block; border: 0; box-shadow: none; padding: 22px 24px 24px;
        transition: background 260ms var(--sp-saida);
      }}
      .sp-semaforo.sp-solido .cap {{ color: inherit; opacity: .82; }}
      .sp-semaforo.sp-solido .num {{
        font-family: {FONTE_NUM}; font-size: 68px; font-weight: 600; line-height: .98; margin: 6px 0 2px;
        font-variant-numeric: tabular-nums; letter-spacing: -.03em; display: block;
      }}
      .sp-semaforo.sp-solido .classe {{ font-size: 21px; margin: 4px 0 10px; }}
      .sp-semaforo.sp-solido .rec {{ color: inherit; opacity: .94; }}
      .sp-rodape {{ font-size: 12px; color: var(--sp-cinza); margin-top: 26px; }}

      /* ---------- controles do Streamlit ---------- */
      .stButton button, .stFormSubmitButton button, .stDownloadButton button {{
        border-radius: 10px; font-weight: 600; border: 1px solid var(--sp-linha-forte);
        transition: transform 140ms var(--sp-saida), background 140ms ease, border-color 140ms ease;
      }}
      .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"],
      .stFormSubmitButton button[kind="primaryFormSubmit"] {{
        background: var(--sp-amarelo); color: var(--sp-grafite); border-color: var(--sp-amarelo-escuro);
      }}
      .stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover,
      .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{
        background: var(--sp-amarelo-escuro); color: var(--sp-grafite); border-color: var(--sp-amarelo-escuro);
      }}
      .stButton button:active, .stFormSubmitButton button:active, .stDownloadButton button:active {{
        transform: scale(.97);
      }}
      :focus-visible {{ outline: 3px solid var(--sp-amarelo-escuro); outline-offset: 2px; border-radius: 6px; }}

      [data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"] {{
        border-radius: 10px !important;
      }}
      /* campos sobre cartao branco precisam de contorno proprio para nao sumirem */
      .stTextInput [data-baseweb="input"], .stNumberInput [data-baseweb="input"],
      .stTextArea [data-baseweb="textarea"] {{
        border: 1px solid var(--sp-linha-forte); background: #fff;
      }}
      .stTextInput [data-baseweb="input"]:focus-within, .stNumberInput [data-baseweb="input"]:focus-within {{
        border-color: var(--sp-grafite);
      }}
      [data-testid="stMetricValue"] {{
        font-family: {FONTE_NUM}; font-variant-numeric: tabular-nums; font-weight: 600;
        color: var(--sp-grafite);
      }}
      [data-testid="stMetricLabel"] p {{
        font-size: 11.5px !important; text-transform: uppercase; letter-spacing: .07em;
        color: var(--sp-cinza); font-weight: 600;
      }}

      .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--sp-linha); }}
      .stTabs [data-baseweb="tab"] {{
        font-weight: 600; color: var(--sp-cinza); border-radius: 8px 8px 0 0; padding: 8px 14px;
      }}
      .stTabs [aria-selected="true"] {{ color: var(--sp-grafite); }}
      .stTabs [data-baseweb="tab-highlight"] {{ background: var(--sp-amarelo-escuro); height: 3px; }}

      [data-testid="stExpander"] details {{
        border: 1px solid var(--sp-linha); border-radius: var(--sp-raio); background: #fff;
      }}
      [data-testid="stDataFrame"] {{ border-radius: var(--sp-raio); overflow: hidden; }}

      /* grafico com a mesma moldura dos cartoes, para o conteudo nao "flutuar" */
      [data-testid="stPlotlyChart"] {{
        background: #fff; border: 1px solid var(--sp-linha); border-radius: var(--sp-raio);
        padding: 6px 10px 2px; box-shadow: var(--sp-sombra);
      }}
      [data-testid="stImage"] img {{ border: 1px solid var(--sp-linha); border-radius: var(--sp-raio); }}

      /* chrome do Streamlit que nao faz sentido numa demonstracao de estande */
      [data-testid="stAppDeployButton"] {{ display: none; }}

      /* ---------- movimento ---------- */
      .sp-semaforo, .sp-alerta, .sp-cartao {{ animation: sp-entrar 220ms var(--sp-saida) both; }}
      @keyframes sp-entrar {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
      @media (prefers-reduced-motion: reduce) {{
        .sp-semaforo, .sp-alerta, .sp-cartao {{ animation: none; }}
        .sp-semaforo, .stButton button, .stFormSubmitButton button, .stDownloadButton button {{ transition: none; }}
      }}

      /* ---------- tela de entrada ---------- */
      .sp-login {{ padding: 0 0 6px; }}
      .sp-login .faixa {{
        height: 7px; width: 72px; background: var(--sp-amarelo); border-radius: 999px; margin: 0 auto 26px;
      }}
      .sp-login .tag {{
        text-align: center; font-size: 13px; color: var(--sp-cinza); margin: 14px 0 18px; line-height: 1.6;
      }}
      .st-key-form_login [data-testid="stForm"] {{
        background: #fff; border: 1px solid var(--sp-linha); border-radius: 18px; padding: 24px 26px 20px;
        box-shadow: 0 2px 4px rgba(23,22,15,.04), 0 26px 50px -30px rgba(23,22,15,.4);
      }}
    </style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- marca
def marca_lateral() -> None:
    """Assinatura da marca no topo do menu lateral (fundo amarelo)."""
    st.markdown(marca.HORIZONTAL_SOBRE_AMARELO, unsafe_allow_html=True)


def cabecalho(titulo: str, subtitulo: str) -> None:
    """Titulo da tela. A marca nao se repete aqui: ela vive no menu lateral."""
    st.markdown(f"<div class='sp-titulo'><h1>{titulo}</h1><div class='sub'>{subtitulo}</div></div>",
                unsafe_allow_html=True)


def cartao_usuario(nome: str, perfil_rotulo: str, usuario: str) -> None:
    inicial = (nome or usuario or "?").strip()[:1].upper()
    st.markdown(f"<div class='sp-usuario'><div class='sp-avatar'>{inicial}</div>"
                f"<div><div class='nome'>{nome}</div>"
                f"<div class='papel'>{perfil_rotulo} · {usuario}</div></div></div>",
                unsafe_allow_html=True)


def chips(titulo: str, itens) -> None:
    corpo = "".join(f"<span class='sp-chip'>{i}</span>" for i in itens)
    st.markdown(f"<div class='sp-secao'>{titulo}</div><div class='sp-chips'>{corpo}</div>",
                unsafe_allow_html=True)


# ---------------------------------------------------------------- blocos
def pill(classe: str) -> str:
    return (f"<span class='sp-pill' style='background:{tema.RISCO[classe]};"
            f"color:{tema.TINTA_RISCO[classe]}'>"
            f"{regras.EMOJI_CLASSE[classe]} Risco {regras.ROTULO_CLASSE[classe]}</span>")


def cartao(rotulo: str, valor: str, sub: str = "") -> None:
    st.markdown(f"<div class='sp-cartao'><div class='sp-rotulo'>{rotulo}</div><div class='sp-valor'>{valor}</div>"
                f"<div class='sp-sub'>{sub}</div></div>", unsafe_allow_html=True)


def semaforo(score: int, classe: str, recomendacao: str, solido: bool = False) -> None:
    """Semáforo do score.

    Por padrão o cartão é claro e a cor de risco fica só na "luz" com o número
    dentro: o sinal continua inequívoco de longe, sem inundar a tela de vermelho
    quando o risco é Crítico. `solido=True` volta ao bloco inteiro colorido.
    """
    if solido:
        st.markdown(f"<div class='sp-semaforo sp-solido' style='background:{tema.RISCO[classe]};"
                    f"color:{tema.TINTA_RISCO[classe]}'>"
                    f"<div class='cap'>Score de risco (0–100)</div>"
                    f"<div class='num'>{score}</div>"
                    f"<div class='classe'>{regras.EMOJI_CLASSE[classe]} "
                    f"Risco {regras.ROTULO_CLASSE[classe]}</div>"
                    f"<div class='rec'>{recomendacao}</div></div>", unsafe_allow_html=True)
        return
    st.markdown(
        f"<div class='sp-semaforo'>"
        f"<div class='luz' style='background:{tema.RISCO[classe]};color:{tema.TINTA_RISCO[classe]}'>"
        f"<span class='num'>{score}</span></div>"
        f"<div class='corpo'>"
        f"<div class='cap'>Score de risco (0–100)</div>"
        f"<div class='classe' style='color:{tema.RISCO_TEXTO[classe]}'>"
        f"{regras.EMOJI_CLASSE[classe]} Risco {regras.ROTULO_CLASSE[classe]}</div>"
        f"<div class='rec'>{recomendacao}</div></div></div>", unsafe_allow_html=True)


def cartao_alerta(a: dict, mostrar_equip: bool = True) -> None:
    cor = tema.RISCO.get(a["nivel"], tema.CINZA_MEDIO)
    tinta = tema.TINTA_RISCO.get(a["nivel"], "#fff")
    equip = f"<b>{a['equipamento_id']}</b> · " if mostrar_equip else ""
    status = {"aberto": "aberto", "reconhecido": "reconhecido", "resolvido": "resolvido"}[a["status"]]
    ocorr = f" · {a['ocorrencias']} ocorrências" if a.get("ocorrencias", 1) > 1 else ""
    st.markdown(
        f"<div class='sp-alerta' style='border-left-color:{cor}'>"
        f"<div>{equip}<span class='sp-pill' style='background:{cor};color:{tinta};font-size:11.5px'>"
        f"{regras.ROTULO_CLASSE[a['nivel']]}</span> <b>{a['mensagem']}</b> "
        f"<span class='sp-estado'>{status}</span> "
        f"<span class='sp-sub'>{ocorr} · desde {str(a['criado_em'])[:16]}</span></div>"
        f"<div class='acao'>{a['recomendacao']}</div>"
        f"<div class='sp-criterio'>Critério: {a['criterio']} · destino: "
        f"{ {'Tecnico': 'Técnico'}.get(a['perfil_destino'], a['perfil_destino']) }</div></div>",
        unsafe_allow_html=True)


# ---------------------------------------------------------------- graficos
def _layout(fig: go.Figure, titulo: str = "", altura: int = 340, y_titulo: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15.5, family="Manrope, IBM Plex Sans, Arial",
                                          color=tema.GRAFITE), x=0, xanchor="left"),
        height=altura, margin=dict(l=10, r=10, t=52, b=10),
        plot_bgcolor=tema.BRANCO, paper_bgcolor=tema.BRANCO,
        font=dict(family="IBM Plex Sans, Arial", color=tema.GRAFITE_MEDIO, size=12.5),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None,
                    font=dict(size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=tema.GRAFITE, font=dict(family="IBM Plex Sans, Arial", color="#fff", size=12.5),
                        bordercolor=tema.GRAFITE))
    fig.update_xaxes(showgrid=False, linecolor=tema.LINHA, ticks="outside", tickcolor=tema.LINHA,
                     ticklen=4, title_font=dict(size=12))
    fig.update_yaxes(gridcolor=tema.GRADE, zeroline=False, title=y_titulo, linecolor="rgba(0,0,0,0)",
                     title_font=dict(size=12))
    return fig


def grafico_tendencia(tab, dimensao: str, medida: str, titulo: str, y_titulo: str, formato: str = ".1f"):
    fig = go.Figure()
    grupos = [g for g in ORDEM_REGIOES + ORDEM_OPERACOES + ORDEM_TIPOS if g in set(tab[dimensao])]
    grupos += sorted(set(tab[dimensao]) - set(grupos))
    for g in grupos:
        s = tab[tab[dimensao] == g]
        fig.add_trace(go.Scatter(x=s["periodo"], y=s[medida], mode="lines+markers", name=rotulo_valor(g),
                                 line=dict(width=2, color=cor_serie(g)), marker=dict(size=7),
                                 hovertemplate=f"%{{y:{formato}}}"))
    return _layout(fig, titulo, y_titulo=y_titulo)


def grafico_barras_h(rotulos, valores, cores, titulo: str, x_titulo: str, texto=None, altura: int = 360):
    fig = go.Figure(go.Bar(x=valores, y=rotulos, orientation="h", marker=dict(color=cores),
                           text=texto, textposition="outside",
                           textfont=dict(family="IBM Plex Mono, monospace", size=12, color=tema.GRAFITE_MEDIO),
                           hovertemplate="%{y}: %{x:.1f}<extra></extra>"))
    fig = _layout(fig, titulo, altura=altura)
    # margem direita maior: o rotulo "+30.9 pts" fica fora da barra e nao pode ser cortado
    fig.update_layout(hovermode="closest", showlegend=False, margin=dict(l=10, r=34, t=52, b=10))
    vals = [float(v) for v in valores] or [0.0]
    folga = (max(vals) - min(0.0, min(vals))) * 0.34 or 1.0
    fig.update_xaxes(title=x_titulo, gridcolor=tema.GRADE,
                     range=[min(0.0, min(vals)) - (folga if min(vals) < 0 else 0), max(vals) + folga])
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def grafico_heatmap(matriz, titulo: str):
    fig = go.Figure(go.Heatmap(
        z=matriz.values, x=[rotulo_valor(c) for c in matriz.columns], y=list(matriz.index),
        colorscale=tema.ESCALA_CALOR, zmin=0, zmax=max(60, float(matriz.max().max())),
        text=matriz.round(0).values, texttemplate="%{text}", hovertemplate="%{y} · %{x}: score %{z:.1f}<extra></extra>",
        textfont=dict(family="IBM Plex Mono, monospace", size=12),
        colorbar=dict(title="Score", outlinewidth=0, thickness=12, len=0.85)))
    fig = _layout(fig, titulo, altura=330)
    fig.update_layout(hovermode="closest")
    return fig


def grafico_contribuicoes(contrib: dict, rotulos: dict, titulo: str = "Por que esse score?"):
    itens = sorted(contrib.items(), key=lambda kv: kv[1], reverse=True)
    itens = [i for i in itens if abs(i[1]) >= 0.5][:6] or itens[:3]
    nomes = [rotulos.get(k, k) for k, _ in itens]
    valores = [v for _, v in itens]
    # fator que empurra para cima usa a cor de risco "Alto"; o que reduz usa "Baixo".
    cores = [tema.RISCO["Alto"] if v > 0 else tema.RISCO["Baixo"] for v in valores]
    texto = [f"{v:+.1f} pts" for v in valores]
    fig = grafico_barras_h(nomes, valores, cores, titulo, "Pontos de score (+ aumenta o risco / − reduz)", texto,
                           altura=300)
    return fig


def grafico_score_equipamento(serie, titulo: str):
    fig = go.Figure()
    for classe in regras.CLASSES:
        lo, hi = regras.carregar_regras()["faixas_score"][classe]
        fig.add_hrect(y0=lo, y1=hi + 1, fillcolor=tema.RISCO[classe], opacity=0.07, line_width=0)
    fig.add_trace(go.Scatter(x=serie["data_hora"], y=serie["score_risco"], mode="lines+markers",
                             line=dict(width=2, color=tema.GRAFITE), marker=dict(size=7,
                             color=[tema.RISCO[c] for c in serie["classe_risco"]]),
                             name="Score", hovertemplate="%{x|%d/%m %H:%M} · score %{y}<extra></extra>"))
    fig = _layout(fig, titulo, altura=280, y_titulo="Score")
    fig.update_yaxes(range=[0, 100])
    fig.update_layout(showlegend=False, hovermode="closest")
    return fig
