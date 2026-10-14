import sys, os, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *
from sheet import lockup_inline
from pecas import OUT, txt

# Camiseta tamanho M deitada: ~700 mm de ponta a ponta de manga, corpo de 500 mm
# de largura e 720 mm de comprimento. 1 unidade = 1 mm.
LARG, COMP = 700, 720
BX0, BX1 = 100, 600          # laterais do corpo
TECIDO = "#17160F"
COSTURA = "#302D22"
COTA = "#8F8A78"
FIAP_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                        "assets", "logo-fiap.png")

SILHUETA = (f"M 250 44 L 300 14 C 330 64 370 64 400 14 L 450 44 "
            f"L 690 150 L 612 290 L {BX1} 250 L {BX1} {COMP - 18} "
            f"Q {BX1} {COMP} {BX1 - 18} {COMP} L {BX0 + 18} {COMP} "
            f"Q {BX0} {COMP} {BX0} {COMP - 18} L {BX0} 250 L 88 290 L 10 150 Z")


def fiap_branco(x, y, larg):
    """FIAP em negativo (branco), para aplicar sobre tecido preto."""
    from PIL import Image
    import io
    im = Image.open(FIAP_PNG).convert("RGBA")
    px = im.load()
    for j in range(im.height):
        for i in range(im.width):
            r, g, b, a = px[i, j]
            if a:
                px[i, j] = (255, 255, 255, a)
    buf = io.BytesIO(); im.save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    alt = larg * im.height / im.width
    return (f'<image x="{x:.2f}" y="{y:.2f}" width="{larg:.2f}" height="{alt:.2f}" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'xlink:href="data:image/png;base64,{b64}"/>'), alt


def marca(larg):
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
                              folha=AMARELO, cor_texto=BRANCO, pad=2)
    return c, larg / lw, lh * (larg / lw)


def cota_h(x1, x2, y, rotulo):
    s = [f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{COTA}" stroke-width="1.4"/>']
    for x in (x1, x2):
        s.append(f'<line x1="{x}" y1="{y-7}" x2="{x}" y2="{y+7}" stroke="{COTA}" stroke-width="1.8"/>')
    t, _ = txt(rotulo, (x1 + x2) / 2, y - 12, 17, "IBMPlexMono-SemiBold", COTA, 0, "middle")
    return "".join(s) + t


def cota_v(y1, y2, x, rotulo):
    s = [f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{COTA}" stroke-width="1.4"/>']
    for y in (y1, y2):
        s.append(f'<line x1="{x-7}" y1="{y}" x2="{x+7}" y2="{y}" stroke="{COTA}" stroke-width="1.8"/>')
    t, _ = txt(rotulo, x - 10, (y1 + y2) / 2 + 6, 17, "IBMPlexMono-SemiBold", COTA, 0, "end")
    return "".join(s) + t


def camisa(frente: bool):
    s = [f'<path d="{SILHUETA}" fill="{TECIDO}" stroke="{COSTURA}" stroke-width="2.5"/>']
    s.append('<path d="M 300 14 C 330 64 370 64 400 14 L 390 4 C 366 50 334 50 310 4 Z"'
             f' fill="{COSTURA}"/>' if frente else
             '<path d="M 300 14 C 326 42 374 42 400 14 L 392 4 C 370 26 330 26 308 4 Z"'
             f' fill="{COSTURA}"/>')
    cx = LARG / 2
    if frente:
        LG = 220
        c, esc, alt = marca(LG)
        x, y = cx - LG / 2, 170
        s.append(f'<g transform="translate({x:.1f} {y:.1f}) scale({esc:.5f})">{c}</g>')
        s.append(cota_h(x, x + LG, y + alt + 34, "220 mm"))
        s.append(cota_v(70, y, BX0 - 34, "100 mm"))
    else:
        LG = 280
        c, esc, alt = marca(LG)
        x, y = cx - LG / 2, 360
        s.append(f'<g transform="translate({x:.1f} {y:.1f}) scale({esc:.5f})">{c}</g>')
        img, hf = fiap_branco(cx - 45, y + alt + 30, 90)
        s.append(img)
        s.append(cota_h(x, x + LG, y + alt + hf + 66, "280 mm"))
        s.append(cota_v(40, y, BX0 - 34, "320 mm"))
        t, _ = txt("FIAP · 90 mm", cx + 62, y + alt + 30 + hf / 2 + 6, 17,
                   "IBMPlexMono-SemiBold", COTA, 0, "start")
        s.append(t)
    return "".join(s)


def folha():
    W, H = 1560, 1080
    s = [f'<rect width="{W}" height="{H}" fill="#F3F1E9"/>']
    t, _ = txt("Camiseta preta — SomPrev Risk", 64, 68, 34, "Manrope-ExtraBold", GRAFITE, -0.5)
    s.append(t)
    t2, _ = txt("Medidas para o tamanho M; nos outros tamanhos a arte é a mesma, só muda a distância "
                "da gola. Impressão DTF ou transfer digital.", 64, 98, 17,
                "IBMPlexSans-Regular", "#6B6657")
    s.append(t2)
    for i, (rot, frente) in enumerate([("FRENTE", True), ("COSTAS", False)]):
        ex, ey, k = 70 + i * 760, 150, 0.86
        r, _ = txt(rot, ex + 60, ey - 10, 18, "IBMPlexSans-SemiBold", "#A06A00", 2.4)
        s.append(r)
        s.append(f'<g transform="translate({ex} {ey}) scale({k})">{camisa(frente)}</g>')
    n, _ = txt("Nas costas a marca fica na metade de baixo: nessa altura o cabelo solto não cobre.",
               64, H - 34, 17, "IBMPlexSans-Regular", "#6B6657")
    s.append(n)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{"".join(s)}</svg>')


def arte_costas_branca(larg_mm=280, larg_fiap=90, respiro=30):
    """Arte das costas pronta para a gráfica: marca + FIAP em branco, fundo transparente."""
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
                              folha=AMARELO, cor_texto=BRANCO, pad=2)
    esc = larg_mm / lw
    h1 = lh * esc
    img, h2 = fiap_branco((larg_mm - larg_fiap) / 2, h1 + respiro, larg_fiap)
    W, H = larg_mm, h1 + respiro + h2
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
            f'viewBox="0 0 {W:.2f} {H:.2f}"><g transform="scale({esc:.5f})">{c}</g>{img}</svg>')


if __name__ == "__main__":
    open(f"{OUT}/camiseta-mockup.svg", "w").write(folha())
    open(f"{OUT}/camiseta-costas.svg", "w").write(arte_costas_branca())
    print("ok")
