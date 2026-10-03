#!/usr/bin/env python3
"""Полная починка репозитория: копирует свежие .ipk из 24.10 в 23.05 и пересобирает Packages."""
import gzip
import hashlib
import io
import os
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).parent


def get_control(ipk_path):
    with open(ipk_path, "rb") as f:
        data = f.read()
    if data[:2] == b"\x1f\x8b":
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as outer:
                for m in outer.getmembers():
                    if "control.tar" in m.name:
                        ext = outer.extractfile(m)
                        if not ext: continue
                        cd = ext.read()
                        mode = "r:gz" if cd[:2] == b"\x1f\x8b" else ("r:xz" if cd[:6] == b"\xfd7zXZ\x00" else "r:")
                        with tarfile.open(fileobj=io.BytesIO(cd), mode=mode) as inner:
                            for mm in inner.getmembers():
                                if mm.name.endswith("control"):
                                    cf = inner.extractfile(mm)
                                    if cf: return cf.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"  [!] {e}")
    return ""


def make_entry(ipk_path):
    ctrl = get_control(ipk_path)
    if not ctrl:
        return None
    fields = {}
    cur = None
    for line in ctrl.splitlines():
        if line.startswith(" ") and cur:
            fields[cur] += "\n" + line
        elif ": " in line:
            k, v = line.split(": ", 1)
            fields[k] = v
            cur = k
    size = os.path.getsize(ipk_path)
    with open(ipk_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return "\n".join([
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
    ])


def rebuild_packages(directory: Path):
    ipks = sorted(directory.glob("*.ipk"))
    if not ipks:
        print(f"  [!] {directory}: нет .ipk")
        return 0
    entries = []
    for ipk in ipks:
        e = make_entry(ipk)
        if e:
            entries.append(e)
            print(f"      [+] {ipk.name}")
    if not entries:
        return 0
    text = "\n\n".join(entries) + "\n"
    (directory / "Packages").write_text(text, encoding="utf-8")
    with gzip.open(directory / "Packages.gz", "wb") as f:
        f.write(text.encode("utf-8"))
    print(f"      → Packages записан ({len(entries)} пакетов)")
    return len(entries)


def clean_ipks(directory: Path):
    """Удаляет все .ipk, Packages, Packages.gz из папки."""
    for pattern in ("*.ipk", "Packages", "Packages.gz"):
        for f in directory.glob(pattern):
            f.unlink()
            print(f"      [x] Удалён {f.name}")


def main():
    print("=" * 60)
    print("ПОЧИНКА РЕПОЗИТОРИЯ")
    print("=" * 60)

    # Источники свежих файлов
    sources = {
        "aarch64_cortex-a53": ROOT / "24.10" / "aarch64_cortex-a53",
        "mipsel_24kc":        ROOT / "24.10" / "mipsel_24kc",
        "mips_24kc":          ROOT / "24.10" / "mips_24kc",
    }

    # Целевые папки
    targets = [
        ("23.05/aarch64_cortex-a53", "aarch64_cortex-a53"),
        ("23.05/mipsel_24kc",        "mipsel_24kc"),
        ("23.05/mips_24kc",          "mips_24kc"),
        ("24.10/aarch64_cortex-a53", "aarch64_cortex-a53"),
        ("24.10/mipsel_24kc",        "mipsel_24kc"),
        ("24.10/mips_24kc",          "mips_24kc"),
    ]

    # Шаг 1: для всех папок 23.05 — очистить и скопировать из 24.10
    print("\n--- Шаг 1: чистим папки 23.05 и копируем файлы из 24.10 ---")
    for rel_path, arch in targets:
        if not rel_path.startswith("23.05"):
            continue
        target_dir = ROOT / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n  >> {rel_path}")
        clean_ipks(target_dir)
        src_dir = sources[arch]
        if not src_dir.exists():
            print(f"      [!] Источник {src_dir} не найден")
            continue
        for f in src_dir.glob("*.ipk"):
            shutil.copy2(f, target_dir / f.name)
            print(f"      [+] Скопирован {f.name}")

    # Шаг 2: удалить старые .ipk с суффиксом -1_ из всех папок
    print("\n--- Шаг 2: удаляем устаревшие файлы с '_-1_' в имени ---")
    for rel_path, _ in targets:
        target_dir = ROOT / rel_path
        for f in target_dir.glob("*-1_*.ipk"):
            f.unlink()
            print(f"      [x] {rel_path}/{f.name}")

    # Шаг 3: пересобрать Packages во всех папках
    print("\n--- Шаг 3: пересобираем Packages во всех папках ---")
    total = 0
    for rel_path, _ in targets:
        target_dir = ROOT / rel_path
        if not target_dir.exists():
            continue
        print(f"\n  >> {rel_path}")
        total += rebuild_packages(target_dir)

    print("\n" + "=" * 60)
    print(f"ГОТОВО. Всего записей в индексах: {total}")
    print("=" * 60)
    print("\nДальше в Git Bash:")
    print("  git add .")
    print('  git commit -m "fix: пересобраны Packages"')
    print("  git push")


if __name__ == "__main__":
    main()