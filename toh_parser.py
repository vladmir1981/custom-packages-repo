"""Парсит toh.json → генерирует devices_data.py."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

# Бренды, которые показываем в UI
WANTED_BRANDS = {
    "tp-link", "asus", "xiaomi", "d-link", "mercusys", "netgear",
    "cudy", "netis", "linksys", "tenda", "zbt", "jcg", "zte",
    "netcore", "dynalink", "zyxel", "sercomm", "sagemcom",
    "huawei", "gl.inet", "mikrotik", "ubiquiti", "teltonika",
    "keenetic", "wavlink", "friendlyelec", "raspberry pi",
    "orange pi", "banana pi", "pine64", "olimex",
}

BRAND_DISPLAY = {
    "tp-link": "TP-Link", "asus": "ASUS", "xiaomi": "Xiaomi",
    "d-link": "D-Link", "zyxel": "ZyXEL", "gl.inet": "GL.iNet",
    "mikrotik": "MikroTik", "ubiquiti": "Ubiquiti",
    "raspberry pi": "Raspberry Pi", "orange pi": "Orange Pi",
    "banana pi": "Banana Pi", "friendlyelec": "FriendlyElec",
    "netcore": "Netcore", "dynalink": "Dynalink",
}

MIN_BRANCHES = ("23.", "24.", "25.")


def _to_str(v):
    """Приводит значение из toh.json (может быть списком) к строке."""
    if isinstance(v, list):
        return v[0] if v else ""
    return str(v) if v is not None else ""


def _extract_profile_from_url(url):
    """openwrt-24.10.5-ramips-mt7621-cudy_m1800-squashfs-sysupgrade.bin → cudy_m1800"""
    if not url:
        return None
    fname = urlparse(url).path.split("/")[-1]
    # openwrt-<ver>-<target>-<subtarget>-<profile>-<type>.bin
    m = re.match(r"openwrt-(?:[\d.]+-)?([a-z0-9_]+)-([a-z0-9_]+)-(.+?)-(?:squashfs|initramfs|factory)", fname)
    if m:
        return m.group(3)
    return None


def _extract_version_from_url(url):
    """https://downloads.openwrt.org/releases/24.10.5/targets/... → 24.10.5"""
    if not url:
        return None
    m = re.search(r"/releases/(\d+\.\d+\.\d+)/", url)
    return m.group(1) if m else None


def parse(columns, entries, all_releases):
    """Возвращает DEVICE_DB."""
    idx = {name: i for i, name in enumerate(columns)}

    def get(entry, name):
        i = idx.get(name)
        return entry[i] if i is not None and i < len(entry) else None

    db = {}

    for entry in entries:
        brand_raw = _to_str(get(entry, "brand")).strip().lower()
        if brand_raw not in WANTED_BRANDS:
            continue
        brand_display = BRAND_DISPLAY.get(brand_raw, brand_raw.title())

        model_raw = _to_str(get(entry, "model")).strip()
        if not model_raw:
            continue

        target = _to_str(get(entry, "target")).strip()
        subtarget = _to_str(get(entry, "subtarget")).strip()
        if not target or not subtarget or target == "-":
            continue

        arch = _to_str(get(entry, "packagearchitecture")).strip()
        if not arch or arch == "-":
            continue

        # profile — из URL прошивки
        upgrade_url = _to_str(get(entry, "firmwareopenwrtupgradeurl"))
        install_url = _to_str(get(entry, "firmwareopenwrtinstallurl"))
        snap_url = _to_str(get(entry, "firmwareopenwrtsnapshotupgradeurl"))

        profile = (_extract_profile_from_url(upgrade_url) or
                   _extract_profile_from_url(install_url))
        if not profile:
            continue

        # версии
        supported_since = _to_str(get(entry, "supportedsincerel")).strip()
        supported_current = _to_str(get(entry, "supportedcurrentrel")).strip()

        versions = set()

        # 1) SNAPSHOT, если есть snapshot URL
        if snap_url and "snapshots" in snap_url:
            versions.add("SNAPSHOT")

        # 2) все релизы между supportedsincerel и supportedcurrentrel
        def rel_key(v):
            try:
                parts = [int(p) for p in v.split(".")]
                return tuple((parts + [0, 0, 0])[:3])
            except Exception:
                return (0, 0, 0)

        lo = rel_key(supported_since) if supported_since and supported_since != "-" else None
        hi = rel_key(supported_current) if supported_current and supported_current != "-" else None

        for rel in all_releases:
            k = rel_key(rel)
            if lo is not None and k < lo:
                continue
            if hi is not None and k > hi:
                continue
            versions.add(rel)

        # 3) отдельные версии прямо из URL (на случай, если границы не сработали)
        for url in (upgrade_url, install_url):
            v = _extract_version_from_url(url)
            if v and any(v.startswith(p) for p in MIN_BRANCHES):
                versions.add(v)

        if not versions:
            continue

        # сортируем: SNAPSHOT первым, потом по убыванию
        def sort_key(v):
            if v == "SNAPSHOT":
                return (0, 0, 0, 0)
            parts = [int(p) for p in v.split(".") if p.isdigit()]
            return (1, -parts[0] if len(parts) > 0 else 0,
                    -parts[1] if len(parts) > 1 else 0,
                    -parts[2] if len(parts) > 2 else 0)

        sorted_versions = sorted(versions, key=sort_key)

        # чистим имя модели от бренда
        display_model = model_raw
        if display_model.lower().startswith(brand_display.lower()):
            display_model = display_model[len(brand_display):].strip(" -_")
        display_model = display_model.upper()

        db.setdefault(brand_display, {})[display_model] = {
            "target": target,
            "subtarget": subtarget,
            "arch": arch,
            "profile": profile,
            "versions": sorted_versions,
        }

    return db


def write_devices_data(db, out_path):
    """Пишет devices_data.py."""
    brands = sorted(db.keys())
    out = Path(out_path)

    if out.exists():
        backup = out.with_suffix(".py.bak")
        backup.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

    with open(out, "w", encoding="utf-8") as f:
        f.write("# АВТОМАТИЧЕСКИ СГЕНЕРИРОВАНО ИЗ toh.json\n")
        f.write("# НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ — перезаписывается\n\n")
        f.write(f"BRANDS = {json.dumps(brands, ensure_ascii=False, indent=4)}\n\n")
        f.write(f"DEVICE_DB = {json.dumps(db, ensure_ascii=False, indent=4)}\n")

    total = sum(len(v) for v in db.values())
    print(f"[Parser] Брендов: {len(db)}, моделей: {total}")
    return total