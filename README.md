# Sudoku Academy

App para aprender las 23 técnicas avanzadas de Sudoku, pensada para el teléfono.
La app es una sola página web (`app/index.html`) dentro de un APK de Android.

Descarga directa de la última versión: https://github.com/JaiderRico/Sudoku-Academy/releases/latest/download/SudokuAcademy.apk

## Actualización automática

Al abrirse (y cada 6 horas si sigue abierta), la app consulta el último Release de este repositorio.
Si hay una versión mayor que la suya, muestra un aviso con las notas y el botón **Descargar e instalar**.
Por eso el repositorio debe ser **público** (igual que APP_GYM): la llave de firma solo está en el secreto `FIRMA_PEM`.

## Cómo se publica una versión

1. Cambiar `app/index.html` (la app).
2. Subir el número en `version.txt` (por ejemplo `1.0.0` → `1.0.1`). El código de versión de Android se calcula solo (`1.0.1` → 10001), así que cada APK nuevo se instala encima del anterior sin perder el progreso.
3. (Opcional) Escribir en `notas.md` qué cambió.
4. Subirlo a `main`. La automatización **Publicar APK** construye el APK, lo revisa con las herramientas oficiales de Android, lo firma con el secreto `FIRMA_PEM` y crea el Release como **Latest**.

Si la versión ya existía, reemplaza el APK de ese Release.

## Firma

- El secreto `FIRMA_PEM` (Settings → Secrets and variables → Actions) contiene la llave privada y el certificado.
- Huella SHA-256 del certificado: `be3952f009d6ec676a4fa7e191edc5f23131cde1b0413b5aed3b900a8755260b`
- Siempre hay que firmar con esta misma llave: Android no deja instalar una actualización firmada con otra.
- La llave **nunca** se sube al repositorio (`.gitignore` bloquea `*.pem`, `*.p12`, `*.jks`).

## Construir en local (sin Android SDK)

```
python3 herramientas/construir_apk.py                 # → trabajo/sin_firmar.apk
pip install cryptography
python3 herramientas/firmar_apk.py trabajo/sin_firmar.apk SudokuAcademy.apk firma_sudoku.pem
```
