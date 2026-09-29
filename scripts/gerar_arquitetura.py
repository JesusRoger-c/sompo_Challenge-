#!/usr/bin/env python3
"""
Gera o diagrama de arquitetura FINAL do SomPrev Risk (Sprint 4) em SVG e PNG.

Uso (a partir da raiz):  python scripts/gerar_arquitetura.py
Saidas:                  document/arquitetura.svg e document/arquitetura.png
O PNG exige a biblioteca opcional `cairosvg`; sem ela, apenas o SVG e gerado.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from somprev import tema  # noqa: E402

W, H = 1680, 860
CW, GAP = 250, 24
X = [28 + i * (CW + GAP) for i in range(6)]
FONTE = "Roboto, 'Noto Sans', 'DejaVu Sans', Arial, sans-serif"
MONO = "'Roboto Mono', 'DejaVu Sans Mono', monospace"
V, VE, G = tema.VERMELHO_INSTITUCIONAL, tema.VERMELHO_ESCURO, tema.GRAFITE
CINZA, LINHA, SUAVE = tema.CINZA_MEDIO, tema.LINHA, tema.VERMELHO_SUAVE


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def caixa(x, y, w, h, titulo, itens, destaque=False, numero=None):
    fundo = SUAVE if destaque else "#FFFFFF"
    borda = V if destaque else "#CFCFCF"
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fundo}" stroke="{borda}" '
           f'stroke-width="{1.8 if destaque else 1.2}"/>']
    if numero:
        out.append(f'<circle cx="{x + 22}" cy="{y + 24}" r="12" fill="{VE}"/>'
                   f'<text x="{x + 22}" y="{y + 28.5}" text-anchor="middle" font-family="{FONTE}" '
                   f'font-size="12" font-weight="700" fill="#fff">{numero}</text>')
    tx = x + (42 if numero else 16)
    out.append(f'<text x="{tx}" y="{y + 29}" font-family="{FONTE}" font-size="15" font-weight="700" '
               f'fill="{G}">{esc(titulo)}</text>')
    for i, item in enumerate(itens):
        out.append(f'<text x="{x + 16}" y="{y + 54 + i * 19}" font-family="{FONTE}" font-size="12" '
                   f'fill="#3A3A3A">• {esc(item)}</text>')
    return "\n".join(out)


def seta(x1, y1, x2, y2, rotulo=None, tracejada=False):
    traco = ' stroke-dasharray="6 5"' if tracejada else ""
    out = f'<path d="M {x1} {y1} L {x2} {y2}" stroke="{V}" stroke-width="2.2" fill="none"{traco} ' \
          f'marker-end="url(#ponta)"/>'
    if rotulo:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 7
        out += (f'<text x="{mx}" y="{my}" text-anchor="middle" font-family="{MONO}" font-size="10.5" '
                f'fill="{CINZA}">{esc(rotulo)}</text>')
    return out


def coluna(x, w, texto):
    return (f'<rect x="{x}" y="96" width="{w}" height="26" rx="6" fill="{G}"/>'
            f'<text x="{x + w / 2}" y="114" text-anchor="middle" font-family="{MONO}" font-size="11.5" '
            f'font-weight="700" fill="#fff" letter-spacing="1.5">{texto}</text>')


def montar() -> str:
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<defs><marker id="ponta" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">'
         f'<path d="M0,0 L8,4 L0,8 Z" fill="{V}"/></marker>'
         f'<linearGradient id="topo" x1="0" x2="1"><stop offset="0" stop-color="{VE}"/>'
         f'<stop offset="1" stop-color="{V}"/></linearGradient></defs>',
         f'<rect width="{W}" height="{H}" fill="{tema.CINZA_CLARO}"/>',
         f'<rect width="{W}" height="72" fill="url(#topo)"/>',
         f'<text x="28" y="44" font-family="{FONTE}" font-size="25" font-weight="700" fill="#fff">'
         f'SomPrev Risk — arquitetura final do MVP (Sprint 4)</text>',
         f'<text x="{W - 28}" y="44" text-anchor="end" font-family="{FONTE}" font-size="13" fill="#fff">'
         f'entrada → qualidade → banco → modelo → regras → saída · Challenge FIAP + Sompo Seguros</text>']

    for x, t in zip(X, ["ENTRADA", "INGESTÃO", "QUALIDADE", "BANCO", "INTELIGÊNCIA", "SAÍDA"]):
        s.append(coluna(x, CW, t))
    a, b, c, d, e, f = X

    s.append(caixa(a, 140, CW, 150, "Telemetria de campo", [
        "sensores de solo e clima", "uso da máquina (horas, carga)", "tipo de operação e terreno",
        "coletor → JSON via HTTPS", "(simulada: permitido)"], numero=1))
    s.append(caixa(a, 310, CW, 118, "Carga histórica", [
        "coleta_bruta.csv (6 meses)", "cadastro da frota", "falhas reais de coleta", "injetadas p/ validação"]))
    s.append(caixa(a, 448, CW, 100, "Simulador (teste)", [
        "python run.py simular", "envios bons e defeituosos", "reconciliação automática"]))

    s.append(caixa(b, 140, CW, 180, "API FastAPI", [
        "POST /telemetria (e /lote)", "chave de ingestão (escopo)", "limite de taxa → 429",
        "payload estrito (Pydantic)", "erros tratados, sem vazar", "X-Request-ID + log JSON"], True, 2))
    s.append(caixa(b, 340, CW, 100, "Pipeline em lote", [
        "python run.py pipeline", "7 etapas reprodutíveis", "mesma seed → mesmos números"], numero=2))

    s.append(caixa(c, 140, CW, 208, "Qualidade de dados", [
        "duplicidade / reenvio → bloqueio", "\"55,3\" e \"Manhã\" → padroniza", "fora da faixa física → ausente",
        "imputa: região/dia, cadastro,", "   histórico da máquina", "crítico ausente → quarentena",
        "toda correção registrada"], True, 3))
    s.append(caixa(c, 368, CW, 80, "Quarentena", ["tabela + motivo da rejeição", "nada é descartado em silêncio"]))

    s.append(caixa(d, 140, CW, 238, "SQLite (WAL)", [
        "regiões · equipamentos", "leituras (+ hash do payload)", "predições (versões + explicação)",
        "alertas (ciclo de vida)", "manutenções · usuários", "auditoria (append-only)", "versões do modelo",
        "CHECK + FK + UNIQUE", "transação atômica por leitura"], True, 4))

    s.append(caixa(e, 140, CW, 190, "Modelo de risco v2", [
        "HistGradientBoosting calibrado", "validação temporal (mar→ago)", "PR-AUC 0,76 · recall 82%",
        "score 0-100 = prob. × 100", "explicação por variável", "model card + hash SHA-256"], True, 5))
    s.append(caixa(e, 350, CW, 150, "Regras e alertas", [
        "regras_risco.json versionado", "faixas 0-14 / 15-39 / 40-69 / 70+", "limiar por custo: score ≥ 15",
        "5 gatilhos explícitos", "agrupamento (anti-fadiga)"], True, 6))

    s.append(caixa(f, 140, CW, 210, "Dashboard (4 perfis)", [
        "Operador: semáforo + por quê", "Técnico: fila de manutenção", "Gestor: tendências e regras",
        "Seguradora: validação e auditoria", "login PBKDF2 + bloqueio", "permissões por perfil"], True, 7))
    s.append(caixa(f, 370, CW, 110, "API de consulta", [
        "leitura + trilha de auditoria", "tendências · alertas · modelo", "verificação da cadeia"]))
    s.append(caixa(f, 500, CW, 100, "Relatórios", [
        "tendência região/operação", "ranking de equipamentos", "Markdown + PNG + CSV"]))

    s += [seta(a + CW, 212, b, 212), seta(a + CW, 368, b, 385), seta(a + CW, 498, b, 280, tracejada=True),
          seta(b + CW, 230, c, 230), seta(b + CW, 390, c, 300),
          seta(c + CW / 2, 348, c + CW / 2, 368), seta(c + CW, 250, d, 250), seta(c + CW, 408, d, 330),
          seta(d + CW, 230, e, 230), seta(e + CW / 2, 330, e + CW / 2, 350), seta(d + CW, 330, e, 420),
          seta(e + CW, 245, f, 245), seta(e + CW, 425, f, 425), seta(e + CW, 470, f, 550)]

    # Faixa de seguranca e rastreabilidade (transversal)
    y = 650
    s.append(f'<rect x="28" y="{y}" width="{W - 56}" height="112" rx="12" fill="#FFFFFF" stroke="{G}" '
             f'stroke-width="1.4" stroke-dasharray="7 5"/>')
    s.append(f'<text x="48" y="{y + 30}" font-family="{FONTE}" font-size="15" font-weight="700" fill="{G}">'
             f'Segurança e rastreabilidade (transversal a todas as etapas)</text>')
    blocos = [
        ("Auditoria encadeada", "SHA-256 evento a evento; triggers impedem UPDATE/DELETE; verificação detecta adulteração"),
        ("Controle de acesso", "4 perfis com permissões explícitas; 2 chaves de API por escopo; sessão expira em 30 min"),
        ("Proteção de dados", "senhas só em hash PBKDF2 (600 mil it.); segredos só no .env; logs mascaram chaves"),
        ("Integridade", "hash do payload na leitura; hash do modelo; 12 verificações automáticas; 105 testes"),
    ]
    for i, (titulo, texto) in enumerate(blocos):
        bx = 48 + i * 400
        s.append(f'<text x="{bx}" y="{y + 60}" font-family="{FONTE}" font-size="13" font-weight="700" '
                 f'fill="{VE}">{esc(titulo)}</text>')
        palavras, linha, linhas = texto.split(), "", []
        for p in palavras:
            if len(linha) + len(p) > 54:
                linhas.append(linha)
                linha = p
            else:
                linha = f"{linha} {p}".strip()
        linhas.append(linha)
        for j, l in enumerate(linhas):
            s.append(f'<text x="{bx}" y="{y + 80 + j * 16}" font-family="{FONTE}" font-size="11.5" '
                     f'fill="#3A3A3A">{esc(l)}</text>')

    s.append(f'<text x="28" y="{H - 60}" font-family="{MONO}" font-size="12" fill="{CINZA}">Fluxo de uma leitura: '
             f'coletor → API (chave + validação) → qualidade (corrige/imputa/quarentena) → transação: leitura + '
             f'predição + explicação + alertas + auditoria → dashboard/relatórios.</text>')
    s.append(f'<text x="28" y="{H - 38}" font-family="{MONO}" font-size="12" fill="{CINZA}">Comandos: '
             f'python run.py configurar | pipeline | api | dashboard | simular | verificar | testes</text>')
    s.append("</svg>")
    return "\n".join(s)


def main() -> None:
    destino = RAIZ / "document"
    svg = montar()
    (destino / "arquitetura.svg").write_text(svg, encoding="utf-8")
    print(f"[OK] {destino / 'arquitetura.svg'}")
    try:
        import cairosvg
    except ImportError:
        print("cairosvg não instalado: PNG não gerado (opcional).")
        return
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(destino / "arquitetura.png"), output_width=W * 2)
    print(f"[OK] {destino / 'arquitetura.png'}")


if __name__ == "__main__":
    main()
