package com.a12.teacher;

import android.content.pm.ActivityInfo;
import android.view.Window;
import androidx.activity.OnBackPressedCallback;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "A12Presentation")
public class PresentationPlugin extends Plugin {
    private OnBackPressedCallback exitOnBack;
    private int previousOrientation;
    private int previousBarsBehavior;
    private int previousVisibleBars;

    @PluginMethod
    public void enter(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            if (exitOnBack == null) {
                WindowInsetsControllerCompat insets = getInsetsController();
                previousOrientation = getActivity().getRequestedOrientation();
                previousBarsBehavior = insets.getSystemBarsBehavior();
                previousVisibleBars = visibleBars();
                exitOnBack = new OnBackPressedCallback(true) {
                    @Override
                    public void handleOnBackPressed() {
                        restoreWindow();
                        notifyListeners("exitRequested", new JSObject());
                    }
                };
                getActivity().getOnBackPressedDispatcher().addCallback(getActivity(), exitOnBack);
                getActivity().setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
                insets.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                insets.hide(presentationBars());
            }
            call.resolve();
        });
    }

    @PluginMethod
    public void exit(PluginCall call) {
        getActivity().runOnUiThread(() -> {
            restoreWindow();
            call.resolve();
        });
    }

    private WindowInsetsControllerCompat getInsetsController() {
        Window window = getActivity().getWindow();
        return WindowCompat.getInsetsController(window, window.getDecorView());
    }

    private static int presentationBars() {
        return WindowInsetsCompat.Type.statusBars() | WindowInsetsCompat.Type.navigationBars();
    }

    private int visibleBars() {
        WindowInsetsCompat insets = ViewCompat.getRootWindowInsets(getActivity().getWindow().getDecorView());
        if (insets == null) return presentationBars();
        int status = WindowInsetsCompat.Type.statusBars();
        int navigation = WindowInsetsCompat.Type.navigationBars();
        return (insets.isVisible(status) ? status : 0) | (insets.isVisible(navigation) ? navigation : 0);
    }

    private void restoreWindow() {
        if (exitOnBack == null) return;
        exitOnBack.remove();
        exitOnBack = null;
        getActivity().setRequestedOrientation(previousOrientation);
        WindowInsetsControllerCompat insets = getInsetsController();
        insets.setSystemBarsBehavior(previousBarsBehavior);
        insets.show(previousVisibleBars);
        insets.hide(presentationBars() & ~previousVisibleBars);
    }
}
