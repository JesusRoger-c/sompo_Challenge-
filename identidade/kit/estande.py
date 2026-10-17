"""Peças do estande: apólice térmica, mini roll-up de mesa e model card A5.

Medidas reais em milímetros, texto já em curvas, QR gerado na hora.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *
from sheet import lockup_inline, lockup_stack
from pecas import pagina, txt, bloco, qr, DESTINO_QR, REPO, VIDEO, MC

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pecas")


# ------------------------------------------------------------------ apólice térmica
def apolice_termica(nome="{{NOME}}", score="{{SCORE}}", faixa="{{FAIXA}}",
                    equipamento="{{EQUIPAMENTO}}", numero="{{NUMERO}}",
                    data="{{DATA}}", salvar=True):
    """Cupom impresso ao vivo na térmica de 58 mm.

    Os valores entram AQUI, na geração, e não por substituição no SVG pronto:
    o texto desta peça já sai convertido em curvas, então no arquivo final não
    existe mais string nenhuma para trocar. Sem argumento, gera o molde com os
    campos visíveis, que serve só para conferir o desenho.

    A impressora só sabe queimar ou não queimar um ponto: não existe cinza, nem
    cor, nem tom de cinza disfarçado de cor clara. Por isso tudo aqui é preto
    puro sobre branco, com fio mínimo de 0,3 mm — abaixo disso some na bobina.
    Área útil de 48 mm (384 pontos a 203 dpi) dentro dos 58 mm do papel.
    """
    L, A = 58.0, 150.0
    m = 5.0                      # margem morta de cada lado
    w = L - 2 * m                # 48 mm úteis
    P = "#000000"
    s = [f'<rect width="{L}" height="{A}" fill="#FFFFFF"/>']

    def linha(y, esp=0.4, tracejada=False):
        d = ' stroke-dasharray="1.2 1.2"' if tracejada else ''
        return (f'<rect x="{m}" y="{y:.1f}" width="{w}" height="{esp}" fill="{P}"/>'
                if not tracejada else
                f'<line x1="{m}" y1="{y:.1f}" x2="{m+w}" y2="{y:.1f}" stroke="{P}" '
                f'stroke-width="{esp}"{d}/>')

    y = 10.0
    # marca, em curvas e sem meio-tom
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=P, aro="none", cubo=P,
                              folha=P, cor_texto=P, pad=1)
    esc = 40 / lw
    s.append(f'<g transform="translate({m + (w-40)/2:.2f} {y:.2f}) scale({esc:.4f})">{c}</g>')
    y += lh * esc + 5

    # 2,35 mm com pouco tracking: a 2,6 o título estourava os 48 mm úteis e a
    # cabeça cortava as duas pontas.
    t, _ = txt("APÓLICE DE RISCO OPERACIONAL", L/2, y, 2.35, "IBMPlexSans-SemiBold", P, 0.16, "middle")
    s.append(t); y += 4.5
    s.append(linha(y, 0.5)); y += 5.5

    def campo(rotulo, valor, mono=True, alt=5.6):
        nonlocal y
        a, _ = txt(rotulo, m, y, 2.3, "IBMPlexSans-Regular", P)
        b, _ = txt(valor, m + w, y, 2.9,
                   "IBMPlexMono-SemiBold" if mono else "IBMPlexSans-SemiBold", P, 0, "end")
        s.append(a); s.append(b); y += alt

    campo("Apólice nº", numero)
    campo("Emitida em", data)
    campo("Segurado", nome, mono=False)
    campo("Equipamento", equipamento)
    y += 1.5
    s.append(linha(y, 0.4, True)); y += 7.5

    # o score, que é o motivo do papel existir
    t, _ = txt("SCORE DE RISCO NA LEITURA", L/2, y, 2.3, "IBMPlexSans-SemiBold", P, 0.2, "middle")
    s.append(t); y += 13.5
    n, _ = txt(str(score), L/2, y, 15.0, "IBMPlexMono-SemiBold", P, -0.3, "middle")
    s.append(n); y += 6.0
    f, _ = txt(str(faixa), L/2, y, 4.2, "Manrope-ExtraBold", P, 0, "middle")
    s.append(f); y += 7.0
    s.append(linha(y, 0.4, True)); y += 6.0

    t, _ = txt("O QUE ESTA APÓLICE COBRE", m, y, 2.3, "IBMPlexSans-SemiBold", P, 0.2)
    s.append(t); y += 5.0
    for item in ["Terreno em declive acima do limite",
                 "Solo saturado por chuva recente",
                 "Fadiga: horas de operação sem parada",
                 "Manutenção vencida da máquina"]:
        p, _ = txt("·", m + 0.5, y, 2.6, "IBMPlexSans-SemiBold", P)
        b, yf = bloco(item, m + 3.2, y, 2.5, w - 3.2, 1.35, "IBMPlexSans-Regular", P)
        s.append(p); s.append(b); y = yf + 4.6
    y += 1.0
    s.append(linha(y, 0.4, True)); y += 5.5

    b, yf = bloco("Vigência: enquanto o dado chegar antes do acidente.",
                  m, y, 2.5, w, 1.35, "IBMPlexSans-SemiBold", P)
    s.append(b); y = yf + 7.0

    s.append(qr(DESTINO_QR, L/2 - 11, y, 22, P))
    y += 25.5
    t, _ = txt("O projeto inteiro", L/2, y, 2.4, "IBMPlexSans-SemiBold", P, 0, "middle")
    s.append(t); y += 4.2
    t, _ = txt("código, modelo e vídeo", L/2, y, 2.2, "IBMPlexSans-Regular", P, 0, "middle")
    s.append(t); y += 7.0

    t, _ = txt("Simulação de demonstração.", L/2, y, 2.2, "IBMPlexSans-Regular", P, 0, "middle")
    s.append(t); y += 3.8
    t, _ = txt("Não é contrato de seguro.", L/2, y, 2.2, "IBMPlexSans-Regular", P, 0, "middle")
    s.append(t); y += 5.5
    t, _ = txt("Challenge FIAP · NEXT 2026", L/2, y, 2.2, "IBMPlexSans-Regular", P, 0.1, "middle")
    s.append(t)

    # A bobina e continua: a altura do cupom e o conteudo, nao um papel fixo.
    # Fecha com 8 mm de sobra para o corte da serrilha.
    A = round(y + 8, 1)
    s[0] = f'<rect width="{L}" height="{A}" fill="#FFFFFF"/>'
    svg_txt = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}mm" height="{A}mm" '
               f'viewBox="0 0 {L} {A}">{"".join(s)}</svg>')
    if salvar:
        open(f"{OUT}/apolice-termica.svg", "w").write(svg_txt)
    return "apolice-termica", L, A, svg_txt


# ------------------------------------------------------------------ mini roll-up
def mini_rollup(guia=False):
    """30 x 42 cm, fica em pe sozinho atras a esquerda da bancada.

    E a peca lida de longe, do corredor: a frase tem que bater antes da marca.
    Os 8 cm de baixo somem dentro da estrutura retratil, entao nada entra la.
    guia=True desenha a marcacao dessa faixa -- so para o grupo, nunca para a
    grafica: anotacao dentro de arte vira anotacao impressa.
    """
    L, A = 300.0, 420.0
    BASE_MORTA = 80.0
    m = 30.0
    PAPEL, AMARELO_E, TINTA2 = "#FBFAF5", "#E0A500", "#4A463A"
    s = [f'<rect width="{L}" height="{A}" fill="{PAPEL}"/>',
         f'<rect x="0" y="0" width="11" height="{A}" fill="{AMARELO}"/>']

    c, lw, lh = lockup_inline("S", "mPrev Risk", pad=2)
    esc = 148 / lw
    s.append(f'<g transform="translate({m:.1f} 40) scale({esc:.4f})">{c}</g>')

    for base, palavra, cor in [(112, "O sinistro", GRAFITE),
                               (151, "que nao", GRAFITE),
                               (190, "aconteceu.", AMARELO_E)]:
        t, _ = txt(palavra.replace("nao", "n\u00e3o"), m, base, 34, "Manrope-ExtraBold", cor, -1.0)
        s.append(t)

    s.append(f'<rect x="{m}" y="210" width="70" height="5" fill="{AMARELO}"/>')
    b, _ = bloco("Risco de frota agricola, previsto antes do acidente."
                 .replace("agricola", "agr\u00edcola"),
                 m, 238, 14, L - 2 * m - 12, 1.45, "IBMPlexSans-Regular", TINTA2)
    s.append(b)

    qr_y, qr_lado = 276, 46
    s.append(qr(DESTINO_QR, m, qr_y, qr_lado, GRAFITE))
    t, _ = txt("Codigo, modelo e video".replace("Codigo", "C\u00f3digo").replace("video", "v\u00eddeo"),
               m + qr_lado + 14, qr_y + 22, 11.5, "IBMPlexSans-SemiBold", GRAFITE)
    s.append(t)
    t, _ = txt("aponte a camera".replace("camera", "c\u00e2mera"),
               m + qr_lado + 14, qr_y + 36, 10.5, "IBMPlexSans-Regular", "#6B6657")
    s.append(t)
    t, _ = txt("Challenge FIAP \u00b7 NEXT 2026", m, A - BASE_MORTA - 4, 10,
               "IBMPlexSans-Regular", "#8A8578", 0.4)
    s.append(t)

    if guia:
        s.append(f'<rect x="0" y="{A-BASE_MORTA}" width="{L}" height="{BASE_MORTA}" '
                 f'fill="#17160F" opacity="0.07"/>')
        s.append(f'<line x1="0" y1="{A-BASE_MORTA}" x2="{L}" y2="{A-BASE_MORTA}" '
                 f'stroke="#9A9486" stroke-width="0.8" stroke-dasharray="5 4"/>')
        t, _ = txt("8 cm engolidos pela estrutura retratil - nao colocar nada aqui"
                   .replace("retratil", "retr\u00e1til").replace("nao", "n\u00e3o"),
                   L/2, A - BASE_MORTA + 22, 9, "IBMPlexSans-Regular", "#7A7568", 0, "middle")
        s.append(t)

    nome = "mini-rollup-guia" if guia else "mini-rollup"
    open(f"{OUT}/{nome}.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}mm" height="{A}mm" '
        f'viewBox="0 0 {L} {A}">{"".join(s)}</svg>')
    return nome, L, A


# ------------------------------------------------------------------ placa rigida
def placa_bancada():
    """30 x 42 cm, em pe atras a esquerda: a peca lida do corredor.

    E a unica peca escura do estande, e e de proposito. Tudo em cima da bancada
    e papel claro; se esta tambem fosse, sumiria no meio. Em grafite ela recorta
    contra a mesa e faz a bancada existir de longe.

    A roda entra gigante, sangrada pelo canto inferior direito, em tom sobre tom:
    de perto se ve que e o simbolo da marca, de longe e so textura que impede o
    fundo de virar um retangulo preto morto. O aro em amarelo queimado e a unica
    coisa que brilha ali embaixo, e puxa o olho para o QR ao lado.
    """
    L, A = 300.0, 420.0
    m = 30.0
    abrir, corpo, W, H, ox, oy = pagina(L, A, 3.0, GRAFITE)
    s = [corpo]
    x = ox + m

    # roda sangrando pelo canto, tom sobre tom
    s.append(roda(ox + L + 18, oy + A + 10, 196,
                  cor_pneu="#221E12", cor_aro="#2C2616", cor_cubo="#221E12"))

    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=BRANCO, aro=AMARELO,
                              cubo=GRAFITE, folha=AMARELO, cor_texto=BRANCO, pad=2)
    esc = 146 / lw
    s.append(f'<g transform="translate({x:.1f} {oy + 36:.1f}) scale({esc:.4f})">{c}</g>')

    for i, (palavra, cor) in enumerate([("O sinistro", BRANCO),
                                        ("que não", BRANCO),
                                        ("aconteceu.", AMARELO)]):
        t, _ = txt(palavra, x, oy + 136 + i * 50, 44, "Manrope-ExtraBold", cor, -1.4)
        s.append(t)

    s.append(f'<rect x="{x:.1f}" y="{oy + 268:.1f}" width="92" height="6" fill="{AMARELO}"/>')
    b, _ = bloco("Risco de frota agrícola, previsto antes do acidente.",
                 x, oy + 292, 15, 210, 1.45, "IBMPlexSans-Regular", "#B6AF9B")
    s.append(b)

    # o QR precisa de fundo claro para ler: vira um cartao branco sobre o grafite
    cx, cy, lado, pad = x, oy + 332, 46.0, 6.0
    s.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{lado + 2*pad:.1f}" '
             f'height="{lado + 2*pad:.1f}" rx="4" fill="#FBFAF5"/>')
    s.append(qr(DESTINO_QR, cx + pad, cy + pad, lado, GRAFITE))
    t, _ = txt("Código, modelo e vídeo", cx + lado + 2 * pad + 16, cy + 26, 13.0,
               "IBMPlexSans-SemiBold", BRANCO)
    s.append(t)
    t, _ = txt("aponte a câmera", cx + lado + 2 * pad + 16, cy + 41, 12.0,
               "IBMPlexSans-Regular", "#8F897A")
    s.append(t)

    t, _ = txt("Challenge FIAP · NEXT 2026", x, oy + A - 13, 11.0,
               "IBMPlexSans-Regular", "#6E6859", 0.45)
    s.append(t)

    open(f"{OUT}/placa-bancada.svg", "w").write(abrir + "".join(s) + "</svg>")
    return "placa-bancada", L, A


# ------------------------------------------------------------------ placa do QR
def placa_qr():
    """12 x 16 cm em pe sobre a bancada: os destinos que o visitante leva embora.

    Quem nao tem tempo de conversar aponta a camera e vai embora com o projeto.
    Por isso cada QR vem com legenda dizendo o que ele abre -- QR sem legenda
    ninguem aponta.
    """
    L, A = 120.0, 160.0
    TINTA2, TINTA3 = "#4A463A", "#8A8578"
    abrir, corpo, W, H, ox, oy = pagina(L, A, 3.0, PAPEL := "#FBFAF5")
    s = [corpo]
    cx = ox + L / 2

    # Esta e a unica peca simetrica do conjunto. Todo o resto e alinhado a
    # esquerda; aqui o eixo central e o proprio assunto -- dois destinos lado a
    # lado, mesmo peso, escolha do visitante. E o simbolo aparece sozinho, sem o
    # nome, porque a marca ja esta dita em tudo que esta em volta na bancada.
    s.append(simbolo(cx, oy + 30, 11.5))

    t, _ = txt("Leve o projeto", cx, oy + 56, 8.2, "Manrope-ExtraBold",
               GRAFITE, -0.22, "middle")
    s.append(t)
    t, _ = txt("aponte a câmera do celular", cx, oy + 64, 3.3,
               "IBMPlexSans-Regular", TINTA2, 0, "middle")
    s.append(t)

    lado, gap = 42.0, 12.0
    x0 = cx - lado - gap / 2
    destinos = [(REPO, "O código", "repositório e modelo"),
                (VIDEO, "O vídeo", "demonstração de 3 min")]
    for i, (destino, titulo, legenda) in enumerate(destinos):
        bx = x0 + i * (lado + gap)
        s.append(qr(destino, bx, oy + 76, lado, GRAFITE))
        t, _ = txt(titulo, bx + lado / 2, oy + 130, 4.6,
                   "IBMPlexSans-SemiBold", GRAFITE, 0, "middle")
        s.append(t)
        t, _ = txt(legenda, bx + lado / 2, oy + 136, 2.9,
                   "IBMPlexSans-Regular", TINTA2, 0, "middle")
        s.append(t)

    s.append(f'<rect x="{cx - 14:.1f}" y="{oy + 144:.1f}" width="28" height="1.2" '
             f'fill="{AMARELO}"/>')
    t, _ = txt("Challenge FIAP · NEXT 2026", cx, oy + A - 10, 2.9,
               "IBMPlexSans-Regular", TINTA3, 0.3, "middle")
    s.append(t)

    open(f"{OUT}/placa-qr.svg", "w").write(abrir + "".join(s) + "</svg>")
    return "placa-qr", L, A


# ------------------------------------------------------------------ placa de mesa
def placa_mesa_frente():
    """15 x 8 cm deitada, na borda da frente: o convite para encostar no trator.

    Fundo amarelo porque e a unica peca que pede uma acao -- precisa destoar do
    resto da bancada, que e papel claro. Texto curto e grande: tem que ser lida
    de pe, a um metro, por quem esta so passando.
    """
    L, A = 150.0, 80.0
    m = 14.0
    abrir, corpo, W, H, ox, oy = pagina(L, A, 3.0, AMARELO)
    s = [corpo]
    x = ox + m

    t, _ = txt("DEMONSTRAÇÃO AO VIVO", x, oy + 20, 3.0,
               "IBMPlexSans-SemiBold", "#6B4A00", 0.62)
    s.append(t)
    t, _ = txt("Pode inclinar o trator", x, oy + 42, 10.5, "Manrope-ExtraBold",
               GRAFITE, -0.3)
    s.append(t)
    t, w = txt("e ver o risco subir na tela", x, oy + 56, 5.4,
               "IBMPlexSans-SemiBold", "#3A2E00")
    s.append(t)
    seta, _ = txt("→", x + w + 6, oy + 56, 5.4, "IBMPlexSans-SemiBold", "#3A2E00")
    s.append(seta)

    open(f"{OUT}/placa-mesa-frente.svg", "w").write(abrir + "".join(s) + "</svg>")
    return "placa-mesa-frente", L, A


def placa_mesa_verso():
    """O verso aponta para voces, nao para o corredor: vira cola do roteiro.

    Quem esta no turno da bancada le de relance e nao trava. Por isso o verso
    existe -- do contrario seria frente e verso pagando por um lado em branco.
    """
    L, A = 150.0, 80.0
    m = 14.0
    TINTA2 = "#4A463A"
    abrir, corpo, W, H, ox, oy = pagina(L, A, 3.0, PAPEL := "#FBFAF5")
    s = [corpo, f'<rect x="{ox:.1f}" y="{oy:.1f}" width="{L}" height="3.5" fill="{AMARELO}"/>']
    x = ox + m

    t, _ = txt("ROTEIRO DE 30 SEGUNDOS", x, oy + 17, 2.8,
               "IBMPlexSans-SemiBold", "#A06A00", 0.55)
    s.append(t)

    passos = ["Peça para a pessoa inclinar o trator na rampa.",
              "Mostre o score subindo no tablet, ao vivo.",
              "Pergunte o nome e imprima a apólice dela."]
    y = oy + 29
    for i, p in enumerate(passos):
        n, _ = txt(str(i + 1), x, y + i * 11, 5.0, "Manrope-ExtraBold", AMARELO_E := "#E0A500")
        s.append(n)
        t, _ = txt(p, x + 8, y + i * 11, 4.0, "IBMPlexSans-Regular", GRAFITE)
        s.append(t)

    t, _ = txt("Se perguntarem o número: 90% dos sinistros avisados antes · PR-AUC 0,76",
               x, oy + A - 13, 3.0, "IBMPlexSans-Regular", TINTA2)
    s.append(t)

    open(f"{OUT}/placa-mesa-verso.svg", "w").write(abrir + "".join(s) + "</svg>")
    return "placa-mesa-verso", L, A


if __name__ == "__main__":
    for feito in [apolice_termica(), mini_rollup(), mini_rollup(guia=True),
                  placa_bancada(), placa_qr(),
                  placa_mesa_frente(), placa_mesa_verso()]:
        n, l, a = feito[0], feito[1], feito[2]
        print(f"{n}.svg  {l:.0f} x {a:.0f} mm")
