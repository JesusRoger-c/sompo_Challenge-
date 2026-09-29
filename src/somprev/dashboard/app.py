"""
Dashboard do SomPrev Risk (Streamlit) - uma visao por perfil de usuario.

    Operador .......... "posso operar agora?" - semaforo, recomendacao, causas, alertas
    Tecnico ........... fila de manutencao preventiva e registro de manutencao
    Gestor ............ tendencias por regiao/operacao/equipamento, alertas, regras
    Seguradora ........ validacao do modelo, tendencias de carteira e auditoria

Seguranca: login com senha em hash (PBKDF2) + bloqueio por tentativas, perfil
fixo por usuario, permissoes checadas em cada acao, expiracao de sessao por
inatividade e registro de todas as acoes na trilha de auditoria encadeada.

Como rodar:  python scripts/run.py dashboard
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Permite rodar tanto via `python scripts/run.py dashboard` quanto via `streamlit run`.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from somprev import config, regras  # noqa: E402
from somprev.banco import repositorio as repo  # noqa: E402
from somprev.banco.conexao import banco_existe, sessao, transacao  # noqa: E402
from somprev.dashboard import cliente_api  # noqa: E402
from somprev.dashboard import componentes as ui  # noqa: E402
from somprev.esquema import ROTULOS, rotulo_valor  # noqa: E402
from somprev.excecoes import SomPrevErro  # noqa: E402
from somprev.relatorios import tendencias  # noqa: E402
from somprev.seguranca import auditoria, autenticacao  # noqa: E402

st.set_page_config(page_title="SomPrev Risk", page_icon="🛡️", layout="wide")
ui.aplicar_estilo()

INATIVIDADE_MAX = timedelta(minutes=30)
FAIXAS = regras.carregar_regras()["faixas_score"]


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------
@st.cache_data(ttl=15, show_spinner="Atualizando dados…")
def carregar_dados():
    """O dashboard e um cliente da API (rotas de consulta) - nao ha leitura de banco por fora
    dela. Ver o aviso no topo de dashboard/cliente_api.py e de api/app.py."""
    leituras = cliente_api.leituras_risco()
    alertas = cliente_api.alertas()
    equipamentos = cliente_api.equipamentos()
    manutencoes = cliente_api.manutencoes()
    return leituras, alertas, equipamentos, manutencoes


def acao_registrada(evento: str, **detalhes) -> None:
    """Registra uma acao do usuario na trilha de auditoria (transacao propria)."""
    with sessao() as conn, transacao(conn):
        auditoria.registrar(conn, evento, ator=st.session_state["login"], perfil=st.session_state["perfil"],
                            detalhes=detalhes or None)


def permitido(permissao: str) -> bool:
    return autenticacao.tem_permissao(st.session_state["perfil"], permissao)


# ---------------------------------------------------------------------------
# Login e sessao
# ---------------------------------------------------------------------------
def tela_login() -> None:
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        st.markdown(f"<h1 style='color:#A4161A;margin-bottom:0'>SomPrev Risk</h1>"
                    "<div class='sp-sub'>Inteligência preditiva de risco para frotas agrícolas</div><br>",
                    unsafe_allow_html=True)
        with st.form("form_login", clear_on_submit=False):
            login = st.text_input("Usuário", max_chars=40)
            senha = st.text_input("Senha", type="password", max_chars=128)
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
        if entrar:
            try:
                with sessao() as conn:
                    usuario = autenticacao.autenticar(conn, login.strip(), senha)
            except SomPrevErro as erro:
                st.error(erro.mensagem)
                return
            st.session_state.update(autenticado=True, login=usuario["login"], perfil=usuario["perfil"],
                                    nome=usuario["nome"], ultimo_uso=datetime.now())
            st.rerun()
        st.caption("Acesso restrito. Tentativas são registradas na trilha de auditoria; após "
                   f"{config.LOGIN_MAX_TENTATIVAS} erros a conta é bloqueada por {config.LOGIN_BLOQUEIO_MINUTOS} min.")


def sair(motivo: str = "logout") -> None:
    try:
        acao_registrada("LOGOUT", motivo=motivo)
    finally:
        for chave in list(st.session_state):
            del st.session_state[chave]


def sessao_valida() -> bool:
    if not st.session_state.get("autenticado"):
        return False
    if datetime.now() - st.session_state.get("ultimo_uso", datetime.min) > INATIVIDADE_MAX:
        sair("sessao expirada por inatividade")
        st.warning("Sessão expirada por inatividade. Entre novamente.")
        return False
    st.session_state["ultimo_uso"] = datetime.now()
    return True


# ---------------------------------------------------------------------------
# Filtros globais
# ---------------------------------------------------------------------------
def filtros(df: pd.DataFrame, chave: str, periodo_padrao: int = 30) -> pd.DataFrame:
    """Linha de filtros acima dos graficos: periodo, regiao, operacao e tipo de maquina."""
    c1, c2, c3, c4 = st.columns([1, 1.4, 1.4, 1.4])
    dias = c1.selectbox("Período", [7, 14, 30, 60, 90, 184], index=[7, 14, 30, 60, 90, 184].index(periodo_padrao),
                        format_func=lambda d: f"Últimos {d} dias" if d < 184 else "Tudo (6 meses)", key=f"{chave}_p")
    regioes = c2.multiselect("Região", [r for r in ui.ORDEM_REGIOES if r in set(df["regiao_nome"])],
                             key=f"{chave}_r", placeholder="Todas")
    operacoes = c3.multiselect("Operação", ui.ORDEM_OPERACOES, format_func=rotulo_valor, key=f"{chave}_o",
                               placeholder="Todas")
    tipos = c4.multiselect("Tipo de equipamento", ui.ORDEM_TIPOS, key=f"{chave}_t", placeholder="Todos")
    fim = df["data_hora"].max()
    out = df[df["data_hora"] > fim - pd.Timedelta(days=dias)]
    if regioes:
        out = out[out["regiao_nome"].isin(regioes)]
    if operacoes:
        out = out[out["tipo_operacao"].isin(operacoes)]
    if tipos:
        out = out[out["equip_tipo"].isin(tipos)]
    return out


def acoes_alerta(alertas: pd.DataFrame, chave: str) -> None:
    """Botoes de ciclo de vida do alerta (reconhecer / resolver), conforme permissao."""
    pode_rec, pode_res = permitido("reconhecer_alerta"), permitido("resolver_alerta")
    if alertas.empty or not (pode_rec or pode_res):
        return
    with st.expander("Atualizar status de um alerta"):
        opcoes = {f"#{a.alerta_id} · {a.equipamento_id} · {a.codigo} ({a.status})": a
                  for a in alertas.itertuples()}
        escolha = st.selectbox("Alerta", list(opcoes), key=f"{chave}_sel")
        comentario = st.text_input("Comentário (opcional)", max_chars=200, key=f"{chave}_com")
        c1, c2 = st.columns(2)
        novo = None
        if pode_rec and c1.button("👁 Reconhecer", key=f"{chave}_rec", width="stretch"):
            novo = "reconhecido"
        if pode_res and c2.button("✅ Resolver", key=f"{chave}_res", width="stretch"):
            novo = "resolvido"
        if novo:
            alerta = opcoes[escolha]
            try:
                with sessao() as conn, transacao(conn):
                    repo.atualizar_status_alerta(conn, int(alerta.alerta_id), novo, st.session_state["login"],
                                                 comentario or None, datetime.now().isoformat(timespec="seconds"))
                    auditoria.registrar(conn, "ALERTA_ATUALIZADO", ator=st.session_state["login"],
                                        perfil=st.session_state["perfil"], equipamento_id=alerta.equipamento_id,
                                        leitura_id=int(alerta.leitura_id),
                                        detalhes={"alerta_id": int(alerta.alerta_id), "de": alerta.status,
                                                  "para": novo, "comentario": comentario or None})
                st.cache_data.clear()
                st.success(f"Alerta #{alerta.alerta_id} → {novo}.")
                st.rerun()
            except SomPrevErro as erro:
                st.error(erro.mensagem)


# ---------------------------------------------------------------------------
# Visao: OPERADOR
# ---------------------------------------------------------------------------
def visao_operador(df: pd.DataFrame, alertas: pd.DataFrame) -> None:
    ui.cabecalho("🚜 Posso operar agora?", "Risco da sua máquina na leitura mais recente, com o que fazer e por quê.")
    ultimas = df.sort_values("data_hora").groupby("equipamento_id").tail(1).sort_values("score_risco", ascending=False)
    rotulo = {r.equipamento_id: f"{r.equipamento_id} · {r.equip_tipo} · {r.regiao_nome} · "
                                 f"{regras.EMOJI_CLASSE[r.classe_risco]} {r.score_risco}" for r in ultimas.itertuples()}
    eq = st.selectbox("Equipamento", list(rotulo), format_func=rotulo.get)
    hist = df[df["equipamento_id"] == eq].sort_values("data_hora")
    atual = hist.iloc[-1]
    contrib = json.loads(atual["explicacao_json"] or "{}")
    fatores = [atual["fator_1"], atual["fator_2"], atual["fator_3"]]

    c1, c2 = st.columns([1.05, 1])
    with c1:
        ui.semaforo(int(atual["score_risco"]), atual["classe_risco"], regras.recomendacao(atual["classe_risco"], fatores))
        st.caption(f"Leitura de {atual['data_hora']:%d/%m/%Y %H:%M} · {rotulo_valor(atual['tipo_operacao'])} · "
                   f"{atual['regiao_nome']} · modelo {atual['modelo_versao']}")
        if atual["qualidade_status"] == "CORRIGIDO":
            st.info(f"ℹ️ Dado corrigido automaticamente pela qualidade de dados: {atual['qualidade_obs']}")
    with c2:
        st.plotly_chart(ui.grafico_contribuicoes(contrib, ROTULOS, "Por que esse score? (contribuição de cada fator)"),
                        width="stretch")

    st.markdown("**Leitura dos sensores**")
    m = st.columns(6)
    m[0].metric("Umidade do solo", f"{atual['umidade_solo_pct']:.0f}%")
    m[1].metric("Chuva 24h", f"{atual['precipitacao_24h_mm']:.0f} mm")
    m[2].metric("Distância da água", f"{atual['distancia_corpo_dagua_m']:.0f} m")
    m[3].metric("Declividade", f"{atual['declividade_graus']:.0f}°")
    m[4].metric("Carga", f"{atual['carga_pct']:.0f}%")
    m[5].metric("Horas s/ manutenção", f"{atual['horas_desde_manutencao']:.0f} h")

    abertos = alertas[(alertas["equipamento_id"] == eq) & (alertas["status"] != "resolvido")]
    st.markdown(f"**Alertas ativos deste equipamento ({len(abertos)})**")
    if abertos.empty:
        st.success("Nenhum alerta ativo para este equipamento.")
    for a in abertos.to_dict("records"):
        ui.cartao_alerta(a, mostrar_equip=False)
    acoes_alerta(abertos, "op")
    st.plotly_chart(ui.grafico_score_equipamento(hist.tail(40), f"Histórico recente do score — {eq}"),
                    width="stretch")


# ---------------------------------------------------------------------------
# Visao: TECNICO DE MANUTENCAO
# ---------------------------------------------------------------------------
def visao_tecnico(df: pd.DataFrame, alertas: pd.DataFrame, equipamentos: pd.DataFrame,
                  manutencoes: pd.DataFrame) -> None:
    ui.cabecalho("🔧 Fila de manutenção preventiva",
                 "Equipamentos priorizados por manutenção vencida, desgaste e risco operacional recente.")
    ultima = df.sort_values("data_hora").groupby("equipamento_id").tail(1).set_index("equipamento_id")
    fila = equipamentos.set_index("equipamento_id")[["tipo", "modelo", "regiao_base", "intervalo_manutencao_h"]].copy()
    fila["horas_desde_manutencao"] = ultima["horas_desde_manutencao"]
    fila["idade_anos"] = ultima["idade_equipamento_anos"]
    fila["uso_do_intervalo"] = fila["horas_desde_manutencao"] / fila["intervalo_manutencao_h"]
    recente = df[df["data_hora"] > df["data_hora"].max() - pd.Timedelta(days=14)]
    fila["score_medio_14d"] = recente.groupby("equipamento_id")["score_risco"].mean()
    ab = alertas[(alertas["status"] != "resolvido") & (alertas["tipo"] == "MANUTENCAO")]
    fila["alertas_manutencao"] = ab.groupby("equipamento_id")["alerta_id"].count()
    fila = fila.fillna({"alertas_manutencao": 0, "score_medio_14d": 0})
    # Prioridade explicita: manutencao vencida pesa mais, depois desgaste e risco recente.
    fila["prioridade"] = (50 * fila["uso_do_intervalo"].clip(0, 2) + 20 * (fila["alertas_manutencao"] > 0)
                          + 1.0 * fila["idade_anos"].fillna(0) + 0.3 * fila["score_medio_14d"]).round(1)
    fila = fila.sort_values("prioridade", ascending=False).reset_index()

    k = st.columns(4)
    with k[0]:
        ui.cartao("Manutenção vencida", str(int((fila["horas_desde_manutencao"] >= 450).sum())), "≥ 450 h desde a revisão")
    with k[1]:
        ui.cartao("Alertas de manutenção", str(len(ab)), "abertos ou reconhecidos")
    with k[2]:
        ui.cartao("Idade média da frota", f"{fila['idade_anos'].mean():.1f} anos", f"{len(fila)} equipamentos")
    with k[3]:
        ui.cartao("Manutenções registradas", str(len(manutencoes)), "no sistema")

    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.markdown("**Fila priorizada**")
        st.dataframe(fila.head(15)[["equipamento_id", "tipo", "regiao_base", "horas_desde_manutencao",
                                    "intervalo_manutencao_h", "idade_anos", "alertas_manutencao",
                                    "score_medio_14d", "prioridade"]],
                     hide_index=True, width="stretch", column_config={
                         "equipamento_id": "Equip.", "tipo": "Tipo", "regiao_base": "Região",
                         "horas_desde_manutencao": st.column_config.ProgressColumn(
                             "Horas s/ manutenção", min_value=0, max_value=900, format="%d h"),
                         "intervalo_manutencao_h": st.column_config.NumberColumn("Intervalo (h)", format="%d"),
                         "idade_anos": st.column_config.NumberColumn("Idade", format="%.1f"),
                         "alertas_manutencao": st.column_config.NumberColumn("Alertas", format="%d"),
                         "score_medio_14d": st.column_config.NumberColumn("Score 14d", format="%.0f"),
                         "prioridade": st.column_config.NumberColumn("Prioridade", format="%.0f")})
        st.caption("Prioridade = 50 × (horas/intervalo, até 2) + 20 se há alerta de manutenção + idade (anos) "
                   "+ 0,3 × score médio de 14 dias.")
    with c2:
        top = fila.head(12)
        cores = [ui.tema.RISCO["Critico"] if h >= 450 else ui.tema.RISCO["Alto"] if h >= 300 else ui.tema.CINZA_MEDIO
                 for h in top["horas_desde_manutencao"]]
        fig = ui.grafico_barras_h(top["equipamento_id"], top["horas_desde_manutencao"], cores,
                                  "Horas desde a última manutenção", "Horas",
                                  [f"{h:.0f} h" for h in top["horas_desde_manutencao"]], altura=420)
        fig.add_vline(x=450, line_dash="dash", line_color=ui.tema.GRAFITE,
                      annotation_text="limite 450 h", annotation_position="top")
        st.plotly_chart(fig, width="stretch")

    st.markdown(f"**Alertas de manutenção ativos ({len(ab)})**")
    for a in ab.head(8).to_dict("records"):
        ui.cartao_alerta(a)
    acoes_alerta(ab, "tec")

    if permitido("registrar_manutencao"):
        with st.form("manutencao", clear_on_submit=True):
            st.markdown("**Registrar manutenção realizada**")
            c1, c2 = st.columns([1, 2])
            eq = c1.selectbox("Equipamento", fila["equipamento_id"])
            descricao = c2.text_input("Serviço executado", max_chars=300,
                                      placeholder="Ex.: troca de óleo, revisão de freios e sistema hidráulico")
            relacionados = ab[ab["equipamento_id"] == eq]
            fechar = st.checkbox("Resolver os alertas de manutenção deste equipamento", value=True)
            if st.form_submit_button("Registrar", type="primary"):
                if len(descricao.strip()) < 5:
                    st.error("Descreva o serviço executado (mínimo 5 caracteres).")
                else:
                    agora = datetime.now().isoformat(timespec="seconds")
                    with sessao() as conn, transacao(conn):
                        mid = repo.registrar_manutencao(conn, eq, st.session_state["login"], descricao.strip(),
                                                        None, agora)
                        fechados = []
                        if fechar:
                            for a in relacionados.itertuples():
                                repo.atualizar_status_alerta(conn, int(a.alerta_id), "resolvido",
                                                             st.session_state["login"], f"Manutenção #{mid}", agora)
                                fechados.append(int(a.alerta_id))
                        auditoria.registrar(conn, "MANUTENCAO_REGISTRADA", ator=st.session_state["login"],
                                            perfil=st.session_state["perfil"], equipamento_id=eq,
                                            detalhes={"manutencao_id": mid, "descricao": descricao.strip(),
                                                      "alertas_resolvidos": fechados})
                    st.cache_data.clear()
                    st.success(f"Manutenção #{mid} registrada para {eq}; {len(fechados)} alerta(s) resolvido(s).")


# ---------------------------------------------------------------------------
# Visao: GESTOR
# ---------------------------------------------------------------------------
def visao_gestor(df_total: pd.DataFrame, alertas: pd.DataFrame, equipamentos: pd.DataFrame) -> None:
    ui.cabecalho("📊 Gestão da frota", "Tendências de risco por região, operação e equipamento; alertas e regras.")
    df = filtros(df_total, "gestor")
    if df.empty:
        st.warning("Nenhuma leitura para os filtros selecionados.")
        return
    abertos = alertas[(alertas["status"] != "resolvido") & alertas["equipamento_id"].isin(df["equipamento_id"])]
    alto = int(df["classe_risco"].isin(["Alto", "Critico"]).sum())
    k = st.columns(5)
    with k[0]:
        ui.cartao("Frota monitorada", str(df["equipamento_id"].nunique()), f"{len(df):,} leituras".replace(",", "."))
    with k[1]:
        ui.cartao("Score médio", f"{df['score_risco'].mean():.0f}", "probabilidade média de sinistro")
    with k[2]:
        ui.cartao("Alto/Crítico", f"{alto / len(df):.0%}", f"{alto:,} leituras".replace(",", "."))
    with k[3]:
        ui.cartao("Alertas ativos", str(len(abertos)),
                  f"{int((abertos['nivel'] == 'Critico').sum())} críticos")
    with k[4]:
        eco = regras.estimar_economia(alto)
        ui.cartao("Prejuízo evitável*", f"R$ {eco / 1e6:.1f} mi".replace(".", ","),
                  "estimativa com premissas ajustáveis")

    abas = st.tabs(["📈 Tendências", "🗺️ Região × operação", "🏆 Ranking da frota", "🔔 Alertas", "⚙️ Regras",
                    "📄 Relatório"])
    with abas[0]:
        c1, c2 = st.columns([1, 1])
        dim = c1.radio("Agrupar por", ["regiao_nome", "tipo_operacao", "equip_tipo", "equipamento_id"],
                       horizontal=True, format_func=lambda d: tendencias.DIMENSOES[d])
        medida = c2.radio("Medida", ["score_medio", "pct_alto_critico"], horizontal=True,
                          format_func=lambda m: "Score médio" if m == "score_medio" else "% em Alto/Crítico")
        base = df
        if dim == "equipamento_id":
            # Comparar 40 linhas seria ilegivel: por padrao, os 5 equipamentos de maior risco recente.
            mais_risco = tendencias.variacao_recente(df, "equipamento_id")["equipamento_id"].head(5).tolist()
            escolhidos = st.multiselect("Equipamentos (até 6)", sorted(df["equipamento_id"].unique()),
                                        default=mais_risco, max_selections=6)
            base = df[df["equipamento_id"].isin(escolhidos or mais_risco)]
        tab = tendencias.tendencia(base, dim)
        if medida == "pct_alto_critico":
            tab["pct_alto_critico"] = tab["pct_alto_critico"] * 100
        st.plotly_chart(ui.grafico_tendencia(tab, dim, medida, f"Tendência semanal — {tendencias.DIMENSOES[dim]}",
                                             "Score médio" if medida == "score_medio" else "% das leituras"),
                        width="stretch")
        var = tendencias.variacao_recente(base, dim)
        var[dim] = var[dim].map(rotulo_valor)
        st.dataframe(var, hide_index=True, width="stretch", column_config={
            dim: tendencias.DIMENSOES[dim], "score_recente": st.column_config.NumberColumn("Score últ. 14 dias", format="%.1f"),
            "score_anterior": st.column_config.NumberColumn("Score 14 dias antes", format="%.1f"),
            "pct_alto_critico_recente": st.column_config.NumberColumn("% Alto/Crítico", format="percent"),
            "leituras_recentes": "Leituras", "variacao": st.column_config.NumberColumn("Variação", format="%+.1f"),
            "tendencia": "Tendência"})
        st.markdown("**Insights automáticos**")
        for frase in tendencias.insights(df, alertas):
            st.markdown(f"- {frase}")
    with abas[1]:
        st.plotly_chart(ui.grafico_heatmap(tendencias.matriz_regiao_operacao(df), "Score médio por região e operação"),
                        width="stretch")
        fat = tendencias.fatores_predominantes(df, "regiao_nome")
        if not fat.empty:
            piv = fat.pivot_table(index="regiao_nome", columns="fator", values="leituras", fill_value=0)
            st.markdown("**Causa nº 1 das leituras Alto/Crítico, por região**")
            st.dataframe(piv, width="stretch")
    with abas[2]:
        rank = tendencias.ranking_equipamentos(df, alertas, dias=min(30, int((df["data_hora"].max()
                                                                                 - df["data_hora"].min()).days) + 1))
        st.dataframe(rank.head(20), hide_index=True, width="stretch", column_config={
            "equipamento_id": "Equip.", "tipo": "Tipo", "regiao": "Região", "leituras": "Leituras",
            "score_medio": st.column_config.ProgressColumn("Score médio", min_value=0, max_value=100, format="%.0f"),
            "pior_score": "Pior score",
            "pct_alto_critico": st.column_config.NumberColumn("% Alto/Crítico", format="percent"),
            "horas_desde_manutencao": st.column_config.NumberColumn("Horas s/ manut.", format="%d"),
            "idade_anos": st.column_config.NumberColumn("Idade", format="%.1f"), "tendencia": "Tendência",
            "alertas_abertos": "Alertas ativos"})
    with abas[3]:
        c1, c2, c3 = st.columns(3)
        f_status = c1.multiselect("Status", ["aberto", "reconhecido", "resolvido"], default=["aberto", "reconhecido"])
        f_tipo = c2.multiselect("Tipo", sorted(alertas["tipo"].unique()), placeholder="Todos")
        f_nivel = c3.multiselect("Nível", ["Medio", "Alto", "Critico"], format_func=rotulo_valor, placeholder="Todos")
        sel = alertas[alertas["equipamento_id"].isin(df["equipamento_id"])]
        if f_status:
            sel = sel[sel["status"].isin(f_status)]
        if f_tipo:
            sel = sel[sel["tipo"].isin(f_tipo)]
        if f_nivel:
            sel = sel[sel["nivel"].isin(f_nivel)]
        st.caption(f"{len(sel)} alertas")
        for a in sel.head(12).to_dict("records"):
            ui.cartao_alerta(a)
        acoes_alerta(sel[sel["status"] != "resolvido"], "gestor")
    with abas[4]:
        editor_regras()
    with abas[5]:
        st.markdown("Exportações do recorte filtrado (ficam registradas na auditoria).")
        rank = tendencias.ranking_equipamentos(df, alertas)
        c1, c2, c3 = st.columns(3)
        for col, (nome, dados) in zip((c1, c2, c3), [
                ("tendencia_regiao.csv", tendencias.tendencia(df, "regiao_nome")),
                ("tendencia_operacao.csv", tendencias.tendencia(df, "tipo_operacao")),
                ("ranking_equipamentos.csv", rank)]):
            if col.download_button(f"⬇️ {nome}", dados.to_csv(index=False).encode("utf-8"), nome, "text/csv",
                                   width="stretch"):
                acao_registrada("RELATORIO_EXPORTADO", arquivo=nome, linhas=len(dados))
        relatorio_md = config.RELATORIOS_DIR / "relatorio_tendencias.md"
        if relatorio_md.exists():
            with st.expander("Relatório gerencial completo (gerado pelo pipeline)"):
                st.markdown(relatorio_md.read_text(encoding="utf-8").split("## Tendência por região")[0])


def editor_regras() -> None:
    atual = regras.carregar_regras()
    st.markdown(f"**Versão em uso:** `{atual['versao']}` · atualizada por {atual.get('atualizado_por', '—')} "
                f"em {atual.get('atualizado_em', '—')}")
    st.markdown("**Faixas de score**  \n" + " · ".join(
        f"{regras.EMOJI_CLASSE[c]} {regras.ROTULO_CLASSE[c]} {lo}–{hi}" for c, (lo, hi) in atual["faixas_score"].items()))
    gat = pd.DataFrame([{"Código": g["codigo"], "Tipo": g["tipo"], "Nível": rotulo_valor(g["nivel"]),
                         "Destino": {"Tecnico": "Técnico"}.get(g["perfil_destino"], g["perfil_destino"]),
                         "Critério": " e ".join(regras.descrever_condicao(c) for c in g["condicoes"])}
                        for g in atual.get("gatilhos", [])])
    st.markdown("**Gatilhos explícitos de alerta** (além do limiar do modelo)")
    st.dataframe(gat, hide_index=True, width="stretch")
    if not permitido("editar_regras"):
        return
    with st.form("regras"):
        st.markdown("**Ajustar parâmetros** (gera nova versão; predições antigas mantêm a versão com que foram feitas)")
        c1, c2, c3 = st.columns(3)
        limiar = c1.number_input("Limiar de alerta do modelo (score)", 1, 100,
                                 int(atual["alerta_modelo"]["limiar_score"]))
        custo = c2.number_input("Custo médio de sinistro (R$)", 1000, 5_000_000,
                                int(atual["economia"]["custo_medio_sinistro_brl"]), step=5000)
        taxa = c3.slider("Taxa de prevenção efetiva", 0.0, 1.0, float(atual["economia"]["taxa_prevencao"]), 0.05)
        limites = {g["codigo"]: g for g in atual.get("gatilhos", [])}
        c4, c5 = st.columns(2)
        manut = c4.number_input("Manutenção vencida a partir de (h)", 100, 2000, int(
            limites["MANUTENCAO_VENCIDA"]["condicoes"][0]["valor"]) if "MANUTENCAO_VENCIDA" in limites else 450,
            step=10)
        agua = c5.number_input("Área alagável: distância da água menor que (m)", 10, 2000, int(
            limites["AREA_ALAGAVEL"]["condicoes"][0]["valor"]) if "AREA_ALAGAVEL" in limites else 200, step=10)
        motivo = st.text_input("Justificativa da alteração (obrigatória)", max_chars=200)
        if st.form_submit_button("Salvar nova versão das regras", type="primary"):
            if len(motivo.strip()) < 10:
                st.error("Informe a justificativa (mínimo 10 caracteres) — ela vai para a trilha de auditoria.")
                return
            novas = copy.deepcopy(atual)
            novas["alerta_modelo"]["limiar_score"] = int(limiar)
            novas["economia"]["custo_medio_sinistro_brl"] = int(custo)
            novas["economia"]["taxa_prevencao"] = float(taxa)
            for g in novas.get("gatilhos", []):
                if g["codigo"] == "MANUTENCAO_VENCIDA":
                    g["condicoes"][0]["valor"] = int(manut)
                if g["codigo"] == "AREA_ALAGAVEL":
                    g["condicoes"][0]["valor"] = int(agua)
            try:
                salvas = regras.salvar_regras(novas, st.session_state["login"])
            except SomPrevErro as erro:
                st.error(erro.mensagem)
                return
            acao_registrada("REGRAS_ALTERADAS", versao_anterior=atual["versao"], versao_nova=salvas["versao"],
                            justificativa=motivo.strip(), limiar=int(limiar), custo=int(custo), taxa=float(taxa),
                            manutencao_h=int(manut), distancia_agua_m=int(agua))
            st.success(f"Regras salvas como {salvas['versao']}. Novas leituras já usam esta versão.")


# ---------------------------------------------------------------------------
# Visao: SEGURADORA
# ---------------------------------------------------------------------------
def visao_seguradora(df_total: pd.DataFrame, alertas: pd.DataFrame) -> None:
    ui.cabecalho("🏢 Seguradora — validação, carteira e auditoria",
                 "Confiabilidade do score, tendências para subscrição e rastreabilidade das decisões.")
    abas = st.tabs(["✅ Validação do modelo", "📈 Carteira e tendências", "🧾 Auditoria", "🧪 Qualidade dos dados"])
    metricas = json.loads(config.METRICAS_PATH.read_text(encoding="utf-8")) if config.METRICAS_PATH.exists() else {}
    with abas[0]:
        if not metricas:
            st.warning("Métricas não encontradas. Rode o pipeline.")
        else:
            final = metricas["modelo_final_teste"]
            s3 = metricas["comparacao"]["Receita Sprint 3"]
            k = st.columns(5)
            with k[0]:
                ui.cartao("Modelo ativo", metricas["versao_modelo"], metricas["modelo_escolhido"])
            with k[1]:
                ui.cartao("PR-AUC (teste)", f"{final['pr_auc']:.2f}", f"Sprint 3: {s3['teste']['pr_auc']:.2f}")
            with k[2]:
                ui.cartao("Recall no limiar", f"{final['recall']:.0%}",
                          f"Sprint 3: {s3['teste_limiar']['recall']:.0%} dos sinistros")
            with k[3]:
                ui.cartao("Brier (calibração)", f"{final['brier']:.3f}", "quanto menor, melhor")
            with k[4]:
                custos = metricas["analise_limiar"]["custo_esperado_teste_brl"]
                ui.cartao("Custo esperado (teste)", f"R$ {custos['modelo_final'] / 1e6:.1f} mi".replace(".", ","),
                          f"Sprint 3: R$ {custos['receita_sprint3'] / 1e6:.1f} mi".replace(".", ","))
            periodo = metricas["divisao_temporal"]
            st.caption(f"Validação temporal: treino {periodo['treino']['periodo']} · validação "
                       f"{periodo['validacao']['periodo']} · teste {periodo['teste']['periodo']} "
                       f"({periodo['teste']['leituras']} leituras nunca vistas pelo modelo).")
            faixas = pd.DataFrame(metricas["taxa_real_por_faixa_teste"])
            fig = ui.grafico_barras_h([f"{regras.EMOJI_CLASSE[f]} {regras.ROTULO_CLASSE[f]}" for f in faixas["faixa"]],
                                      faixas["taxa_real_sinistro"] * 100, [ui.tema.RISCO[f] for f in faixas["faixa"]],
                                      "Taxa REAL de sinistro por faixa prevista (teste)", "% de leituras com sinistro",
                                      [f"{t:.0%} (n={n})" for t, n in zip(faixas["taxa_real_sinistro"],
                                                                         faixas["leituras"])], altura=280)
            c1, c2 = st.columns([1.2, 1])
            c1.plotly_chart(fig, width="stretch")
            c2.image(str(config.MODELS_DIR / "calibracao.png"), caption="Calibração: score ≈ probabilidade real")
            c3, c4 = st.columns(2)
            c3.image(str(config.MODELS_DIR / "comparacao_modelos.png"))
            c4.image(str(config.MODELS_DIR / "importancia_variaveis.png"))
            with st.expander("Model card (uso pretendido, limitações e monitoramento)"):
                if config.MODEL_CARD_PATH.exists():
                    st.json(json.loads(config.MODEL_CARD_PATH.read_text(encoding="utf-8")))
    with abas[1]:
        df = filtros(df_total, "seg", periodo_padrao=184)
        if df.empty:
            st.warning("Nenhuma leitura para os filtros selecionados.")
        else:
            tab = tendencias.tendencia(df, "regiao_nome")
            st.plotly_chart(ui.grafico_tendencia(tab, "regiao_nome", "score_medio",
                                                 "Score médio semanal por região", "Score médio"),
                            width="stretch")
            rotulado = df.dropna(subset=["houve_sinistro"])
            carteira = (rotulado.groupby("regiao_nome")
                        .agg(leituras=("leitura_id", "count"), score_medio=("score_risco", "mean"),
                             sinistralidade_real=("houve_sinistro", "mean"),
                             alto_critico=("classe_risco", lambda s: s.isin(["Alto", "Critico"]).mean()))
                        .sort_values("score_medio", ascending=False).reset_index())
            st.markdown("**Carteira por região** (score previsto × sinistralidade observada)")
            st.dataframe(carteira, hide_index=True, width="stretch", column_config={
                "regiao_nome": "Região", "leituras": "Leituras",
                "score_medio": st.column_config.NumberColumn("Score médio", format="%.1f"),
                "sinistralidade_real": st.column_config.NumberColumn("Sinistralidade real", format="percent"),
                "alto_critico": st.column_config.NumberColumn("% Alto/Crítico", format="percent")})
    with abas[2]:
        c1, c2 = st.columns([1, 2])
        if c1.button("🔐 Verificar integridade da auditoria", type="primary", width="stretch"):
            resultado = cliente_api.verificar_auditoria()
            with sessao() as conn, transacao(conn):
                auditoria.registrar(conn, "VERIFICACAO_AUDITORIA", ator=st.session_state["login"],
                                    perfil=st.session_state["perfil"],
                                    status="SUCESSO" if resultado["integra"] else "FALHA",
                                    detalhes={"eventos": resultado["eventos_verificados"]})
            (c2.success if resultado["integra"] else c2.error)(resultado["resumo"])
        eventos = cliente_api.auditoria(limite=1000)
        tipos = st.multiselect("Eventos", sorted(eventos["evento"].unique()), placeholder="Todos os eventos")
        if tipos:
            eventos = eventos[eventos["evento"].isin(tipos)]
        st.dataframe(eventos[["auditoria_id", "data_hora", "evento", "ator", "perfil", "status", "leitura_id",
                              "equipamento_id", "modelo_versao", "detalhes", "hash_registro"]],
                     hide_index=True, width="stretch", height=380)
        with st.expander("Verificações automáticas do sistema"):
            for i in cliente_api.verificacao_sistema():
                st.markdown(f"{'✅' if i['ok'] else '❌'} **{i['verificacao']}** — {i['detalhe']}")
    with abas[3]:
        if config.RELATORIO_QUALIDADE_JSON.exists():
            rel = json.loads(config.RELATORIO_QUALIDADE_JSON.read_text(encoding="utf-8"))
            k = st.columns(4)
            with k[0]:
                ui.cartao("Registros recebidos", f"{rel['recebidas']:,}".replace(",", "."), "coleta bruta")
            with k[1]:
                ui.cartao("Aceitos", f"{rel['aceitas']:,}".replace(",", "."),
                          f"{rel['aceitas_com_correcao']} com correção automática")
            with k[2]:
                ui.cartao("Duplicados removidos", str(sum(rel["duplicidades"].values())), "reenvios de pacote")
            with k[3]:
                ui.cartao("Quarentena", str(rel["quarentena_total"]), f"aproveitamento {rel['taxa_aproveitamento']:.1%}")
            c1, c2 = st.columns(2)
            c1.markdown("**Correções e imputações**")
            c1.dataframe(pd.DataFrame([{"Tratamento": k, "Registros": v} for k, v in
                                       {**rel["correcoes"], **rel["imputacoes"]}.items()]),
                         hide_index=True, width="stretch")
            c2.markdown("**Motivos de quarentena**")
            c2.dataframe(pd.DataFrame([{"Motivo": k, "Registros": v} for k, v in rel["quarentena"].items()]),
                         hide_index=True, width="stretch")
        quarentena = cliente_api.quarentena()
        st.markdown(f"**Leituras em quarentena ({len(quarentena)})** — inclui rejeições em tempo real da API")
        st.dataframe(quarentena[["quarentena_id", "recebido_em", "origem", "equipamento_id", "data_hora", "motivo"]],
                     hide_index=True, width="stretch", height=260)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not banco_existe():
        st.error("Banco de dados não encontrado. Rode antes: `python scripts/run.py pipeline`")
        return
    if not sessao_valida():
        tela_login()
        return
    perfil = st.session_state["perfil"]
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state['nome']}")
        st.markdown(f"Perfil: **{config.ROTULO_PERFIL[perfil]}**  \nUsuário: `{st.session_state['login']}`")
        if st.button("Sair", width="stretch"):
            sair()
            st.rerun()
        st.divider()
        st.caption("Permissões deste perfil")
        st.caption(" · ".join(sorted(autenticacao.PERMISSOES[perfil])))

    leituras, alertas, equipamentos, manutencoes = carregar_dados()
    if leituras.empty:
        st.warning("Ainda não há leituras processadas.")
        return
    if perfil == "Operador":
        visao_operador(leituras, alertas)
    elif perfil == "Tecnico":
        visao_tecnico(leituras, alertas, equipamentos, manutencoes)
    elif perfil == "Gestor":
        visao_gestor(leituras, alertas, equipamentos)
    else:
        visao_seguradora(leituras, alertas)
    with st.sidebar:
        st.divider()
        st.caption(f"Modelo {leituras['modelo_versao'].iloc[-1]} · regras {regras.carregar_regras()['versao']} · "
                   f"dados até {leituras['data_hora'].max():%d/%m/%Y %H:%M}")


main()
