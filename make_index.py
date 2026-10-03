#!/usr/bin/env python3
"""
Генерирует Packages и Packages.gz для папки с .ipk файлами.

Использование:
    python3 make_index.py <путь_к_папке>
"""
import gzip
import hashlib
import io
import os
import sys
import tarfile
import glob


def get_control(ipk_path):
    with open(ipk_path, "rb") as f:
        data = f.read()

    # Современный .ipk = tar.gz
    if data[:2] == b"\x1f\x8b":
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as outer:
                for member in outer.getmembers():
                    if "control.tar" in member.name:
                        ext = outer.extractfile(member)
                        if not ext:
                            continue
                        ctrl_data = ext.read()
                        if ctrl_data[:2] == b"\x1f\x8b":
                            inner_mode = "r:gz"
                        elif ctrl_data[:6] == b"\xfd7zXZ\x00":
                            inner_mode = "r:xz"
                        elif ctrl_data[:3] == b"BZh":
                            inner_mode = "r:bz2"
                        else:
                            inner_mode = "r:"
                        with tarfile.open(fileobj=io.BytesIO(ctrl_data), mode=inner_mode) as inner:
                            for m in inner.getmembers():
                                if m.name.endswith("control"):
                                    cf = inner.extractfile(m)
                                    if cf:
                                        return cf.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"  [!] tar.gz разбор упал: {e}")

    # Старый .ipk = ar-архив
    if data.startswith(b"!<arch>\n"):
        pos = 8
        entries = {}
        while pos + 60 <= len(data):
            hdr = data[pos:pos+60]
            if hdr[58:60] != b"\x60\x0a":
                break
            name = hdr[0:16].decode("ascii", "ignore").strip()
            try:
                size = int(hdr[48:58].decode("ascii", "ignore").strip())
            except ValueError:
                break
            pos += 60
            if name.startswith("#1/"):
                try:
                    name_len = int(name[3:])
                except ValueError:
                    name_len = 0
                real = data[pos:pos+name_len].decode("ascii", "ignore").strip()
                pos += name_len
                size -= name_len
            else:
                real = name.rstrip("/")
            payload = data[pos:pos+size]
            pos += size
            if pos % 2:
                pos += 1
            entries[real] = payload

        for name, payload in entries.items():
            if name.startswith("control.tar"):
                if payload[:2] == b"\x1f\x8b":
                    mode = "r:gz"
                elif payload[:6] == b"\xfd7zXZ\x00":
                    mode = "r:xz"
                else:
                    mode = "r:"
                try:
                    with tarfile.open(fileobj=io.BytesIO(payload), mode=mode) as t:
                        for m in t.getmembers():
                            if m.name.endswith("control"):
                                f = t.extractfile(m)
                                if f:
                                    return f.read().decode("utf-8", "ignore")
                except Exception as e:
                    print(f"  [!] control.tar не открылся: {e}")

    return ""


def make_entry(ipk_path):
    ctrl = get_control(ipk_path)
    if not ctrl:
        print(f"  [!] control не прочитан: {os.path.basename(ipk_path)}")
        return None

    fields = {}
    current = None
    for line in ctrl.splitlines():
        if line.startswith(" ") and current:
            fields[current] += "\n" + line
        elif ": " in line:
            k, v = line.split(": ", 1)
            fields[k] = v
            current = k

    size = os.path.getsize(ipk_path)
    with open(ipk_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    name = os.path.basename(ipk_path)

    return "\n".join([
        f"Package: {fields.get('Package', '')}",
        f"Version: {fields.get('Version', '')}",
        f"Depends: {fields.get('Depends', '')}",
        f"Provides: {fields.get('Provides', '')}",
        "Status: install ok installed",
        f"Architecture: {fields.get('Architecture', '')}",
        "Installed-Size: 0",
        f"Filename: {name}",
        f"Size: {size}",
        f"SHA256sum: {sha}",
        f"Description: {fields.get('Description', '')}",
    ])


def main():
    if len(sys.argv) < 2:
        print("Использование: python3 make_index.py <папка>")
        sys.exit(1)

    out_dir = sys.argv[1]
    if not os.path.isdir(out_dir):
        print(f"[!] Папка не найдена: {out_dir}")
        sys.exit(1)

    ipks = sorted(glob.glob(os.path.join(out_dir, "*.ipk")))
    print(f"[Инфо] {out_dir}: найдено {len(ipks)} .ipk")

    entries = []
    for ipk in ipks:
        e = make_entry(ipk)
        if e:
            entries.append(e)
            print(f"  [+] {os.path.basename(ipk)}")

    if not entries:
        print("[!] Ни одной записи — Packages не будет создан")
        sys.exit(1)

    text = "\n\n".join(entries) + "\n"
    with open(os.path.join(out_dir, "Packages"), "w", encoding="utf-8") as f:
        f.write(text)
    with gzip.open(os.path.join(out_dir, "Packages.gz"), "wb") as f:
        f.write(text.encode("utf-8"))

    print(f"\n[+] Записано {len(entries)} пакетов в Packages и Packages.gz")


if __name__ == "__main__":
    main()
