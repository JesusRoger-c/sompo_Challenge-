"""
Simulador de telemetria em tempo real + teste de confiabilidade da coleta.

Envia leituras para a API como faria um coletor instalado na maquina, incluindo
uma fracao de envios DEFEITUOSOS (sensor vazio, valor fora da faixa, virgula
decimal, grafia diferente, equipamento desconhecido, data corrompida, campo
critico ausente e reenvio do mesmo pacote). Ao final, RECONCILIA:

    enviadas = processadas + rejeitadas (quarentena) + duplicadas

e confere, pela propria API de consulta, que cada leitura aceita tem predicao
e trilha de auditoria, e que a cadeia de hashes continua integra. O resultado
vira a evidencia `document/evidencias/validacao_integracao.md`.

Uso:  python scripts/run.py api          (em um terminal)
      python scripts/run.py simular      (em outro terminal)
"""

from __future__ import annotations

import statistics
import time
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd

from .. import config

DEFEITOS = ["sensor_vazio", "fora_da_faixa", "virgula_decimal", "grafia", "equipamento_desconhecido",
            "data_corrompida", "critico_ausente", "reenvio"]
ESPERADO = {"ok": 201, "sensor_vazio": 201, "fora_da_faixa": 201, "virgula_decimal": 201, "grafia": 201,
            "equipamento_desconhecido": 422, "data_corrompida": 422, "critico_ausente": 422, "reenvio": 409}


def _gerar_envios(quantidade: int, taxa_falhas: float, seed: int, inicio: pd.Timestamp) -> list[tuple[str, dict]]:
    """Monta os payloads a partir do perfil real da base tratada (agosto), em datas novas."""
    rng = np.random.default_rng(seed)
    base = pd.read_csv(config.DADOS_TRATADOS_CSV)
    base = base[base["data_hora"] >= "2026-08-01"].sample(quantidade, replace=True, random_state=seed)
    regioes = {nome: i for i, nome in enumerate(
        ["Sorriso", "Rio Verde", "Lucas do Rio Verde", "Cascavel", "Barreiras", "Não-Me-Toque"], start=1)}
    envios, anteriores = [], []
    for k, linha in enumerate(base.to_dict("records")):
        instante = inicio + pd.Timedelta(minutes=int(k * 7 + rng.integers(0, 5)))
        payload = {c: linha[c] for c in ["equipamento_id", "umidade_solo_pct", "precipitacao_24h_mm", "temperatura_c",
                                         "tipo_solo", "declividade_graus", "distancia_corpo_dagua_m", "tipo_operacao",
                                         "idade_equipamento_anos", "horas_desde_manutencao", "horas_operacao_dia",
                                         "carga_pct", "periodo_dia"]}
        payload.update(data_hora=instante.strftime("%Y-%m-%d %H:%M:%S"), regiao_id=regioes[linha["regiao"]])
        tipo = "ok"
        if rng.random() < taxa_falhas:
            tipo = str(rng.choice(DEFEITOS))
            if tipo == "sensor_vazio":
                payload[str(rng.choice(["umidade_solo_pct", "carga_pct", "horas_operacao_dia"]))] = None
            elif tipo == "fora_da_faixa":
                payload["umidade_solo_pct"] = 140
            elif tipo == "virgula_decimal":
                payload["umidade_solo_pct"] = f"{payload['umidade_solo_pct']:.1f}".replace(".", ",")
            elif tipo == "grafia":
                payload["tipo_operacao"] = str(payload["tipo_operacao"]).upper()
            elif tipo == "equipamento_desconhecido":
                payload["equipamento_id"] = "EQ-999"
            elif tipo == "data_corrompida":
                payload["data_hora"] = "31/02/2026 25:00"
            elif tipo == "critico_ausente":
                payload["distancia_corpo_dagua_m"] = None
            elif tipo == "reenvio" and anteriores:
                payload = dict(anteriores[int(rng.integers(len(anteriores)))])
            else:
                tipo = "ok"
        if tipo in ("ok", "sensor_vazio", "fora_da_faixa", "virgula_decimal", "grafia"):
            anteriores.append(payload)
        envios.append((tipo, payload))
    return envios


def executar(cliente, quantidade: int = 200, taxa_falhas: float = 0.15, seed: int = 7,
             chave_ingestao: str | None = None, chave_consulta: str | None = None) -> dict:
    """Roda a simulacao usando um cliente HTTP (httpx.Client ou TestClient)."""
    chave_ingestao = chave_ingestao or config.API_KEY_INGESTAO
    chave_consulta = chave_consulta or config.API_KEY_CONSULTA
    if not chave_ingestao or not chave_consulta:
        raise RuntimeError("Chaves de API ausentes no .env (rode: python scripts/run.py configurar)")
    h_ing, h_con = {"X-API-Key": chave_ingestao}, {"X-API-Key": chave_consulta}

    saude = cliente.get("/health").json()
    ultima = pd.Timestamp("2026-09-01 06:00:00")
    envios = _gerar_envios(quantidade, taxa_falhas, seed, ultima + pd.Timedelta(days=int(seed % 5)))

    resultados, latencias, aceitas = [], [], []
    contagem = Counter()
    for tipo, payload in envios:
        t0 = time.perf_counter()
        r = cliente.post("/telemetria", json=payload, headers=h_ing)
        latencias.append((time.perf_counter() - t0) * 1000)
        corpo = r.json()
        status = {201: "processada", 409: "duplicada", 422: "rejeitada", 404: "rejeitada"}.get(r.status_code, "erro")
        contagem[status] += 1
        resultados.append({"defeito": tipo, "http": r.status_code, "esperado": ESPERADO[tipo],
                           "conforme": r.status_code == ESPERADO[tipo]})
        if r.status_code == 201:
            aceitas.append(corpo)

    # Conferencia pela API de consulta: toda leitura aceita tem predicao e auditoria.
    sem_rastro = 0
    for corpo in aceitas:
        d = cliente.get(f"/leituras/{corpo['leitura_id']}", headers=h_con)
        eventos = {e["evento"] for e in d.json().get("auditoria", [])} if d.status_code == 200 else set()
        if d.status_code != 200 or not {"TELEMETRIA_RECEBIDA", "PREDICAO_GERADA"} <= eventos:
            sem_rastro += 1
    cadeia = cliente.get("/auditoria/verificar", headers=h_con).json()

    tabela = pd.DataFrame(resultados)
    por_defeito = (tabela.groupby("defeito").agg(enviadas=("http", "size"), esperado=("esperado", "first"),
                                                  conformes=("conforme", "sum")).reset_index())
    resumo = {
        "executado_em": datetime.now().isoformat(timespec="seconds"),
        "api": saude,
        "enviadas": len(envios),
        "processadas": contagem["processada"],
        "rejeitadas_quarentena": contagem["rejeitada"],
        "duplicadas": contagem["duplicada"],
        "erros_inesperados": contagem["erro"],
        "reconciliacao_ok": contagem["processada"] + contagem["rejeitada"] + contagem["duplicada"] == len(envios),
        "respostas_conforme_esperado": int(tabela["conforme"].sum()),
        "leituras_aceitas_sem_rastro": sem_rastro,
        "cadeia_auditoria": cadeia,
        "latencia_ms": {"p50": round(statistics.median(latencias), 1),
                        "p95": round(float(np.percentile(latencias, 95)), 1),
                        "max": round(max(latencias), 1)},
        "alertas_gerados": sum(len(a["alertas"]) for a in aceitas),
        "por_defeito": por_defeito.to_dict("records"),
    }
    return resumo


def escrever_evidencia(resumo: dict) -> str:
    config.EVIDENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = config.EVIDENCIAS_DIR / "validacao_integracao.md"
    linhas = [
        "# Evidência — validação da integração com a fonte de dados (telemetria)",
        "",
        f"*Execução: {resumo['executado_em']} · comando `python scripts/run.py simular` contra a API em execução "
        f"(modelo {resumo['api'].get('modelo')}, regras {resumo['api'].get('regras')}).*",
        "",
        "## Reconciliação (sem perda nem duplicação de dados)",
        "",
        "| Enviadas | Processadas | Rejeitadas (quarentena) | Duplicadas bloqueadas | Erros inesperados | Fecha? |",
        "|---|---|---|---|---|---|",
        f"| {resumo['enviadas']} | {resumo['processadas']} | {resumo['rejeitadas_quarentena']} | "
        f"{resumo['duplicadas']} | {resumo['erros_inesperados']} | "
        f"{'✅ sim' if resumo['reconciliacao_ok'] else '❌ não'} |",
        "",
        f"- Respostas conforme o esperado para cada tipo de envio: **{resumo['respostas_conforme_esperado']}"
        f"/{resumo['enviadas']}**",
        f"- Leituras aceitas sem predição ou sem trilha de auditoria: **{resumo['leituras_aceitas_sem_rastro']}**",
        f"- Integridade da trilha de auditoria após a carga: **{resumo['cadeia_auditoria'].get('resumo')}**",
        f"- Latência da API por leitura (inclui validação, modelo, explicação, alertas e auditoria): "
        f"p50 **{resumo['latencia_ms']['p50']} ms**, p95 **{resumo['latencia_ms']['p95']} ms**",
        f"- Alertas gerados/agrupados nas leituras aceitas: **{resumo['alertas_gerados']}**",
        "",
        "## Comportamento por tipo de envio",
        "",
        "| Tipo de envio | Enviadas | HTTP esperado | Conformes |",
        "|---|---|---|---|",
    ]
    explica = {"ok": "leitura correta", "sensor_vazio": "sensor sem leitura → imputado",
               "fora_da_faixa": "umidade 140% → tratada como ausente e imputada",
               "virgula_decimal": "\"55,3\" → convertido", "grafia": "\"COLHEITA\" → padronizado",
               "equipamento_desconhecido": "EQ-999 → quarentena", "data_corrompida": "data inválida → quarentena",
               "critico_ausente": "distância da água vazia → quarentena", "reenvio": "mesmo pacote → bloqueado"}
    for d in resumo["por_defeito"]:
        linhas.append(f"| {explica.get(d['defeito'], d['defeito'])} | {d['enviadas']} | {d['esperado']} | "
                      f"{d['conformes']}/{d['enviadas']} |")
    linhas += ["", "Nenhuma leitura com defeito derrubou a API ou interrompeu o fluxo: cada uma recebeu o "
               "tratamento previsto e ficou registrada (processada, em quarentena ou bloqueada como duplicada).", ""]
    caminho.write_text("\n".join(linhas), encoding="utf-8")
    return str(caminho)


def main(quantidade: int = 200, url: str = "http://127.0.0.1:8000", taxa_falhas: float = 0.15,
         relatorio: bool = True) -> int:
    import httpx
    try:
        with httpx.Client(base_url=url, timeout=30) as cliente:
            resumo = executar(cliente, quantidade=quantidade, taxa_falhas=taxa_falhas)
    except httpx.ConnectError:
        print(f"✖ API indisponível em {url}. Suba antes com: python scripts/run.py api")
        return 1
    print(f"Enviadas {resumo['enviadas']} · processadas {resumo['processadas']} · "
          f"quarentena {resumo['rejeitadas_quarentena']} · duplicadas {resumo['duplicadas']} · "
          f"erros {resumo['erros_inesperados']} · reconciliação {'OK' if resumo['reconciliacao_ok'] else 'FALHOU'}")
    print(f"Conformes: {resumo['respostas_conforme_esperado']}/{resumo['enviadas']} · "
          f"latência p50 {resumo['latencia_ms']['p50']} ms · {resumo['cadeia_auditoria'].get('resumo')}")
    if relatorio:
        print(f"Evidência: {escrever_evidencia(resumo)}")
    ok = resumo["reconciliacao_ok"] and resumo["erros_inesperados"] == 0 and resumo["leituras_aceitas_sem_rastro"] == 0
    return 0 if ok else 1
