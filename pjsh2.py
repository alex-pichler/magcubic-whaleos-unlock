#!/usr/bin/env python3
"""Robust prompt-aware shell runner for the projector's :9999 shell.
Sends each command with a unique sentinel and reads until it returns, so slow
device responses don't get truncated. PJ_HOST selects the device IP.

Usage: PJ_HOST=<PROJECTOR_IP> python3 -I pjsh2.py 'cmd1' 'cmd2' ...
       PJ_HOST=<PROJECTOR_IP> python3 -I pjsh2.py - <<'EOF'   (one cmd per line)
"""
import os
import socket
import sys
import time

HOST = os.environ.get("PJ_HOST", "<PROJECTOR_IP>")
PORT = 9999


def run(cmd, timeout=25):
    sent = "__PJDONE_%d__" % (int(time.time() * 1000) % 1000000)
    s = socket.create_connection((HOST, PORT), 8)
    s.settimeout(timeout)
    s.sendall((cmd + " 2>&1; echo " + sent + "\n").encode())
    buf = b""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = s.recv(65536)
        except socket.timeout:
            break
        if not d:
            break
        buf += d
        if sent.encode() in buf:
            break
    s.close()
    out = buf.decode("utf-8", "replace")
    # strip the shell banner/prompt lines and the sentinel
    lines = []
    for ln in out.splitlines():
        if sent in ln:
            break
        if "can't find tty fd" in ln or "won't have full job control" in ln:
            continue
        # drop a leading prompt fragment like ":/storage/... $ cmd"
        lines.append(ln)
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["-"]:
        args = [l for l in sys.stdin.read().splitlines() if l.strip()]
    for c in args:
        print("$ " + c)
        print(run(c))
