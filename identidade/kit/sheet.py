import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *

OUT = os.path.dirname(os.path.abspath(__file__))


def lockup_inline(texto_a, texto_b, *, fonte="Manrope-ExtraBold", size=140, tracking=-2.0,
                  pneu=GRAFITE, aro=AMARELO, cubo=GRAFITE, folha=VERDE, veia=None,
                  cor_texto=GRAFITE, com_broto=True, fator_roda=1.18, pad=28, espelho=False,
                  gap=0.06):
    """texto_a + [roda] + texto_b numa linha."""
    m = medidas(fonte, size)
    cap = m["cap"]
    R = cap / 2 * fator_roda
    wa = largura(texto_a, fonte, size, tracking)
    wb = largura(texto_b, fonte, size, tracking)
    g = size * gap
    base_y = pad + (R * 2.06 if com_broto else cap)  # espaco para o broto
    topo_broto = R * 2.05
    x = pad
    da, _ = texto_path(texto_a, fonte, size, tracking, x, base_y)
    cx = x + wa + g + R
    xb = cx + R + g
    db, _ = texto_path(texto_b, fonte, size, tracking, xb, base_y)
    cy = base_y - cap / 2
    corpo = (f'<g>{simbolo(cx, cy, R, pneu=pneu, aro=aro, cubo=cubo, folha=folha, veia=veia, com_broto=com_broto, espelho=espelho)}</g>'
             f'<path d="{da}" fill="{cor_texto}"/><path d="{db}" fill="{cor_texto}"/>')
    W = xb + wb + pad
    H = base_y + m["desc"] * 0.55 + pad
    return corpo, W, H


def lockup_stack(*, fonte="Manrope-ExtraBold", size=92, tracking=-1.4, R=64,
                 pneu=GRAFITE, aro=AMARELO, cubo=GRAFITE, folha=VERDE, veia=None,
                 cor_texto=GRAFITE, cor_tag=None, tag="SEGURO QUE PREVÊ", pad=30):
    nome = "SomPrev Risk"
    w = largura(nome, fonte, size, tracking)
    cx = max(w, R * 2.4) / 2 + pad
    cy = pad + R * 2.08
    base = cy + R + size * 1.02
    d, _ = texto_path(nome, fonte, size, tracking, cx - w / 2, base)
    corpo = [simbolo(cx, cy, R, pneu=pneu, aro=aro, cubo=cubo, folha=folha, veia=veia),
             f'<path d="{d}" fill="{cor_texto}"/>']
    H = base + pad
    if tag:
        ts = size * 0.26
        tw = largura(tag, "IBMPlexSans-SemiBold", ts, ts * 0.22)
        dt, _ = texto_path(tag, "IBMPlexSans-SemiBold", ts, ts * 0.22, cx - tw / 2, base + size * 0.42)
        corpo.append(f'<path d="{dt}" fill="{cor_tag or AMARELO_E}"/>')
        H = base + size * 0.42 + pad
    W = cx * 2
    return "\n".join(corpo), W, H


def arvore(cx, cy, R, cor=VERDE, cor2=None):
    k = R / 50.0
    cor2 = cor2 or cor
    def T(x, y):
        return cx + x * k, cy - y * k
    p0 = T(6, 22); c1 = T(16, 44); p1 = T(18, 66)
    out = [f'<path d="M {p0[0]:.2f} {p0[1]:.2f} Q {c1[0]:.2f} {c1[1]:.2f} {p1[0]:.2f} {p1[1]:.2f}" stroke="{cor}" '
           f'stroke-width="{7*k:.2f}" stroke-linecap="round" fill="none"/>']
    for (x, y, r) in [(-2, 80, 17), (38, 80, 17), (18, 72, 18), (18, 100, 19)]:
        p = T(x, y)
        out.append(f'<circle cx="{p[0]:.2f}" cy="{p[1]:.2f}" r="{r*k:.2f}" fill="{cor2}"/>')
    return "\n".join(out)


def simbolo_arvore(cx, cy, R, **kw):
    return arvore(cx, cy, R, kw.pop("folha", VERDE)) + "\n" + roda(cx, cy, R, **kw)


def card(titulo, svg_txt, fundo="#FFFFFF"):
    return (f'<div class="c"><div class="t">{titulo}</div>'
            f'<div class="p" style="background:{fundo}">{svg_txt}</div></div>')


cards = []

# 1 — minusculo, broto verde
c, W, H = lockup_inline("S", "mPrev Risk")
cards.append(card("1 · SomPrev Risk — broto verde", svg(W, H, c)))

# 2 — minusculo, broto amarelo sobre grafite
c, W, H = lockup_inline("S", "mPrev Risk", aro=AMARELO, folha=AMARELO, cor_texto=GRAFITE)
cards.append(card("2 · broto amarelo (2 cores)", svg(W, H, c)))

# 3 — caixa alta
c, W, H = lockup_inline("S", "MPREV RISK", size=118, tracking=0.5)
cards.append(card("3 · caixa alta", svg(W, H, c)))

# 4 — empilhado
c, W, H = lockup_stack()
cards.append(card("4 · empilhado com assinatura", svg(W, H, c)))

# 5 — arvore
m = medidas("Manrope-ExtraBold", 140)
R = m["cap"] / 2
wa = largura("S", "Manrope-ExtraBold", 140, -2)
wb = largura("mPrev Risk", "Manrope-ExtraBold", 140, -2)
g = 140 * 0.06
base = 28 + R * 2.5
cx = 28 + wa + g + R
xb = cx + R + g
da, _ = texto_path("S", "Manrope-ExtraBold", 140, -2, 28, base)
db, _ = texto_path("mPrev Risk", "Manrope-ExtraBold", 140, -2, xb, base)
cy = base - m["cap"] / 2
c = (simbolo_arvore(cx, cy, R) + f'<path d="{da}" fill="{GRAFITE}"/><path d="{db}" fill="{GRAFITE}"/>')
cards.append(card("5 · arvore em vez de broto", svg(xb + wb + 28, base + 40, c)))

# 6 — simbolo isolado grande
c = simbolo(110, 118, 92)
cards.append(card("6 · simbolo isolado", svg(230, 230, c)))

# 7 — negativo sobre grafite
c, W, H = lockup_inline("S", "mPrev Risk", aro=AMARELO, pneu=BRANCO, cubo=GRAFITE,
                        folha=AMARELO, cor_texto=BRANCO)
cards.append(card("7 · sobre grafite", svg(W, H, c, fundo=GRAFITE), fundo=GRAFITE))

# 8 — sobre amarelo
c, W, H = lockup_inline("S", "mPrev Risk", aro=CREME, pneu=GRAFITE, cubo=GRAFITE,
                        folha=GRAFITE, cor_texto=GRAFITE)
cards.append(card("8 · sobre amarelo (1 cor)", svg(W, H, c, fundo=AMARELO), fundo=AMARELO))

# 9 — mono grafite (bordado 1 cor)
c, W, H = lockup_inline("S", "mPrev Risk", aro="none", pneu=GRAFITE, cubo=GRAFITE,
                        folha=GRAFITE, cor_texto=GRAFITE)
cards.append(card("9 · monocromatico (bordado)", svg(W, H, c)))

# 10 — tamanho minimo 18px de altura
c = simbolo(26, 28, 22)
cards.append(card("10 · teste de tamanho minimo", svg(56, 56, c)))

# 11 — broto espelhado (sobe pela esquerda)
c, W, H = lockup_inline("S", "mPrev Risk", espelho=True)
cards.append(card("11 · broto espelhado", svg(W, H, c)))

# 12 — com veia na folha
c, W, H = lockup_inline("S", "mPrev Risk", veia=VERDE_E)
cards.append(card("12 · folha com nervura", svg(W, H, c)))

html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#F2F0EA;font-family:system-ui,sans-serif;padding:36px}}
h1{{font-size:22px;margin:0 0 6px}}
p.s{{color:#666;margin:0 0 28px;font-size:14px}}
.g{{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}}
.c{{background:#fff;border:1px solid #DDD9D0;border-radius:14px;overflow:hidden}}
.t{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#8A8578;padding:12px 16px;border-bottom:1px solid #EEEBE4}}
.p{{padding:26px;display:flex;align-items:center;justify-content:center;min-height:170px}}
.p svg{{max-width:100%;height:auto;max-height:190px}}
</style></head><body>
<h1>SomPrev Risk — estudos de logo</h1>
<p class="s">Roda de trator no lugar do O, com broto de duas folhas. Amarelo {AMARELO} · grafite {GRAFITE} · verde {VERDE}</p>
<div class="g">{''.join(cards)}</div></body></html>"""

open(f"{OUT}/sheet.html", "w").write(html)
print("ok")
