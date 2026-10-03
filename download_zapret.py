#!/usr/bin/env python3
"""Скачивает zapret 1.x (IPK для 23.05/24.10) и zapret2 (APK+IPK для 25.12)."""
import io, os, shutil, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0"}

ZAPRET1_TAG = "v72.20260307"
ZAPRET1_REPO = "remittor/zapret-openwrt"
ZAPRET1_ARCHS = {
    "aarch64_cortex-a53": ["24.10/aarch64_cortex-a53", "23.05/aarch64_cortex-a53"],
    "mipsel_24kc":        ["24.10/mipsel_24kc",        "23.05/mipsel_24kc"],
    "mips_24kc":          ["24.10/mips_24kc",          "23.05/mips_24kc"],
}

ZAPRET2_TAG = "v1.0.5.2"
ZAPRET2_REPO = "1andrevich/zapret2-openwrt"
ZAPRET2_ARCHS = {
    "aarch64_cortex-a53": ["25.12/aarch64_cortex-a53"],
    "mipsel_24kc":        ["25.12/mipsel_24kc"],
    "mips_24kc":          ["25.12/mips_24kc"],
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
    print("\n=== ZAPRET2 (APK + IPK + pub) для 25.12 ===")
    base = f"https://github.com/{ZAPRET2_REPO}/releases/download/{ZAPRET2_TAG}"

    # Ключ подписи
    print("\n[Ключ] zapret2-1andrevich.pub")
    try:
        (ROOT / "zapret2-1andrevich.pub").write_bytes(download(f"{base}/zapret2-1andrevich.pub"))
        print("  [+] OK")
    except Exception as e:
        print(f"  [!] {e}")

    # luci-app-zapret2 (.apk + .ipk)
    for ext in ("apk", "ipk"):
        fname = f"luci-app-zapret2.{ext}"
        print(f"\n[{ext.upper()}] {fname}")
        try:
            data = download(f"{base}/{fname}")
            for arch, dirs in ZAPRET2_ARCHS.items():
                for td in dirs:
                    d = ROOT / td
                    d.mkdir(parents=True, exist_ok=True)
                    (d / fname).write_bytes(data)
            print("  [+] разложен во все 3 папки")
        except Exception as e:
            print(f"  [!] {e}")

    # zapret2 (.apk + .ipk) для каждой арх
    for arch, dirs in ZAPRET2_ARCHS.items():
        for ext in ("apk", "ipk"):
            fname = f"zapret2_{arch}.{ext}"
            print(f"\n[{ext.upper()}] {fname}")
            try:
                data = download(f"{base}/{fname}")
                for td in dirs:
                    d = ROOT / td
                    d.mkdir(parents=True, exist_ok=True)
                    (d / fname).write_bytes(data)
                print(f"  [+] {len(data)/1024:.0f} КБ")
            except Exception as e:
                print(f"  [!] {e}")


def main():
    download_zapret1()
    download_zapret2()
    print("\n=== ГОТОВО ===")


if __name__ == "__main__":
    main()