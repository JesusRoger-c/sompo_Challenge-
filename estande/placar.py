#!/usr/bin/env python3
"""
Servidor do placar do estande — SomPrev Risk (NEXT 2026).

O que ele faz, e por que existe
-------------------------------
A tela do placar (placar.html) pontua a inclinação medida usando o MODELO DE
VERDADE, que vive na API do projeto. Chamar a API direto do navegador daria dois
problemas:

  1. CORS. Página e API ficam em portas diferentes, e a API não libera origem
     cruzada — ela é um backend de sistema, não de navegador.
  2. A chave de ingestão ficaria escrita dentro de um HTML aberto num notebook em
     cima da bancada. O projeto inteiro conta uma história de chaves com escopo,
     limite de taxa e auditoria; deixar a chave no cliente contradiz exatamente
     isso na frente de quem avalia.

Então este servidor fica no meio: serve a página e repassa a pontuação para a
API, guardando a chave do lado de cá. Só biblioteca padrão — nada para instalar.

Os três cenários
----------------
O modelo olha 12 variáveis. No estande o visitante mexe em UMA de verdade: a
declividade, medida pelo sensor. As outras descrevem o contexto da operação.

Testando contra o modelo real (17/10) ficou claro que o declive sozinho move o
score de 10 a 20 pontos — ele não leva de "Baixo" a "Crítico" sozinho, porque o
modelo não é um espelho do sensor. Em vez de maquiar isso, a demonstração usa
três contextos declarados, e a conversa fica mais forte:

    1. Dia seco, máquina nova .......  5 -> 15   o declive sozinho muda pouco
    2. Depois da chuva .............. 26 -> 59   MESMO declive, solo molhado, muda de faixa
    3. Chuva forte + manutenção ..... 77 -> 92   já está crítico parado; o declive só piora

É o argumento central do projeto numa demonstração de 30 segundos: risco é a
combinação, não uma variável. Os números acima vieram do modelo, não de ajuste
manual — rode `estande/conferir_cenarios.py` para reproduzir.

Como usar no dia
----------------
    1) API de pé:        python scripts/run.py api
    2) Chave:            export SOMPREV_API_KEY="...a sua chave de ingestão..."
    3) Placar:           python estande/placar.py
    4) Abra:             http://localhost:8800
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PAGINA = AQUI / "placar.html"

PORTA = int(os.getenv("PLACAR_PORTA", "8800"))
API = os.getenv("SOMPREV_API_URL", "http://127.0.0.1:8000").rstrip("/")
CHAVE = os.getenv("SOMPREV_API_KEY", "")
EQUIPAMENTO = os.getenv("SOMPREV_EQUIPAMENTO", "EQ-021")

_COMUM = {"equipamento_id": EQUIPAMENTO, "regiao_id": 4,
          "tipo_operacao": "Colheita", "periodo_dia": "Manha", "temperatura_c": 24.0}

CENARIOS = {
    "seco": {
        "nome": "Dia seco, máquina nova",
        "resumo": "Solo arenoso seco, sem chuva, longe da água, revisão em dia.",
        "contexto": {**_COMUM, "tipo_solo": "Arenoso", "umidade_solo_pct": 30,
                     "precipitacao_24h_mm": 0, "distancia_corpo_dagua_m": 1200,
                     "idade_equipamento_anos": 2, "horas_desde_manutencao": 40,
                     "horas_operacao_dia": 5, "carga_pct": 55},
    },
    "chuva": {
        "nome": "Depois da chuva",
        "resumo": "Solo argiloso encharcado, 28 mm nas últimas 24 h, perto de curso d'água.",
        "contexto": {**_COMUM, "tipo_solo": "Argiloso", "umidade_solo_pct": 66,
                     "precipitacao_24h_mm": 28, "distancia_corpo_dagua_m": 700,
                     "idade_equipamento_anos": 4, "horas_desde_manutencao": 100,
                     "horas_operacao_dia": 7, "carga_pct": 70},
    },
    "critico": {
        "nome": "Chuva forte + manutenção vencida",
        "resumo": "Solo saturado, 33 mm de chuva, máquina de 8 anos com 260 h sem revisão.",
        "contexto": {**_COMUM, "tipo_solo": "Argiloso", "umidade_solo_pct": 70,
                     "precipitacao_24h_mm": 33, "distancia_corpo_dagua_m": 480,
                     "idade_equipamento_anos": 8, "horas_desde_manutencao": 260,
                     "horas_operacao_dia": 9, "carga_pct": 84},
    },
}
PADRAO = "chuva"       # o cenário que melhor mostra a virada de faixa

# A API recusa duas leituras do mesmo equipamento no MESMO SEGUNDO ("Leitura
# duplicada", HTTP 409) — proteção correta dela contra reenvio. Milissegundos não
# resolvem: a checagem é por segundo. No estande, duas inclinações seguidas caem
# no mesmo segundo o tempo todo, então o relógio da demonstração só anda para a
# frente e, se ainda assim bater, a tentativa seguinte pula mais longe.
_trava = threading.Lock()
_ultimo = [datetime.now() - timedelta(seconds=1)]


def _instante(pulo: int = 0) -> str:
    with _trava:
        agora = datetime.now()
        if agora <= _ultimo[0]:
            agora = _ultimo[0] + timedelta(seconds=1)
        if pulo:
            agora += timedelta(seconds=pulo)
        _ultimo[0] = agora
        return agora.strftime("%Y-%m-%d %H:%M:%S")


def pontuar(declividade: float, cenario: str) -> tuple[int, dict]:
    if not CHAVE:
        return 503, {"erro": 'Falta a chave: export SOMPREV_API_KEY="..." antes de subir o placar.'}

    escolhido = CENARIOS.get(cenario) or CENARIOS[PADRAO]
    base = dict(escolhido["contexto"])
    base["declividade_graus"] = round(float(declividade), 1)

    pulo = 0
    for tentativa in range(6):
        corpo = dict(base)
        corpo["data_hora"] = _instante(pulo)
        req = urllib.request.Request(
            f"{API}/telemetria", data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-API-Key": CHAVE}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                dados = json.loads(r.read().decode("utf-8"))
                dados["cenario"] = cenario
                dados["cenario_nome"] = escolhido["nome"]
                return r.status, dados
        except urllib.error.HTTPError as e:
            bruto = e.read().decode("utf-8", "replace")[:400]
            try:
                erro = json.loads(bruto)
            except json.JSONDecodeError:
                erro = {"erro": bruto or f"HTTP {e.code}"}
            if e.code == 409:
                pulo = 2 ** tentativa          # escapa de um bloco de segundos já usados
                continue
            return e.code, erro
        except urllib.error.URLError as e:
            return 503, {"erro": f"API não respondeu em {API}. Ela está de pé? ({e.reason})"}

    return 409, {"erro": "Não consegui um horário livre para a leitura. Reinicie o placar."}


class Handler(BaseHTTPRequestHandler):
    def _responder(self, status: int, tipo: str, dados: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def _json(self, status: int, corpo: dict) -> None:
        self._responder(status, "application/json",
                        json.dumps(corpo, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):  # noqa: N802
        rota = self.path.split("?")[0]
        if rota in ("/", "/placar", "/index.html"):
            if not PAGINA.exists():
                return self._responder(500, "text/plain; charset=utf-8", f"Não achei {PAGINA}".encode())
            return self._responder(200, "text/html; charset=utf-8", PAGINA.read_bytes())
        if rota == "/cenarios":
            return self._json(200, {"padrao": PADRAO, "cenarios": [
                {"chave": k, "nome": v["nome"], "resumo": v["resumo"]} for k, v in CENARIOS.items()]})
        if rota == "/saude":
            return self._json(200, {"ok": True, "api": API, "chave": bool(CHAVE)})
        self._responder(404, "text/plain; charset=utf-8", b"nao encontrado")

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/pontuar"):
            return self._responder(404, "text/plain; charset=utf-8", b"nao encontrado")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            pedido = json.loads(self.rfile.read(n) or b"{}")
            graus = float(pedido.get("declividade_graus", 0))
            cenario = str(pedido.get("cenario") or PADRAO)
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"erro": "declividade_graus inválida"})
        status, corpo = pontuar(graus, cenario)
        self._json(status, corpo)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    print(f"Placar  : http://localhost:{PORTA}")
    print(f"API     : {API}")
    print(f"Chave   : {'ok' if CHAVE else 'FALTANDO — export SOMPREV_API_KEY'}")
    print(f"Cenários: {', '.join(CENARIOS)}  (padrão: {PADRAO})")
    print("Ctrl+C para parar.\n")
    ThreadingHTTPServer(("0.0.0.0", PORTA), Handler).serve_forever()
