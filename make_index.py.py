# make_index.py
import gzip
import hashlib
import io
import os
import sys
import tarfile
from pathlib import Path


def _read_ar(data: bytes) -> list:
    """Возвращает список (name, payload_bytes) из ar-архива."""
    entries = []
    if not data.startswith(b"!<arch>\n"):
        return entries
    pos = 8
    while pos + 60 <= len(data):
        hdr = data[pos:pos+60]
        if hdr[58:60] != b"\x60\x0a":
            break
        name = hdr[0:16].decode("ascii", "ignore").strip()
        size_str = hdr[48:58].decode("ascii", "ignore").strip()
        try:
            size = int(size_str)
        except ValueError:
            break
        pos += 60

        # Extended name (GNU ar: "#1/N", где N — длина имени в payload)
        real_name = name.rstrip("/")
        if name.startswith("#1/"):
            try:
                name_len = int(name[3:])
            except ValueError:
                name_len = 0
            real_name = data[pos:pos+name_len].decode("ascii", "ignore").strip()
            pos += name_len
            size -= name_len

        payload = data[pos:pos+size]
        pos += size
        if pos % 2 == 1:
            pos += 1
        entries.append((real_name, payload))
    return entries


def _open_control_tar(payload: bytes):
    """Открывает tar-объект из payload (gz / xz / несжатый)."""
    if payload[:2] == b"\x1f\x8b":
        return tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz")
    if payload[:6] == b"\xfd7zXZ\x00":
        return tarfile.open(fileobj=io.BytesIO(payload), mode="r:xz")
    if payload[:3] == b"BZh":
        return tarfile.open(fileobj=io.BytesIO(payload), mode="r:bz2")
    return tarfile.open(fileobj=io.BytesIO(payload), mode="r:")


def read_control(ipk_path: Path) -> str:
    data = ipk_path.read_bytes()

    # Случай A: классический ar-архив (.ipk)
    if data.startswith(b"!<arch>\n"):
        for name, payload in _read_ar(data):
            if name.startswith("control.tar"):
                try:
                    with _open_control_tar(payload) as tar:
                        for m in tar.getmembers():
                            if m.name.endswith("control") or m.name == "./control":
                                f = tar.extractfile(m)
                                if f:
                                    return f.read().decode("utf-8", "ignore")
                except Exception as e:
                    print(f"  [!] control.tar не открылся: {e}")
        return ""

    # Случай B: .ipk — это сразу tar (gz/xz) — редко, но бывает
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for m in tar.getmembers():
                if m.name.endswith("control") or m.name == "./control":
                    f = tar.extractfile(m)
                    if f:
                        return f.read().decode("utf-8", "ignore")
    except Exception:
        pass
    return ""


def make_entry(ipk_path: Path, control_text: str) -> str:
    size = ipk_path.stat().st_size
    sha = hashlib.sha256(ipk_path.read_bytes()).hexdigest()

    fields = {}
    current = None
    for line in control_text.splitlines():
        if line.startswith(" ") and current:
            fields[current] += "\n" + line
        elif ": " in line:
            k, v = line.split(": ", 1)
            fields[k] = v
            current = k

    lines = [
        f"Package: {fields.get('Package', '')}",
        f"Version: {fields.get('Version', '')}",
        f"Depends: {fields.get('Depends', '')}",
        f"Provides: {fields.get('Provides', '')}",
        "Status: install ok installed",
        f"Architecture: {fields.get('Architecture', '')}",
        "Installed-Size: 0",
        f"Filename: {ipk_path.name}",
        f"Size: {size}",
        f"SHA256sum: {sha}",
        f"Description: {fields.get('Description', '')}",
    ]
    for extra in ("Section", "Maintainer", "License"):
        if fields.get(extra):
            lines.append(f"{extra}: {fields[extra]}")
    return "\n".join(lines)


def process_dir(directory: Path) -> int:
    ipks = sorted(directory.glob("*.ipk"))
    if not ipks:
        return 0
    print(f"[Инфо] {directory}: найдено {len(ipks)} .ipk")

    entries = []
    for ipk in ipks:
        control = read_control(ipk)
        if not control:
            print(f"  [!] Пропускаю {ipk.name} — control не прочитан")
            continue
        entries.append(make_entry(ipk, control))

    if not entries:
        print(f"  [!] Нет валидных записей — Packages не обновляю")
        return 0

    text = "\n\n".join(entries) + "\n"
    (directory / "Packages").write_text(text, encoding="utf-8")
    with gzip.open(directory / "Packages.gz", "wb") as f:
        f.write(text.encode("utf-8"))
    print(f"[Инфо] {directory}: Packages и Packages.gz записаны ({len(entries)} шт.)")
    return len(entries)


def main():
    root = Path(__file__).parent
    total = 0
    for d in sorted(root.rglob("*")):
        if d.is_dir() and not any(p.startswith(".") for p in d.parts):
            total += process_dir(d)
    print(f"\n[Готово] Всего записей: {total}")


if __name__ == "__main__":
    main()