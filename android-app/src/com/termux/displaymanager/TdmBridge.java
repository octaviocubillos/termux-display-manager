package com.termux.displaymanager;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.widget.Toast;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;

public class TdmBridge {
    private final Context context;
    private final WebView webView;
    private static volatile boolean isServerRunning = false;

    public TdmBridge(Context context, WebView webView) {
        this.context = context;
        this.webView = webView;
        startLocalBundleServer();
    }

    private void startLocalBundleServer() {
        if (isServerRunning) return;
        isServerRunning = true;
        new Thread(() -> {
            try (ServerSocket serverSocket = new ServerSocket(19051, 10, InetAddress.getByName("127.0.0.1"))) {
                while (!Thread.currentThread().isInterrupted()) {
                    try {
                        Socket client = serverSocket.accept();
                        new Thread(() -> {
                            try (InputStream in = context.getAssets().open("tdm-bundle.tar.gz");
                                 OutputStream out = client.getOutputStream();
                                 BufferedReader reader = new BufferedReader(new InputStreamReader(client.getInputStream()))) {
                                String line = reader.readLine();
                                String responseHeader = "HTTP/1.1 200 OK\r\nContent-Type: application/gzip\r\nConnection: close\r\n\r\n";
                                out.write(responseHeader.getBytes());
                                byte[] buf = new byte[16384];
                                int len;
                                while ((len = in.read(buf)) != -1) {
                                    out.write(buf, 0, len);
                                }
                                out.flush();
                                client.close();
                            } catch (Exception ignored) {
                            }
                        }).start();
                    } catch (Exception ignored) {
                    }
                }
            } catch (Exception ignored) {
            } finally {
                isServerRunning = false;
            }
        }).start();
    }

    @JavascriptInterface
    public boolean isTermuxInstalled() {
        return isAppInstalled("com.termux");
    }

    @JavascriptInterface
    public boolean isTermuxX11Installed() {
        return isAppInstalled("com.termux.x11");
    }

    @JavascriptInterface
    public boolean isAppInstalled(String packageName) {
        try {
            context.getPackageManager().getPackageInfo(packageName, 0);
            return true;
        } catch (PackageManager.NameNotFoundException e) {
            return false;
        }
    }

    @JavascriptInterface
    public boolean hasRunCommandPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return context.checkSelfPermission("com.termux.permission.RUN_COMMAND") == PackageManager.PERMISSION_GRANTED;
        }
        return true;
    }

    @JavascriptInterface
    public void requestTermuxPermission() {
        if (context instanceof MainActivity) {
            ((MainActivity) context).requestAllPermissions();
        }
    }

    @JavascriptInterface
    public void openAppSettings() {
        if (context instanceof MainActivity) {
            ((MainActivity) context).openAppSettings();
        }
    }

    @JavascriptInterface
    public void markSetupCompleted() {
        SharedPreferences prefs = context.getSharedPreferences("tdm_prefs", Context.MODE_PRIVATE);
        prefs.edit().putBoolean("has_completed_setup", true).apply();
    }

    @JavascriptInterface
    public void launchSetupWizard() {
        if (webView != null) {
            webView.post(() -> webView.loadUrl("file:///android_asset/setup.html"));
        }
    }

    @JavascriptInterface
    public void resetSetup() {
        SharedPreferences prefs = context.getSharedPreferences("tdm_prefs", Context.MODE_PRIVATE);
        prefs.edit().putBoolean("has_completed_setup", false).apply();
        launchSetupWizard();
    }

    private void tryExtractBundleToStorage() {
        try {
            File downloadDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            if (downloadDir != null && (downloadDir.exists() || downloadDir.mkdirs())) {
                File bundleFile = new File(downloadDir, "tdm-bundle.tar.gz");
                try (InputStream in = context.getAssets().open("tdm-bundle.tar.gz");
                     OutputStream out = new FileOutputStream(bundleFile)) {
                    byte[] buffer = new byte[8192];
                    int read;
                    while ((read = in.read(buffer)) != -1) {
                        out.write(buffer, 0, read);
                    }
                    out.flush();
                }
            }
        } catch (Exception ignored) {
        }
    }

    @JavascriptInterface
    public void installBackendInTermux() {
        new Thread(() -> {
            tryExtractBundleToStorage();

            String inlineCmd = "mkdir -p $HOME/.termux && " +
                    "echo 'allow-external-apps = true' >> $HOME/.termux/termux.properties && " +
                    "pkg update -y || true && " +
                    "pkg install -y python x11-repo dbus xorg-xauth xorg-xsetroot procps || true && " +
                    "(tar -xzf /sdcard/Download/tdm-bundle.tar.gz -C $HOME 2>/dev/null || " +
                    "tar -xzf /sdcard/tdm-bundle.tar.gz -C $HOME 2>/dev/null || " +
                    "python3 -c \"import urllib.request, tarfile; tarfile.open(fileobj=urllib.request.urlopen('http://127.0.0.1:19051/bundle.tar.gz', timeout=15), mode='r:gz').extractall('$HOME')\") && " +
                    "cd $HOME/termux-display-manager && bash install.sh";

            boolean success = false;
            try {
                Intent intent = new Intent();
                intent.setClassName("com.termux", "com.termux.app.RunCommandService");
                intent.setAction("com.termux.RUN_COMMAND");
                intent.putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/bash");
                intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{"-c", inlineCmd});
                intent.putExtra("com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home");
                intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true);
                intent.putExtra("com.termux.RUN_COMMAND_IN_BACKGROUND", true);
                intent.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");

                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent);
                } else {
                    context.startService(intent);
                }
                success = true;
            } catch (Exception e) {
                // Si falla el envío en segundo plano por permisos de Android, copiar al portapapeles y abrir Termux
                copyToClipboard(inlineCmd);
                openTermuxApp();
            }

            if (!success) {
                copyToClipboard(inlineCmd);
                openTermuxApp();
            }
        }).start();
    }

    @JavascriptInterface
    public void startTermuxService() {
        try {
            Intent intent = new Intent();
            intent.setClassName("com.termux", "com.termux.app.RunCommandService");
            intent.setAction("com.termux.RUN_COMMAND");
            intent.putExtra("com.termux.RUN_COMMAND_PATH", "/data/data/com.termux/files/usr/bin/tdm");
            intent.putExtra("com.termux.RUN_COMMAND_ARGUMENTS", new String[]{"server", "--port", "19050"});
            intent.putExtra("com.termux.RUN_COMMAND_BACKGROUND", true);
            intent.putExtra("com.termux.RUN_COMMAND_IN_BACKGROUND", true);
            intent.putExtra("com.termux.RUN_COMMAND_SESSION_ACTION", "0");

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
        } catch (Exception ignored) {
        }
    }

    @JavascriptInterface
    public void openTermuxApp() {
        try {
            Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage("com.termux");
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(launchIntent);
            } else {
                openUrlInBrowser("https://f-droid.org/packages/com.termux/");
            }
        } catch (Exception e) {
            Toast.makeText(context, "Error abriendo Termux: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    @JavascriptInterface
    public void openTermuxX11() {
        try {
            Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage("com.termux.x11");
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                context.startActivity(launchIntent);
            } else {
                Toast.makeText(context, "Termux:X11 no está instalado", Toast.LENGTH_SHORT).show();
            }
        } catch (Exception e) {
            Toast.makeText(context, "Error abriendo Termux:X11: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    @JavascriptInterface
    public void openRdClient(int port) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("rdp://127.0.0.1:" + port));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(context, "Conéctate a rdp://127.0.0.1:" + port, Toast.LENGTH_LONG).show();
        }
    }

    @JavascriptInterface
    public void openVncViewer(int port) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("vnc://127.0.0.1:" + port));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(context, "Conéctate a vnc://127.0.0.1:" + port, Toast.LENGTH_LONG).show();
        }
    }

    @JavascriptInterface
    public void copyToClipboard(String text) {
        try {
            ClipboardManager clipboard = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
            ClipData clip = ClipData.newPlainText("TDM Command", text);
            clipboard.setPrimaryClip(clip);
            Toast.makeText(context, "✓ Comando copiado al portapapeles", Toast.LENGTH_SHORT).show();
        } catch (Exception ignored) {
        }
    }

    @JavascriptInterface
    public void openUrlInBrowser(String url) {
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            context.startActivity(intent);
        } catch (Exception ignored) {
        }
    }

    @JavascriptInterface
    public void showNativeToast(String message) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show();
    }
}
