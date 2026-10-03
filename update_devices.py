"""Одна команда: обновить toh.json → сгенерировать devices_data.py."""
import json
import sys
from pathlib import Path

import toh_updater
import toh_parser

ROOT = Path(__file__).parent


def main():
    force = "--force" in sys.argv

    print("[1/2] Проверяю обновления toh.json...")
    r = toh_updater.check_and_update(force=force)
    print(f"      → {r['status']}: {r['message']}")

    if r["status"] == "error":
        print("[!] Не удалось получить toh.json. Использую кэш.")
        toh_path = toh_updater.get_toh_path()
        if not toh_path:
            print("[!] Кэша тоже нет. Выхожу.")
            sys.exit(1)
    else:
        toh_path = toh_updater.get_toh_path()
        if not toh_path:
            print("[!] toh.json не найден после скачивания. Выхожу.")
            sys.exit(1)

    print("[2/2] Парсинг и генерация devices_data.py...")
    with open(toh_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Файл toh.json имеет вид:
    # {"columns": [...], "entries": [[...], [...], ...]}
    columns = data.get("columns", [])
    entries = data.get("entries", [])

    if not columns or not entries:
        print("[!] toh.json пуст или имеет неожиданную структуру.")
        print(f"    Ключи верхнего уровня: {list(data.keys())[:10]}")
        sys.exit(1)

    releases = toh_updater.load_all_releases()
    if releases:
        print(f"      Релизов OpenWrt: {len(releases)}  ({releases[0]} … {releases[-1]})")
    else:
        print(f"      [!] Список релизов пуст — все модели получат только SNAPSHOT")

    db = toh_parser.parse(columns, entries, releases)
    total = toh_parser.write_devices_data(db, ROOT / "devices_data.py")
    print(f"[Готово] devices_data.py: {total} устройств")


if __name__ == "__main__":
    main()