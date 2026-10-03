"""Скачивает toh.json и .versions.json с openwrt.org. Кэширует."""
import hashlib
import json
import time
from pathlib import Path
import urllib.request

CACHE_DIR = Path(__file__).parent / "toh_cache"
CACHE_DIR.mkdir(exist_ok=True)
TOH_FILE = CACHE_DIR / "toh.json"
VERSIONS_FILE = CACHE_DIR / "versions.json"
HASH_FILE = CACHE_DIR / "toh.sha256"
META_FILE = CACHE_DIR / "meta.json"

TOH_URL = "https://openwrt.org/toh.json"
VERSIONS_URLS = [
    "https://downloads.openwrt.org/.versions.json",
    "https://downloads.openwrt.org/releases/.versions.json",
]

UA = {"User-Agent": "Mozilla/5.0 (OpenWrt-Builder-Lite)"}


def _download(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def check_and_update(force=False):
    """
    Скачивает toh.json если он изменился (или force=True).
    .versions.json скачивается ВСЕГДА, если его нет.
    """
    status = "up_to_date"
    message = "База уже актуальна"
    size = 0
    new_hash = None

    # --- toh.json ---
    if force or not TOH_FILE.exists():
        try:
            data = _download(TOH_URL)
            new_hash = _sha256(data)
            old_hash = HASH_FILE.read_text().strip() if HASH_FILE.exists() else None
            if force or old_hash != new_hash:
                TOH_FILE.write_bytes(data)
                HASH_FILE.write_text(new_hash)
                META_FILE.write_text(json.dumps({
                    "updated_at": int(time.time()),
                    "size_bytes": len(data),
                }))
                status = "updated"
                message = f"Скачано обновление ({len(data)/1024:.0f} КБ)"
                size = len(data)
        except Exception as e:
            status = "error"
            message = f"Не удалось скачать toh.json: {e}"

    # --- versions.json (если нет — скачиваем) ---
    if not VERSIONS_FILE.exists() or force:
        ok = _update_versions()
        if not ok:
            message += " | versions.json НЕ скачался!"

    return {"status": status, "message": message,
            "hash": new_hash, "size": size}


def _update_versions():
    """Пытается скачать .versions.json по всем известным URL."""
    for url in VERSIONS_URLS:
        try:
            data = _download(url)
            VERSIONS_FILE.write_bytes(data)
            print(f"[versions] OK: {url} ({len(data)} байт)")
            return True
        except Exception as e:
            print(f"[versions] {url} → {e}")
    return False


def get_toh_path():
    return TOH_FILE if TOH_FILE.exists() else None


def get_versions_path():
    return VERSIONS_FILE if VERSIONS_FILE.exists() else None


def load_all_releases():
    """
    Возвращает список стабильных релизов OpenWrt (23.05, 24.10, 25.12).
    Структура файла: {"versions_list": ["25.12.5", "24.10.8", ...]}
    """
    if not VERSIONS_FILE.exists():
        print("[versions] Файл не найден")
        return []

    try:
        data = json.loads(VERSIONS_FILE.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        print(f"[versions] Не распарсил JSON: {e}")
        return []

    # Вытаскиваем список из любого разумного места
    names = []
    if isinstance(data, dict):
        for key in ("versions_list", "versions"):
            v = data.get(key)
            if isinstance(v, list):
                names = [str(x) for x in v]
                break
            elif isinstance(v, dict):
                names = list(v.keys())
                break
    elif isinstance(data, list):
        names = [str(x) for x in data]

    if not names:
        print("[versions] Не смог вытащить список версий")
        return []

    # Только 23.05 / 24.10 / 25.12, без -rc
    result = []
    for name in names:
        if "-" in name:
            continue
        if name.startswith(("23.05", "24.10", "25.12")):
            result.append(name)

    def key(v):
        parts = [int(p) for p in v.split(".") if p.isdigit()]
        return tuple((parts + [0, 0, 0])[:3])

    return sorted(set(result), key=key)