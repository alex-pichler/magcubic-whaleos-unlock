package com.pj.ctl;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
public class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context ctx, Intent i) {
        Pjctl.run(ctx.getApplicationContext());
    }
}
