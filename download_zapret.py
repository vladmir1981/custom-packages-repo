#!/usr/bin/env python3
"""Скачивает zapret 1.x (IPK для 23.05/24.10) и zapret2 (APK для 25.12, IPK для 23.05/24.10/25.12)."""
import io, os, shutil, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0"}

# === zapret 1.x (remittor) — только IPK ===
ZAPRET1_TAG = "v72.20260307"
ZAPRET1_REPO = "remittor/zapret-openwrt"
ZAPRET1_ARCHS = {
    "aarch64_cortex-a53": ["24.10/aarch64_cortex-a53", "23.05/aarch64_cortex-a53"],
    "mipsel_24kc":        ["24.10/mipsel_24kc",        "23.05/mipsel_24kc"],
    "mips_24kc":          ["24.10/mips_24kc",          "23.05/mips_24kc"],
}

# === zapret2 (1andrevich) — APK и IPK ===
ZAPRET2_TAG = "v1.0.5.2"
ZAPRET2_REPO = "1andrevich/zapret2-openwrt"

# .apk → только 25.12
ZAPRET2_APK_DIRS = {
    "aarch64_cortex-a53": ["25.12/aarch64_cortex-a53"],
    "mipsel_24kc":        ["25.12/mipsel_24kc"],
    "mips_24kc":          ["25.12/mips_24kc"],
}
# .ipk → 24.10 и 23.05
ZAPRET2_IPK_DIRS = {
    "aarch64_cortex-a53": ["24.10/aarch64_cortex-a53", "23.05/aarch64_cortex-a53"],
    "mipsel_24kc":        ["24.10/mipsel_24kc",        "23.05/mipsel_24kc"],
    "mips_24kc":          ["24.10/mips_24kc",          "23.05/mips_24kc"],
}


def download(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def download_zapret1():
    print("\n=== ZAPRET 1.x (IPK) для 23.05/24.10 ===")
    for arch, dirs in ZAPRET1_ARCHS.items():
        filename = f"zapret_{ZAPRET1_TAG}_{arch}.zip"
        url = f"https://github.com/{ZAPRET1_REPO}/releases/download/{ZAPRET1_TAG}/{filename}"
        print(f"\n[Арх] {filename}")
        try:
            data = download(url)
        except Exception as e:
            print(f"  [!] {e}")
            continue
        primary = ROOT / dirs[0]
        primary.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            tmp = ROOT / "_tmp"
            if tmp.exists(): shutil.rmtree(tmp)
            tmp.mkdir()
            zf.extractall(tmp)
            for ipk in tmp.rglob("*.ipk"):
                shutil.copy2(ipk, primary / ipk.name)
                print(f"  [→] {ipk.name}")
            shutil.rmtree(tmp)
        for other in dirs[1:]:
            d = ROOT / other
            d.mkdir(parents=True, exist_ok=True)
            for ipk in primary.glob("*.ipk"):
                shutil.copy2(ipk, d / ipk.name)


def download_zapret2():
    print("\n=== ZAPRET2 — APK (25.12) + IPK (24.10 и 23.05) ===")
    base = f"https://github.com/{ZAPRET2_REPO}/releases/download/{ZAPRET2_TAG}"

    # Публичный ключ (нужен только для 25.12)
    print("\n[Ключ] zapret2-1andrevich.pub")
    try:
        (ROOT / "zapret2-1andrevich.pub").write_bytes(download(f"{base}/zapret2-1andrevich.pub"))
        print("  [+] OK")
    except Exception as e:
        print(f"  [!] {e}")

    # luci-app-zapret2 — APK → 25.12
    print("\n[APK] luci-app-zapret2.apk → 25.12")
    try:
        data = download(f"{base}/luci-app-zapret2.apk")
        for _, dirs in ZAPRET2_APK_DIRS.items():
            for td in dirs:
                d = ROOT / td
                d.mkdir(parents=True, exist_ok=True)
                (d / "luci-app-zapret2.apk").write_bytes(data)
        print("  [+] OK")
    except Exception as e:
        print(f"  [!] {e}")

    # luci-app-zapret2 — IPK → 24.10 и 23.05
    print("\n[IPK] luci-app-zapret2.ipk → 24.10 и 23.05")
    try:
        data = download(f"{base}/luci-app-zapret2.ipk")
        for _, dirs in ZAPRET2_IPK_DIRS.items():
            for td in dirs:
                d = ROOT / td
                d.mkdir(parents=True, exist_ok=True)
                (d / "luci-app-zapret2.ipk").write_bytes(data)
        print("  [+] OK")
    except Exception as e:
        print(f"  [!] {e}")

    # zapret2 по архитектурам
    for arch in ("aarch64_cortex-a53", "mipsel_24kc", "mips_24kc"):
        print(f"\n[APK] zapret2_{arch}.apk → 25.12")
        try:
            data = download(f"{base}/zapret2_{arch}.apk")
            for td in ZAPRET2_APK_DIRS[arch]:
                d = ROOT / td
                d.mkdir(parents=True, exist_ok=True)
                (d / f"zapret2_{arch}.apk").write_bytes(data)
            print(f"  [+] {len(data)/1024:.0f} КБ")
        except Exception as e:
            print(f"  [!] {e}")

        print(f"[IPK] zapret2_{arch}.ipk → 24.10 и 23.05")
        try:
            data = download(f"{base}/zapret2_{arch}.ipk")
            for td in ZAPRET2_IPK_DIRS[arch]:
                d = ROOT / td
                d.mkdir(parents=True, exist_ok=True)
                (d / f"zapret2_{arch}.ipk").write_bytes(data)
            print(f"  [+] {len(data)/1024:.0f} КБ")
        except Exception as e:
            print(f"  [!] {e}")


def main():
    download_zapret1()
    download_zapret2()
    print("\n=== ГОТОВО ===")
    print("Дальше:")
    print("  python make_index.py      # пересобрать Packages.gz")
    print("  python make_apkindex.py   # пересобрать APKINDEX.tar.gz")
    print("  git add . && git commit -m 'add: zapret2 для 23.05/24.10' && git push")


if __name__ == "__main__":
    main()