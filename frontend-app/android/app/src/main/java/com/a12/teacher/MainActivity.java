package com.a12.teacher;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(FileDownloadPlugin.class);
        registerPlugin(PresentationPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
