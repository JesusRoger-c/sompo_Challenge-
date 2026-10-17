#!/usr/bin/env bash
# Derruba o que o abrir_estande.sh subiu.
set -uo pipefail
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS="$AQUI/.logs/pids"
[ -f "$PIDS" ] || { echo "Nada anotado para derrubar."; exit 0; }
while read -r pid nome; do
  if kill "$pid" 2>/dev/null; then printf '  %s parado (pid %s)\n' "$nome" "$pid"
  else printf '  %s já estava parado\n' "$nome"; fi
done < "$PIDS"
: > "$PIDS"
echo "Estande fechado."
