#!/usr/bin/env bash
#
# Abre o estande inteiro com um comando — SomPrev Risk · NEXT 2026
#
# Sábado de manhã, com gente passando e o relógio correndo, ninguém lembra de
# três comandos em três abas. Este script sobe tudo, espera cada peça responder
# e só então diz "pronto". Se algo não subir, ele FALA o que foi, em vez de
# deixar você descobrir às 12h05.
#
#   ./estande/abrir_estande.sh          sobe tudo
#   ./estande/fechar_estande.sh         derruba tudo
#
set -uo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"
LOGS="$AQUI/.logs"
PIDS="$LOGS/pids"
mkdir -p "$LOGS"; : > "$PIDS"

v()  { printf '\033[32m%s\033[0m\n' "$1"; }   # verde
x()  { printf '\033[31m%s\033[0m\n' "$1"; }   # vermelho
i()  { printf '\033[2m%s\033[0m\n'  "$1"; }   # apagado

cd "$RAIZ"

# ------------------------------------------------------ 0. a libcairo do Mac
# A apolice e desenhada com cairosvg, que depende da libcairo instalada pelo
# Homebrew. Nos Macs com chip M o Python nao procura em /opt/homebrew/lib
# sozinho, e a impressao morre com "no library called cairo-2 was found".
# Resolver aqui deixa o estande independente do que esta no .zprofile: o placar
# herda esta variavel, e o apolice.py que ele chama herda do placar.
if [ -z "${DYLD_FALLBACK_LIBRARY_PATH:-}" ]; then
  for d in /opt/homebrew/lib /usr/local/lib; do
    if [ -f "$d/libcairo.2.dylib" ]; then
      export DYLD_FALLBACK_LIBRARY_PATH="$d"
      i "libcairo encontrada em $d"
      break
    fi
  done
fi

# ---------------------------------------------------------------- 1. a chave
if [ -f .env ]; then set -a; . ./.env; set +a; fi
if [ -z "${SOMPREV_API_KEY:-}" ]; then
  x "Falta a chave de ingestão."
  i "  Rode:  python scripts/run.py configurar     (cria o .env)"
  i "  Ou:    export SOMPREV_API_KEY=\"...\""
  exit 1
fi
v "Chave encontrada."

# ------------------------------------------------------------- 2. subir peça
PY="${PYTHON:-python3}"

sobe () {                       # sobe <nome> <log> <comando...>
  local nome="$1" log="$2"; shift 2
  "$@" > "$LOGS/$log" 2>&1 &
  echo "$! $nome" >> "$PIDS"
  i "  $nome subindo (log: estande/.logs/$log)"
}

espera () {                     # espera <nome> <url> <segundos>
  local nome="$1" url="$2" limite="${3:-40}" n=0
  while [ "$n" -lt "$limite" ]; do
    if curl -fsS -m 2 "$url" >/dev/null 2>&1; then v "  $nome respondendo."; return 0; fi
    sleep 1; n=$((n+1))
  done
  x "  $nome NÃO respondeu em ${limite}s."
  i "     Veja o fim do log:  tail -20 estande/.logs/${nome}.log"
  return 1
}

# --------------------------------------------------- 1b. portas ja ocupadas
# Sem esta checagem acontece o pior tipo de falha: um processo ANTIGO continua
# na porta, o novo morre com "Address already in use", e o teste de saude passa
# -- respondendo pelo processo velho, com o codigo velho. O script diria
# "ESTANDE DE PE" enquanto voce roda uma versao que nao e a sua.
ocupada=0
for par in "8000:API" "8800:placar" "8501:dashboard"; do
  porta="${par%%:*}"; quem="${par##*:}"
  if lsof -ti "tcp:$porta" >/dev/null 2>&1; then
    x "Porta $porta ($quem) ja esta ocupada."
    ocupada=1
  fi
done
if [ "$ocupada" -eq 1 ]; then
  i ""
  i "  Tem coisa de uma execucao anterior ainda rodando."
  i "  Derrube tudo e rode de novo:"
  i "      ./estande/fechar_estande.sh && ./estande/abrir_estande.sh"
  exit 1
fi

falhou=0

echo; i "API do modelo"
sobe api api.log "$PY" scripts/run.py api
espera api http://127.0.0.1:8000/health 45 || falhou=1

echo; i "Placar do estande"
sobe placar placar.log "$PY" "$AQUI/placar.py"
espera placar http://127.0.0.1:8800/saude 20 || falhou=1

echo; i "Dashboard"
sobe dashboard dashboard.log "$PY" scripts/run.py dashboard
espera dashboard http://127.0.0.1:8501 40 || i "  (dashboard demora mais; confira sozinha daqui a pouco)"

# --------------------------------------------------------- 3. o que conferir
echo
if [ "$falhou" -eq 0 ]; then
  v "================= ESTANDE DE PÉ ================="
else
  x "================= SUBIU COM FALHA ==============="
fi
cat <<FIM

  Placar (tela do visitante) ..... http://localhost:8800
  Dashboard ...................... http://localhost:8501
  API ............................ http://127.0.0.1:8000/health

  ANTES DE ABRIR, confira nesta ordem:
    1. O notebook está na rede Wi-Fi  "SomPrev-Risk"
    2. O placar em tela cheia e o canto diz "sensor conectado"
    3. Incline o trator: o número muda e a faixa muda de cor
    4. Imprima uma apólice de teste:
         python3 identidade/kit/apolice.py --nome "Teste" --score 72
    5. Se o sensor estiver fora, aperte M no placar — modo manual salva o dia

  Para derrubar tudo:  ./estande/fechar_estande.sh

FIM
exit "$falhou"
