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
    """Lista o que o computador enxerga: portas seriais (Bluetooth) e USB.

    A termica portatil de 58 mm costuma ser Bluetooth. Depois de parear no
    macOS, ela aparece como uma porta serial em /dev/cu.ALGUMACOISA -- e e esse
    caminho que vai no --porta. Se for um modelo USB, use --vendor/--product.
    """
    import glob
    portas = sorted(set(glob.glob("/dev/cu.*") + glob.glob("/dev/tty.usb*")
                        + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/rfcomm*")))
    descartar = ("debug-console", "Bluetooth-Incoming")
    portas = [x for x in portas if not any(d in x for d in descartar)]
    print("PORTAS SERIAIS (impressora Bluetooth aparece aqui depois de pareada):")
    if portas:
        for x in portas:
            print(f"  {x}")
        print("\n  Use assim:  python3 apolice.py --nome \"Fulano\" --score 59 --porta <a porta acima>")
    else:
        print("  nenhuma. A impressora esta ligada e pareada no Bluetooth do Mac?")

    print("\nDISPOSITIVOS USB:")
    try:
        import usb.core
        dispositivos = list(usb.core.find(find_all=True))
    except ImportError:
        print("  (pyusb nao instalada: pip3 install pyusb python-escpos)")
        return
    except Exception as erro:
        # NoBackendError: a pyusb esta instalada mas falta a libusb do sistema
        # (brew install libusb). Nao importa para a termica Bluetooth, que vai
        # por porta serial -- entao avisa e sai, em vez de derrubar o comando.
        print(f"  (nao deu para listar: {type(erro).__name__} -- falta a libusb do sistema;")
        print("   irrelevante se a sua impressora e Bluetooth, use a porta serial acima)")
        return
    achou = False
    for d in dispositivos:
        try:
            fab, prod = d.manufacturer, d.product
        except Exception:
            fab = prod = "(sem permissao de leitura)"
        print(f"  idVendor=0x{d.idVendor:04x}  idProduct=0x{d.idProduct:04x}  {fab} {prod}")
        achou = True
    if not achou:
        print("  nenhum. Se a impressora for USB, confira o cabo.")
    else:
        print("\n  Use assim:  python3 apolice.py --nome ... --vendor 0x0416 --product 0x5011")


def _finalizar(p, img):
    # fragment_height: o python-escpos fatia imagens altas de 960 em 960 pontos
    # e manda um comando de raster por fatia. A apolice tem ~1500 pontos, e esta
    # termica perde o sincronismo entre uma fatia e outra: a primeira sai certa e
    # a segunda vira pagina e pagina de "?". Mandando a imagem inteira num
    # comando so, o problema deixa de existir.
    p.image(img, impl="bitImageRaster", fragment_height=img.height + 16)
    p.ln(3)
    try:
        p.cut()        # nem toda 58 mm tem guilhotina; serrilha manual resolve
    except Exception:
        p.ln(2)
    p.close()


def imprimir_usb(img, vendor, product, perfil):
    from escpos.printer import Usb
    _finalizar(Usb(vendor, product, profile=perfil), img)


def imprimir_serial(img, porta, baud, perfil):
    """Caminho da termica Bluetooth: depois de pareada, ela e uma porta serial.

    dsrdtr=False e obrigatorio aqui. O python-escpos liga controle de fluxo por
    HARDWARE (DSR/DTR) por padrao; numa porta serial de verdade existe um fio
    para esse sinal, mas numa porta Bluetooth ele nunca chega. O efeito e cruel:
    em vez de dar erro, a escrita fica bloqueada para sempre dentro de
    select()/tcdrain() e so sai com Ctrl+C.

    O write_timeout e o cinto de seguranca: se ainda assim travar, levanta erro
    em 20 segundos em vez de pendurar o terminal.
    """
    from escpos.printer import Serial
    p = Serial(devfile=porta, baudrate=baud, profile=perfil, dsrdtr=False, timeout=5)
    try:
        p.device.write_timeout = 20
    except Exception:
        pass
    _finalizar(p, img)


def main():
    ap = argparse.ArgumentParser(description="Apolice de demonstracao na termica 58 mm")
    ap.add_argument("--nome", default="Visitante")
    ap.add_argument("--score", type=int, default=72)
    ap.add_argument("--faixa", default=None, help="forca a faixa; padrao e deduzir do score")
    ap.add_argument("--equipamento", default="TRATOR 4X4 / 110 CV")
    ap.add_argument("--previa", action="store_true", help="salva PNG em vez de imprimir")
    ap.add_argument("--procurar", action="store_true",
                    help="lista portas seriais (Bluetooth) e dispositivos USB")
    ap.add_argument("--porta", default=None,
                    help="porta serial da termica Bluetooth, ex.: /dev/cu.PT-210")
    ap.add_argument("--baud", type=int, default=9600,
                    help="velocidade da porta serial (9600 na maioria; 115200 em algumas)")
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
        if a.porta:
            imprimir_serial(img, a.porta, a.baud, a.perfil)
        else:
            imprimir_usb(img, int(a.vendor, 16), int(a.product, 16), a.perfil)
    except Exception as e:
        print(f"nao deu para imprimir: {e}\n", file=sys.stderr)
        print("Rode 'python3 apolice.py --procurar' para ver as portas e os USB.\n"
              "Se a impressora for Bluetooth, pareie no macOS e passe --porta /dev/cu.ALGO\n"
              "(se nao sair nada, tente --baud 115200).\n"
              "Confira tambem se a bobina esta com o lado termico para fora.", file=sys.stderr)
        raise SystemExit(1)
    print(f"impresso: {a.nome}  score {a.score}  {a.faixa or faixa_de(a.score)}")


if __name__ == "__main__":
    main()
