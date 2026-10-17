#!/usr/bin/env python3
"""Imprime a apolice do visitante na termica de 58 mm.

Por que nao e HTML no navegador: a termica so entende ESC/POS, e no macOS as
58 mm baratas raramente aparecem como impressora do sistema. Entao o caminho e
outro -- a arte em SVG vira um bitmap de 384 pontos e vai direto para a
impressora como imagem. Mesmo desenho, sem driver, sem fila de impressao.

  Testar sem impressora (gera PNG igual ao que sairia no papel):
      python3 apolice.py --nome "Maria Sabrina" --score 78 --previa

  Imprimir de verdade, pela USB:
      python3 apolice.py --nome "Maria Sabrina" --score 78

  Descobrir o endereco USB da impressora:
      python3 apolice.py --procurar
"""
import argparse, os, random, sys, datetime, io

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

# 203 dpi e o padrao dessas impressoras: 8 pontos por milimetro.
DPI = 203.0
PX_MM = DPI / 25.4
LARG_PAPEL = 58.0     # mm, a bobina inteira
MARGEM = 5.0          # mm mortos de cada lado, que a cabeca nao alcanca
LARG_UTIL = 384       # pontos imprimiveis (48 mm)

FAIXAS = [(0, 25, "BAIXO"), (25, 50, "MEDIO"), (50, 75, "ALTO"), (75, 101, "CRITICO")]


def faixa_de(score):
    for lo, hi, nome in FAIXAS:
        if lo <= score < hi:
            return nome
    return "CRITICO"


def numero_apolice():
    """Numero de aparencia plausivel, sem fingir ser de uma apolice real."""
    return f"SP-{datetime.date.today().strftime('%y%m%d')}-{random.randint(100, 999)}"


def montar_svg(nome, score, equipamento, faixa=None, numero=None, data=None):
    """Gera o cupom JA com os valores dentro.

    Nao da para trocar texto no SVG pronto: a peca sai com tudo convertido em
    curvas, entao no arquivo final nao existe mais string nenhuma. O desenho e
    refeito do zero a cada visitante, o que custa milissegundos.
    """
    from estande import apolice_termica
    _, _, _, svg = apolice_termica(
        nome=nome.strip()[:24],
        score=int(score),
        faixa=(faixa or faixa_de(int(score))).upper(),
        equipamento=equipamento,
        numero=numero or numero_apolice(),
        data=data or datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        salvar=False,
    )
    return svg


def bitmap(svg_txt):
    """SVG -> imagem 1 bit de 384 pontos de largura, do jeito que a cabeca imprime.

    A termica nao tem meio-tom: cada ponto queima ou nao queima. Por isso o
    corte e em preto e branco puro por limiar, e nunca em dithering -- textura
    pontilhada numa bobina de 58 mm vira sujeira cinza.
    """
    import cairosvg
    from PIL import Image

    png = cairosvg.svg2png(bytestring=svg_txt.encode("utf-8"), dpi=DPI,
                           background_color="#FFFFFF")
    img = Image.open(io.BytesIO(png)).convert("L")

    corte = int(round(MARGEM * PX_MM))
    img = img.crop((corte, 0, corte + LARG_UTIL, img.height))
    if img.width != LARG_UTIL:                     # arredondamento do cairo
        img = img.resize((LARG_UTIL, img.height), Image.LANCZOS)
    return img.point(lambda p: 0 if p < 128 else 255, mode="1")


def procurar():
    """Lista o que esta plugado, para descobrir vendor/product id."""
    try:
        import usb.core
    except ImportError:
        raise SystemExit("falta a pyusb: pip3 install pyusb python-escpos")
    achou = False
    for d in usb.core.find(find_all=True):
        try:
            fab, prod = d.manufacturer, d.product
        except Exception:
            fab = prod = "(sem permissao de leitura)"
        print(f"  idVendor=0x{d.idVendor:04x}  idProduct=0x{d.idProduct:04x}  {fab} {prod}")
        achou = True
    if not achou:
        print("  nada encontrado. A impressora esta ligada e no cabo USB?")
    print("\nUse assim:  python3 apolice.py --nome ... --vendor 0x0416 --product 0x5011")


def imprimir(img, vendor, product, perfil):
    from escpos.printer import Usb
    p = Usb(vendor, product, profile=perfil)
    p.image(img, impl="bitImageRaster")
    p.ln(3)
    try:
        p.cut()        # nem toda 58 mm tem guilhotina; serrilha manual resolve
    except Exception:
        p.ln(2)
    p.close()


def main():
    ap = argparse.ArgumentParser(description="Apolice de demonstracao na termica 58 mm")
    ap.add_argument("--nome", default="Visitante")
    ap.add_argument("--score", type=int, default=72)
    ap.add_argument("--faixa", default=None, help="forca a faixa; padrao e deduzir do score")
    ap.add_argument("--equipamento", default="TRATOR 4X4 / 110 CV")
    ap.add_argument("--previa", action="store_true", help="salva PNG em vez de imprimir")
    ap.add_argument("--procurar", action="store_true", help="lista dispositivos USB")
    ap.add_argument("--vendor", default="0x0416", help="idVendor da impressora")
    ap.add_argument("--product", default="0x5011", help="idProduct da impressora")
    ap.add_argument("--perfil", default="TM-T88III", help="perfil ESC/POS")
    a = ap.parse_args()

    if a.procurar:
        return procurar()

    img = bitmap(montar_svg(a.nome, a.score, a.equipamento, a.faixa))

    if a.previa:
        saida = os.path.join(AQUI, "..", "pecas", "apolice-previa.png")
        img.save(saida)
        mm = img.height / PX_MM
        print(f"previa: {os.path.abspath(saida)}")
        print(f"{img.width} x {img.height} pontos  ({mm:.0f} mm de bobina)")
        return

    try:
        imprimir(img, int(a.vendor, 16), int(a.product, 16), a.perfil)
    except Exception as e:
        print(f"nao deu para imprimir: {e}\n", file=sys.stderr)
        print("Tente 'python3 apolice.py --procurar' para achar o endereco certo,\n"
              "e confira se a bobina esta com o lado termico para fora.", file=sys.stderr)
        raise SystemExit(1)
    print(f"impresso: {a.nome}  score {a.score}  {a.faixa or faixa_de(a.score)}")


if __name__ == "__main__":
    main()
