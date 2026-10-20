#!/usr/bin/env bash
# Derruba o que o abrir_estande.sh subiu.
set -uo pipefail
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS="$AQUI/.logs/pids"
if [ -f "$PIDS" ]; then
  while read -r pid nome; do
    if kill "$pid" 2>/dev/null; then printf '  %s parado (pid %s)\n' "$nome" "$pid"
    else printf '  %s já estava parado\n' "$nome"; fi
  done < "$PIDS"
  : > "$PIDS"
fi

# Varredura por porta: pega tambem o que ficou de execucoes antigas, cujos pids
# nao estao anotados em lugar nenhum -- que foi exatamente o que escondeu um
# placar velho na 8800 e fez o novo nem subir.
for par in "8000:API" "8800:placar" "8501:dashboard"; do
  porta="${par%%:*}"; quem="${par##*:}"
  for pid in $(lsof -ti "tcp:$porta" 2>/dev/null); do
    kill "$pid" 2>/dev/null && printf '  %s solto na porta %s parado (pid %s)\n' "$quem" "$porta" "$pid"
  done
done

echo "Estande fechado."
