"""Gerador de marca SomPrev Risk — texto convertido em curvas (sem dependencia de fonte)."""
import math, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fontes")

# ---------------------------------------------------------------- paleta
GRAFITE   = "#17160F"
AMARELO   = "#FFC400"
AMARELO_E = "#E3A400"
VERDE     = "#1A7048"
VERDE_E   = "#0E4A2F"
BRANCO    = "#FFFFFF"
CREME     = "#FFFBF0"

_cache = {}


def _font(name):
    if name not in _cache:
        _cache[name] = TTFont(f"{FONTS}/{name}.ttf")
    return _cache[name]


def texto_path(txt, fonte="Manrope-ExtraBold", size=100, tracking=0.0, x=0.0, y=0.0):
    """Retorna (d, largura_total). y = linha de base. Eixo y para baixo (SVG)."""
    f = _font(fonte)
    upem = f["head"].unitsPerEm
    s = size / upem
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    try:
        kern_pairs = {}
        kern = f["GPOS"]
    except Exception:
        kern_pairs = {}
    ds = []
    cursor = 0.0
    for ch in txt:
        gname = cmap.get(ord(ch))
        if gname is None:
            cursor += size * 0.3
            continue
        pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}")
        tp = TransformPen(pen, Transform(s, 0, 0, -s, x + cursor, y))
        gs[gname].draw(tp)
        d = pen.getCommands()
        if d:
            ds.append(d)
        cursor += hmtx[gname][0] * s + tracking
    return " ".join(ds), cursor - (tracking if txt else 0)


def medidas(fonte="Manrope-ExtraBold", size=100):
    f = _font(fonte)
    upem = f["head"].unitsPerEm
    s = size / upem
    os2 = f["OS/2"]
    return {
        "cap": os2.sCapHeight * s if hasattr(os2, "sCapHeight") else size * 0.72,
        "x": os2.sxHeight * s if hasattr(os2, "sxHeight") else size * 0.52,
        "asc": f["hhea"].ascent * s,
        "desc": -f["hhea"].descent * s,
    }


def largura(txt, fonte="Manrope-ExtraBold", size=100, tracking=0.0):
    f = _font(fonte)
    s = size / f["head"].unitsPerEm
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    w = 0.0
    for ch in txt:
        g = cmap.get(ord(ch))
        w += (hmtx[g][0] * s if g else size * 0.3) + tracking
    return w - (tracking if txt else 0)


# ---------------------------------------------------------------- simbolo
def _pol(r, a):
    """polar -> cartesiano, y para cima, angulo em graus."""
    t = math.radians(a)
    return r * math.cos(t), r * math.sin(t)


def _circ(cx, cy, r, sentido=1):
    """Sub-path de circulo. sentido=1 horario, -1 anti-horario."""
    f = 1 if sentido > 0 else 0
    return (f'M {cx-r:.3f} {cy:.3f} a {r:.3f} {r:.3f} 0 1 {f} {2*r:.3f} 0 '
            f'a {r:.3f} {r:.3f} 0 1 {f} {-2*r:.3f} 0 Z ')


def roda(
    cx=0.0, cy=0.0, R=50.0,
    cor_pneu=GRAFITE, cor_aro=AMARELO, cor_cubo=GRAFITE,
    n_garras=12, shear=14.0, larg_garra=0.085,
    aro_r=0.55, cubo_r=0.165, parafusos=5, paraf_r=0.055, paraf_dist=0.335,
    banda=0.045,
):
    """Roda de trator de frente: circulo perfeito com garras vazadas na banda."""
    def P(r, a):
        x, y = _pol(r, a)
        return cx + x, cy - y

    r_out = R
    r_in = R * aro_r
    r_garra = r_in + (r_out - r_in) * banda * 2   # base das garras, deixa um aro continuo

    d = _circ(cx, cy, r_out, 1) + _circ(cx, cy, r_in, -1)
    passo = 360.0 / n_garras
    # sulco de largura linear constante: meio-angulo = asin((g/2)/r)
    g = R * larg_garra
    w_in = math.degrees(math.asin(min(1.0, (g / 2) / r_garra)))
    w_out = math.degrees(math.asin(min(1.0, (g / 2) / r_out)))
    for i in range(n_garras):
        a = i * passo + 90.0
        a1, a2 = a - w_in, a + w_in
        b1, b2 = a + shear - w_out, a + shear + w_out
        p1, p2 = P(r_garra, a1), P(r_out, b1)
        p3, p4 = P(r_out, b2), P(r_garra, a2)
        d += (f'M {p1[0]:.2f} {p1[1]:.2f} L {p2[0]:.2f} {p2[1]:.2f} '
              f'A {r_out:.2f} {r_out:.2f} 0 0 1 {p3[0]:.2f} {p3[1]:.2f} '
              f'L {p4[0]:.2f} {p4[1]:.2f} '
              f'A {r_garra:.2f} {r_garra:.2f} 0 0 0 {p1[0]:.2f} {p1[1]:.2f} Z ')

    out = []
    if cor_aro and cor_aro != "none":
        out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r_in:.2f}" fill="{cor_aro}"/>')
    out.append(f'<path fill="{cor_pneu}" fill-rule="evenodd" d="{d.strip()}"/>')
    out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{R*cubo_r:.2f}" fill="{cor_cubo}"/>')
    for i in range(parafusos):
        a = 90.0 + i * (360.0 / parafusos)
        x, y = P(R * paraf_dist, a)
        out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{R*paraf_r:.2f}" fill="{cor_cubo}"/>')
    return "\n".join(out)


def _folha(bx, by, tx, ty, bojo, cor, veia=None, cy_flip=True):
    """Folha amendoada entre base (bx,by) e ponta (tx,ty). Coordenadas SVG."""
    dx, dy = tx - bx, ty - by
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    mx, my = bx + dx * 0.5, by + dy * 0.5
    c1 = (mx + px * bojo, my + py * bojo)
    c2 = (mx - px * bojo, my - py * bojo)
    d = (f'M {bx:.2f} {by:.2f} Q {c1[0]:.2f} {c1[1]:.2f} {tx:.2f} {ty:.2f} '
         f'Q {c2[0]:.2f} {c2[1]:.2f} {bx:.2f} {by:.2f} Z')
    s = f'<path d="{d}" fill="{cor}"/>'
    if veia:
        s += (f'\n<path d="M {bx+ux*L*0.12:.2f} {by+uy*L*0.12:.2f} '
              f'L {bx+ux*L*0.88:.2f} {by+uy*L*0.88:.2f}" stroke="{veia}" '
              f'stroke-width="{L*0.055:.2f}" stroke-linecap="round" fill="none" opacity="0.9"/>')
    return s


def broto(cx=0.0, cy=0.0, R=50.0, cor=VERDE, veia=None, espelho=False, escala=1.0):
    """Dois brotos saindo do topo-direita da roda. Desenhar ANTES da roda."""
    k = R / 50.0 * escala
    sx = -1 if espelho else 1

    def T(x, y):
        return cx + sx * x * k, cy - y * k

    # haste: sai de dentro da roda e sobe para a direita
    p0 = T(8, 18); c1 = T(26, 28); c2 = T(36, 42); p3 = T(38, 58)
    out = [f'<path d="M {p0[0]:.2f} {p0[1]:.2f} C {c1[0]:.2f} {c1[1]:.2f} '
           f'{c2[0]:.2f} {c2[1]:.2f} {p3[0]:.2f} {p3[1]:.2f}" fill="none" '
           f'stroke="{cor}" stroke-width="{7*k:.2f}" stroke-linecap="round"/>']
    # folha direita (abre para fora)
    out.append(_folha(*T(39, 57), *T(88, 80), 21 * k * sx, cor, veia))
    # folha esquerda (abre para cima)
    out.append(_folha(*T(35, 54), *T(14, 100), 18 * k * sx, cor, veia))
    return "\n".join(out)


def simbolo(cx, cy, R, *, pneu=GRAFITE, aro=AMARELO, cubo=GRAFITE,
            folha=VERDE, veia=None, com_broto=True, espelho=False, escala_broto=1.0):
    s = []
    if com_broto:
        s.append(broto(cx, cy, R, folha, veia, espelho, escala_broto))
    s.append(roda(cx, cy, R, pneu, aro, cubo))
    return "\n".join(s)


def svg(largura_px, altura_px, corpo, fundo=None, vb=None):
    vb = vb or f"0 0 {largura_px} {altura_px}"
    bg = f'<rect width="100%" height="100%" fill="{fundo}"/>' if fundo else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{largura_px}" '
            f'height="{altura_px}" viewBox="{vb}">{bg}\n{corpo}\n</svg>')
