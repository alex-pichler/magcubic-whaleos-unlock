# Generic raw transact() probe for ISystemControl 1.0.
# Runs inside Kodi via:  PJ_HOST=<PROJECTOR_IP> python3 -I pjeval.py < sc_call.py
# Edit CALLS below. Arg spec: ('s', str) | ('i', int)
import ctypes
P = ctypes.c_void_p; PS = ctypes.sizeof(P)
TOKEN = "vendor.amlogic.hardware.systemcontrol@1.0::ISystemControl"
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
CLL = g(E, 54, ctypes.CFUNCTYPE(ctypes.c_longlong, P, P, P, P))
CVA = g(E, 63, ctypes.CFUNCTYPE(None, P, P, P, P))
GSM = g(E, 113, ctypes.CFUNCTYPE(P, P, P, ctypes.c_char_p, ctypes.c_char_p))
CSOA = g(E, 116, ctypes.CFUNCTYPE(P, P, P, P, P)); NS = g(E, 167, ctypes.CFUNCTYPE(P, P, ctypes.c_char_p))
GSUC = g(E, 169, ctypes.CFUNCTYPE(ctypes.c_char_p, P, P, P))
def exc(t):
    if XO(env): XD(env); XC(env); print("  !!exc", t); return True
    return False
def S(s): return NS(env, s.encode())
def js(j):
    if not j: return None
    c = GSUC(env, j, None); return c.decode('utf-8', 'replace') if c else None
def jv(*o):
    a = (ctypes.c_uint64 * len(o))(*[int(x) & 0xFFFFFFFFFFFFFFFF if x else 0 for x in o]); return ctypes.cast(a, P)
cB = FC(env, b"android/os/HwBinder"); cP = FC(env, b"android/os/HwParcel")
mGS = GSM(env, cB, b"getService", b"(Ljava/lang/String;Ljava/lang/String;)Landroid/os/IHwBinder;")
mI = GM(env, cP, b"<init>", b"()V"); mWT = GM(env, cP, b"writeInterfaceToken", b"(Ljava/lang/String;)V")
mWS = GM(env, cP, b"writeString", b"(Ljava/lang/String;)V")
mWI = GM(env, cP, b"writeInt32", b"(I)V")
mRL = GM(env, cP, b"readInt64", b"()J")
mRI = GM(env, cP, b"readInt32", b"()I")
mRS = GM(env, cP, b"readString", b"()Ljava/lang/String;")
mV = GM(env, cP, b"verifySuccess", b"()V")
mRT = GM(env, cP, b"releaseTemporaryStorage", b"()V")
bd = CSOA(env, cB, mGS, jv(S(TOKEN), S("default")))
mT = GM(env, GOC(env, bd), b"transact", b"(ILandroid/os/HwParcel;Landroid/os/HwParcel;I)V")

def call(code, args, out="i", label=""):
    rq = NO(env, cP, mI, jv()); rp = NO(env, cP, mI, jv())
    CVA(env, rq, mWT, jv(S(TOKEN)))
    for kind, val in args:
        if kind == 's': CVA(env, rq, mWS, jv(S(val)))
        elif kind == 'i': CVA(env, rq, mWI, jv(int(val)))
    CVA(env, bd, mT, jv(code, rq, rp, 0))
    if exc("tx%d" % code): return None
    CVA(env, rp, mV, jv())
    if exc("vfy%d" % code): return None
    v = []
    for t in out:
        if t == 'i': v.append(CIA(env, rp, mRI, jv()))
        elif t == 'l': v.append(CLL(env, rp, mRL, jv()))
        elif t == 's': v.append(js(COA(env, rp, mRS, jv())))
        if exc("rd@%d" % code): break
    CVA(env, rq, mRT, jv())
    print("%-28s code=%-3d -> %r" % (label, code, v))
    return v

print("=== read-only validation of the extracted code map ===")
call(10, [('s', "ro.build.version.release"), ('s', "?")], "is", "getPropertyString 10")
call(10, [('s', "ro.build.type"), ('s', "?")], "is", "getPropertyString 10")
call(11, [('s', "ro.build.version.sdk"), ('i', -1)], "ii", "getPropertyInt 11")
call(12, [('s', "ro.serialno.nonexistent"), ('l', -1)], "il", "getPropertyLong 12")
call(297, [], "s", "getChipVersionInfo 297")
call(363, [], "is", "securityEnabled 363")
