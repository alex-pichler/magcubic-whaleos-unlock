import os
import socket
import subprocess
import threading
import time
import io
import contextlib
import traceback

SD = '/storage/emulated/0/pj/'
SH_PORT = 9999
PY_PORT = 9998
PYEND = b'\n__PJEND__\n'


def log(s):
    try:
        with open(SD + 'addon.log', 'a') as f:
            f.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), s))
    except Exception:
        pass


def shell_server():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    while True:
        try:
            srv.bind(('0.0.0.0', SH_PORT))
            srv.listen(4)
            break
        except Exception as e:
            log('sh bind exc %r, retry 30s' % (e,))
            time.sleep(30)
    log('sh listening on %d' % SH_PORT)
    while True:
        try:
            conn, addr = srv.accept()
        except Exception as e:
            log('sh accept exc %r' % (e,))
            return
        try:
            subprocess.Popen(['/system/bin/sh', '-i'],
                             stdin=conn, stdout=conn, stderr=conn, cwd=SD)
        except Exception as e:
            log('sh popen exc %r' % (e,))
            try:
                conn.close()
            except Exception:
                pass


# globals persist across pyeval calls so state can be built up
PYGLOBALS = {'__name__': 'pjeval'}


def handle_pyeval(conn):
    data = b''
    try:
        conn.settimeout(30)
        while PYEND not in data:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
    except Exception as e:
        try:
            conn.sendall(('recv error: %r' % (e,)).encode())
            conn.close()
        except Exception:
            pass
        return
    code = data.split(PYEND)[0].decode('utf-8', 'replace')
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(code, PYGLOBALS)
        out = buf.getvalue()
    except Exception:
        out = buf.getvalue() + '\n--TRACEBACK--\n' + traceback.format_exc()
    try:
        conn.sendall(out.encode('utf-8', 'replace'))
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


def pyeval_server():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    while True:
        try:
            srv.bind(('0.0.0.0', PY_PORT))
            srv.listen(4)
            break
        except Exception as e:
            log('py bind exc %r, retry 30s' % (e,))
            time.sleep(30)
    log('py listening on %d' % PY_PORT)
    while True:
        try:
            conn, addr = srv.accept()
        except Exception as e:
            log('py accept exc %r' % (e,))
            return
        threading.Thread(target=handle_pyeval, args=(conn,), daemon=True).start()


try:
    os.makedirs(SD, exist_ok=True)
except Exception:
    pass
log('addon script.pjshell v2 loaded (sh+pyeval)')
threading.Thread(target=shell_server, daemon=True).start()
pyeval_server()
