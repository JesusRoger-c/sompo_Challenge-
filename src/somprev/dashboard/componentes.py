"""
Componentes visuais reutilizaveis do dashboard (estilo, cartoes e graficos).

Padroes de visualizacao adotados:
  * Cores de RISCO (verde -> vermelho) sao reservadas as faixas de risco e
    sempre acompanhadas do rotulo escrito (nunca so a cor).
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

# Paleta categorica validada (ordem fixa, segura para daltonismo em pares adjacentes).
CATEGORICA = tema.CATEGORICA
ORDEM_REGIOES = ["Sorriso", "Rio Verde", "Lucas do Rio Verde", "Cascavel", "Barreiras", "Não-Me-Toque"]
ORDEM_OPERACOES = ["Plantio", "Pulverizacao", "Colheita", "Transporte"]
ORDEM_TIPOS = ["Trator", "Colheitadeira", "Pulverizador"]


def cor_serie(nome: str) -> str:
    for ordem in (ORDEM_REGIOES, ORDEM_OPERACOES, ORDEM_TIPOS):
        if nome in ordem:
            return CATEGORICA[ordem.index(nome)]
    return CATEGORICA[zlib.crc32(str(nome).encode()) % len(CATEGORICA)]   # estavel entre execucoes


def aplicar_estilo() -> None:
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@600;700&family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@500;600&display=swap');
      html, body, [class*="css"], .stMarkdown, .stText {{ font-family: 'Roboto', Arial, sans-serif; }}
      h1, h2, h3 {{ font-family: 'Roboto Slab', Georgia, serif; letter-spacing: -.01em; }}
      [data-testid="stMetricValue"] {{ font-family: 'Roboto Mono', monospace; }}
      .block-container {{ padding-top: 1.6rem; border-top: 4px solid {tema.VERMELHO_INSTITUCIONAL}; }}
      .sp-cartao {{ background: #fff; border: 1px solid {tema.LINHA}; border-radius: 14px; padding: 16px 18px;
                    height: 100%; }}
      .sp-rotulo {{ font-size: 12.5px; color: {tema.CINZA_MEDIO}; text-transform: uppercase; letter-spacing: .04em; }}
      .sp-valor {{ font-family: 'Roboto Mono', monospace; font-size: 26px; white-space: nowrap; font-weight: 600; color: {tema.GRAFITE};
                   line-height: 1.15; }}
      .sp-sub {{ font-size: 12.5px; color: {tema.CINZA_MEDIO}; }}
      .sp-pill {{ display: inline-block; padding: 3px 12px; border-radius: 999px; color: #fff; font-weight: 700;
                  font-size: 13px; }}
      .sp-alerta {{ border-left: 5px solid; border-radius: 10px; background: #fff; padding: 10px 14px;
                    margin-bottom: 8px; border-top: 1px solid {tema.LINHA}; border-right: 1px solid {tema.LINHA};
                    border-bottom: 1px solid {tema.LINHA}; }}
      .sp-criterio {{ font-family: 'Roboto Mono', monospace; font-size: 12px; color: {tema.CINZA_MEDIO}; }}
      .sp-semaforo {{ border-radius: 18px; padding: 22px; color: #fff; transition: background 220ms ease; }}
      .sp-semaforo .num {{ font-family: 'Roboto Mono', monospace; font-size: 64px; font-weight: 700; line-height: 1; }}
      .sp-rodape {{ font-size: 12px; color: {tema.CINZA_MEDIO}; margin-top: 24px; }}

      /* Entrada discreta do semaforo/alertas ao montar a tela (uma vez por carregamento, nao repetitiva) */
      .sp-semaforo, .sp-alerta {{ animation: sp-entrar 220ms ease-out both; }}
      @keyframes sp-entrar {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}

      /* Feedback tatil nos botoes (o Streamlit nao anima isso por padrao) */
      .stButton button, .stFormSubmitButton button, .stDownloadButton button {{
        transition: transform 140ms ease-out, box-shadow 140ms ease-out;
      }}
      .stButton button:active, .stFormSubmitButton button:active, .stDownloadButton button:active {{
        transform: scale(0.97);
      }}

      @media (prefers-reduced-motion: reduce) {{
        .sp-semaforo, .sp-alerta {{ animation: none; }}
        .sp-semaforo, .stButton button, .stFormSubmitButton button, .stDownloadButton button {{ transition: none; }}
      }}
    </style>""", unsafe_allow_html=True)


def cabecalho(titulo: str, subtitulo: str) -> None:
    st.markdown(f"<h1 style='margin:0;color:{tema.VERMELHO_ESCURO}'>SomPrev Risk</h1>"
                f"<div style='color:{tema.CINZA_MEDIO};margin-bottom:6px'>Inteligência preditiva de risco para "
                f"frotas agrícolas · Challenge FIAP + Sompo Seguros</div>"
                f"<h3 style='margin-top:10px'>{titulo}</h3><div class='sp-sub'>{subtitulo}</div>",
                unsafe_allow_html=True)


def pill(classe: str) -> str:
    return (f"<span class='sp-pill' style='background:{tema.RISCO[classe]}'>"
            f"{regras.EMOJI_CLASSE[classe]} Risco {regras.ROTULO_CLASSE[classe]}</span>")


def cartao(rotulo: str, valor: str, sub: str = "") -> None:
    st.markdown(f"<div class='sp-cartao'><div class='sp-rotulo'>{rotulo}</div><div class='sp-valor'>{valor}</div>"
                f"<div class='sp-sub'>{sub}</div></div>", unsafe_allow_html=True)


def semaforo(score: int, classe: str, recomendacao: str) -> None:
    st.markdown(f"<div class='sp-semaforo' style='background:{tema.RISCO[classe]}'>"
                f"<div style='font-size:14px;opacity:.9'>SCORE DE RISCO (0–100)</div>"
                f"<div class='num'>{score}</div>"
                f"<div style='font-size:22px;font-weight:700;margin:6px 0'>{regras.EMOJI_CLASSE[classe]} "
                f"Risco {regras.ROTULO_CLASSE[classe]}</div>"
                f"<div style='font-size:16px'>{recomendacao}</div></div>", unsafe_allow_html=True)


def cartao_alerta(a: dict, mostrar_equip: bool = True) -> None:
    cor = tema.RISCO.get(a["nivel"], tema.CINZA_MEDIO)
    equip = f"<b>{a['equipamento_id']}</b> · " if mostrar_equip else ""
    status = {"aberto": "🔔 aberto", "reconhecido": "👁 reconhecido", "resolvido": "✅ resolvido"}[a["status"]]
    ocorr = f" · {a['ocorrencias']} ocorrências" if a.get("ocorrencias", 1) > 1 else ""
    st.markdown(
        f"<div class='sp-alerta' style='border-left-color:{cor}'>"
        f"<div>{equip}<span class='sp-pill' style='background:{cor};font-size:11px'>"
        f"{regras.ROTULO_CLASSE[a['nivel']]}</span> <b>{a['mensagem']}</b> "
        f"<span class='sp-sub'>· {status}{ocorr} · desde {str(a['criado_em'])[:16]}</span></div>"
        f"<div style='margin:4px 0'>👉 {a['recomendacao']}</div>"
        f"<div class='sp-criterio'>Critério: {a['criterio']} · destino: "
        f"{ {'Tecnico': 'Técnico'}.get(a['perfil_destino'], a['perfil_destino']) }</div></div>",
        unsafe_allow_html=True)


def _layout(fig: go.Figure, titulo: str = "", altura: int = 340, y_titulo: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=15)), height=altura, margin=dict(l=10, r=10, t=48, b=10),
        plot_bgcolor="#fff", paper_bgcolor="#fff", font=dict(family="Roboto, Arial", color=tema.GRAFITE),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None), hovermode="x unified")
    fig.update_xaxes(showgrid=False, linecolor=tema.LINHA)
    fig.update_yaxes(gridcolor="#EFEFEF", zeroline=False, title=y_titulo)
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
                           text=texto, textposition="outside", hovertemplate="%{y}: %{x:.1f}<extra></extra>"))
    fig = _layout(fig, titulo, altura=altura)
    fig.update_layout(hovermode="closest", showlegend=False)
    vals = [float(v) for v in valores] or [0.0]
    folga = (max(vals) - min(0.0, min(vals))) * 0.28 or 1.0
    fig.update_xaxes(title=x_titulo, gridcolor="#EFEFEF",
                     range=[min(0.0, min(vals)) - (folga if min(vals) < 0 else 0), max(vals) + folga])
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig


def grafico_heatmap(matriz, titulo: str):
    fig = go.Figure(go.Heatmap(
        z=matriz.values, x=[rotulo_valor(c) for c in matriz.columns], y=list(matriz.index),
        colorscale=[[0, "#FFF5EB"], [0.5, "#FD8D3C"], [1, "#A63603"]], zmin=0, zmax=max(60, float(matriz.max().max())),
        text=matriz.round(0).values, texttemplate="%{text}", hovertemplate="%{y} · %{x}: score %{z:.1f}<extra></extra>",
        colorbar=dict(title="Score")))
    fig = _layout(fig, titulo, altura=330)
    fig.update_layout(hovermode="closest")
    return fig


def grafico_contribuicoes(contrib: dict, rotulos: dict, titulo: str = "Por que esse score?"):
    itens = sorted(contrib.items(), key=lambda kv: kv[1], reverse=True)
    itens = [i for i in itens if abs(i[1]) >= 0.5][:6] or itens[:3]
    nomes = [rotulos.get(k, k) for k, _ in itens]
    valores = [v for _, v in itens]
    cores = [tema.VERMELHO_INSTITUCIONAL if v > 0 else tema.RISCO["Baixo"] for v in valores]
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
