"""
=============================================================================
 SomPrev Risk  |  Dashboard funcional (Streamlit)
 Challenge FIAP + Sompo Seguros  -  Sprint 2
=============================================================================
Le o banco src/database/somprev_risk.db AO VIVO e apresenta 3 visoes, uma por
persona (Operador / Gestor / Seguradora), com semaforo de risco, mapa de
calor por regiao, ranking da frota e trilha de auditoria.

Como rodar (a partir da raiz do repositorio):
    pip install -r config/requirements.txt
    python src/scripts/popular_banco.py    # garante o banco populado
    streamlit run src/dashboards/app.py
"""

import os
import sys
import sqlite3
import pandas as pd
import streamlit as st

# O app reside em src/dashboards/ e o tema central em src/scripts/. Essa pasta e
# adicionada ao path para reaproveitar a mesma paleta do diagrama, evitando
# divergencia de cor entre dashboard e diagrama.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import tema
import risco_utils as ru   # premissas economicas (estimar_economia) e rotulos

DB = os.path.join(os.path.dirname(__file__), "..", "database", "somprev_risk.db")
# Cores do semaforo de risco vindas do tema central (fonte unica de verdade).
CORES = tema.RISCO


def fmt_reais(v):
    """Formata um valor em R$ de forma compacta (mi/mil) para os cards de KPI."""
    if v >= 1_000_000:
        return f"R$ {v/1_000_000:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if v >= 1_000:
        return f"R$ {v/1_000:,.0f} mil".replace(",", ".")
    return f"R$ {v:,.0f}".replace(",", ".")


def card_prejuizo_evitavel(n_alertas):
    """Renderiza o card 'Prejuízo evitável estimado' (destaque vinho/grafite,
    NÃO no vermelho de risco) com a fórmula em letra pequena."""
    economia = ru.estimar_economia(n_alertas)
    custo = f"R$ {ru.CUSTO_MEDIO_SINISTRO/1000:.0f} mil"
    st.markdown(
        f"<div style='background:{tema.GRAFITE};color:#fff;padding:16px 18px;border-radius:12px;"
        f"border-left:5px solid {tema.VERMELHO_ESCURO}'>"
        f"<div style='font-size:13px;opacity:.85'>Prejuízo evitável estimado</div>"
        f"<div style='font-family:\"Roboto Mono\",monospace;font-size:32px;font-weight:600;margin:2px 0'>{fmt_reais(economia)}</div>"
        f"<div style='font-size:11px;opacity:.7'>{n_alertas:,} alertas Alto/Crítico × {custo} × "
        f"{int(ru.TAXA_PREVENCAO*100)}% (prevenção). Premissas ajustáveis.</div></div>".replace(",", "."),
        unsafe_allow_html=True)
RECS = {
    "Baixo": "✅ Operação liberada. Condições dentro do esperado.",
    "Medio": "⚠️ Operação com atenção. Reduza a velocidade e evite áreas úmidas.",
    "Alto": "🟠 Operação com restrições. Exija supervisão e replaneje a rota.",
    "Critico": "⛔ Operação NÃO recomendada. Suspenda e reavalie as condições.",
}

st.set_page_config(page_title="SomPrev Risk", page_icon="🔎", layout="wide")


def aplicar_tema():
    """Injeta a identidade visual (fontes Roboto + cores Sompo) via CSS custom.

    O Streamlit nao expoe um tema de marca diretamente; a injecao de um bloco
    <style> aplica a fonte e o vermelho institucional sem reescrever os
    componentes. As cores derivam do tema central (fonte unica de definicao).
    """
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@600;700&family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@500;600&display=swap');
      html, body, [class*="css"] {{ font-family:'Roboto',Arial,Helvetica,sans-serif; }}
      h1,h2,h3 {{ font-family:'Roboto Slab',Georgia,serif; letter-spacing:-.01em; }}
      /* numeros das metricas em monospace -> cara de produto de dados */
      [data-testid="stMetricValue"] {{ font-family:'Roboto Mono','Courier New',monospace; }}
      /* acento da marca: barra vermelha no topo e titulo institucional */
      .block-container {{ border-top:3px solid {tema.VERMELHO_INSTITUCIONAL}; }}
      h1 {{ color:{tema.VERMELHO_ESCURO}; }}
    </style>
    """, unsafe_allow_html=True)


# @st.cache_data: o banco e lido uma unica vez e reaproveitado — sem reconsultar
# o SQLite a cada troca de aba, o que mantem a navegacao instantanea.
@st.cache_data
def carregar():
    # Um unico JOIN reune leitura + regiao + predicao: cada linha equivale a uma
    # "leitura com seu score e fatores", unidade que as tres telas utilizam.
    con = sqlite3.connect(DB)
    # O JOIN inclui equipamentos para trazer o TIPO (Trator/Colheitadeira/
    # Pulverizador), necessario para o filtro por tipo de equipamento na sidebar.
    leituras = pd.read_sql("""
        SELECT l.*, r.nome AS regiao_nome, r.estado,
               e.tipo AS equip_tipo, e.modelo AS equip_modelo,
               p.score_risco, p.classe_risco, p.prob_sinistro,
               p.fator_1, p.fator_2, p.fator_3, p.modelo_versao
        FROM leituras l
        JOIN regioes r       ON r.regiao_id      = l.regiao_id
        JOIN equipamentos e  ON e.equipamento_id = l.equipamento_id
        JOIN predicoes p     ON p.leitura_id     = l.leitura_id
    """, con)
    con.close()
    return leituras


def filtros_sidebar(df):
    """Filtros globais (região, tipo de equipamento, classe de risco) aplicados
    às três visões. Padrão 'Todos' = sem filtro. Retorna o df já filtrado.

    Os filtros são globais e ficam na barra lateral para que um recorte (ex.: só
    Colheitadeiras de Barreiras em risco Crítico) mantenha KPIs, gráficos e
    tabelas coerentes entre si — todos derivam do mesmo df filtrado.
    """
    st.sidebar.markdown("### Filtros")
    regioes = ["Todas"] + sorted(df["regiao_nome"].dropna().unique().tolist())
    tipos = ["Todos"] + sorted(df["equip_tipo"].dropna().unique().tolist())
    classes = ["Todas", "Baixo", "Medio", "Alto", "Critico"]
    f_reg = st.sidebar.selectbox("Região", regioes)
    f_tipo = st.sidebar.selectbox("Tipo de equipamento", tipos)
    f_classe = st.sidebar.selectbox("Classe de risco", classes)

    out = df
    if f_reg != "Todas":
        out = out[out["regiao_nome"] == f_reg]
    if f_tipo != "Todos":
        out = out[out["equip_tipo"] == f_tipo]
    if f_classe != "Todas":
        out = out[out["classe_risco"] == f_classe]
    return out


def cabecalho():
    aplicar_tema()  # fontes Roboto + cores Sompo antes de desenhar o cabecalho
    st.markdown(
        f"<h1 style='margin-bottom:0;color:{tema.VERMELHO_ESCURO}'>SomPrev Risk</h1>"
        f"<p style='color:{tema.CINZA_MEDIO};margin-top:2px'>Inteligência preditiva de risco para "
        "frotas agrícolas · Challenge FIAP + Sompo Seguros</p>", unsafe_allow_html=True)


def pill(classe):
    return (f"<span style='background:{CORES[classe]};color:#fff;padding:4px 14px;"
            f"border-radius:20px;font-weight:700'>Risco {classe}</span>")


def view_operador(df):
    st.subheader("🚜 Visão do Operador — risco do equipamento em campo")
    equipamentos = sorted(df["equipamento_id"].unique())
    eq = st.selectbox("Equipamento", equipamentos)
    sub = df[df["equipamento_id"] == eq].sort_values("data_hora").iloc[-1]

    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("Score de risco (0–100)", int(sub["score_risco"]))
        st.markdown(pill(sub["classe_risco"]), unsafe_allow_html=True)
        st.markdown(f"#### {RECS[sub['classe_risco']]}")
    with c2:
        st.markdown("**Leitura atual dos sensores**")
        m = st.columns(4)
        m[0].metric("Umidade solo", f"{sub['umidade_solo_pct']:.0f}%")
        m[1].metric("Chuva 24h", f"{sub['precipitacao_24h_mm']:.0f} mm")
        m[2].metric("Dist. água", f"{sub['distancia_corpo_dagua_m']:.0f} m")
        m[3].metric("Declividade", f"{sub['declividade_graus']:.0f}°")
        st.markdown("**Por que esse risco? (top fatores)**")
        st.write(f"1. {sub['fator_1']}  ·  2. {sub['fator_2']}  ·  3. {sub['fator_3']}")


def view_gestor(df):
    st.subheader("📊 Visão do Gestor — frota e regiões")
    k = st.columns(4)
    k[0].metric("Frota monitorada", df["equipamento_id"].nunique())
    k[1].metric("Leituras", f"{len(df):,}".replace(",", "."))
    alto = df["classe_risco"].isin(["Alto", "Critico"]).sum()
    k[2].metric("Risco Alto/Crítico", f"{alto:,}".replace(",", "."))
    k[3].metric("Score médio", f"{df['score_risco'].mean():.1f}")

    card_prejuizo_evitavel(int(alto))  # recalcula conforme os filtros ativos
    st.markdown("")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Risco médio por região**")
        reg = (df.groupby(["regiao_nome", "estado"])["score_risco"].mean()
                 .round(1).sort_values(ascending=False).reset_index())
        st.bar_chart(reg.set_index("regiao_nome")["score_risco"])
    with c2:
        st.markdown("**Distribuição por faixa de risco**")
        dist = df["classe_risco"].value_counts().reindex(["Baixo", "Medio", "Alto", "Critico"])
        st.bar_chart(dist)

    st.markdown("**Ranking da frota por risco médio**")
    rank = (df.groupby("equipamento_id")
              .agg(score_medio=("score_risco", "mean"),
                   criticas=("classe_risco", lambda s: (s == "Critico").sum()))
              .round(1).sort_values("score_medio", ascending=False).head(10).reset_index())
    st.dataframe(rank, use_container_width=True)


def view_seguradora(df):
    st.subheader("🏢 Visão da Seguradora — validação e auditoria")
    st.markdown("**Validação: taxa real de sinistro por faixa de risco prevista**")
    val = (df.groupby("classe_risco")
             .agg(leituras=("leitura_id", "count"),
                  taxa_sinistro_real=("houve_sinistro", lambda s: round(100 * s.mean(), 1)))
             .reindex(["Baixo", "Medio", "Alto", "Critico"]).reset_index())
    cols = st.columns(4)
    for col, (_, r) in zip(cols, val.iterrows()):
        # com filtro de classe, faixas ausentes ficam sem leitura -> mostra "—"
        taxa = "—" if pd.isna(r["taxa_sinistro_real"]) else f"{r['taxa_sinistro_real']}%"
        col.markdown(
            f"<div style='background:{CORES[r['classe_risco']]};color:#fff;padding:14px;"
            f"border-radius:12px;text-align:center'><div>Risco {r['classe_risco']}</div>"
            f"<div style='font-size:30px;font-weight:700'>{taxa}</div>"
            f"<div style='font-size:12px'>sinistro real</div></div>", unsafe_allow_html=True)
    st.info("Leituras de risco Baixo quase não viram sinistro; as de risco Crítico quase sempre. "
            "Essa separação comprova a confiabilidade do score.")

    alto = int(df["classe_risco"].isin(["Alto", "Critico"]).sum())
    card_prejuizo_evitavel(alto)  # recalcula conforme os filtros ativos
    st.markdown("")

    st.markdown("**Trilha de auditoria — alertas de maior risco**")
    audit = (df[df["classe_risco"].isin(["Alto", "Critico"])]
             .sort_values("score_risco", ascending=False)
             [["equipamento_id", "regiao_nome", "score_risco", "classe_risco",
               "fator_1", "modelo_versao", "data_hora"]].head(20))
    st.dataframe(audit, use_container_width=True)


def main():
    cabecalho()
    if not os.path.exists(DB):
        st.error("Banco não encontrado. Rode antes:  python src/scripts/popular_banco.py")
        return
    df_total = carregar()
    aba = st.sidebar.radio("Perfil de acesso", ["🚜 Operador", "📊 Gestor", "🏢 Seguradora"])
    st.sidebar.markdown("---")
    df = filtros_sidebar(df_total)  # filtros globais aplicados às 3 visões
    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Modelo: {df_total['modelo_versao'].iloc[0]}  ·  "
        f"{len(df):,}/{len(df_total):,} leituras".replace(",", "."))

    if df.empty:
        st.warning("Nenhuma leitura para os filtros selecionados. Ajuste os filtros na barra lateral.")
        return
    if aba.endswith("Operador"):
        view_operador(df)
    elif aba.endswith("Gestor"):
        view_gestor(df)
    else:
        view_seguradora(df)


if __name__ == "__main__":
    main()
