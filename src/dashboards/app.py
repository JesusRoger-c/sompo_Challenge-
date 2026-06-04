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

# O app vive em src/dashboards/, mas o tema central esta em src/scripts/.
# Adicionamos essa pasta ao path para reaproveitar a MESMA paleta do diagrama,
# evitando que dashboard e diagrama divirjam de cor com o tempo.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import tema

DB = os.path.join(os.path.dirname(__file__), "..", "database", "somprev_risk.db")
# Cores do semaforo de risco vindas do tema central (fonte unica de verdade).
CORES = tema.RISCO
RECS = {
    "Baixo": "✅ Operação liberada. Condições dentro do esperado.",
    "Medio": "⚠️ Operação com atenção. Reduza a velocidade e evite áreas úmidas.",
    "Alto": "🟠 Operação com restrições. Exija supervisão e replaneje a rota.",
    "Critico": "⛔ Operação NÃO recomendada. Suspenda e reavalie as condições.",
}

st.set_page_config(page_title="SomPrev Risk", page_icon="🌱", layout="wide")


# @st.cache_data: lemos o banco uma vez e reaproveitamos — sem reconsultar o
# SQLite a cada clique de aba, deixando a navegacao instantanea.
@st.cache_data
def carregar():
    # Um JOIN unico ja traz leitura + regiao + predicao: cada linha vira "leitura
    # com seu score e fatores", que e a unidade que as 3 telas precisam.
    con = sqlite3.connect(DB)
    leituras = pd.read_sql("""
        SELECT l.*, r.nome AS regiao_nome, r.estado,
               p.score_risco, p.classe_risco, p.prob_sinistro,
               p.fator_1, p.fator_2, p.fator_3, p.modelo_versao
        FROM leituras l
        JOIN regioes r   ON r.regiao_id  = l.regiao_id
        JOIN predicoes p ON p.leitura_id = l.leitura_id
    """, con)
    con.close()
    return leituras


def cabecalho():
    st.markdown(
        "<h1 style='margin-bottom:0'>🌱 SomPrev Risk</h1>"
        "<p style='color:#6f7a72;margin-top:2px'>Inteligência preditiva de risco para "
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
        col.markdown(
            f"<div style='background:{CORES[r['classe_risco']]};color:#fff;padding:14px;"
            f"border-radius:12px;text-align:center'><div>Risco {r['classe_risco']}</div>"
            f"<div style='font-size:30px;font-weight:700'>{r['taxa_sinistro_real']}%</div>"
            f"<div style='font-size:12px'>sinistro real</div></div>", unsafe_allow_html=True)
    st.info("Leituras de risco Baixo quase não viram sinistro; as de risco Crítico quase sempre. "
            "Essa separação comprova a confiabilidade do score.")

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
    df = carregar()
    aba = st.sidebar.radio("Perfil de acesso", ["🚜 Operador", "📊 Gestor", "🏢 Seguradora"])
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Modelo: {df['modelo_versao'].iloc[0]}  ·  {len(df):,} leituras".replace(",", "."))
    if aba.endswith("Operador"):
        view_operador(df)
    elif aba.endswith("Gestor"):
        view_gestor(df)
    else:
        view_seguradora(df)


if __name__ == "__main__":
    main()
