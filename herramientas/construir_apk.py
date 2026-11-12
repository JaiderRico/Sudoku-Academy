#!/usr/bin/env python3
"""Construye el APK (sin firmar, ya alineado) de Sudoku Academy SIN Android SDK.

La app es un WebView a pantalla completa que abre app/index.html.
Todo se genera aquí con la librería estándar de Python:
  - classes.dex          (MainActivity escrita a mano en bytecode Dalvik)
  - AndroidManifest.xml  (XML binario)
  - resources.arsc       (un solo recurso: el ícono)
Luego se firma con apksigner (en GitHub Actions) o con firmar_apk.py (local).

Uso:
  python3 herramientas/construir_apk.py --version 1.0.0 --salida trabajo/sin_firmar.apk
"""
import argparse, hashlib, pathlib, struct, zipfile, zlib

PAQUETE = 'com.jaider.sudokuacademy'
NOMBRE_APP = 'Sudoku Academy'
MIN_SDK, TARGET_SDK = 24, 34   # 34: sin el "edge-to-edge" forzado de Android 15 (la barra de estado no tapa la app)
RAIZ = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- utilidades
def uleb(n):
    out = bytearray()
    while True:
        b = n & 0x7f; n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n: return bytes(out)

def pad4(b):
    return b + b'\0' * (-len(b) % 4)


# ---------------------------------------------------------------- DEX
def construir_dex():
    """MainActivity:
        onCreate(b): super.onCreate(b); requestWindowFeature(1 /*sin barra de título*/);
                     WebView w = new WebView(this); WebSettings s = w.getSettings();
                     s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setTextZoom(100);
                     w.loadUrl("file:///android_asset/index.html"); setContentView(w);
    """
    CLS = 'L' + PAQUETE.replace('.', '/') + '/MainActivity;'
    ACT, CTX, BUNDLE, VIEW = 'Landroid/app/Activity;', 'Landroid/content/Context;', 'Landroid/os/Bundle;', 'Landroid/view/View;'
    WS, WV, STR = 'Landroid/webkit/WebSettings;', 'Landroid/webkit/WebView;', 'Ljava/lang/String;'
    URL = 'file:///android_asset/index.html'

    def shorty(ret, params):
        s = lambda t: 'L' if t.startswith(('L', '[')) else t
        return s(ret) + ''.join(s(p) for p in params)

    # (clase, nombre, retorno, parámetros)
    metodos = [
        (ACT, '<init>', 'V', []), (ACT, 'onCreate', 'V', [BUNDLE]), (ACT, 'requestWindowFeature', 'Z', ['I']),
        (ACT, 'setContentView', 'V', [VIEW]), (CLS, '<init>', 'V', []), (CLS, 'onCreate', 'V', [BUNDLE]),
        (WS, 'setDomStorageEnabled', 'V', ['Z']), (WS, 'setJavaScriptEnabled', 'V', ['Z']), (WS, 'setTextZoom', 'V', ['I']),
        (WV, '<init>', 'V', [CTX]), (WV, 'getSettings', WS, []), (WV, 'loadUrl', 'V', [STR]),
    ]
    protos = sorted({(r, tuple(p)) for _, _, r, p in metodos})
    tipos = {ACT, CLS, WS, WV}
    for _, _, r, p in metodos: tipos.add(r); tipos.update(p)
    cadenas = set(tipos) | {URL} | {n for _, n, _, _ in metodos} | {shorty(r, p) for r, p in protos}

    # Orden canónico: cadenas por UTF-16, tipos por índice de cadena, protos por (retorno, params), métodos por (clase, nombre, proto)
    cadenas = sorted(cadenas, key=lambda s: s.encode('utf-16-be'))
    si = {s: i for i, s in enumerate(cadenas)}
    tipos = sorted(tipos, key=lambda t: si[t])
    ti = {t: i for i, t in enumerate(tipos)}
    protos = sorted(protos, key=lambda pr: (ti[pr[0]], [ti[x] for x in pr[1]]))
    pi = {pr: i for i, pr in enumerate(protos)}
    metodos = sorted(metodos, key=lambda m: (ti[m[0]], si[m[1]], pi[(m[2], tuple(m[3]))]))
    mi = {(c, n, r, tuple(p)): i for i, (c, n, r, p) in enumerate(metodos)}
    M = lambda c, n, r, p=(): mi[(c, n, r, tuple(p))]

    def inv(op, regs, midx):  # formato 35c: invoke-* {regs}, método
        n = len(regs); r = list(regs) + [0] * (5 - n)
        return [(n << 12) | op, midx, (r[3] << 12) | (r[2] << 8) | (r[1] << 4) | r[0]]

    # <init>: registros p0=v0
    code_init = inv(0x70, [0], M(ACT, '<init>', 'V')) + [0x000e]
    # onCreate: v0=WebView v1=ajustes/url v2=constante, p0=v3 (this) p1=v4 (bundle)
    code_on = []
    code_on += inv(0x6f, [3, 4], M(ACT, 'onCreate', 'V', [BUNDLE]))           # invoke-super
    code_on += [(1 << 12) | (2 << 8) | 0x12]                                  # const/4 v2, 1
    code_on += inv(0x6e, [3, 2], M(ACT, 'requestWindowFeature', 'Z', ['I']))   # sin barra de título
    code_on += [(0 << 8) | 0x22, ti[WV]]                                      # new-instance v0, WebView
    code_on += inv(0x70, [0, 3], M(WV, '<init>', 'V', [CTX]))
    code_on += inv(0x6e, [0], M(WV, 'getSettings', WS))
    code_on += [(1 << 8) | 0x0c]                                              # move-result-object v1
    code_on += inv(0x6e, [1, 2], M(WS, 'setJavaScriptEnabled', 'V', ['Z']))
    code_on += inv(0x6e, [1, 2], M(WS, 'setDomStorageEnabled', 'V', ['Z']))   # localStorage (progreso)
    code_on += [(2 << 8) | 0x13, 100]                                         # const/16 v2, 100
    code_on += inv(0x6e, [1, 2], M(WS, 'setTextZoom', 'V', ['I']))            # ignora el tamaño de letra del sistema
    code_on += [(1 << 8) | 0x1a, si[URL]]                                     # const-string v1, URL
    code_on += inv(0x6e, [0, 1], M(WV, 'loadUrl', 'V', [STR]))
    code_on += inv(0x6e, [3, 0], M(ACT, 'setContentView', 'V', [VIEW]))
    code_on += [0x000e]                                                       # return-void

    def code_item(regs, ins, outs, insns):
        return struct.pack('<HHHHII', regs, ins, outs, 0, 0, len(insns)) + struct.pack('<%dH' % len(insns), *insns)

    # --- disposición
    H = 0x70
    off = H
    o_str = off; off += 4 * len(cadenas)
    o_typ = off; off += 4 * len(tipos)
    o_pro = off; off += 12 * len(protos)
    o_met = off; off += 8 * len(metodos)
    o_cls = off; off += 32
    data_off = off

    data = bytearray()
    def at(): return data_off + len(data)
    def align():
        while at() % 4: data.append(0)

    align()
    o_code_init = at(); data += code_item(1, 1, 1, code_init); align()
    o_code_on = at(); data += code_item(5, 2, 2, code_on); align()
    n_code = 2

    listas = {}
    o_tl = at()
    for r, p in protos:
        if p and p not in listas:
            align(); listas[p] = at()
            data += struct.pack('<I', len(p)) + b''.join(struct.pack('<H', ti[x]) for x in p)
    align()
    n_tl = len(listas)

    o_sd = at(); offs_str = []
    for s in cadenas:
        offs_str.append(at())
        data += uleb(len(s.encode('utf-16-le')) // 2) + s.encode('utf-8') + b'\0'

    o_cd = at()
    m_init = M(CLS, '<init>', 'V'); m_on = M(CLS, 'onCreate', 'V', [BUNDLE])
    data += uleb(0) + uleb(0) + uleb(1) + uleb(1)
    data += uleb(m_init) + uleb(0x10001) + uleb(o_code_init)    # public constructor
    data += uleb(m_on) + uleb(0x4) + uleb(o_code_on)            # protected onCreate
    align()

    o_map = at()
    items = [(0x0000, 1, 0), (0x0001, len(cadenas), o_str), (0x0002, len(tipos), o_typ), (0x0003, len(protos), o_pro),
             (0x0005, len(metodos), o_met), (0x0006, 1, o_cls), (0x2001, n_code, o_code_init)]
    if n_tl: items.append((0x1001, n_tl, min(listas.values())))
    items += [(0x2002, len(cadenas), o_sd), (0x2000, 1, o_cd), (0x1000, 1, o_map)]
    items.sort(key=lambda x: x[2])
    data += struct.pack('<I', len(items)) + b''.join(struct.pack('<HHII', t, 0, n, o) for t, n, o in items)

    secc = bytearray()
    secc += b''.join(struct.pack('<I', o) for o in offs_str)
    secc += b''.join(struct.pack('<I', si[t]) for t in tipos)
    for r, p in protos:
        secc += struct.pack('<III', si[shorty(r, p)], ti[r], listas.get(p, 0) if p else 0)
    for c, n, r, p in metodos:
        secc += struct.pack('<HHI', ti[c], pi[(r, tuple(p))], si[n])
    secc += struct.pack('<IIIIIIII', ti[CLS], 0x1, ti[ACT], 0, 0xFFFFFFFF, 0, o_cd, 0)
    assert H + len(secc) == data_off

    total = data_off + len(data)
    hdr = bytearray(b'dex\n035\0' + b'\0' * 24)
    hdr += struct.pack('<IIIIII', total, H, 0x12345678, 0, 0, o_map)
    hdr += struct.pack('<IIIIIIIIIIII', len(cadenas), o_str, len(tipos), o_typ, len(protos), o_pro, 0, 0,
                       len(metodos), o_met, 1, o_cls)
    hdr += struct.pack('<II', len(data), data_off)
    assert len(hdr) == H
    dex = bytearray(hdr + secc + data)
    dex[12:32] = hashlib.sha1(dex[32:]).digest()
    dex[8:12] = struct.pack('<I', zlib.adler32(bytes(dex[12:])) & 0xFFFFFFFF)
    return bytes(dex)


# ---------------------------------------------------------------- XML binario / recursos
def pool_utf16(strs):
    cuerpo = bytearray(); offs = []
    for s in strs:
        offs.append(len(cuerpo))
        u = s.encode('utf-16-le')
        cuerpo += struct.pack('<H', len(u) // 2) + u + b'\0\0'
    cuerpo = pad4(bytes(cuerpo))
    start = 28 + 4 * len(strs)
    return struct.pack('<HHIIIIII', 0x0001, 28, start + len(cuerpo), len(strs), 0, 0, start, 0) + \
        b''.join(struct.pack('<I', o) for o in offs) + cuerpo

ANDROID_NS = 'http://schemas.android.com/apk/res/android'
ATTR_IDS = {'label': 0x01010001, 'icon': 0x01010002, 'name': 0x01010003, 'exported': 0x01010010,
            'configChanges': 0x0101001f, 'minSdkVersion': 0x0101020c, 'versionCode': 0x0101021b,
            'versionName': 0x0101021c, 'targetSdkVersion': 0x01010270, 'allowBackup': 0x01010280}
T_REF, T_STR, T_DEC, T_HEX, T_BOOL = 0x01, 0x03, 0x10, 0x11, 0x12

def construir_manifest(version, codigo):
    arbol = ('manifest', [(None, 'package', T_STR, PAQUETE), ('a', 'versionCode', T_DEC, codigo), ('a', 'versionName', T_STR, version)], [
        ('uses-sdk', [('a', 'minSdkVersion', T_DEC, MIN_SDK), ('a', 'targetSdkVersion', T_DEC, TARGET_SDK)], []),
        ('application', [('a', 'label', T_STR, NOMBRE_APP), ('a', 'icon', T_REF, 0x7f010000), ('a', 'allowBackup', T_BOOL, True)], [
            ('activity', [('a', 'name', T_STR, PAQUETE + '.MainActivity'), ('a', 'exported', T_BOOL, True),
                          ('a', 'configChanges', T_HEX, 0x04a0)], [   # orientation|keyboardHidden|screenSize: girar no reinicia
                ('intent-filter', [], [
                    ('action', [('a', 'name', T_STR, 'android.intent.action.MAIN')], []),
                    ('category', [('a', 'name', T_STR, 'android.intent.category.LAUNCHER')], [])])])])])

    attrs_res = list(ATTR_IDS)          # primero los nombres con id de recurso, en el orden del mapa
    otras = []
    def recoger(n):
        tag, at, hijos = n
        for s in [tag] + [a[1] for a in at if a[1] not in ATTR_IDS] + [a[3] for a in at if a[2] == T_STR]:
            if s not in attrs_res and s not in otras: otras.append(s)
        for h in hijos: recoger(h)
    recoger(arbol)
    for s in ('android', ANDROID_NS):
        if s not in otras: otras.append(s)
    strs = attrs_res + otras
    idx = {s: i for i, s in enumerate(strs)}

    cuerpo = bytearray()
    cuerpo += struct.pack('<HHIIIII', 0x0100, 16, 24, 1, 0xFFFFFFFF, idx['android'], idx[ANDROID_NS])
    def emitir(n):
        tag, at, hijos = n
        at = sorted(at, key=lambda a: ATTR_IDS.get(a[1], 0))   # sin id primero, luego por id
        bloques = bytearray()
        for ns, nom, tp, val in at:
            if tp == T_STR: raw, data = idx[val], idx[val]
            elif tp == T_BOOL: raw, data = 0xFFFFFFFF, 0xFFFFFFFF if val else 0
            else: raw, data = 0xFFFFFFFF, val
            bloques += struct.pack('<IIIHBBI', idx[ANDROID_NS] if ns else 0xFFFFFFFF, idx[nom], raw, 8, 0, tp, data)
        ext = struct.pack('<IIHHHHHH', 0xFFFFFFFF, idx[tag], 20, 20, len(at), 0, 0, 0)
        cuerpo.extend(struct.pack('<HHIII', 0x0102, 16, 16 + len(ext) + len(bloques), 1, 0xFFFFFFFF) + ext + bloques)
        for h in hijos: emitir(h)
        cuerpo.extend(struct.pack('<HHIIIII', 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, idx[tag]))
    emitir(arbol)
    cuerpo += struct.pack('<HHIIIII', 0x0101, 16, 24, 1, 0xFFFFFFFF, idx['android'], idx[ANDROID_NS])

    pool = pool_utf16(strs)
    mapa = struct.pack('<HHI', 0x0180, 8, 8 + 4 * len(attrs_res)) + b''.join(struct.pack('<I', ATTR_IDS[a]) for a in attrs_res)
    contenido = pool + mapa + bytes(cuerpo)
    return struct.pack('<HHI', 0x0003, 8, 8 + len(contenido)) + contenido

def construir_arsc(ruta_icono):
    valores = pool_utf16([ruta_icono])
    tipos = pool_utf16(['drawable'])
    claves = pool_utf16(['ic_launcher'])
    spec = struct.pack('<HHIBBHII', 0x0202, 16, 20, 1, 0, 0, 1, 0)
    config = struct.pack('<I', 64) + b'\0' * 60
    entrada = struct.pack('<HHI', 8, 0, 0) + struct.pack('<HBBI', 8, 0, T_STR, 0)
    th = 20 + len(config)
    tipo = struct.pack('<HHIBBHII', 0x0201, th, th + 4 + len(entrada), 1, 0, 0, 1, th + 4) + config + struct.pack('<I', 0) + entrada
    nombre = PAQUETE.encode('utf-16-le').ljust(256, b'\0')
    ph = 288
    cabecera_pkg = struct.pack('<HHII', 0x0200, ph, 0, 0x7f) + nombre + struct.pack('<IIIII', ph, 1, ph + len(tipos), 1, 0)
    pkg = bytearray(cabecera_pkg + tipos + claves + spec + tipo)
    struct.pack_into('<I', pkg, 4, len(pkg))
    cuerpo = valores + bytes(pkg)
    return struct.pack('<HHII', 0x0002, 12, 12 + len(cuerpo), 1) + cuerpo


# ---------------------------------------------------------------- ZIP alineado
def escribir_apk(salida, entradas):
    """entradas: lista de (nombre, bytes, comprimir). Las no comprimidas quedan alineadas a 4 bytes (zipalign)."""
    with open(salida, 'wb') as f, zipfile.ZipFile(f, 'w') as z:
        for nombre, datos, comprimir in entradas:
            zi = zipfile.ZipInfo(nombre, date_time=(2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED if comprimir else zipfile.ZIP_STORED
            zi.create_system = 0
            if not comprimir:
                inicio = f.tell() + 30 + len(nombre.encode())
                zi.extra = b'\0' * (-inicio % 4)
            z.writestr(zi, datos)


def codigo_de_version(v):
    a, b, c = (int(x) for x in v.split('.'))
    return a * 10000 + b * 100 + c

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', default=(RAIZ / 'version.txt').read_text().strip())
    ap.add_argument('--html', default=str(RAIZ / 'app' / 'index.html'))
    ap.add_argument('--icono', default=str(RAIZ / 'herramientas' / 'icono.png'))
    ap.add_argument('--salida', default=str(RAIZ / 'trabajo' / 'sin_firmar.apk'))
    a = ap.parse_args()
    ruta_icono = 'res/drawable/ic_launcher.png'
    pathlib.Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    escribir_apk(a.salida, [
        ('AndroidManifest.xml', construir_manifest(a.version, codigo_de_version(a.version)), True),
        ('classes.dex', construir_dex(), True),
        ('resources.arsc', construir_arsc(ruta_icono), False),   # Android 11+ exige que vaya sin comprimir y alineado
        (ruta_icono, pathlib.Path(a.icono).read_bytes(), False),
        ('assets/index.html', pathlib.Path(a.html).read_bytes(), True),
    ])
    print(f'APK sin firmar: {a.salida}  (versión {a.version}, código {codigo_de_version(a.version)})')

if __name__ == '__main__':
    main()
