"""
=============================================================================
 SomPrev Risk  |  Treino e Validacao do Modelo Preditivo de Risco
 Challenge FIAP + Sompo Seguros  -  Sprint 2
=============================================================================

O que este script faz:
  1. Carrega a base (datasets/leituras_agricolas.csv).
  2. Monta um pre-processamento (One-Hot nas categoricas, escala nas numericas).
  3. Treina e COMPARA tres algoritmos supervisionados:
        - Logistic Regression  (baseline linear, interpretavel)
        - Random Forest        (escolhido - ver justificativa abaixo)
        - Gradient Boosting    (proxy do XGBoost, sem dependencia extra)
  4. Avalia com hold-out (treino/teste) + validacao cruzada (5 folds).
  5. Salva metricas REAIS (models/metricas.json) e graficos de validacao.
  6. Persiste o modelo escolhido (models/modelo_risco.pkl) para uso no
     banco de dados e no dashboard.

Por que Random Forest (justificativa tecnica)?
  - Captura relacoes NAO-LINEARES e INTERACOES entre variaveis (ex.: solo
    encharcado + chuva forte) sem precisar cria-las a mao.
  - Lida bem com variaveis numericas e categoricas em escalas diferentes.
  - E robusto a outliers e reduz overfitting via bagging (varias arvores).
  - Fornece importancia de variaveis -> sustenta a explicabilidade que o
    Gestor e a Seguradora precisam ("quais fatores elevam o risco").
  - A probabilidade prevista vira, de forma natural, o nosso SCORE 0-100.

Uso (a partir da raiz do repositorio):
    python src/scripts/treinar_modelo.py
"""

import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                      # backend sem tela (gera PNGs)
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, roc_curve, classification_report,
)
import joblib

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import risco_utils as ru
import tema  # paleta central: cores das faixas de risco vem daqui

# Caminhos robustos relativos a src/: o script vive em src/scripts/, logo
# SRC_DIR e a pasta src/ e datasets/models ficam em src/datasets e src/models.
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(SRC_DIR, "datasets")
MODELS_DIR = os.path.join(SRC_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 120, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25})

PALETA = {"rf": "#0B6E4F", "lr": "#6C8EBF", "gb": "#E8761B"}


def construir_preprocessador():
    """One-Hot nas categoricas; padronizacao nas numericas.

    Por que tratar os dois grupos diferente?
      - Numericas: padronizamos (media 0, desvio 1) porque elas estao em escalas
        muito diferentes (mm de chuva vs. graus de declividade). Sem isso,
        modelos sensiveis a escala (ex.: Regressao Logistica) dao peso indevido
        a variavel de numeros maiores.
      - Categoricas: One-Hot porque 'tipo_solo' nao tem ordem numerica — tratar
        Arenoso=1, Misto=2... inventaria uma hierarquia falsa. One-Hot cria uma
        coluna 0/1 por categoria, sem sugerir ordem inexistente.
    'handle_unknown=ignore' evita quebrar se aparecer uma categoria nova em producao.
    """
    return ColumnTransformer([
        ("num", StandardScaler(), ru.FEATURES_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore"), ru.FEATURES_CAT),
    ])


def avaliar(nome, modelo, X_tr, X_te, y_tr, y_te, cv):
    """Treina, mede no teste e roda validacao cruzada. Devolve dict de metricas."""
    modelo.fit(X_tr, y_tr)
    y_pred = modelo.predict(X_te)
    # Usamos a PROBABILIDADE da classe positiva (coluna 1), nao so o 0/1: e ela
    # que vira o score 0-100 e que permite calcular a ROC-AUC.
    y_prob = modelo.predict_proba(X_te)[:, 1]

    # Por que validacao cruzada ALEM do hold-out? O hold-out mede o desempenho em
    # UMA unica divisao treino/teste — pode ter dado sorte (ou azar) na amostra.
    # A CV de 5 folds treina/avalia 5 vezes em particoes diferentes; a media +-
    # desvio mostra se o resultado e estavel ou fruto do acaso daquele split.
    auc_cv = cross_val_score(modelo, X_tr, y_tr, cv=cv, scoring="roc_auc")

    m = {
        "modelo": nome,
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "precision": round(precision_score(y_te, y_pred), 4),
        "recall": round(recall_score(y_te, y_pred), 4),
        "f1": round(f1_score(y_te, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_te, y_prob), 4),
        "auc_cv_media": round(auc_cv.mean(), 4),
        "auc_cv_desvio": round(auc_cv.std(), 4),
    }
    print(f"  {nome:<20} acc={m['accuracy']:.3f}  prec={m['precision']:.3f}  "
          f"rec={m['recall']:.3f}  f1={m['f1']:.3f}  auc={m['roc_auc']:.3f}  "
          f"(CV-AUC {m['auc_cv_media']:.3f} +/- {m['auc_cv_desvio']:.3f})")
    return m, y_pred, y_prob


def main():
    print("=" * 70)
    print(" SomPrev Risk - Treino do Modelo de Risco")
    print("=" * 70)

    df = pd.read_csv(os.path.join(DATASETS_DIR, "leituras_agricolas.csv"))
    X = df[ru.FEATURES]
    y = df[ru.ALVO]
    print(f"Base: {len(df)} leituras | taxa de sinistro: {y.mean():.1%}")

    # stratify=y mantem a mesma proporcao de sinistros no treino e no teste —
    # essencial com classes desbalanceadas (~30% positivos), senao o teste
    # poderia ficar com poucos sinistros e distorcer as metricas.
    # random_state=42 fixa a divisao: todo mundo reproduz exatamente os numeros.
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Por que comparar 3 algoritmos em vez de ja escolher um? Para justificar a
    # escolha com evidencia, e nao por gosto: um baseline linear (Regressao
    # Logistica) e dois modelos de arvore (Random Forest e Gradient Boosting).
    # class_weight='balanced' compensa o desbalanceamento, fazendo o modelo dar
    # peso justo a classe minoritaria (os sinistros, que sao o que importa prever).
    pre = construir_preprocessador()
    modelos = {
        "Logistic Regression": Pipeline([("pre", pre),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))]),
        "Random Forest": Pipeline([("pre", pre),
            ("clf", RandomForestClassifier(n_estimators=300, max_depth=None,
                    min_samples_leaf=2, class_weight="balanced", random_state=42, n_jobs=-1))]),
        "Gradient Boosting": Pipeline([("pre", pre),
            ("clf", GradientBoostingClassifier(n_estimators=250, max_depth=3,
                    learning_rate=0.08, random_state=42))]),
    }

    print("\n[1] Comparacao de modelos (hold-out 25% + CV 5 folds):")
    resultados, preds, probs = {}, {}, {}
    for nome, mdl in modelos.items():
        m, yp, ypb = avaliar(nome, mdl, X_tr, X_te, y_tr, y_te, cv)
        resultados[nome] = m
        preds[nome] = yp
        probs[nome] = ypb

    # ---- Escolha: Random Forest ------------------------------------------
    # Por que o RF e nao o de maior AUC? O Gradient Boosting tem AUC quase igual,
    # mas o RF entrega a melhor ACURACIA, e robusto, treina rapido em paralelo e
    # oferece importancia de variaveis pronta — a explicabilidade que gestor e
    # seguradora exigem. Empate tecnico decidido pela interpretabilidade.
    escolhido = "Random Forest"
    modelo_final = modelos[escolhido]
    print(f"\n[2] Modelo escolhido: {escolhido}")
    print("\nRelatorio de classificacao (conjunto de teste):")
    print(classification_report(y_te, preds[escolhido],
          target_names=["Sem sinistro", "Com sinistro"]))

    # =====================================================================
    #  GRAFICOS DE VALIDACAO
    # =====================================================================
    # 2.1 Matriz de confusao do modelo escolhido
    cm = confusion_matrix(y_te, preds[escolhido])
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    im = ax.imshow(cm, cmap="Greens")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Sem sinistro", "Com sinistro"])
    ax.set_yticklabels(["Sem sinistro", "Com sinistro"])
    ax.set_xlabel("Previsto"); ax.set_ylabel("Real")
    ax.set_title(f"Matriz de Confusao - {escolhido}")
    total = cm.sum()
    for i in range(2):
        for j in range(2):
            pct = cm[i, j] / total * 100
            ax.text(j, i, f"{cm[i,j]}\n({pct:.1f}%)", ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() * 0.5 else "black",
                    fontsize=12, fontweight="bold")
    ax.grid(False)
    fig.tight_layout(); fig.savefig(f"{MODELS_DIR}/matriz_confusao.png"); plt.close(fig)
    print(f"[OK] {MODELS_DIR}/matriz_confusao.png")

    # 2.2 Importancia das variaveis (Random Forest)
    nomes_oh = (ru.FEATURES_NUM +
                list(modelo_final.named_steps["pre"]
                     .named_transformers_["cat"].get_feature_names_out(ru.FEATURES_CAT)))
    importancias = modelo_final.named_steps["clf"].feature_importances_
    imp = pd.Series(importancias, index=nomes_oh).sort_values(ascending=True).tail(12)
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    ax.barh(imp.index, imp.values, color=PALETA["rf"])
    ax.set_title("Importancia das Variaveis - Random Forest")
    ax.set_xlabel("Importancia relativa")
    fig.tight_layout(); fig.savefig(f"{MODELS_DIR}/importancia_variaveis.png"); plt.close(fig)
    print(f"[OK] {MODELS_DIR}/importancia_variaveis.png")

    # 2.3 Curvas ROC (todos os modelos)
    fig, ax = plt.subplots(figsize=(6, 5))
    for nome, cor in zip(modelos, [PALETA["lr"], PALETA["rf"], PALETA["gb"]]):
        fpr, tpr, _ = roc_curve(y_te, probs[nome])
        ax.plot(fpr, tpr, color=cor, lw=2,
                label=f"{nome} (AUC={resultados[nome]['roc_auc']:.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("Falso Positivo"); ax.set_ylabel("Verdadeiro Positivo")
    ax.set_title("Curva ROC - Comparacao de Modelos"); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(f"{MODELS_DIR}/curva_roc.png"); plt.close(fig)
    print(f"[OK] {MODELS_DIR}/curva_roc.png")

    # 2.4 Distribuicao do score por faixa de risco
    # Por que a probabilidade vira score 0-100? Multiplicamos por 100 para entregar
    # ao usuario um numero intuitivo (uma "nota de risco") em vez de uma
    # probabilidade entre 0 e 1 — mesma informacao, leitura mais facil em campo.
    score_te = (probs[escolhido] * 100)
    # Cores das faixas vindas do tema central (sem hex duplicado neste script).
    cores_faixa = [tema.RISCO["Baixo"], tema.RISCO["Medio"], tema.RISCO["Alto"], tema.RISCO["Critico"]]
    faixas = [(0, 25, "Baixo"), (26, 50, "Medio"), (51, 75, "Alto"), (76, 100, "Critico")]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.hist(score_te, bins=25, color=tema.VERMELHO_INSTITUCIONAL, alpha=0.85, edgecolor="white")
    for (lo, hi, _), c in zip(faixas, cores_faixa):
        ax.axvspan(lo, hi, color=c, alpha=0.10)
    for x in [25, 50, 75]:
        ax.axvline(x, color="gray", ls="--", alpha=0.6)
    ax.set_title("Distribuicao do Score de Risco (conjunto de teste)")
    ax.set_xlabel("Score de risco (0-100)"); ax.set_ylabel("Qtde de leituras")
    fig.tight_layout(); fig.savefig(f"{MODELS_DIR}/distribuicao_score.png"); plt.close(fig)
    print(f"[OK] {MODELS_DIR}/distribuicao_score.png")

    # 2.5 Comparacao de metricas entre modelos (barras agrupadas)
    metricas_nomes = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    larg = 0.25
    x = np.arange(len(metricas_nomes))
    for i, (nome, cor) in enumerate(zip(modelos, [PALETA["lr"], PALETA["rf"], PALETA["gb"]])):
        vals = [resultados[nome][m] for m in metricas_nomes]
        ax.bar(x + (i - 1) * larg, vals, larg, label=nome, color=cor)
    ax.set_xticks(x); ax.set_xticklabels([m.upper() for m in metricas_nomes])
    ax.set_ylim(0.5, 1.0); ax.set_title("Comparacao de Desempenho entre Modelos")
    ax.legend()
    fig.tight_layout(); fig.savefig(f"{MODELS_DIR}/comparacao_modelos.png"); plt.close(fig)
    print(f"[OK] {MODELS_DIR}/comparacao_modelos.png")

    # 2.6 Matriz de correlacao das variaveis numericas (+ alvo)
    corr = df[ru.FEATURES_NUM + [ru.ALVO]].corr()
    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(corr, cmap="RdYlGn_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr))); ax.set_yticks(range(len(corr)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i,j]:.2f}", ha="center", va="center",
                    fontsize=7, color="black")
    ax.set_title("Matriz de Correlacao (variaveis x sinistro)")
    fig.colorbar(im, fraction=0.046, pad=0.04)
    ax.grid(False)
    fig.tight_layout(); fig.savefig(f"{MODELS_DIR}/matriz_correlacao.png"); plt.close(fig)
    print(f"[OK] {MODELS_DIR}/matriz_correlacao.png")

    # =====================================================================
    #  SALVAR MODELO + METRICAS
    # =====================================================================
    joblib.dump(modelo_final, os.path.join(MODELS_DIR, "modelo_risco.pkl"))
    print(f"[OK] {MODELS_DIR}/modelo_risco.pkl")

    # Correlacoes com o alvo (para o README/relatorio)
    correl_alvo = (df[ru.FEATURES_NUM]
                   .corrwith(df[ru.ALVO]).abs().sort_values(ascending=False).round(3))

    saida = {
        "modelo_escolhido": escolhido,
        "n_amostras": int(len(df)),
        "taxa_sinistro": round(float(y.mean()), 4),
        "split_teste": 0.25,
        "comparacao": resultados,
        "matriz_confusao": {
            "verdadeiro_negativo": int(cm[0, 0]), "falso_positivo": int(cm[0, 1]),
            "falso_negativo": int(cm[1, 0]), "verdadeiro_positivo": int(cm[1, 1]),
        },
        "correlacao_com_sinistro": correl_alvo.to_dict(),
        "versao_modelo": "rf-v1.0",
    }
    with open(os.path.join(MODELS_DIR, "metricas.json"), "w", encoding="utf-8") as f:
        json.dump(saida, f, indent=2, ensure_ascii=False)
    print(f"[OK] {MODELS_DIR}/metricas.json")

    print("\n[3] Correlacao (|r|) das variaveis numericas com o sinistro:")
    for k, v in correl_alvo.items():
        print(f"     {ru.ROTULOS.get(k,k):<34} {v:.3f}")
    print("\nConcluido.")


if __name__ == "__main__":
    main()
