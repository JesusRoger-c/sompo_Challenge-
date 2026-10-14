import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *
from sheet import lockup_inline, lockup_stack

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logo")
os.makedirs(OUT, exist_ok=True)


def grava(nome, corpo, W, H, fundo=None):
    s = svg(round(W, 1), round(H, 1), corpo, fundo)
    open(f"{OUT}/{nome}.svg", "w").write(s)
    return nome


# ---- horizontal, cores oficiais, fundo claro
c, W, H = lockup_inline("S", "mPrev Risk")
grava("somprev-horizontal", c, W, H)

# ---- horizontal negativo (fundo grafite)
c, W, H = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
                        folha=AMARELO, cor_texto=BRANCO)
grava("somprev-horizontal-negativo", c, W, H)

# ---- horizontal sobre amarelo
c, W, H = lockup_inline("S", "mPrev Risk", pneu=GRAFITE, aro=CREME, cubo=GRAFITE,
                        folha=GRAFITE, cor_texto=GRAFITE)
grava("somprev-horizontal-sobre-amarelo", c, W, H)

# ---- horizontal monocromatico grafite (bordado / carimbo / fax)
c, W, H = lockup_inline("S", "mPrev Risk", pneu=GRAFITE, aro="none", cubo=GRAFITE,
                        folha=GRAFITE, cor_texto=GRAFITE)
grava("somprev-horizontal-mono-grafite", c, W, H)

# ---- horizontal monocromatico branco
c, W, H = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro="none", cubo=BRANCO,
                        folha=BRANCO, cor_texto=BRANCO)
grava("somprev-horizontal-mono-branco", c, W, H)

# ---- empilhado com assinatura
c, W, H = lockup_stack()
grava("somprev-empilhado", c, W, H)

c, W, H = lockup_stack(pneu=BRANCO, aro=AMARELO, folha=AMARELO, cor_texto=BRANCO, cor_tag=AMARELO)
grava("somprev-empilhado-negativo", c, W, H)

# ---- simbolo
grava("somprev-simbolo", simbolo(110, 118, 92), 220, 240)
grava("somprev-simbolo-mono-grafite",
      simbolo(110, 118, 92, pneu=GRAFITE, aro="none", cubo=GRAFITE, folha=GRAFITE), 220, 240)
grava("somprev-simbolo-mono-branco",
      simbolo(110, 118, 92, pneu=BRANCO, aro="none", cubo=BRANCO, folha=BRANCO), 220, 240)

# ---- icone quadrado (favicon / avatar), roda centralizada em bloco amarelo
ico = (f'<rect width="256" height="256" rx="56" fill="{AMARELO}"/>'
       + simbolo(128, 142, 78, pneu=GRAFITE, aro=CREME, cubo=GRAFITE, folha=GRAFITE))
grava("somprev-icone", ico, 256, 256)

ico2 = (f'<rect width="256" height="256" rx="56" fill="{GRAFITE}"/>'
        + simbolo(128, 142, 78, pneu=BRANCO, aro=AMARELO, cubo=GRAFITE, folha=AMARELO))
grava("somprev-icone-escuro", ico2, 256, 256)

print("\n".join(sorted(os.listdir(OUT))))
