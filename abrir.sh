#!/usr/bin/env bash
# DEDALUS · abre el panel (macOS / Linux)
#
#   ./abrir.sh
#
# Pide la clave de Oracle sin mostrarla y sin guardarla en ningún archivo.
# Enter sin escribir nada = arranca con SQLite local (sin Oracle).
set -euo pipefail
cd "$(dirname "$0")"

export CNOSOS_ORDS_URL="${CNOSOS_ORDS_URL:-https://gee0c29fc768a8c-cnosos.adb.sa-bogota-1.oraclecloudapps.com/ords/cnosos_app/_/sql}"
export CNOSOS_DB_USUARIO="${CNOSOS_DB_USUARIO:-cnosos_app}"

read -r -s -p "Clave de Oracle (Enter = sin Oracle): " clave
echo
if [ -n "$clave" ]; then
  export DEDALUS_ALMACEN=oracle_rest
  export CNOSOS_DB_CLAVE="$clave"
  echo "Conectando a Oracle (unos segundos)..."
else
  export DEDALUS_ALMACEN=sqlite
  echo "Sin clave: arranco con SQLite local."
fi
unset clave

for par in "GEMINI_API_KEY:Gemini" "GROQ_API_KEY:Groq"; do
  var="${par%%:*}"; nombre="${par##*:}"
  if [ -z "${!var:-}" ]; then
    read -r -s -p "Llave de $nombre (Enter = sin $nombre): " valor; echo
    [ -n "$valor" ] && export "$var=$valor"
    unset valor
  fi
  if [ -n "${!var:-}" ]; then echo "  $nombre: lista"; else echo "  $nombre: sin llave"; fi
done

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
exec "$PY" -m dedalus.panel --abrir "$@"
