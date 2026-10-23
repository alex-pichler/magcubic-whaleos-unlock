#!/usr/bin/env python3
# Run Python code INSIDE Kodi's process (via the pjshell addon pyeval server on 9998).
# Usage: PJ_HOST=<PROJECTOR_IP> python3 -I pjeval.py < code.py
#        PJ_HOST=<PROJECTOR_IP> python3 -I pjeval.py 'print(1+1)'
import os
import socket
import sys

HOST = os.environ.get('PJ_HOST', '<PROJECTOR_IP>')
PORT = 9998
PYEND = b'\n__PJEND__\n'

code = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
s = socket.create_connection((HOST, PORT), 8)
s.settimeout(40)
s.sendall(code.encode('utf-8') + PYEND)
out = b''
while True:
    try:
        chunk = s.recv(65536)
    except socket.timeout:
        break
    if not chunk:
        break
    out += chunk
s.close()
sys.stdout.write(out.decode('utf-8', 'replace'))
