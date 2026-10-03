# download_zapret.py
"""
Скачивает готовые .ipk из релизов remittor/zapret-openwrt,
раскладывает по папкам custom-packages-repo и генерирует Packages.
"""
import io
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

# === Конфигурация ===
RELEASE_TAG = "v72.20260307"
REPO = "remittor/zapret-openwrt"

# Какие архитектуры качаем (zip → куда класть)
ARCH_MAP = {
    "aarch64_cortex-a53": [
        "24.10/aarch64_cortex-a53",
        "23.05/aarch64_cortex-a53",
    ],
    "mipsel_24kc": [
        "24.10/mipsel_24kc",
        "23.05/mipsel_24kc",
    ],
    "mips_24kc": [
        "24.10/mips_24kc",
        "23.05/mips_24kc",
    ],
}

BASE_DIR = Path(__file__).parent


def download_zip(arch: str, target_dir: Path) -> bool:
    """Скачивает и распаковывает один zip-архив."""
    filename = f"zapret_{RELEASE_TAG}_{arch}.zip"
    url = f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}/{filename}"

    print(f"\n[Арх] Скачиваю {filename}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            data = response.read()
    except Exception as e:
        print(f"  [!] Ошибка скачивания: {e}")
        return False

    print(f"  [+] Получено {len(data)/1024:.0f} КБ")
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            print(f"  [+] В архиве {len(names)} файлов:")
            for n in names:
                print(f"      {n}")
            zf.extractall(target_dir)
        return True
    except Exception as e:
        print(f"  [!] Ошибка распаковки: {e}")
        return False


def find_ipks(directory: Path) -> list:
    """Находит все .ipk в папке (рекурсивно)."""
    return sorted(directory.rglob("*.ipk"))


def move_ipks_to_root(directory: Path):
    """Переносит .ipk из подпапок в корень directory."""
    for ipk in list(directory.rglob("*.ipk")):
        if ipk.parent != directory:
            dest = directory / ipk.name
            shutil.move(str(ipk), str(dest))
            print(f"  [→] {ipk.relative_to(directory)} → {ipk.name}")

    # Удаляем пустые подпапки
    for sub in list(directory.iterdir()):
        if sub.is_dir():
            try:
                sub.rmdir()
            except OSError:
                pass


def cleanup_dir(directory: Path):
    """Удаляет всё кроме .ipk из папки."""
    for f in directory.iterdir():
        if f.is_file() and f.suffix != ".ipk":
            if f.name in ("Packages", "Packages.gz", ".gitkeep"):
                continue
            try:
                f.unlink()
                print(f"  [x] Удалён лишний файл: {f.name}")
            except OSError:
                pass


def main():
    print("=" * 60)
    print(f"Скачивание zapret {RELEASE_TAG} из {REPO}")
    print("=" * 60)

    # Скачиваем в первую папку из списка, потом копируем в остальные
    for arch, target_dirs in ARCH_MAP.items():
        # Сначала в первую папку
        primary = BASE_DIR / target_dirs[0]
        print(f"\n### {arch} → {target_dirs[0]}")

        if not download_zip(arch, primary):
            print(f"  [!] Пропускаю {arch}")
            continue

        # Раскладываем файлы
        move_ipks_to_root(primary)
        cleanup_dir(primary)

        ipks = sorted(primary.glob("*.ipk"))
        print(f"  [Итог] В {target_dirs[0]}: {len(ipks)} .ipk")
        for ipk in ipks:
            print(f"      {ipk.name}")

        # Копируем во все остальные папки (23.05 те же самые файлы)
        for other in target_dirs[1:]:
            other_dir = BASE_DIR / other
            other_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n  → Копирую в {other}")
            for ipk in ipks:
                shutil.copy2(str(ipk), str(other_dir / ipk.name))
                print(f"      {ipk.name}")
            # Чистим всё лишнее в целевой
            cleanup_dir(other_dir)

    print("\n" + "=" * 60)
    print("Готово! Теперь запустите: python make_index.py")
    print("=" * 60)


if __name__ == "__main__":
    main()