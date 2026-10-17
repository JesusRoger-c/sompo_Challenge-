#!/usr/bin/env python3
"""
Confere os três cenários do placar contra o modelo de verdade.

Para que serve: os números que a demonstração mostra (5→15, 26→59, 77→92) saíram
do modelo, não de ajuste manual. Se alguém rodar o pipeline de novo e o modelo
mudar, a demonstração pode deixar de atravessar as faixas — e isso só apareceria
na frente do avaliador. Este script responde em 20 segundos.

    1) API de pé:  python scripts/run.py api
    2) Chave:      export SOMPREV_API_KEY="..."
    3) Rode:       python estande/conferir_cenarios.py

O que esperar: cada cenário deve SUBIR de faixa (ou se manter em Crítico, no
terceiro) entre 0° e 25°. Se um cenário ficar parado na mesma faixa, ajuste o
contexto dele em placar.py e rode isto de novo.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from placar import CENARIOS, pontuar  # noqa: E402

ANGULOS = (0, 10, 18, 25)
LARGURA = max(len(c["nome"]) for c in CENARIOS.values())


def main() -> int:
    print(f"\nConferência dos cenários do placar — ângulos {ANGULOS}\n")
    problemas = []

    for chave, cenario in CENARIOS.items():
        celulas, faixas = [], []
        for g in ANGULOS:
            status, corpo = pontuar(g, chave)
            if status >= 400 or "score_risco" not in corpo:
                print(f"  {cenario['nome']}: ERRO — {corpo.get('erro', status)}")
                return 2
            celulas.append(f"{g:>2}°: {corpo['score_risco']:>3} {corpo['classe_risco']:<8}")
            faixas.append(corpo["classe_risco"])

        print(f"  {cenario['nome']:<{LARGURA}}  " + " | ".join(celulas))
        if faixas[0] == faixas[-1] and faixas[0] != "Critico":
            problemas.append(f"{cenario['nome']}: começa e termina em {faixas[0]} — "
                             f"a inclinação não muda a faixa.")

    print()
    if problemas:
        print("Atenção:")
        for p in problemas:
            print(f"  - {p}")
        print("\nAjuste o contexto do cenário em placar.py (mais umidade ou mais horas sem\n"
              "manutenção deixam a operação mais sensível ao declive) e rode de novo.")
        return 1

    print("Os três cenários atravessam as faixas como esperado. Demonstração de pé.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
