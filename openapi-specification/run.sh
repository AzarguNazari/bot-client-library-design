#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"

if [[ ! -f index.html || ! -f openapi.yaml ]]; then
  echo "index.html and openapi.yaml must be next to run.sh" >&2
  exit 1
fi

port_is_free() {
  python3 - "$1" <<'PY'
import socket, sys
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(("127.0.0.1", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
}

port="${PORT:-8765}"
if ! port_is_free "$port"; then
  port="$(python3 - <<'PY'
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("127.0.0.1", 0))
print(sock.getsockname()[1])
sock.close()
PY
)"
fi

python3 -m http.server "$port" --bind 127.0.0.1 &
server_pid=$!

cleanup() {
  kill "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ready=0
for _ in $(seq 1 50); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${port}/"; then
    ready=1
    break
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    echo "Failed to start the OpenAPI server" >&2
    exit 1
  fi
  sleep 0.1
done

if [[ "$ready" -ne 1 ]]; then
  echo "OpenAPI server did not become ready" >&2
  exit 1
fi

url="http://127.0.0.1:${port}/"
echo "AiChatBot API: ${url}"
echo "Press Ctrl+C to stop."

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$url"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$url" >/dev/null 2>&1 || true
else
  echo "Open ${url} in a browser."
fi

wait "$server_pid"
