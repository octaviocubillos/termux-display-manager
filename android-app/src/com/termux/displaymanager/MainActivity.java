package com.termux.displaymanager;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.view.KeyEvent;
import android.view.View;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private WebView webView;
    private static final String SERVER_URL = "http://127.0.0.1:19050/";
    private static final String SETUP_WIZARD_URL = "file:///android_asset/setup.html";
    private static final String DASHBOARD_FALLBACK_URL = "file:///android_asset/index.html";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Solicitar permisos en tiempo de ejecución (RUN_COMMAND y Almacenamiento)
        requestAllPermissions();

        webView = findViewById(R.id.webview);
        setupWebView();

        // Cargar interfaz según estado de configuración previa
        loadAppInterface();
    }

    public void requestAllPermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            String[] permissions = new String[]{
                "com.termux.permission.RUN_COMMAND",
                Manifest.permission.WRITE_EXTERNAL_STORAGE,
                Manifest.permission.READ_EXTERNAL_STORAGE
            };
            requestPermissions(permissions, 100);
        }
    }

    public void openAppSettings() {
        try {
            Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
            intent.setData(Uri.parse("package:" + getPackageName()));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception ignored) {
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // Hardware Acceleration
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);

        // Inyectar puente nativo Android
        TdmBridge bridge = new TdmBridge(this, webView);
        webView.addJavascriptInterface(bridge, "AndroidBridge");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                if (failingUrl.startsWith("http://127.0.0.1:19050")) {
                    SharedPreferences prefs = getSharedPreferences("tdm_prefs", MODE_PRIVATE);
                    boolean hasCompletedSetup = prefs.getBoolean("has_completed_setup", false);
                    if (!hasCompletedSetup) {
                        view.loadUrl(SETUP_WIZARD_URL);
                    } else {
                        view.loadUrl(DASHBOARD_FALLBACK_URL);
                    }
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient());
    }

    public void loadAppInterface() {
        SharedPreferences prefs = getSharedPreferences("tdm_prefs", MODE_PRIVATE);
        boolean hasCompletedSetup = prefs.getBoolean("has_completed_setup", false);

        if (!hasCompletedSetup) {
            // SI ES LA PRIMERA VEZ, SIEMPRE ABRIR EL ASISTENTE DE CONFIGURACIÓN DE 4 PASOS
            webView.loadUrl(SETUP_WIZARD_URL);
            return;
        }

        new Thread(() -> {
            boolean serverAvailable = false;
            try {
                URL url = new URL("http://127.0.0.1:19050/api/status");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(800);
                conn.setReadTimeout(800);
                conn.setRequestMethod("GET");
                int code = conn.getResponseCode();
                serverAvailable = (code == 200);
                conn.disconnect();
            } catch (Exception ignored) {
            }

            final boolean isOnline = serverAvailable;
            runOnUiThread(() -> {
                if (isOnline) {
                    webView.loadUrl(SERVER_URL);
                } else {
                    webView.loadUrl(DASHBOARD_FALLBACK_URL);
                }
            });
        }).start();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
}
