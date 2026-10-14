"""Artes de impressao do SomPrev Risk: cartao-semente, model card PVC e camisetas.

Tudo em milimetros reais (1 unidade do viewBox = 1 mm), texto ja convertido em
curvas, sangria e marcas de corte onde a grafica precisa.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *
from sheet import lockup_inline, lockup_stack
import qrcode

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pecas")
os.makedirs(OUT, exist_ok=True)
# O QR aponta para o vídeo, não para o repositório: o repositório é PRIVADO e um QR
# que abre 404 na frente do avaliador é pior do que não ter QR. Se o grupo tornar o
# repositório público antes do evento, basta trocar a constante e regerar as peças.
VIDEO = "https://youtu.be/C6JPlqNLA2g"
REPO = "https://github.com/JesusRoger-c/sompo_Challenge-"   # privado hoje
DESTINO_QR = VIDEO
MC = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                    "src", "models", "model_card.json")))


# ------------------------------------------------------------------ utilidades
def pagina(w, h, sangria=0.0, fundo=None, marcas=True):
    """Devolve (abrir, fechar, W, H, ox, oy). Coordenadas uteis comecam em (ox, oy)."""
    W, H = w + 2 * sangria, h + 2 * sangria
    abrir = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" '
             f'viewBox="0 0 {W} {H}">')
    corpo = f'<rect width="{W}" height="{H}" fill="{fundo}"/>' if fundo else ""
    if marcas and sangria:
        t, g = 2.4, 0.9                       # tamanho da marca e folga
        linhas = []
        for (x, y, dx, dy) in [(sangria, 0, 0, 1), (sangria + w, 0, 0, 1),
                               (sangria, H, 0, -1), (sangria + w, H, 0, -1),
                               (0, sangria, 1, 0), (0, sangria + h, 1, 0),
                               (W, sangria, -1, 0), (W, sangria + h, -1, 0)]:
            linhas.append(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x + dx * t:.2f}" '
                          f'y2="{y + dy * t:.2f}" stroke="#999" stroke-width="0.12"/>')
        corpo += "".join(linhas)
    return abrir, corpo, W, H, sangria, sangria


def txt(s, x, y, size, fonte="IBMPlexSans-Regular", cor=GRAFITE, tracking=0.0,
        ancora="start", opacidade=None):
    w = largura(s, fonte, size, tracking)
    if ancora == "middle":
        x -= w / 2
    elif ancora == "end":
        x -= w
    d, _ = texto_path(s, fonte, size, tracking, x, y)
    op = f' opacity="{opacidade}"' if opacidade else ""
    return f'<path d="{d}" fill="{cor}"{op}/>', w


def bloco(s, x, y, size, larg_max, entrelinha=1.42, fonte="IBMPlexSans-Regular",
          cor=GRAFITE, tracking=0.0):
    """Quebra o texto na largura dada. Devolve (svg, y_final)."""
    palavras, linha, linhas = s.split(), "", []
    for p in palavras:
        t = (linha + " " + p).strip()
        if largura(t, fonte, size, tracking) > larg_max and linha:
            linhas.append(linha); linha = p
        else:
            linha = t
    if linha:
        linhas.append(linha)
    out = []
    for i, L in enumerate(linhas):
        s_, _ = txt(L, x, y + i * size * entrelinha, size, fonte, cor, tracking)
        out.append(s_)
    return "".join(out), y + (len(linhas) - 1) * size * entrelinha


def qr(dados, x, y, lado, cor=GRAFITE, fundo=None):
    q = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(dados); q.make(fit=True)
    m = q.get_matrix()
    n = len(m)
    p = lado / n
    out = [f'<rect x="{x - p * 2:.2f}" y="{y - p * 2:.2f}" width="{lado + p * 4:.2f}" '
           f'height="{lado + p * 4:.2f}" fill="{fundo}"/>'] if fundo else []
    d = []
    for i, linha in enumerate(m):
        j = 0
        while j < n:
            if linha[j]:
                k = j
                while k + 1 < n and linha[k + 1]:
                    k += 1
                d.append(f'M{x + j * p:.3f} {y + i * p:.3f}h{(k - j + 1) * p:.3f}'
                         f'v{p:.3f}h-{(k - j + 1) * p:.3f}z')
                j = k + 1
            else:
                j += 1
    out.append(f'<path d="{"".join(d)}" fill="{cor}"/>')
    return "".join(out)


def grava(nome, svg_txt):
    open(f"{OUT}/{nome}.svg", "w").write(svg_txt)
    return nome


# ------------------------------------------------------------------ 1. cartao-semente
def cartao_semente_frente():
    abrir, corpo, W, H, ox, oy = pagina(90, 50, 3, AMARELO)
    s = [corpo]
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=GRAFITE, aro="#FFF6DC", cubo=GRAFITE,
                              folha=GRAFITE, cor_texto=GRAFITE, pad=2)
    esc = 54 / lw
    s.append(f'<g transform="translate({ox + 45 - 27:.2f} {oy + 9:.2f}) scale({esc:.4f})">{c}</g>')
    y = oy + 9 + lh * esc + 7.5
    a, _ = txt("Este cartão vira planta.", ox + 45, y, 4.6, "Manrope-ExtraBold", GRAFITE, -0.06, "middle")
    s.append(a)
    b, _ = txt("Papel-semente: enterre, regue e veja no que dá.", ox + 45, y + 5.4, 2.7,
               "IBMPlexSans-Regular", "#4A3F10", 0, "middle")
    s.append(b)
    s.append(f'<rect x="{ox + 30:.2f}" y="{oy + 42.4:.2f}" width="30" height="0.45" fill="{GRAFITE}" opacity=".55"/>')
    c2, _ = txt("SEGURO QUE PREVÊ", ox + 45, oy + 47, 2.4, "IBMPlexSans-SemiBold", GRAFITE, 0.62, "middle")
    s.append(c2)
    return abrir + "".join(s) + "</svg>"


def cartao_semente_verso():
    abrir, corpo, W, H, ox, oy = pagina(90, 50, 3, PAPEL := "#FBFAF5")
    s = [corpo]
    a, _ = txt("COMO PLANTAR", ox + 7, oy + 11, 2.5, "IBMPlexSans-SemiBold", "#A06A00", 0.5)
    s.append(a)
    passos = ["Molhe o cartão inteiro e deixe de molho por 1 minuto.",
              "Enterre em 1 cm de terra, num vaso com sol da manhã.",
              "Regue todo dia por 15 dias. Brota entre o 7º e o 14º."]
    y = oy + 16.5
    for i, p in enumerate(passos):
        n, _ = txt(str(i + 1), ox + 7, y + i * 7.4, 3.0, "Manrope-ExtraBold", AMARELO_E := "#E0A500")
        s.append(n)
        bl, _ = bloco(p, ox + 11.4, y + i * 7.4, 2.55, 36.5, 1.5, "IBMPlexSans-Regular", "#3A362C")
        s.append(bl)
    # coluna da direita
    s.append(f'<rect x="{ox + 54:.2f}" y="{oy + 7:.2f}" width="0.3" height="36" fill="#E7E3D6"/>')
    s.append(qr(DESTINO_QR, ox + 60.5, oy + 10, 20, GRAFITE))
    q1, _ = txt("O projeto em 5 min", ox + 70.5, oy + 34.2, 2.5, "IBMPlexSans-SemiBold", GRAFITE, 0, "middle")
    q2, _ = txt("vídeo de demonstração", ox + 70.5, oy + 37.6, 2.2, "IBMPlexSans-Regular", "#6B6657", 0, "middle")
    s.append(q1); s.append(q2)
    r, _ = txt("SomPrev Risk · Challenge FIAP · NEXT 2026", ox + 45, oy + 45.6, 2.2,
               "IBMPlexSans-Regular", "#8A8578", 0, "middle")
    s.append(r)
    return abrir + "".join(s) + "</svg>"


# ------------------------------------------------------------------ 2. model card PVC
def model_card_frente():
    abrir, corpo, W, H, ox, oy = pagina(85.6, 54, 2, GRAFITE)
    m = MC["metricas_teste"]
    s = [corpo]
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
                              folha=AMARELO, cor_texto=BRANCO, pad=2)
    esc = 34 / lw
    s.append(f'<g transform="translate({ox + 6:.2f} {oy + 5:.2f}) scale({esc:.4f})">{c}</g>')
    a, _ = txt("FICHA DO MODELO", ox + 79.6, oy + 9.4, 2.3, "IBMPlexSans-SemiBold", AMARELO, 0.5, "end")
    s.append(a)
    s.append(f'<rect x="{ox + 6:.2f}" y="{oy + 15.6:.2f}" width="73.6" height="0.3" fill="#3A3728"/>')

    # O destaque é o que o modelo entrega, não a sigla do algoritmo: ninguém no
    # estande sabe o que é "hgb-v2.0", mas todo mundo entende 9 em cada 10.
    b, _ = txt(f'{m["recall"]*100:.0f}%', ox + 6, oy + 29.5, 11.0, "IBMPlexMono-SemiBold", AMARELO, -0.3)
    s.append(b)
    t1, _ = txt("dos sinistros são avisados", ox + 29.5, oy + 24.4, 3.0, "IBMPlexSans-SemiBold", BRANCO)
    t2, _ = txt("antes de acontecer", ox + 29.5, oy + 28.8, 3.0, "IBMPlexSans-SemiBold", BRANCO)
    t3, _ = txt("no conjunto de teste, com dados nunca vistos", ox + 29.5, oy + 32.8, 2.3,
                "IBMPlexSans-Regular", "#A8A392")
    s.append(t1); s.append(t2); s.append(t3)

    # Três métricas, não quatro: a precisão (32%) sem contexto vira "erra duas de
    # cada três" na leitura de quem passa pelo estande. O porquê do limiar fica na
    # linha abaixo, e a conversa sobre o trade-off acontece ao vivo.
    metricas = [("PR-AUC", f'{m["pr_auc"]:.2f}'.replace(".", ",")),
                ("ROC-AUC", f'{m["roc_auc"]:.2f}'.replace(".", ",")),
                ("BRIER", f'{m["brier"]:.3f}'.replace(".", ","))]
    x0 = ox + 6
    for i, (rot, val) in enumerate(metricas):
        x = x0 + i * 18.6
        r, _ = txt(rot, x, oy + 39.6, 1.95, "IBMPlexSans-SemiBold", "#908B78", 0.3)
        v, _ = txt(val, x, oy + 44.8, 4.4, "IBMPlexMono-SemiBold", BRANCO, -0.05)
        s.append(r); s.append(v)
        if i:
            s.append(f'<rect x="{x - 3.6:.2f}" y="{oy + 36.8:.2f}" width="0.3" height="9" fill="#3A3728"/>')
    c3, _ = txt(f'{MC["versao"]} · {MC["algoritmo"]} · {len(MC["variaveis"])} variáveis '
                f'· scikit-learn {MC["scikit_learn"]}',
                ox + 6, oy + 50.4, 2.0, "IBMPlexSans-Regular", "#726D5E")
    s.append(c3)
    return abrir + "".join(s) + "</svg>"


def model_card_verso():
    abrir, corpo, W, H, ox, oy = pagina(85.6, 54, 2, "#FBFAF5")
    s = [corpo]
    s.append(f'<rect x="{ox:.2f}" y="{oy:.2f}" width="85.6" height="3.4" fill="{AMARELO}"/>')
    secoes = [(9.6, "PARA QUE SERVE",
               "Apoiar decisões preventivas: liberar, restringir ou suspender a operação."),
              (20.0, "FORA DO ESCOPO",
               "Negar cobertura ou precificar apólice sem revisão humana."),
              (30.4, "COMO FOI VALIDADO",
               "Treino até 30/06, validação em julho, teste em agosto de 2026 — leituras "
               "inéditas. O limiar prioriza não deixar sinistro passar.")]
    for y, rot, texto in secoes:
        a, _ = txt(rot, ox + 6, oy + y, 2.1, "IBMPlexSans-SemiBold", "#A06A00", 0.4)
        s.append(a)
        bl, _ = bloco(texto, ox + 6, oy + y + 3.5, 2.2, 54, 1.4, "IBMPlexSans-Regular", "#3A362C")
        s.append(bl)
    s.append(f'<rect x="{ox + 6:.2f}" y="{oy + 41.2:.2f}" width="50" height="0.25" fill="#DDD8C8"/>')
    bl, _ = bloco("Dados simulados — recalibrar com sinistros reais antes do uso produtivo.",
                  ox + 6, oy + 44.8, 2.0, 50, 1.4, "IBMPlexSans-Regular", "#8A8578")
    s.append(bl)
    s.append(qr(DESTINO_QR, ox + 62.5, oy + 10, 17, GRAFITE))
    q, _ = txt("vídeo do projeto", ox + 71, oy + 30.4, 2.05, "IBMPlexSans-Regular", "#6B6657", 0, "middle")
    s.append(q)
    h, _ = txt("SHA256 DO ARTEFATO", ox + 71, oy + 37.6, 1.85, "IBMPlexSans-SemiBold", "#A09A86", 0.25, "middle")
    s.append(h)
    h2, _ = txt(MC["hash_artefato_sha256"][:16], ox + 71, oy + 41.2, 2.05, "IBMPlexMono-SemiBold",
                "#3A362C", 0, "middle")
    s.append(h2)
    r, _ = txt("Challenge FIAP · NEXT 2026", ox + 6, oy + 51.2, 1.95,
               "IBMPlexSans-Regular", "#A09A86")
    s.append(r)
    return abrir + "".join(s) + "</svg>"


# ------------------------------------------------------------------ 3. camisetas
FIAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                    "assets", "logo-fiap.png")


def _fiap(x, y, larg):
    import base64
    b = base64.b64encode(open(FIAP, "rb").read()).decode()
    alt = larg * 642 / 2385
    return (f'<image x="{x:.2f}" y="{y:.2f}" width="{larg:.2f}" height="{alt:.2f}" '
            f'xlink:href="data:image/png;base64,{b}" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink"/>'), alt


def arte_peito(larg_mm=200):
    """Estampa do peito: marca horizontal negativa, para camiseta preta."""
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
                              folha=AMARELO, cor_texto=BRANCO, pad=2)
    esc = larg_mm / lw
    W, H = larg_mm, lh * esc
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
            f'viewBox="0 0 {W:.2f} {H:.2f}"><g transform="scale({esc:.5f})">{c}</g></svg>')


def arte_costas(larg_mm=260, larg_fiap=70, respiro=22):
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO, cubo=GRAFITE,
                              folha=AMARELO, cor_texto=BRANCO, pad=2)
    esc = larg_mm / lw
    h1 = lh * esc
    img, h2 = _fiap((larg_mm - larg_fiap) / 2, h1 + respiro, larg_fiap)
    W, H = larg_mm, h1 + respiro + h2
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.2f}mm" height="{H:.2f}mm" '
            f'viewBox="0 0 {W:.2f} {H:.2f}"><g transform="scale({esc:.5f})">{c}</g>{img}</svg>')


if __name__ == "__main__":
    grava("cartao-semente-frente", cartao_semente_frente())
    grava("cartao-semente-verso", cartao_semente_verso())
    grava("model-card-frente", model_card_frente())
    grava("model-card-verso", model_card_verso())
    grava("camiseta-frente-peito", arte_peito())
    grava("camiseta-costas", arte_costas())
    print("\n".join(sorted(os.listdir(OUT))))
