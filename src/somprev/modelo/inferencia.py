"""
Inferencia do modelo de risco: carregar o artefato, prever e explicar.

Explicacao local (por que ESTA leitura tem esse score?)
------------------------------------------------------
Na Sprint 3 os "top 3 fatores" vinham de uma formula fixa, independente do
modelo. Na Sprint 4 a explicacao passa a vir DO PROPRIO MODELO:

    contribuicao(variavel) = P(sinistro | leitura)
                           - media[ P(sinistro | leitura com a variavel trocada
                                     por valores tipicos da frota) ]

Os "valores tipicos" sao 15 quantis (numericas) ou as categorias com suas
frequencias (categoricas) observados no periodo de treino. Se, ao trocar a
umidade de 92% por umidades comuns da frota, o risco cai em media 30 pontos,
a umidade explica 30 pontos do score. E a mesma ideia do SHAP intervencional
(efeito marginal de cada variavel), sem dependencia extra, deterministica e
auditavel: a explicacao gravada no banco pode ser recalculada a qualquer momento.

Usar uma DISTRIBUICAO de referencia (e nao um unico valor mediano) evita um
vies: se a mediana da umidade ja for alta, trocar 92% por ela quase nao muda o
risco e a umidade "sumiria" da explicacao mesmo sendo a causa principal.
"""

from __future__ import annotations

import os
import threading

import joblib
import numpy as np
import pandas as pd

from .. import config
from ..esquema import FEATURES, FEATURES_CAT
from ..excecoes import ModeloIndisponivel
from ..logs import obter_logger

log = obter_logger("modelo.inferencia")

_CACHE: dict = {}
_TRAVA = threading.Lock()


class ModeloRisco:
    """Envelope do artefato treinado (modelo calibrado + metadados)."""

    def __init__(self, artefato: dict):
        faltando = {"modelo", "versao", "features", "referencia"} - set(artefato)
        if not faltando and not all(isinstance(v, dict) for v in artefato["referencia"].values()):
            faltando = {"referencia (formato antigo)"}
        if faltando:
            raise ModeloIndisponivel(f"Artefato do modelo incompleto (faltam {sorted(faltando)}). "
                                     "Rode: python scripts/run.py pipeline")
        if list(artefato["features"]) != FEATURES:
            raise ModeloIndisponivel("As variáveis do modelo não conferem com o contrato de dados. "
                                     "Rode: python scripts/run.py pipeline")
        self.modelo = artefato["modelo"]
        self.versao: str = artefato["versao"]
        self.algoritmo: str = artefato.get("algoritmo", "?")
        self.referencia: dict = artefato["referencia"]
        self.treinado_em: str = artefato.get("treinado_em", "?")

    def prever(self, X: pd.DataFrame) -> np.ndarray:
        """Probabilidade calibrada de sinistro para cada linha."""
        return self.modelo.predict_proba(X[FEATURES])[:, 1]

    def explicar(self, X: pd.DataFrame, probs: np.ndarray | None = None) -> list[dict[str, float]]:
        """Contribuicao (em pontos de score) de cada variavel, para cada linha.

        Vetorizado: para cada variavel monta um unico bloco (N leituras x K valores
        de referencia) e chama o modelo uma vez - rapido o bastante para a carga
        historica inteira e instantaneo para uma leitura da API.
        """
        X = X[FEATURES].reset_index(drop=True)
        n = len(X)
        probs = self.prever(X) if probs is None else np.asarray(probs)
        contrib = np.zeros((len(FEATURES), n))
        for j, var in enumerate(FEATURES):
            ref = self.referencia[var]
            valores, pesos = ref["valores"], np.asarray(ref["pesos"], dtype=float)
            bloco = pd.concat([X] * len(valores), ignore_index=True)
            bloco[var] = np.repeat(np.asarray(valores, dtype=object), n)
            if var not in FEATURES_CAT:
                bloco[var] = bloco[var].astype(float)
            p_troca = self.prever(bloco).reshape(len(valores), n)
            contrib[j] = (probs - (pesos[:, np.newaxis] * p_troca).sum(axis=0) / pesos.sum()) * 100
        return [{var: round(float(contrib[j, i]), 2) for j, var in enumerate(FEATURES)} for i in range(n)]


def top_fatores(contribuicoes: dict[str, float], n: int = 3) -> list[str]:
    """As n variaveis que MAIS elevaram o risco (contribuicao positiva, em ordem)."""
    ordenadas = sorted(contribuicoes.items(), key=lambda kv: kv[1], reverse=True)
    positivas = [k for k, v in ordenadas if v > 0]
    return (positivas + [k for k, _ in ordenadas if k not in positivas])[:n]


def carregar_modelo(caminho=None) -> ModeloRisco:
    """Carrega o modelo com cache; recarrega sozinho se o arquivo mudar (novo treino)."""
    caminho = caminho or config.MODELO_PATH
    try:
        assinatura = (str(caminho), os.path.getmtime(caminho))
    except OSError as erro:
        raise ModeloIndisponivel("Modelo não encontrado. Rode: python scripts/run.py pipeline") from erro
    with _TRAVA:
        if _CACHE.get("assinatura") != assinatura:
            try:
                artefato = joblib.load(caminho)
            except Exception as erro:  # pickle corrompido ou versao incompativel
                log.exception("Falha ao carregar modelo")
                raise ModeloIndisponivel("Não foi possível carregar o modelo (arquivo corrompido ou versão "
                                         "incompatível do scikit-learn). Rode: python scripts/run.py pipeline") from erro
            if not isinstance(artefato, dict):
                raise ModeloIndisponivel("Formato de modelo antigo (Sprint 3). Rode: python scripts/run.py pipeline")
            _CACHE["modelo"] = ModeloRisco(artefato)
            _CACHE["assinatura"] = assinatura
        return _CACHE["modelo"]
