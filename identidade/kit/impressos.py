"""Resumo executivo A4 e model card A5 — frente e verso, para o flyer da Printi.

Medidas reais em milimetros (1 unidade do viewBox = 1 mm), sangria de 3 mm,
texto ja convertido em curvas. Todo numero vem de src/models/model_card.json:
nada aqui e digitado a mao, para a peca nao descolar do modelo.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brandkit import *
from sheet import lockup_inline
from pecas import pagina, txt, bloco, qr, grava, DESTINO_QR, MC

M = MC["metricas_teste"]
CM = M["matriz_confusao"]
SINISTROS = CM["verdadeiro_positivo"] + CM["falso_negativo"]   # 177
AVISADOS = CM["verdadeiro_positivo"]                            # 159
PERDIDOS = CM["falso_negativo"]                                 # 18
TOTAL_LEITURAS = sum(CM.values())                               # 961

PAPEL = "#FBFAF5"
TINTA = "#3A362C"       # corpo de texto
TINTA2 = "#6B6657"      # apoio
TINTA3 = "#A09A86"      # rodape
AMBAR = "#A06A00"       # rotulo de secao sobre fundo claro
LINHA = "#E7E3D6"

SANGRIA = 3.0


def num(v, casas=2):
    return f"{v:.{casas}f}".replace(".", ",")


# ---------------------------------------------------------------- blocos comuns
def rotulo(s, x, y, size=2.6, cor=AMBAR):
    return txt(s, x, y, size, "IBMPlexSans-SemiBold", cor, size * 0.17)[0]


def regua(x, y, larg, cor=LINHA, esp=0.25):
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{larg:.2f}" height="{esp}" fill="{cor}"/>'


def marca_topo(ox, oy, larg, cor_texto=GRAFITE, pneu=GRAFITE, aro=AMARELO,
               cubo=GRAFITE, folha=VERDE):
    c, lw, lh = lockup_inline("S", "mPrev Risk", pneu=pneu, aro=aro, cubo=cubo,
                              folha=folha, cor_texto=cor_texto, pad=2)
    esc = larg / lw
    return (f'<g transform="translate({ox:.2f} {oy:.2f}) scale({esc:.4f})">{c}</g>',
            lh * esc)


# ================================================================ RESUMO A4
A4_L, A4_A = 210.0, 297.0
BARRA = 8.0            # faixa amarela da lateral esquerda
ME = 26.0              # margem esquerda util (depois da barra)
MD = 18.0              # margem direita
COL = A4_L - ME - MD   # 166 mm de coluna de texto


def resumo_frente():
    abrir, corpo, W, H, ox, oy = pagina(A4_L, A4_A, SANGRIA, PAPEL)
    s = [corpo, f'<rect x="0" y="0" width="{SANGRIA + BARRA}" height="{H}" fill="{AMARELO}"/>']
    x = ox + ME

    m, mh = marca_topo(x, oy + 16, 62)
    s.append(m)

    # ---- manchete
    y = oy + 16 + mh + 26
    for i, (palavra, cor) in enumerate([("O sinistro", GRAFITE),
                                        ("que não aconteceu.", AMARELO_E)]):
        t, _ = txt(palavra, x, y + i * 13.2, 11.6, "Manrope-ExtraBold", cor, -0.35)
        s.append(t)
    y += 13.2 + 9
    t, _ = txt("Risco operacional de frota agrícola, previsto antes do acidente.",
               x, y, 4.3, "IBMPlexSans-Regular", TINTA2)
    s.append(t)
    y += 12
    s.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="44" height="1.4" fill="{AMARELO}"/>')

    # ---- o problema
    y += 15
    s.append(rotulo("O PROBLEMA", x, y))
    y += 7.5
    b, y = bloco("Seguro de frota agrícola age depois. A máquina tomba, a safra para, "
                 "alguém se machuca — e só então o sinistro existe para a seguradora.",
                 x, y, 4.0, COL, 1.5, "IBMPlexSans-SemiBold", GRAFITE)
    s.append(b)
    y += 8.5
    b, y = bloco("Toda a informação que teria evitado aquilo — declive do terreno, solo "
                 "encharcado pela chuva da noite, manutenção vencida, horas seguidas de "
                 "operação — já estava disponível antes. Só ninguém estava lendo.",
                 x, y, 3.3, COL, 1.55, "IBMPlexSans-Regular", TINTA)
    s.append(b)

    # ---- como funciona
    y += 16
    s.append(rotulo("COMO FUNCIONA, EM TRÊS LINHAS", x, y))
    y += 8
    passos = ["A máquina já informa onde está, como está o solo e há quanto tempo opera.",
              "O modelo transforma essa leitura em um score de 0 a 100 e uma faixa de risco.",
              "O alerta chega ao operador e à seguradora enquanto ainda dá para mudar a operação."]
    for i, p in enumerate(passos):
        n, _ = txt(str(i + 1), x, y, 5.2, "Manrope-ExtraBold", AMARELO_E, -0.1)
        s.append(n)
        b, yf = bloco(p, x + 9.5, y, 3.3, COL - 9.5, 1.5, "IBMPlexSans-Regular", TINTA)
        s.append(b)
        y = yf + 9.5

    # ---- os numeros
    y += 6
    s.append(regua(x, y, COL))
    y += 11
    s.append(rotulo("OS NÚMEROS QUE PROVAM", x, y))
    y += 20.5

    h, hw = txt(f'{M["recall"]*100:.0f}%', x, y, 21.0, "IBMPlexMono-SemiBold", GRAFITE, -0.6)
    s.append(h)
    t, _ = txt("dos sinistros são avisados", x + hw + 9, y - 10.2, 4.6,
               "IBMPlexSans-SemiBold", GRAFITE)
    s.append(t)
    t, _ = txt("antes de acontecer", x + hw + 9, y - 4.2, 4.6, "IBMPlexSans-SemiBold", GRAFITE)
    s.append(t)
    t, _ = txt("conjunto de teste — leituras que o modelo nunca viu", x + hw + 9, y + 1.6,
               3.0, "IBMPlexSans-Regular", TINTA2)
    s.append(t)

    y += 13
    b, y = bloco(f"Das {TOTAL_LEITURAS} leituras de teste, {SINISTROS} operações terminaram em "
                 f"sinistro. O SomPrev Risk avisou {AVISADOS} delas antes. Um seguro que só "
                 f"reage ficaria sabendo das {SINISTROS} depois.",
                 x, y, 3.3, COL, 1.55, "IBMPlexSans-Regular", TINTA)
    s.append(b)

    # ---- tres metricas
    y += 15
    met = [("PR-AUC", num(M["pr_auc"]), "qualidade do ranking de risco"),
           ("ROC-AUC", num(M["roc_auc"]), "separação entre risco e não risco"),
           ("BRIER", num(M["brier"], 3), "calibração da probabilidade")]
    cl = COL / 3
    for i, (rot, val, exp) in enumerate(met):
        cx = x + i * cl
        if i:
            s.append(f'<rect x="{cx - 7:.2f}" y="{y - 5.2:.2f}" width="0.25" height="17" fill="{LINHA}"/>')
        r, _ = txt(rot, cx, y, 2.4, "IBMPlexSans-SemiBold", TINTA3, 0.42)
        v, _ = txt(val, cx, y + 8.4, 7.4, "IBMPlexMono-SemiBold", GRAFITE, -0.12)
        e, _ = bloco(exp, cx, y + 13.6, 2.6, cl - 9, 1.35, "IBMPlexSans-Regular", TINTA2)
        s.append(r); s.append(v); s.append(e)

    # ---- rodape
    yr = oy + A4_A - 14
    s.append(regua(x, yr - 7, COL))
    t, _ = txt("Challenge FIAP · NEXT 2026", x, yr, 2.8, "IBMPlexSans-Regular", TINTA3, 0.3)
    s.append(t)
    t, _ = txt("continua no verso →", ox + A4_L - MD, yr, 2.8,
               "IBMPlexSans-SemiBold", AMBAR, 0.1, "end")
    s.append(t)
    return abrir + "".join(s) + "</svg>"


def resumo_verso():
    abrir, corpo, W, H, ox, oy = pagina(A4_L, A4_A, SANGRIA, PAPEL)
    s = [corpo, f'<rect x="0" y="0" width="{SANGRIA + BARRA}" height="{H}" fill="{AMARELO}"/>']
    x = ox + ME
    y = oy + 24

    s.append(rotulo("O QUE ISSO VALE PARA UMA SEGURADORA", x, y, 3.0))
    y += 11
    pontos = [
        ("Sinistro evitado é sinistro não pago.",
         f"O modelo não precisa acertar todos. Cada uma das {AVISADOS} leituras avisadas "
         f"é uma chance de intervir antes do acidente — e um acidente que não acontece "
         f"não entra na sinistralidade."),
        ("Risco observado, não risco médio.",
         f"O score é uma probabilidade calibrada (Brier {num(M['brier'], 3)}), medida "
         f"leitura a leitura. Duas máquinas da mesma frota, no mesmo dia, podem receber "
         f"tratamento diferente — sempre com revisão humana."),
        ("O alerta custa pouco; o sinistro custa caro.",
         f"Por isso o limiar não foi escolhido para acertar na média, e sim pelo menor "
         f"custo esperado: avisa mais do que o necessário para não deixar sinistro passar. "
         f"No teste isso significou alertar em {M['taxa_alerta']*100:.0f}% das operações "
         f"e ainda perder {PERDIDOS} dos {SINISTROS} sinistros."),
        ("O segurado recebe algo além da fatura.",
         "O mesmo aviso que protege a carteira chega ao operador como informação útil "
         "no dia de trabalho. É a diferença entre cobrar pelo risco e ajudar a reduzi-lo."),
    ]
    for titulo, texto in pontos:
        s.append(f'<rect x="{x:.2f}" y="{y - 3.0:.2f}" width="3.2" height="3.2" fill="{AMARELO}"/>')
        t, _ = txt(titulo, x + 7, y, 3.7, "IBMPlexSans-SemiBold", GRAFITE)
        s.append(t)
        b, yf = bloco(texto, x + 7, y + 6.4, 3.2, COL - 7, 1.55, "IBMPlexSans-Regular", TINTA)
        s.append(b)
        y = yf + 11

    # ---- como foi validado
    y += 3
    s.append(regua(x, y - 6, COL))
    s.append(rotulo("COMO FOI VALIDADO", x, y))
    y += 7.5
    b, y = bloco("Treino até 30/06/2026, validação em julho, teste em agosto — três períodos "
                 "separados no tempo, sem embaralhar as leituras. O teste usou apenas dados "
                 "posteriores a tudo que o modelo viu no treino, que é a única forma de não "
                 "enganar a si mesmo com série temporal.",
                 x, y, 3.2, COL, 1.55, "IBMPlexSans-Regular", TINTA)
    s.append(b)
    y += 7
    b, y = bloco(f'{MC["algoritmo"]} · {len(MC["variaveis"])} variáveis · '
                 f'scikit-learn {MC["scikit_learn"]} · {MC["versao"]}',
                 x, y, 2.8, COL, 1.4, "IBMPlexMono-SemiBold", TINTA2)
    s.append(b)

    # ---- limites
    y += 13
    s.append(rotulo("OS LIMITES, DITOS NA FRENTE", x, y))
    y += 7.5
    b, y = bloco("Os dados são simulados, como o enunciado permite — antes de qualquer uso "
                 "produtivo o modelo precisa ser recalibrado com sinistros reais. Seis meses "
                 "de série não cobrem um ciclo climático anual. E o modelo apoia decisão "
                 "preventiva: não nega cobertura nem precifica apólice sozinho.",
                 x, y, 3.2, COL, 1.55, "IBMPlexSans-Regular", TINTA)
    s.append(b)

    # ---- proximo passo
    y += 13
    s.append(rotulo("PRÓXIMO PASSO", x, y))
    y += 7.5
    b, y = bloco("Recalibrar com histórico real de sinistros. Rodar um piloto em uma frota "
                 "por uma safra, comparando operações com e sem alerta. Só então discutir "
                 "efeito em precificação.",
                 x, y, 3.2, COL, 1.55, "IBMPlexSans-Regular", TINTA)
    s.append(b)

    # ---- QR + assinatura
    # Ancorado no fim do texto, nao numa altura fixa: se algum bloco crescer, o
    # QR desce junto em vez de ser atropelado pela regua.
    y += 12
    s.append(regua(x, y, COL))
    yq = y + 11
    s.append(qr(DESTINO_QR, x, yq, 30, GRAFITE))
    t, _ = txt("O projeto inteiro", x + 38, yq + 11, 4.2, "IBMPlexSans-SemiBold", GRAFITE)
    s.append(t)
    t, _ = txt("código, modelo, documentação e vídeo", x + 38, yq + 17.6, 3.2,
               "IBMPlexSans-Regular", TINTA2)
    s.append(t)
    t, _ = txt("aponte a câmera", x + 38, yq + 23.4, 2.8, "IBMPlexSans-Regular", TINTA3)
    s.append(t)

    m, mh = marca_topo(ox + A4_L - MD - 52, yq + 2, 52)
    s.append(m)

    yr = oy + A4_A - 14
    t, _ = txt("Challenge FIAP · NEXT 2026", x, yr, 2.8, "IBMPlexSans-Regular", TINTA3, 0.3)
    s.append(t)
    return abrir + "".join(s) + "</svg>"


# ================================================================ MODEL CARD A5
A5_L, A5_A = 148.0, 210.0
MA5 = 14.0
COL5 = A5_L - 2 * MA5   # 120 mm


def model_card_a5_frente():
    abrir, corpo, W, H, ox, oy = pagina(A5_L, A5_A, SANGRIA, GRAFITE)
    s = [corpo]
    x = ox + MA5

    m, mh = marca_topo(x, oy + 16, 50, cor_texto=BRANCO, pneu=BRANCO, aro=AMARELO,
                       cubo=GRAFITE, folha=AMARELO)
    s.append(m)
    t, _ = txt("FICHA DO MODELO", ox + A5_L - MA5, oy + 16 + mh - 1.5, 2.6,
               "IBMPlexSans-SemiBold", AMARELO, 0.45, "end")
    s.append(t)
    y = oy + 16 + mh + 11
    s.append(regua(x, y, COL5, "#3A3728", 0.3))

    # ---- o numero que importa
    y += 27
    h, hw = txt(f'{M["recall"]*100:.0f}%', x, y, 26.0, "IBMPlexMono-SemiBold", AMARELO, -0.8)
    s.append(h)
    y += 10
    t, _ = txt("dos sinistros são avisados", x, y, 4.6, "IBMPlexSans-SemiBold", BRANCO)
    s.append(t)
    t, _ = txt("antes de acontecer", x, y + 6, 4.6, "IBMPlexSans-SemiBold", BRANCO)
    s.append(t)
    y += 13
    b, y = bloco(f"No conjunto de teste, {AVISADOS} dos {SINISTROS} sinistros foram sinalizados "
                 f"antes de ocorrer — em leituras de agosto de 2026, posteriores a tudo que o "
                 f"modelo viu no treino.",
                 x, y, 2.9, COL5, 1.5, "IBMPlexSans-Regular", "#A8A392")
    s.append(b)

    # ---- tres metricas
    y += 20
    s.append(regua(x, y - 10, COL5, "#3A3728", 0.3))
    met = [("PR-AUC", num(M["pr_auc"])), ("ROC-AUC", num(M["roc_auc"])),
           ("BRIER", num(M["brier"], 3))]
    cl = COL5 / 3
    for i, (rot, val) in enumerate(met):
        cx = x + i * cl
        if i:
            s.append(f'<rect x="{cx - 6:.2f}" y="{y - 5:.2f}" width="0.3" height="15" fill="#3A3728"/>')
        r, _ = txt(rot, cx, y, 2.2, "IBMPlexSans-SemiBold", "#908B78", 0.38)
        v, _ = txt(val, cx, y + 8, 6.6, "IBMPlexMono-SemiBold", BRANCO, -0.1)
        s.append(r); s.append(v)

    # ---- matriz de confusao, em palavras
    y += 28
    s.append(rotulo("O QUE ACONTECEU NAS 961 LEITURAS DE TESTE", x, y, 2.3, "#908B78"))
    y += 9
    barras = [(AVISADOS, "sinistros avisados antes", AMARELO),
              (PERDIDOS, "sinistros que passaram", "#C9552A"),
              (CM["falso_positivo"], "alertas sem sinistro", "#6B6657"),
              (CM["verdadeiro_negativo"], "operações liberadas, sem sinistro", "#3A3728")]
    maior = max(b[0] for b in barras)
    # Colunas fixas: barra ate 46 mm, numero alinhado pela direita em 58 e rotulo
    # em 63. Pendurar numero e rotulo no fim da barra faria cada linha comecar
    # num lugar diferente, e a leitura vertical se perde.
    LARG_MAX = 46.0
    for v, rot, cor in barras:
        larg = max(2.0, LARG_MAX * v / maior)
        s.append(f'<rect x="{x:.2f}" y="{y - 3.2:.2f}" width="{larg:.2f}" height="4.2" fill="{cor}"/>')
        t, _ = txt(str(v), x + 58, y, 3.2, "IBMPlexMono-SemiBold", BRANCO, 0, "end")
        s.append(t)
        t, _ = txt(rot, x + 63, y, 2.8, "IBMPlexSans-Regular", "#A8A392")
        s.append(t)
        y += 8.4

    # ---- rodape tecnico
    yr = oy + A5_A - 16
    s.append(regua(x, yr - 8, COL5, "#3A3728", 0.3))
    t, _ = txt(f'{MC["versao"]} · {MC["algoritmo"]} · {len(MC["variaveis"])} variáveis '
               f'· scikit-learn {MC["scikit_learn"]}', x, yr, 2.4,
               "IBMPlexSans-Regular", "#726D5E")
    s.append(t)
    return abrir + "".join(s) + "</svg>"


def model_card_a5_verso():
    abrir, corpo, W, H, ox, oy = pagina(A5_L, A5_A, SANGRIA, PAPEL)
    s = [corpo, f'<rect x="{ox:.2f}" y="{oy:.2f}" width="{A5_L}" height="5" fill="{AMARELO}"/>']
    x = ox + MA5
    y = oy + 22

    secoes = [
        ("PARA QUE SERVE",
         "Apoiar decisões preventivas antes e durante a operação de máquinas agrícolas: "
         "liberar, restringir ou suspender — e informar a gestão de risco da carteira."),
        ("FORA DO ESCOPO",
         "Negar cobertura ou precificar apólice de forma automática, sem revisão humana."),
        ("COMO FOI VALIDADO",
         "Treino até 30/06/2026, validação em julho, teste em agosto — períodos separados "
         "no tempo, sem embaralhar. O limiar foi escolhido pelo menor custo esperado e "
         "prioriza não deixar sinistro passar."),
        ("O QUE O MODELO LÊ",
         "Umidade e tipo de solo, chuva nas últimas 24 h, temperatura, declividade, "
         "distância de corpo d'água, idade do equipamento, horas desde a manutenção, "
         "horas de operação no dia, carga, tipo de operação e período do dia."),
        ("LIMITES",
         "Dados simulados, como o enunciado permite: recalibrar com sinistros reais antes "
         "de uso produtivo. Seis meses de série não cobrem um ciclo climático anual."),
    ]
    for rot, texto in secoes:
        s.append(rotulo(rot, x, y, 2.4))
        b, yf = bloco(texto, x, y + 6.4, 2.9, COL5, 1.5, "IBMPlexSans-Regular", TINTA)
        s.append(b)
        y = yf + 12.5

    # ---- QR + hash
    y = oy + A5_A - 62
    s.append(regua(x, y - 8, COL5))
    s.append(qr(DESTINO_QR, x, y, 26, GRAFITE))
    t, _ = txt("O projeto inteiro", x + 33, y + 9, 3.4, "IBMPlexSans-SemiBold", GRAFITE)
    s.append(t)
    t, _ = txt("código, modelo e vídeo", x + 33, y + 14.6, 2.8,
               "IBMPlexSans-Regular", TINTA2)
    s.append(t)
    t, _ = txt("SHA256 DO ARTEFATO", x + 33, y + 22.4, 2.1, "IBMPlexSans-SemiBold", TINTA3, 0.3)
    s.append(t)
    t, _ = txt(MC["hash_artefato_sha256"][:24], x + 33, y + 26.6, 2.5,
               "IBMPlexMono-SemiBold", TINTA)
    s.append(t)

    yr = oy + A5_A - 14
    t, _ = txt("Challenge FIAP · NEXT 2026", x, yr, 2.5, "IBMPlexSans-Regular", TINTA3, 0.3)
    s.append(t)
    return abrir + "".join(s) + "</svg>"


if __name__ == "__main__":
    feitos = [
        ("resumo-executivo-frente", resumo_frente(), A4_L, A4_A),
        ("resumo-executivo-verso", resumo_verso(), A4_L, A4_A),
        ("model-card-a5-frente", model_card_a5_frente(), A5_L, A5_A),
        ("model-card-a5-verso", model_card_a5_verso(), A5_L, A5_A),
    ]
    for nome, svg, l, a in feitos:
        grava(nome, svg)
        print(f"{nome}.svg  {l:.0f} x {a:.0f} mm (+{SANGRIA:.0f} mm de sangria)")
