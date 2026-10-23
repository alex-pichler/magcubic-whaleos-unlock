package com.pj.ctl;
import android.app.Activity;
import android.os.Bundle;
public class MainActivity extends Activity {
    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        Pjctl.run(getApplicationContext());
        finish();
    }
}
