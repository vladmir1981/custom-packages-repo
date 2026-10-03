#!/usr/bin/env python3
"""
Генерирует APKINDEX.tar.gz для папок 25.12/* с .apk файлами zapret2.

Метаданные берёт из соответствующих .ipk файлов, которые лежат РЯДОМ
в той же папке 25.12/<arch>/.
"""
import base64, hashlib, io, os, sys, tarfile
from pathlib import Path


def sha1_q1(data):
    return "Q1" + base64.b64encode(hashlib.sha1(data).digest()).decode("ascii")


def read_ipk_control(ipk_path):
    with open(ipk_path, "rb") as f:
        data = f.read()
    if data[:2] == b"\x1f\x8b":
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as outer:
                for m in outer.getmembers():
                    if "control.tar" in m.name:
                        ext = outer.extractfile(m)
                        if not ext:
                            continue
                        cd = ext.read()
                        mode = ("r:gz" if cd[:2] == b"\x1f\x8b"
                                else "r:xz" if cd[:6] == b"\xfd7zXZ\x00" else "r:")
                        with tarfile.open(fileobj=io.BytesIO(cd), mode=mode) as inner:
                            for mm in inner.getmembers():
                                if mm.name.endswith("control"):
                                    f = inner.extractfile(mm)
                                    if f:
                                        return f.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"  [!] tar.gz: {e}")
    return ""


def parse_control(text):
    fields = {}
    cur = None
    for line in text.splitlines():
        if line.startswith(" ") and cur:
            fields[cur] += "\n" + line
        elif ": " in line:
            k, v = line.split(": ", 1)
            fields[k] = v
            cur = k
    return fields


def find_ipk(apk_dir, apk_name):
    """zapret2_aarch64_cortex-a53.apk → zapret2_aarch64_cortex-a53.ipk
       luci-app-zapret2.apk → luci-app-zapret2.ipk"""
    base = apk_name[:-4]  # убираем .apk
    candidate = apk_dir / f"{base}.ipk"
    if candidate.exists():
        return candidate
    return None


def build_entry(apk_path, ipk_path):
    apk_data = apk_path.read_bytes()
    apk_size = len(apk_data)
    q1 = sha1_q1(apk_data)

    ctrl_text = read_ipk_control(str(ipk_path))
    if not ctrl_text:
        print(f"  [!] control не читается: {ipk_path.name}")
        return None

    c = parse_control(ctrl_text)
    name = c.get("Package", "")
    ver = c.get("Version", "")
    arch = c.get("Architecture", "")
    depends = c.get("Depends", "").replace(",", " ")
    provides = c.get("Provides", "").replace(",", " ")
    desc = c.get("Description", "").strip()
    license_ = c.get("License", "")

    lines = [
        f"C:{q1}",
        f"P:{name}",
        f"V:{ver}",
        f"A:{arch}",
        f"S:{apk_size}",
        f"I:{apk_size}",
    ]
    if desc:
        lines.append(f"T:{desc}")
    if license_:
        lines.append(f"L:{license_}")
    lines.append(f"o:{name}")
    if depends:
        lines.append(f"D:{depends}")
    if provides:
        lines.append(f"p:{provides}")
    return "\n".join(lines)


def build_apkindex(apk_dir):
    apk_dir = Path(apk_dir)
    if not apk_dir.exists():
        return 0

    apks = sorted(apk_dir.glob("*.apk"))
    if not apks:
        print(f"  [!] {apk_dir}: нет .apk")
        return 0

    print(f"\n[Инфо] {apk_dir}: {len(apks)} .apk")
    entries = []
    for apk in apks:
        ipk = find_ipk(apk_dir, apk.name)
        if not ipk:
            print(f"  [!] Нет .ipk для {apk.name}")
            continue
        print(f"  Метаданные из: {ipk.name}")
        entry = build_entry(apk, ipk)
        if entry:
            entries.append(entry)
            print(f"  [+] {apk.name}")

    if not entries:
        return 0

    index_text = "\n\n".join(entries) + "\n"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = index_text.encode("utf-8")
        ti = tarfile.TarInfo(name="APKINDEX")
        ti.size = len(data)
        ti.mtime = 0
        ti.mode = 0o644
        tar.addfile(ti, io.BytesIO(data))

    out = apk_dir / "APKINDEX.tar.gz"
    out.write_bytes(buf.getvalue())
    print(f"  [+] {out.name}: {len(entries)} пакетов, {len(buf.getvalue())} байт")
    return len(entries)


def main():
    root = Path(__file__).parent / "25.12"
    if not root.exists():
        print(f"[!] Нет папки {root}")
        sys.exit(1)
    total = 0
    for sub in sorted(root.iterdir()):
        if sub.is_dir():
            total += build_apkindex(sub)
    print(f"\n[Готово] Всего записей: {total}")


if __name__ == "__main__":
    main()