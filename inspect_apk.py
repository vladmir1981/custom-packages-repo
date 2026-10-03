import sys
from pathlib import Path

p = Path("25.12/aarch64_cortex-a53/zapret-72.20260307-r1.apk")

if not p.exists():
    print(f"[!] Файл не найден: {p}")
    sys.exit(1)

data = p.read_bytes()
print(f"Файл: {p}")
print(f"Размер: {len(data)} байт ({len(data)/1024:.1f} КБ)")
print()
print(f"Первые 64 байта (hex):")
print(data[:64].hex(" "))
print()
print(f"Первые 64 байта (repr):")
print(repr(data[:64]))
print()

# Сигнатуры
if data[:2] == b"\x1f\x8b":
    print("[+] gzip")
elif data[:6] == b"\xfd7zXZ\x00":
    print("[+] xz")
elif data[:3] == b"BZh":
    print("[+] bzip2")
elif data[:4] == b"PK\x03\x04":
    print("[+] ZIP")
elif data.startswith(b"!<arch>\n"):
    print("[+] ar-архив")
elif data[:4] == b"\x28\xb5\x2f\xfd":
    print("[+] zstd")
elif data[:2] == b"AD":
    print("[+] Alpine apk v3 (magic AD)")
else:
    print("[?] Формат не распознан, начало файла:")
    try:
        print(data[:200].decode("utf-8", "replace"))
    except Exception:
        pass