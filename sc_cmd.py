# Call a V1_1 ISystemControl method over raw transact().
# usage: edit CODE / CMD, run:  PJ_HOST=<PROJECTOR_IP> python3 -I pjeval.py < sc_cmd.py
import ctypes
P = ctypes.c_void_p; PS = ctypes.sizeof(P)
TOKEN = "vendor.amlogic.hardware.systemcontrol@1.1::ISystemControl"
CODE = 386          # systemCmd(hidl_string)
ARGS = ["id > /data/data/org.xbmc.kodi/cache/syscmd_id.txt"]

libnh = ctypes.CDLL('libnativehelper.so')
GV = libnh.JNI_GetCreatedJavaVMs; GV.restype = ctypes.c_int
GV.argtypes = [ctypes.POINTER(P), ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
vm = P(); n = ctypes.c_int(); GV(ctypes.byref(vm), 1, ctypes.byref(n))
def g(t, i, pr): return pr(ctypes.cast(t + i * PS, ctypes.POINTER(P))[0])
At = g(ctypes.cast(vm, ctypes.POINTER(P))[0], 4, ctypes.CFUNCTYPE(ctypes.c_int, P, ctypes.POINTER(P), P))
env = P(); At(vm, ctypes.byref(env), None); E = ctypes.cast(env, ctypes.POINTER(P))[0]
FC = g(E, 6, ctypes.CFUNCTYPE(P, P, ctypes.c_char_p)); XO = g(E, 15, ctypes.CFUNCTYPE(P, P))
XD = g(E, 16, ctypes.CFUNCTYPE(None, P)); XC = g(E, 17, ctypes.CFUNCTYPE(None, P))
NO = g(E, 30, ctypes.CFUNCTYPE(P, P, P, P, P)); GOC = g(E, 31, ctypes.CFUNCTYPE(P, P, P))
GM = g(E, 33, ctypes.CFUNCTYPE(P, P, P, ctypes.c_char_p, ctypes.c_char_p))
CIA = g(E, 51, ctypes.CFUNCTYPE(ctypes.c_int, P, P, P, P))
CVA = g(E, 63, ctypes.CFUNCTYPE(None, P, P, P, P))
GSM = g(E, 113, ctypes.CFUNCTYPE(P, P, P, ctypes.c_char_p, ctypes.c_char_p))
CSOA = g(E, 116, ctypes.CFUNCTYPE(P, P, P, P, P)); NS = g(E, 167, ctypes.CFUNCTYPE(P, P, ctypes.c_char_p))
def exc(t):
    if XO(env): XD(env); XC(env); print("  !!exc", t); return True
    return False
def S(s): return NS(env, s.encode())
def jv(*o):
    a = (ctypes.c_uint64 * len(o))(*[int(x) & 0xFFFFFFFFFFFFFFFF if x else 0 for x in o]); return ctypes.cast(a, P)
cB = FC(env, b"android/os/HwBinder"); cP = FC(env, b"android/os/HwParcel")
mGS = GSM(env, cB, b"getService", b"(Ljava/lang/String;Ljava/lang/String;)Landroid/os/IHwBinder;")
mI = GM(env, cP, b"<init>", b"()V"); mWT = GM(env, cP, b"writeInterfaceToken", b"(Ljava/lang/String;)V")
mWS = GM(env, cP, b"writeString", b"(Ljava/lang/String;)V")
mV = GM(env, cP, b"verifySuccess", b"()V")
mRT = GM(env, cP, b"releaseTemporaryStorage", b"()V")
bd = CSOA(env, cB, mGS, jv(S(TOKEN), S("default")))
if not bd:
    print("no binder for", TOKEN); raise SystemExit
mT = GM(env, GOC(env, bd), b"transact", b"(ILandroid/os/HwParcel;Landroid/os/HwParcel;I)V")
rq = NO(env, cP, mI, jv()); rp = NO(env, cP, mI, jv())
CVA(env, rq, mWT, jv(S(TOKEN)))
for a in ARGS:
    CVA(env, rq, mWS, jv(S(a)))
CVA(env, bd, mT, jv(CODE, rq, rp, 0))
if exc("tx%d" % CODE):
    print("transact failed (code %d not accepted)" % CODE)
else:
    CVA(env, rp, mV, jv())
    print("transact %d ok, verifySuccess=%s" % (CODE, not exc("verify")))
CVA(env, rq, mRT, jv())
