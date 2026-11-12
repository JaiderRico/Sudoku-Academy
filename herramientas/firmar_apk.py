#!/usr/bin/env python3
"""Firma un APK con APK Signature Scheme v2 (sin Android SDK). Requiere: pip install cryptography

GitHub Actions usa apksigner (más completo); este script es para firmar en local con la misma llave.
Uso:  python3 herramientas/firmar_apk.py entrada.apk salida.apk firma_sudoku.pem
El .pem debe contener la llave privada y el certificado (el mismo texto del secreto FIRMA_PEM).
"""
import hashlib, struct, sys
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

def lp(b): return struct.pack('<I', len(b)) + b

def digest_v2(secciones):
    trozos = []
    for s in secciones:
        for i in range(0, len(s), 1 << 20):
            c = s[i:i + (1 << 20)]
            trozos.append(hashlib.sha256(b'\xa5' + struct.pack('<I', len(c)) + c).digest())
    return hashlib.sha256(b'\x5a' + struct.pack('<I', len(trozos)) + b''.join(trozos)).digest()

def firmar(apk, pem):
    llave = serialization.load_pem_private_key(pem, None)
    cert = x509.load_pem_x509_certificate(pem)
    eocd = apk.rfind(b'PK\x05\x06')
    cd_size, cd_off = struct.unpack_from('<II', apk, eocd + 12)
    secciones = [apk[:cd_off], apk[cd_off:cd_off + cd_size], apk[eocd:]]
    d = digest_v2(secciones)
    ALG = 0x0103  # RSASSA-PKCS1-v1_5 + SHA-256
    signed = lp(lp(struct.pack('<I', ALG) + lp(d))) + lp(lp(cert.public_bytes(serialization.Encoding.DER))) + lp(b'')
    firma = llave.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    pub = llave.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = lp(signed) + lp(lp(struct.pack('<I', ALG) + lp(firma))) + lp(pub)
    valor = lp(lp(signer))
    par = struct.pack('<QI', 4 + len(valor), 0x7109871a) + valor
    tam = len(par) + 8 + 16
    bloque = struct.pack('<Q', tam) + par + struct.pack('<Q', tam) + b'APK Sig Block 42'
    nuevo_eocd = bytearray(apk[eocd:])
    struct.pack_into('<I', nuevo_eocd, 16, cd_off + len(bloque))
    return apk[:cd_off] + bloque + apk[cd_off:cd_off + cd_size] + bytes(nuevo_eocd)

if __name__ == '__main__':
    ent, sal, pem = sys.argv[1:4]
    open(sal, 'wb').write(firmar(open(ent, 'rb').read(), open(pem, 'rb').read()))
    print('APK firmado (v2):', sal)
