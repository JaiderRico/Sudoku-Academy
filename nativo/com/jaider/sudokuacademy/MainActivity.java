package com.jaider.sudokuacademy;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;

import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * WebView a pantalla completa con app/index.html.
 * Puente "Android" para JavaScript: descarga la versión nueva y la instala sin salir de la app
 * (PackageInstaller: Android solo pide confirmar con "Actualizar").
 */
public class MainActivity extends Activity {
    private static final String ACCION_INSTALAR = "com.jaider.sudokuacademy.INSTALAR";
    private WebView web;
    private String pendiente;          // URL a descargar cuando el usuario dé el permiso de instalar
    private volatile boolean ocupado;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);   // localStorage (progreso)
        s.setTextZoom(100);             // ignora el tamaño de letra del sistema
        web.addJavascriptInterface(new Puente(), "Android");
        web.loadUrl("file:///android_asset/index.html");
        setContentView(web);
        resultado(getIntent());
    }

    @Override
    protected void onNewIntent(Intent i) {
        super.onNewIntent(i);
        resultado(i);
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Volvió de Ajustes: si ya dio el permiso, sigue con la descarga.
        if (pendiente != null) {
            String u = pendiente;
            if (puedeInstalar()) { pendiente = null; descargar(u); }
            else { pendiente = null; avisar("permiso_no", ""); }
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    private boolean puedeInstalar() {
        return Build.VERSION.SDK_INT < 26 || getPackageManager().canRequestPackageInstalls();
    }

    /** Llama a window.onDescarga(estado, valor) en la página. */
    private void avisar(final String estado, final Object valor) {
        final String v = valor instanceof Number ? valor.toString() : JSONObject.quote(String.valueOf(valor));
        runOnUiThread(new Runnable() {
            @Override public void run() {
                if (web != null) web.evaluateJavascript("window.onDescarga&&window.onDescarga(" + JSONObject.quote(estado) + "," + v + ")", null);
            }
        });
    }

    /** Respuesta del instalador de Android. */
    private void resultado(Intent i) {
        if (i == null || !ACCION_INSTALAR.equals(i.getAction())) return;
        int st = i.getIntExtra(PackageInstaller.EXTRA_STATUS, -999);
        if (st == PackageInstaller.STATUS_PENDING_USER_ACTION) {
            Intent confirmar = i.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirmar != null) {
                try { startActivity(confirmar); avisar("confirmar", ""); }
                catch (Exception e) { avisar("error", "No se pudo abrir el instalador: " + e.getMessage()); }
            }
        } else if (st == PackageInstaller.STATUS_SUCCESS) {
            avisar("listo", "");
        } else if (st == PackageInstaller.STATUS_FAILURE_ABORTED) {
            ocupado = false; avisar("cancelado", "");
        } else {
            ocupado = false;
            String m = i.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
            avisar("error", m == null ? ("código " + st) : m);
        }
    }

    private void descargar(final String url) {
        if (ocupado) return;
        ocupado = true;
        new Thread(new Runnable() {
            @Override public void run() {
                PackageInstaller.Session sesion = null;
                try {
                    avisar("progreso", 0);
                    HttpURLConnection c = null;
                    String dir = url;
                    for (int saltos = 0; saltos < 6; saltos++) {     // GitHub redirige a otro servidor
                        c = (HttpURLConnection) new URL(dir).openConnection();
                        c.setInstanceFollowRedirects(false);
                        c.setConnectTimeout(20000);
                        c.setReadTimeout(30000);
                        c.setRequestProperty("User-Agent", "SudokuAcademy");
                        int code = c.getResponseCode();
                        if (code >= 300 && code < 400) { dir = new URL(new URL(dir), c.getHeaderField("Location")).toString(); c.disconnect(); continue; }
                        if (code != 200) throw new Exception("HTTP " + code);
                        break;
                    }
                    long total = c.getContentLength();
                    PackageInstaller pi = getPackageManager().getPackageInstaller();
                    PackageInstaller.SessionParams p = new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
                    p.setAppPackageName(getPackageName());
                    if (total > 0) p.setSize(total);
                    if (Build.VERSION.SDK_INT >= 31) p.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_NOT_REQUIRED);
                    int id = pi.createSession(p);
                    sesion = pi.openSession(id);
                    InputStream in = c.getInputStream();
                    OutputStream out = sesion.openWrite("SudokuAcademy.apk", 0, total > 0 ? total : -1);
                    byte[] buf = new byte[65536];
                    long hecho = 0; int ultimo = -1, n;
                    while ((n = in.read(buf)) > 0) {
                        out.write(buf, 0, n);
                        hecho += n;
                        if (total > 0) { int pct = (int) (hecho * 100 / total); if (pct != ultimo) { ultimo = pct; avisar("progreso", pct); } }
                    }
                    sesion.fsync(out);
                    out.close(); in.close(); c.disconnect();
                    avisar("instalando", "");
                    Intent vuelta = new Intent(MainActivity.this, MainActivity.class).setAction(ACCION_INSTALAR);
                    int flags = PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 31 ? 0x02000000 /* FLAG_MUTABLE */ : 0);
                    PendingIntent pend = PendingIntent.getActivity(MainActivity.this, 7, vuelta, flags);
                    sesion.commit(pend.getIntentSender());
                    sesion.close();
                } catch (Exception e) {
                    if (sesion != null) try { sesion.abandon(); } catch (Exception ignored) {}
                    ocupado = false;
                    avisar("error", "No se pudo descargar: " + e.getMessage());
                }
            }
        }).start();
    }

    /** Lo que ve JavaScript como window.Android. */
    public class Puente {
        @JavascriptInterface public int version() { return 2; }

        @JavascriptInterface public void instalar(final String url) {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    if (ocupado) return;
                    if (!puedeInstalar()) {
                        pendiente = url;
                        avisar("permiso", "");
                        try {
                            startActivity(new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getPackageName())));
                        } catch (Exception e) { pendiente = null; avisar("error", "No se pudo abrir Ajustes."); }
                        return;
                    }
                    descargar(url);
                }
            });
        }
    }
}
