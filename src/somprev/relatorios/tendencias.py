"""
Relatorios de tendencia de risco por equipamento, regiao e tipo de operacao.

As funcoes de agregacao sao usadas por tres consumidores:
  * dashboard (graficos interativos por perfil);
  * API (GET /relatorios/tendencias);
  * relatorio gerencial exportavel (Markdown + PNG + CSV em document/relatorios/).

Leitura dos indicadores:
  score_medio ......... media do score 0-100 (probabilidade calibrada x 100);
  pct_alto_critico .... fracao de leituras nas faixas Alto ou Critico;
  variacao ............ score medio das ultimas 2 semanas menos o das 2 anteriores
                        (> +3 = "subindo", < -3 = "caindo", senao "estavel").
"""

from __future__ import annotations

from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .. import config, regras, tema  # noqa: E402
from ..esquema import ROTULOS  # noqa: E402

LIMITE_VARIACAO = 3.0
DIMENSOES = {"regiao_nome": "Região", "tipo_operacao": "Tipo de operação", "equipamento_id": "Equipamento",
             "equip_tipo": "Tipo de equipamento"}


def _alto_critico(s: pd.Series) -> float:
    return float(s.isin(["Alto", "Critico"]).mean())


def tendencia(df: pd.DataFrame, dimensao: str, freq: str = "W-MON") -> pd.DataFrame:
    """Serie temporal (semanal por padrao) de risco agrupada por uma dimensao."""
    base = df.assign(periodo=df["data_hora"].dt.to_period(freq.split("-")[0]).dt.start_time)
    return (base.groupby(["periodo", dimensao])
                .agg(leituras=("leitura_id", "count"), score_medio=("score_risco", "mean"),
                     pct_alto_critico=("classe_risco", _alto_critico),
                     sinistros_reais=("houve_sinistro", "sum"))
                .reset_index().round({"score_medio": 1, "pct_alto_critico": 3}))


def variacao_recente(df: pd.DataFrame, dimensao: str, dias: int = 14) -> pd.DataFrame:
    """Compara as ultimas `dias` com as `dias` anteriores para cada grupo."""
    fim = df["data_hora"].max()
    recente = df[df["data_hora"] > fim - pd.Timedelta(days=dias)]
    anterior = df[(df["data_hora"] <= fim - pd.Timedelta(days=dias))
                  & (df["data_hora"] > fim - pd.Timedelta(days=2 * dias))]
    tabela = pd.DataFrame({
        "score_recente": recente.groupby(dimensao)["score_risco"].mean(),
        "score_anterior": anterior.groupby(dimensao)["score_risco"].mean(),
        "pct_alto_critico_recente": recente.groupby(dimensao)["classe_risco"].agg(_alto_critico),
        "leituras_recentes": recente.groupby(dimensao)["leitura_id"].count(),
    })
    tabela["variacao"] = tabela["score_recente"] - tabela["score_anterior"]
    tabela["tendencia"] = np.select([tabela["variacao"] > LIMITE_VARIACAO, tabela["variacao"] < -LIMITE_VARIACAO],
                                    ["subindo", "caindo"], "estável")
    return tabela.round(2).sort_values("score_recente", ascending=False).reset_index()


def ranking_equipamentos(df: pd.DataFrame, alertas: pd.DataFrame | None = None, dias: int = 30) -> pd.DataFrame:
    """Ranking da frota nos ultimos `dias`: risco, tendencia, manutencao e alertas abertos."""
    fim = df["data_hora"].max()
    janela = df[df["data_hora"] > fim - pd.Timedelta(days=dias)]
    ultima = df.sort_values("data_hora").groupby("equipamento_id").tail(1).set_index("equipamento_id")
    rank = janela.groupby("equipamento_id").agg(
        tipo=("equip_tipo", "first"), regiao=("regiao_nome", lambda s: s.mode().iloc[0]),
        leituras=("leitura_id", "count"), score_medio=("score_risco", "mean"), pior_score=("score_risco", "max"),
        pct_alto_critico=("classe_risco", _alto_critico))
    rank["horas_desde_manutencao"] = ultima["horas_desde_manutencao"]
    rank["idade_anos"] = ultima["idade_equipamento_anos"]
    var = variacao_recente(df, "equipamento_id").set_index("equipamento_id")
    rank["tendencia"] = var["tendencia"]
    if alertas is not None and not alertas.empty:
        abertos = alertas[alertas["status"] != "resolvido"].groupby("equipamento_id")["alerta_id"].count()
        rank["alertas_abertos"] = abertos
    rank["alertas_abertos"] = rank.get("alertas_abertos", pd.Series(dtype=float)).fillna(0).astype(int)
    return rank.round(2).sort_values("score_medio", ascending=False).reset_index()


def matriz_regiao_operacao(df: pd.DataFrame, dias: int | None = None) -> pd.DataFrame:
    base = df if dias is None else df[df["data_hora"] > df["data_hora"].max() - pd.Timedelta(days=dias)]
    return base.pivot_table(index="regiao_nome", columns="tipo_operacao", values="score_risco",
                            aggfunc="mean").round(1)


def fatores_predominantes(df: pd.DataFrame, dimensao: str | None = None) -> pd.DataFrame:
    """Frequencia do fator nº 1 entre as leituras Alto/Critico (por grupo, se pedido)."""
    alto = df[df["classe_risco"].isin(["Alto", "Critico"])]
    chaves = [dimensao, "fator_1"] if dimensao else ["fator_1"]
    tab = alto.groupby(chaves)["leitura_id"].count().rename("leituras").reset_index()
    tab["fator"] = tab["fator_1"].map(ROTULOS)
    return tab.sort_values("leituras", ascending=False)


def insights(df: pd.DataFrame, alertas: pd.DataFrame | None = None) -> list[str]:
    """Frases objetivas para o resumo executivo (geradas a partir dos dados)."""
    frases = []
    reg = variacao_recente(df, "regiao_nome")
    if not reg.empty:
        topo = reg.iloc[0]
        frases.append(f"**{topo['regiao_nome']}** tem o maior risco médio nas últimas 2 semanas "
                      f"(score {topo['score_recente']:.0f}, {topo['pct_alto_critico_recente']:.0%} das leituras em "
                      f"Alto/Crítico), tendência **{topo['tendencia']}**.")
        subindo = reg[reg["tendencia"] == "subindo"]
        if not subindo.empty:
            frases.append("Risco **subindo** em: " + ", ".join(
                f"{r.regiao_nome} (+{r.variacao:.0f} pts)" for r in subindo.itertuples()) + ".")
        caindo = reg[reg["tendencia"] == "caindo"]
        if not caindo.empty:
            frases.append("Risco **caindo** em: " + ", ".join(
                f"{r.regiao_nome} ({r.variacao:.0f} pts)" for r in caindo.itertuples()) + ".")
    op = variacao_recente(df, "tipo_operacao")
    if not op.empty:
        frases.append(f"A operação de maior risco recente é **{op.iloc[0]['tipo_operacao']}** "
                      f"(score médio {op.iloc[0]['score_recente']:.0f}).")
    fat = fatores_predominantes(df[df["data_hora"] > df["data_hora"].max() - pd.Timedelta(days=30)])
    if not fat.empty:
        total = fat["leituras"].sum()
        frases.append(f"Principal causa das leituras Alto/Crítico no último mês: **{fat.iloc[0]['fator']}** "
                      f"({fat.iloc[0]['leituras'] / total:.0%} dos casos).")
    if alertas is not None and not alertas.empty:
        abertos = alertas[alertas["status"] != "resolvido"]
        manut = abertos[abertos["tipo"] == "MANUTENCAO"]["equipamento_id"].nunique()
        frases.append(f"{len(abertos)} alertas em aberto; {manut} equipamentos aguardam manutenção preventiva.")
    return frases


# ---------------------------------------------------------------------------
# Relatorio gerencial exportavel
# ---------------------------------------------------------------------------
def _grafico_linhas(tab: pd.DataFrame, dimensao: str, titulo: str, arquivo, paleta=None) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.4))
    grupos = tab[dimensao].unique()
    cores = paleta or tema.CATEGORICA
    for i, g in enumerate(grupos):
        serie = tab[tab[dimensao] == g]
        ax.plot(serie["periodo"], serie["score_medio"], marker="o", ms=3, lw=1.8, label=g,
                color=cores[i % len(cores)])
    ax.set(title=titulo, ylabel="Score médio de risco", xlabel="Semana")
    ax.grid(alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=8, ncol=3, loc="upper left")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=130)
    plt.close(fig)


def gerar_relatorio(df: pd.DataFrame, alertas: pd.DataFrame, destino=None) -> dict:
    """Gera Markdown + PNGs + CSVs com as tendencias. Devolve os caminhos gerados."""
    destino = destino or config.RELATORIOS_DIR
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = {}

    t_reg = tendencia(df, "regiao_nome")
    t_op = tendencia(df, "tipo_operacao")
    _grafico_linhas(t_reg, "regiao_nome", "Tendência semanal do risco por região", destino / "tendencia_regiao.png")
    _grafico_linhas(t_op, "tipo_operacao", "Tendência semanal do risco por tipo de operação",
                    destino / "tendencia_operacao.png")
    top_equip = variacao_recente(df, "equipamento_id")["equipamento_id"].head(5).tolist()
    t_eq = tendencia(df[df["equipamento_id"].isin(top_equip)], "equipamento_id")
    _grafico_linhas(t_eq, "equipamento_id", "Tendência semanal — 5 equipamentos de maior risco recente",
                    destino / "tendencia_equipamento.png")
    arquivos["graficos"] = ["tendencia_regiao.png", "tendencia_operacao.png", "tendencia_equipamento.png"]

    matriz = matriz_regiao_operacao(df, dias=30)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    im = ax.imshow(matriz.values, cmap="YlOrRd", vmin=0, vmax=max(60, np.nanmax(matriz.values)))
    ax.set_xticks(range(matriz.shape[1]), matriz.columns)
    ax.set_yticks(range(matriz.shape[0]), matriz.index)
    for i in range(matriz.shape[0]):
        for j in range(matriz.shape[1]):
            v = matriz.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9)
    ax.set_title("Score médio — região × operação (últimos 30 dias)")
    fig.colorbar(im, fraction=0.04)
    fig.tight_layout()
    fig.savefig(destino / "matriz_regiao_operacao.png", dpi=130)
    plt.close(fig)
    arquivos["graficos"].append("matriz_regiao_operacao.png")

    rank = ranking_equipamentos(df, alertas)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    top = rank.head(12).iloc[::-1]
    cores = [tema.RISCO[regras.classificar(int(round(s)))] for s in top["score_medio"]]
    ax.barh(top["equipamento_id"] + " · " + top["tipo"], top["score_medio"], color=cores)
    ax.set(title="Equipamentos com maior risco médio (últimos 30 dias)", xlabel="Score médio")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(destino / "ranking_equipamentos.png", dpi=130)
    plt.close(fig)
    arquivos["graficos"].append("ranking_equipamentos.png")

    t_reg.to_csv(destino / "tendencia_regiao.csv", index=False)
    t_op.to_csv(destino / "tendencia_operacao.csv", index=False)
    tendencia(df, "equipamento_id").to_csv(destino / "tendencia_equipamento.csv", index=False)
    rank.to_csv(destino / "ranking_equipamentos.csv", index=False)
    arquivos["csv"] = ["tendencia_regiao.csv", "tendencia_operacao.csv", "tendencia_equipamento.csv",
                       "ranking_equipamentos.csv"]

    var_reg = variacao_recente(df, "regiao_nome")
    var_op = variacao_recente(df, "tipo_operacao")
    abertos = alertas[alertas["status"] != "resolvido"] if not alertas.empty else alertas

    def tabela_md(t: pd.DataFrame, colunas: dict) -> str:
        cab = "| " + " | ".join(colunas.values()) + " |\n|" + "---|" * len(colunas) + "\n"
        linhas = []
        for r in t.to_dict("records"):
            celulas = []
            for c in colunas:
                v = r.get(c)
                if isinstance(v, float):
                    v = f"{v:.0%}" if c.startswith("pct") else f"{v:+.1f}" if c == "variacao" else f"{v:.1f}"
                celulas.append(str(v))
            linhas.append("| " + " | ".join(celulas) + " |")
        return cab + "\n".join(linhas)

    periodo = f"{df['data_hora'].min():%d/%m/%Y} a {df['data_hora'].max():%d/%m/%Y}"
    md = [
        "# Relatório de Tendências de Risco — SomPrev Risk",
        "",
        f"*Gerado automaticamente em {datetime.now():%d/%m/%Y %H:%M} · período dos dados: {periodo} · "
        f"{len(df):,} leituras · modelo {df['modelo_versao'].iloc[-1]} · regras {df['regras_versao'].iloc[-1]}*".replace(",", "."),
        "",
        "## Resumo executivo",
        "",
        *[f"- {f}" for f in insights(df, alertas)],
        "",
        "## Tendência por região",
        "",
        "![Tendência por região](tendencia_regiao.png)",
        "",
        tabela_md(var_reg, {"regiao_nome": "Região", "score_recente": "Score (últ. 14 dias)",
                            "score_anterior": "Score (14 dias antes)", "variacao": "Variação",
                            "tendencia": "Tendência", "pct_alto_critico_recente": "pct Alto/Crítico"}),
        "",
        "## Tendência por tipo de operação",
        "",
        "![Tendência por operação](tendencia_operacao.png)",
        "",
        tabela_md(var_op, {"tipo_operacao": "Operação", "score_recente": "Score (últ. 14 dias)",
                           "score_anterior": "Score (14 dias antes)", "variacao": "Variação",
                           "tendencia": "Tendência", "pct_alto_critico_recente": "pct Alto/Crítico"}),
        "",
        "## Região × operação",
        "",
        "![Matriz região x operação](matriz_regiao_operacao.png)",
        "",
        "## Equipamentos que exigem atenção",
        "",
        "![Tendência por equipamento](tendencia_equipamento.png)",
        "",
        "![Ranking de equipamentos](ranking_equipamentos.png)",
        "",
        tabela_md(rank.head(10), {"equipamento_id": "Equipamento", "tipo": "Tipo", "regiao": "Região",
                                  "score_medio": "Score médio", "pct_alto_critico": "pct Alto/Crítico",
                                  "horas_desde_manutencao": "Horas desde manutenção",
                                  "tendencia": "Tendência", "alertas_abertos": "Alertas abertos"}),
        "",
        "## Alertas em aberto por tipo e nível",
        "",
    ]
    if abertos is not None and not abertos.empty:
        piv = abertos.pivot_table(index="tipo", columns="nivel", values="alerta_id", aggfunc="count",
                                  fill_value=0).reindex(columns=["Medio", "Alto", "Critico"], fill_value=0)
        md += ["| Tipo | Médio | Alto | Crítico |", "|---|---|---|---|"]
        md += [f"| {t} | {r['Medio']} | {r['Alto']} | {r['Critico']} |" for t, r in piv.iterrows()]
    else:
        md.append("Nenhum alerta em aberto.")
    md += ["", "---", "",
           "**Como ler:** score = probabilidade calibrada de sinistro × 100. Faixas: "
           + ", ".join(f"{regras.ROTULO_CLASSE[c]} {lo}–{hi}" for c, (lo, hi)
                       in regras.carregar_regras()["faixas_score"].items())
           + ". Tendência compara as duas últimas semanas com as duas anteriores (±3 pontos).", ""]
    (destino / "relatorio_tendencias.md").write_text("\n".join(md), encoding="utf-8")
    arquivos["markdown"] = "relatorio_tendencias.md"
    return arquivos
