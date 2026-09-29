"""
Treino, selecao, calibracao e avaliacao do modelo de risco - versao 2 (Sprint 4).

O que mudou em relacao a Sprint 2/3 e por que:

1. VALIDACAO TEMPORAL (treino = mar-jun | validacao = jul | teste = ago).
   Na operacao real o modelo sempre preve o FUTURO com base no passado. Um
   split aleatorio mistura datas e superestima o desempenho, porque o modelo
   "ve" dias vizinhos do teste. O teste fica intocado ate a avaliacao final.

2. METRICAS ADEQUADAS A UM PROBLEMA PREVENTIVO E DESBALANCEADO (~30% sinistros).
   Acuracia engana (um modelo que nunca alerta acertaria 70%). Usamos:
     - PR-AUC (average precision): qualidade do ranking na classe rara (criterio de selecao);
     - ROC-AUC: capacidade de separacao;
     - Brier score: qualidade da PROBABILIDADE (o score 0-100 e a probabilidade);
     - Recall/precisao no limiar de alerta: quantos sinistros o sistema antecipa
       e quanto "alarme falso" ele custa.

3. AJUSTE DE HIPERPARAMETROS com busca aleatoria e validacao cruzada temporal
   (TimeSeriesSplit) apenas no periodo de treino.

4. CALIBRACAO (Platt) no periodo de validacao: com class_weight='balanced' o
   modelo aprende bem a ORDENAR o risco, mas suas probabilidades ficam
   infladas. Calibrar faz o score 70 significar ~70% de chance de sinistro.

5. LIMIAR DE ALERTA ESCOLHIDO POR CUSTO, e nao fixo em 0,5:
       custo(limiar) = alertas x custo da parada preventiva
                     + sinistros nao alertados x custo medio x taxa de prevencao
   As premissas vem de config/regras_risco.json e ficam registradas.

6. COMPARACAO JUSTA COM A RECEITA DA SPRINT 3 (Random Forest padrao, limiar 0,5,
   sem calibracao) nos MESMOS dados e no MESMO teste.

7. RASTREABILIDADE: model card com versao, periodo de dados, hash do artefato,
   versao do scikit-learn, metricas e limitacoes conhecidas.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402
from sklearn.calibration import CalibratedClassifierCV, calibration_curve  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier  # noqa: E402
from sklearn.frozen import FrozenEstimator  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,  # noqa: E402
                             f1_score, fbeta_score, log_loss, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder, StandardScaler  # noqa: E402

from .. import config, regras, tema  # noqa: E402
from ..esquema import ALVO, FEATURES, FEATURES_CAT, FEATURES_NUM, ROTULOS  # noqa: E402
from ..logs import obter_logger  # noqa: E402

log = obter_logger("modelo.treino")
warnings.filterwarnings("ignore", category=UserWarning)

VERSAO_MODELO = "v2.0"
CORTE_VALIDACAO = "2026-07-01"
CORTE_TESTE = "2026-08-01"
CORES = {"Logistic Regression": "#6C8EBF", "Random Forest": "#0B6E4F",
         "HistGradientBoosting": "#E8761B", "Receita Sprint 3": "#9E9E9E"}


# ---------------------------------------------------------------------------
# Construcao dos candidatos
# ---------------------------------------------------------------------------
def _preprocessador(escalar: bool) -> ColumnTransformer:
    """One-Hot nas categoricas (sem ordem falsa); padronizacao so p/ modelos lineares."""
    num = StandardScaler() if escalar else "passthrough"
    return ColumnTransformer([
        ("num", num, FEATURES_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore"), FEATURES_CAT),
    ])


def candidatos(seed: int) -> dict[str, tuple[Pipeline, dict]]:
    """Algoritmos comparados e seus espacos de busca de hiperparametros."""
    return {
        "Logistic Regression": (
            Pipeline([("pre", _preprocessador(True)),
                      ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))]),
            {"clf__C": [0.03, 0.1, 0.3, 1.0, 3.0]},
        ),
        "Random Forest": (
            Pipeline([("pre", _preprocessador(False)),
                      ("clf", RandomForestClassifier(class_weight="balanced", random_state=seed, n_jobs=-1))]),
            {"clf__n_estimators": [200, 300, 400], "clf__max_depth": [8, 12, 16, None],
             "clf__min_samples_leaf": [2, 5, 10, 20], "clf__max_features": ["sqrt", 0.5]},
        ),
        "HistGradientBoosting": (
            Pipeline([("pre", _preprocessador(False)),
                      ("clf", HistGradientBoostingClassifier(class_weight="balanced", random_state=seed))]),
            {"clf__learning_rate": [0.03, 0.06, 0.1], "clf__max_depth": [3, 4, 6],
             "clf__max_iter": [150, 250, 400], "clf__min_samples_leaf": [20, 40, 80],
             "clf__l2_regularization": [0.0, 0.5, 1.0]},
        ),
    }


def receita_sprint3(seed: int) -> Pipeline:
    """Configuracao usada na Sprint 3 (baseline para comparacao justa)."""
    return Pipeline([("pre", _preprocessador(True)),
                     ("clf", RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                                    class_weight="balanced", random_state=seed, n_jobs=-1))])


# ---------------------------------------------------------------------------
# Metricas
# ---------------------------------------------------------------------------
def metricas_probabilisticas(y, p) -> dict:
    return {
        "roc_auc": round(float(roc_auc_score(y, p)), 4),
        "pr_auc": round(float(average_precision_score(y, p)), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
        "log_loss": round(float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))), 4),
    }


def metricas_no_limiar(y, p, limiar: float) -> dict:
    pred = (p >= limiar).astype(int)
    vn, fp, fn, vp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "limiar": round(float(limiar), 3),
        "precisao": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred)), 4),
        "f1": round(float(f1_score(y, pred)), 4),
        "f2": round(float(fbeta_score(y, pred, beta=2)), 4),
        "taxa_alerta": round(float(pred.mean()), 4),
        "matriz_confusao": {"verdadeiro_negativo": int(vn), "falso_positivo": int(fp),
                            "falso_negativo": int(fn), "verdadeiro_positivo": int(vp)},
    }


def custo_esperado(y, p, limiar: float, economia: dict) -> float:
    pred = p >= limiar
    fn = int(((~pred) & (y == 1)).sum())
    alertas = int(pred.sum())
    return (alertas * economia["custo_parada_preventiva_brl"]
            + fn * economia["custo_medio_sinistro_brl"] * economia["taxa_prevencao"])


def escolher_limiar(y, p, economia: dict) -> tuple[float, pd.DataFrame]:
    """Varre limiares de 0,05 a 0,95 e escolhe o de menor custo esperado."""
    grade = np.round(np.arange(0.05, 0.96, 0.01), 2)
    linhas = []
    for t in grade:
        pred = p >= t
        linhas.append({"limiar": t, "custo_brl": custo_esperado(y, p, t, economia),
                       "recall": recall_score(y, pred), "precisao": precision_score(y, pred, zero_division=0),
                       "taxa_alerta": pred.mean()})
    tabela = pd.DataFrame(linhas)
    melhor = float(tabela.loc[tabela["custo_brl"].idxmin(), "limiar"])
    return melhor, tabela


def taxa_real_por_faixa(y, p, regras_ativas: dict) -> list[dict]:
    """Taxa REAL de sinistro por faixa prevista (no conjunto de teste)."""
    scores = np.array([regras.prob_para_score(v) for v in p])
    classes = np.array([regras.classificar(s, regras_ativas) for s in scores])
    saida = []
    for classe in regras.CLASSES:
        m = classes == classe
        saida.append({"faixa": classe, "leituras": int(m.sum()),
                      "taxa_real_sinistro": round(float(y[m].mean()), 4) if m.any() else None})
    return saida


# ---------------------------------------------------------------------------
# Graficos
# ---------------------------------------------------------------------------
def _salvar(fig, nome: str) -> None:
    fig.tight_layout()
    fig.savefig(config.MODELS_DIR / nome, dpi=130)
    plt.close(fig)


def _graficos(y_te, probs_te: dict, final_p, tabela_limiar, limiar, importancias, faixas, cm) -> None:
    plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.25,
                         "axes.spines.top": False, "axes.spines.right": False})

    fig, ax = plt.subplots(figsize=(6, 5))
    for nome, p in probs_te.items():
        fpr, tpr, _ = roc_curve(y_te, p)
        ax.plot(fpr, tpr, lw=2, color=CORES.get(nome, "#333"), label=f"{nome} (AUC {roc_auc_score(y_te, p):.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set(xlabel="Taxa de falso positivo", ylabel="Taxa de verdadeiro positivo (recall)",
           title="Curva ROC — conjunto de teste (agosto)")
    ax.legend(loc="lower right", fontsize=8)
    _salvar(fig, "curva_roc.png")

    fig, ax = plt.subplots(figsize=(6, 5))
    for nome, p in probs_te.items():
        prec, rec, _ = precision_recall_curve(y_te, p)
        ax.plot(rec, prec, lw=2, color=CORES.get(nome, "#333"),
                label=f"{nome} (PR-AUC {average_precision_score(y_te, p):.3f})")
    ax.axhline(y_te.mean(), color="k", ls="--", alpha=0.4, label=f"Taxa-base ({y_te.mean():.0%})")
    ax.set(xlabel="Recall (sinistros antecipados)", ylabel="Precisão (alertas corretos)",
           title="Precisão × Recall — conjunto de teste")
    ax.legend(loc="lower left", fontsize=8)
    _salvar(fig, "curva_precisao_recall.png")

    fig, ax = plt.subplots(figsize=(6, 5))
    frac, media = calibration_curve(y_te, final_p, n_bins=10, strategy="quantile")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Calibração perfeita")
    ax.plot(media, frac, "o-", color=tema.VERMELHO_INSTITUCIONAL, lw=2, label="Modelo final (calibrado)")
    ax.set(xlabel="Probabilidade prevista (score/100)", ylabel="Frequência real de sinistro",
           title="Calibração do score — conjunto de teste")
    ax.legend(loc="upper left")
    _salvar(fig, "calibracao.png")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.2, 6.4), sharex=True)
    x = tabela_limiar["limiar"] * 100
    ax1.plot(x, tabela_limiar["custo_brl"] / 1e6, color=tema.GRAFITE, lw=2)
    ax1.axvline(limiar * 100, color=tema.VERMELHO_INSTITUCIONAL, ls="--", lw=1.5)
    ax1.set(ylabel="Custo esperado (R$ mi)",
            title=f"Escolha do limiar de alerta por custo (validação) → score ≥ {limiar * 100:.0f}")
    ax2.plot(x, tabela_limiar["recall"], color="#2a78d6", lw=2, label="Recall (sinistros alertados)")
    ax2.plot(x, tabela_limiar["precisao"], color="#eb6834", lw=2, label="Precisão (alertas corretos)")
    ax2.axvline(limiar * 100, color=tema.VERMELHO_INSTITUCIONAL, ls="--", lw=1.5)
    ax2.set(xlabel="Limiar de alerta (score)", ylabel="Proporção", ylim=(0, 1.02))
    ax2.legend(loc="center right", fontsize=8)
    _salvar(fig, "analise_limiar.png")

    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    ax.imshow(cm, cmap="Reds")
    rotulos = ["Sem sinistro", "Com sinistro"]
    ax.set_xticks([0, 1], [f"Sem alerta", f"Alerta"])
    ax.set_yticks([0, 1], rotulos)
    ax.set(xlabel="Decisão do sistema", ylabel="Realidade",
           title=f"Matriz de confusão no limiar {limiar * 100:.0f}")
    total = cm.sum()
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]}\n({cm[i, j] / total:.1%})", ha="center", va="center", fontsize=12,
                    fontweight="bold", color="white" if cm[i, j] > cm.max() * 0.5 else "black")
    ax.grid(False)
    _salvar(fig, "matriz_confusao.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    imp = importancias.sort_values()
    ax.barh([ROTULOS.get(i, i) for i in imp.index], imp.values, color=tema.VERMELHO_ESCURO)
    ax.set(xlabel="Queda de PR-AUC ao embaralhar a variável", title="Importância das variáveis (permutação, teste)")
    _salvar(fig, "importancia_variaveis.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    nomes = [f["faixa"] for f in faixas]
    taxas = [(f["taxa_real_sinistro"] or 0) * 100 for f in faixas]
    barras = ax.bar([regras.ROTULO_CLASSE[n] for n in nomes], taxas, color=[tema.RISCO[n] for n in nomes])
    for b, f in zip(barras, faixas):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
                f"{b.get_height():.1f}%\n(n={f['leituras']})", ha="center", fontsize=9)
    ax.set(ylabel="Sinistros reais (%)", ylim=(0, 110),
           title="Taxa real de sinistro por faixa de risco prevista (teste)")
    _salvar(fig, "taxa_real_por_faixa.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.hist(final_p * 100, bins=25, color=tema.VERMELHO_INSTITUCIONAL, alpha=0.85, edgecolor="white")
    for x in (25, 50, 75):
        ax.axvline(x, color="gray", ls="--", alpha=0.6)
    ax.axvline(limiar * 100, color=tema.GRAFITE, lw=2, label=f"Limiar de alerta ({limiar * 100:.0f})")
    ax.set(xlabel="Score de risco (0-100)", ylabel="Leituras", title="Distribuição do score — teste")
    ax.legend()
    _salvar(fig, "distribuicao_score.png")


def _grafico_comparacao(comparacao: dict) -> None:
    nomes = list(comparacao)
    metricas = ["roc_auc", "pr_auc", "recall", "precisao"]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    largura = 0.8 / len(nomes)
    x = np.arange(len(metricas))
    for i, nome in enumerate(nomes):
        valores = [comparacao[nome]["teste"][m] if m in comparacao[nome]["teste"]
                   else comparacao[nome]["teste_limiar"][m] for m in metricas]
        ax.bar(x + (i - (len(nomes) - 1) / 2) * largura, valores, largura, label=nome,
               color=CORES.get(nome, "#333"))
    ax.set_xticks(x, ["ROC-AUC", "PR-AUC", "Recall no limiar", "Precisão no limiar"])
    ax.set_ylim(0, 1.05)
    ax.set_title("Comparação de modelos — conjunto de teste (agosto)")
    ax.legend(fontsize=8, ncol=2)
    _salvar(fig, "comparacao_modelos.png")


# ---------------------------------------------------------------------------
# Treino principal
# ---------------------------------------------------------------------------
def sha256_arquivo(caminho) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as arq:
        for bloco in iter(lambda: arq.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def dividir_temporal(df: pd.DataFrame):
    df = df.sort_values("data_hora")
    treino = df[df["data_hora"] < CORTE_VALIDACAO]
    valid = df[(df["data_hora"] >= CORTE_VALIDACAO) & (df["data_hora"] < CORTE_TESTE)]
    teste = df[df["data_hora"] >= CORTE_TESTE]
    return treino, valid, teste


def treinar(tratado: pd.DataFrame, rapido: bool = False, seed: int | None = None) -> dict:
    """Executa todo o ciclo de treino e grava os artefatos. Devolve as metricas.

    `rapido=True` reduz a busca de hiperparametros (usado nos testes automatizados).
    """
    seed = config.SEED if seed is None else seed
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    regras_ativas = regras.carregar_regras()
    economia = regras_ativas["economia"]

    base = tratado.dropna(subset=[ALVO]).copy()
    base[ALVO] = base[ALVO].astype(int)
    treino, valid, teste = dividir_temporal(base)
    X_tr, y_tr = treino[FEATURES], treino[ALVO].to_numpy()
    X_va, y_va = valid[FEATURES], valid[ALVO].to_numpy()
    X_te, y_te = teste[FEATURES], teste[ALVO].to_numpy()
    log.info("Treino iniciado", extra={"contexto": {"treino": len(treino), "validacao": len(valid),
                                                    "teste": len(teste)}})

    cv = TimeSeriesSplit(n_splits=3 if rapido else 5)
    comparacao, modelos, probs_va, probs_te = {}, {}, {}, {}
    for nome, (pipe, espaco) in candidatos(seed).items():
        busca = RandomizedSearchCV(pipe, espaco, n_iter=2 if rapido else 12, scoring="average_precision",
                                   cv=cv, random_state=seed, n_jobs=-1, refit=True)
        busca.fit(X_tr, y_tr)
        modelo = busca.best_estimator_
        p_va = modelo.predict_proba(X_va)[:, 1]
        p_te = modelo.predict_proba(X_te)[:, 1]
        modelos[nome], probs_va[nome], probs_te[nome] = modelo, p_va, p_te
        comparacao[nome] = {
            "melhores_hiperparametros": {k.replace("clf__", ""): v for k, v in busca.best_params_.items()},
            "cv_temporal_pr_auc": round(float(busca.best_score_), 4),
            "validacao": metricas_probabilisticas(y_va, p_va),
            "teste": metricas_probabilisticas(y_te, p_te),
        }
        print(f"  {nome:<22} PR-AUC valid={comparacao[nome]['validacao']['pr_auc']:.3f}  "
              f"ROC-AUC valid={comparacao[nome]['validacao']['roc_auc']:.3f}")

    # Selecao pelo PR-AUC na VALIDACAO (o teste nao participa da escolha).
    escolhido = max(comparacao, key=lambda n: comparacao[n]["validacao"]["pr_auc"])
    base_modelo = modelos[escolhido]

    # Calibracao (Platt) no periodo de validacao, com o modelo congelado.
    calibrado = CalibratedClassifierCV(FrozenEstimator(base_modelo), method="sigmoid")
    calibrado.fit(X_va, y_va)
    p_va_cal = calibrado.predict_proba(X_va)[:, 1]
    p_te_cal = calibrado.predict_proba(X_te)[:, 1]

    limiar, tabela_limiar = escolher_limiar(y_va, p_va_cal, economia)

    # Baseline: receita da Sprint 3 nos mesmos dados (limiar fixo 0,5, sem calibracao).
    s3 = receita_sprint3(seed).fit(X_tr, y_tr)
    p_te_s3 = s3.predict_proba(X_te)[:, 1]
    comparacao["Receita Sprint 3"] = {"descricao": "Random Forest padrão, limiar 0,5, sem calibração",
                                      "teste": metricas_probabilisticas(y_te, p_te_s3),
                                      "teste_limiar": metricas_no_limiar(y_te, p_te_s3, 0.5)}
    for nome in modelos:
        comparacao[nome]["teste_limiar"] = metricas_no_limiar(
            y_te, p_te_cal if nome == escolhido else probs_te[nome], limiar if nome == escolhido else 0.5)

    final_teste = {**metricas_probabilisticas(y_te, p_te_cal), **metricas_no_limiar(y_te, p_te_cal, limiar)}
    faixas = taxa_real_por_faixa(y_te, p_te_cal, regras_ativas)
    custo_final = custo_esperado(y_te, p_te_cal, limiar, economia)
    custo_s3 = custo_esperado(y_te, p_te_s3, 0.5, economia)
    custo_sem_modelo = int((y_te == 1).sum()) * economia["custo_medio_sinistro_brl"] * economia["taxa_prevencao"]

    # Explicabilidade global: importancia por permutacao no teste.
    perm = permutation_importance(calibrado, X_te, y_te, scoring="average_precision",
                                  n_repeats=3 if rapido else 8, random_state=seed, n_jobs=-1)
    importancias = pd.Series(perm.importances_mean, index=FEATURES).sort_values(ascending=False)

    # Distribuicao de referencia (valores tipicos do treino) para a explicacao local.
    quantis = np.linspace(0.03, 0.97, 15)
    referencia = {c: {"valores": [float(v) for v in X_tr[c].quantile(quantis)], "pesos": [1.0] * len(quantis)}
                  for c in FEATURES_NUM}
    for c in FEATURES_CAT:
        freq = X_tr[c].value_counts(normalize=True)
        referencia[c] = {"valores": [str(v) for v in freq.index], "pesos": [float(p) for p in freq.values]}

    algoritmo_curto = {"Random Forest": "rf", "HistGradientBoosting": "hgb", "Logistic Regression": "lr"}[escolhido]
    versao = f"{algoritmo_curto}-{VERSAO_MODELO}"
    artefato = {"modelo": calibrado, "versao": versao, "algoritmo": escolhido, "features": FEATURES,
                "referencia": referencia, "treinado_em": datetime.now().isoformat(timespec="seconds"),
                "limiar_recomendado": limiar}
    joblib.dump(artefato, config.MODELO_PATH, compress=3)
    hash_artefato = sha256_arquivo(config.MODELO_PATH)

    cm = np.array([[final_teste["matriz_confusao"]["verdadeiro_negativo"], final_teste["matriz_confusao"]["falso_positivo"]],
                   [final_teste["matriz_confusao"]["falso_negativo"], final_teste["matriz_confusao"]["verdadeiro_positivo"]]])
    _graficos(y_te, {**{n: probs_te[n] for n in modelos}, "Receita Sprint 3": p_te_s3}, p_te_cal,
              tabela_limiar, limiar, importancias, faixas, cm)
    _grafico_comparacao(comparacao)

    metricas = {
        "versao_modelo": versao,
        "modelo_escolhido": escolhido,
        "criterio_selecao": "maior PR-AUC no período de validação (julho)",
        "calibracao": "Platt (sigmoid) ajustada no período de validação",
        "divisao_temporal": {
            "treino": {"periodo": f"{treino['data_hora'].min()[:10]} a {treino['data_hora'].max()[:10]}",
                       "leituras": len(treino), "taxa_sinistro": round(float(y_tr.mean()), 4)},
            "validacao": {"periodo": f"{valid['data_hora'].min()[:10]} a {valid['data_hora'].max()[:10]}",
                          "leituras": len(valid), "taxa_sinistro": round(float(y_va.mean()), 4)},
            "teste": {"periodo": f"{teste['data_hora'].min()[:10]} a {teste['data_hora'].max()[:10]}",
                      "leituras": len(teste), "taxa_sinistro": round(float(y_te.mean()), 4)},
        },
        "comparacao": comparacao,
        "modelo_final_teste": final_teste,
        "analise_limiar": {
            "limiar_escolhido": limiar,
            "limiar_score": int(round(limiar * 100)),
            "premissas": economia,
            "custo_esperado_teste_brl": {"sem_modelo": round(custo_sem_modelo),
                                         "receita_sprint3": round(custo_s3),
                                         "modelo_final": round(custo_final)},
        },
        "taxa_real_por_faixa_teste": faixas,
        "importancia_permutacao": {k: round(float(v), 4) for k, v in importancias.items()},
        "n_amostras_rotuladas": int(len(base)),
        "hash_artefato_sha256": hash_artefato,
    }
    with open(config.METRICAS_PATH, "w", encoding="utf-8") as arq:
        json.dump(metricas, arq, indent=2, ensure_ascii=False)

    model_card = {
        "nome": "SomPrev Risk — modelo de risco de sinistro operacional",
        "versao": versao,
        "algoritmo": escolhido,
        "hiperparametros": comparacao[escolhido]["melhores_hiperparametros"],
        "treinado_em": artefato["treinado_em"],
        "scikit_learn": sklearn.__version__,
        "hash_artefato_sha256": hash_artefato,
        "uso_pretendido": "Apoiar decisões PREVENTIVAS antes/durante a operação de máquinas agrícolas "
                          "(liberar, restringir ou suspender) e a gestão de risco da seguradora.",
        "fora_do_escopo": "Negar cobertura ou precificar apólice de forma automática sem revisão humana.",
        "variaveis": FEATURES,
        "saida": "probabilidade calibrada de sinistro → score 0-100 → faixa → alertas",
        "dados": "Telemetria simulada (permitido pelo enunciado), gerador v2 com clima regional, "
                 "sazonalidade e cadastro fixo de frota; tratada pela etapa de qualidade.",
        "metricas_teste": final_teste,
        "limitacoes": [
            "Treinado com dados simulados: precisa ser recalibrado com sinistros reais da Sompo antes de uso produtivo.",
            "Período de 6 meses: não captura um ciclo climático anual completo.",
            "A explicação local mede a contribuição de cada variável em relação a uma leitura típica; "
            "é uma aproximação e não uma relação causal.",
        ],
        "monitoramento": "Reavaliar mensalmente PR-AUC, calibração (Brier) e taxa real por faixa; "
                         "retreinar se PR-AUC cair mais de 0,05 ou a calibração se deslocar.",
    }
    with open(config.MODEL_CARD_PATH, "w", encoding="utf-8") as arq:
        json.dump(model_card, arq, indent=2, ensure_ascii=False)

    log.info("Treino concluido", extra={"contexto": {"versao": versao, "pr_auc_teste": final_teste["pr_auc"],
                                                     "recall_teste": final_teste["recall"]}})
    return metricas
