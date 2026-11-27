#!/usr/bin/env bash
# Prueba de punta a punta en el emulador: la app vieja (1.0.0) se actualiza sola a la versión publicada
# tocando "Actualizar ahora" y luego "Actualizar" en la ventana de Android.
set -u
PKG=com.jaider.sudokuacademy
ESPERADA="$1"
mkdir -p trabajo/capturas
cap() { adb exec-out screencap -p > "trabajo/capturas/$1.png" 2>/dev/null || true; }
tocar() {  # tocar "<regex de texto>" segundos
  local fin=$((SECONDS + $2))
  while [ $SECONDS -lt $fin ]; do
    adb shell uiautomator dump /sdcard/u.xml >/dev/null 2>&1
    adb shell cat /sdcard/u.xml > trabajo/u.xml 2>/dev/null
    local b
    b=$(python3 - "$1" <<'PY'
import re,sys
x=open('trabajo/u.xml',encoding='utf-8',errors='ignore').read()
for n in re.finditer(r'<node [^>]*>', x):
    t=n.group(0); m=re.search(r'(?:text|content-desc)="([^"]*)"',t)
    txt=' '.join(re.findall(r'(?:text|content-desc)="([^"]*)"',t))
    if re.search(sys.argv[1], txt, re.I) and 'clickable="true"' in t or (re.search(sys.argv[1], txt, re.I) and 'Button' in t):
        bb=re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',t)
        if bb: a,b_,c,d=map(int,bb.groups()); print((a+c)//2,(b_+d)//2); break
PY
)
    if [ -n "$b" ]; then echo "Toco '$1' en $b"; adb shell input tap $b; return 0; fi
    sleep 2
  done
  echo "No apareció '$1'"; return 1
}
adb shell dumpsys package $PKG | grep versionName
cap 1_inicio
tocar 'Actualizar ahora' 90 || { cap fallo_boton; cat trabajo/u.xml | head -c 4000; exit 1; }
sleep 3; cap 2_descargando
tocar '^(Update|Actualizar|Install|Instalar)$' 180 || { cap fallo_confirmar; head -c 4000 trabajo/u.xml; exit 1; }
cap 3_confirmado
for i in $(seq 1 60); do
  V=$(adb shell dumpsys package $PKG | grep -m1 versionName | sed 's/.*versionName=//' | tr -d '\r ')
  echo "versión instalada: $V"
  if [ "$V" = "$ESPERADA" ]; then echo "✅ Se actualizó sola dentro de la app a $V"; cap 4_listo; exit 0; fi
  sleep 3
done
cap fallo_final; exit 1
