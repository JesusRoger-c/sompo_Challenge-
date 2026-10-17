"""Artes para vestuário: peito da polo (bordado) e peito da camiseta (estampa).

Tudo em milímetros reais, fundo transparente, texto já em curvas. O bordado tem
regras próprias: no peito esquerdo de uma polo cabem ~90 mm de largura, e a
máquina trabalha por cor sólida — por isso existem as versões de uma cor só.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *
from sheet import lockup_inline, lockup_inline_caixa, lockup_stack

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pecas")
os.makedirs(OUT, exist_ok=True)


def arte(nome, larg_mm, *, empilhado=False, pneu=GRAFITE, aro=AMARELO, cubo=GRAFITE,
         folha=VERDE, cor_texto=GRAFITE, tag=None):
    if empilhado:
        corpo, W, H = lockup_stack(pneu=pneu, aro=aro, cubo=cubo, folha=folha,
                                   cor_texto=cor_texto, tag=tag,
                                   cor_tag=cor_texto if tag else None, pad=4)
        vb = f"0 0 {W:.2f} {H:.2f}"
    else:
        # caixa recalculada: a arte vai sozinha para a bordadeira e nao pode
        # chegar com o broto cortado no topo
        corpo, vb, W, H = lockup_inline_caixa(pneu=pneu, aro=aro, cubo=cubo,
                                              folha=folha, cor_texto=cor_texto, pad=3)
    esc = larg_mm / W
    svg_txt = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{larg_mm:.2f}mm" '
               f'height="{H * esc:.2f}mm" viewBox="{vb}">{corpo}</svg>')
    open(f"{OUT}/{nome}.svg", "w").write(svg_txt)
    return nome, round(larg_mm, 1), round(H * esc, 1)


if __name__ == "__main__":
    feitos = [
        # Peito esquerdo da polo — 90 mm é o que cabe sem invadir a costura.
        arte("polo-peito-cores", 90),
        arte("polo-peito-negativo", 90, pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
             folha=AMARELO, cor_texto=BRANCO),
        arte("polo-peito-bordado-1cor-grafite", 90, pneu=GRAFITE, aro="none",
             cubo=GRAFITE, folha=GRAFITE, cor_texto=GRAFITE),
        arte("polo-peito-bordado-1cor-branco", 90, pneu=BRANCO, aro="none",
             cubo=BRANCO, folha=BRANCO, cor_texto=BRANCO),
        # Versão empilhada, para quem preferir a marca mais alta e estreita no peito.
        arte("polo-peito-empilhado-cores", 62, empilhado=True, tag="SEGURO QUE PREVÊ"),
        arte("polo-peito-empilhado-negativo", 62, empilhado=True, tag="SEGURO QUE PREVÊ",
             pneu=BRANCO, aro=AMARELO, cubo=GRAFITE, folha=AMARELO, cor_texto=BRANCO),
        # Só o símbolo, para bordado pequeno (boné, manga, gola).
    ]
    # O símbolo não cabe num quadrado: o broto sobe 2,05 R acima do centro e
    # avança 1,76 R para a direita. A caixa é calculada a partir disso.
    R = 50.0
    W, H = R * 2.76, R * 3.05
    cx, cy = R, R * 2.05
    larg = 34.0
    open(f"{OUT}/polo-simbolo.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{larg:.2f}mm" '
        f'height="{larg * H / W:.2f}mm" viewBox="0 0 {W:.1f} {H:.1f}">'
        f'{simbolo(cx, cy, R)}</svg>')
    feitos.append(("polo-simbolo", larg, round(larg * H / W, 1)))
    for n, w, h in feitos:
        print(f"{n}.svg  {w} x {h} mm")
