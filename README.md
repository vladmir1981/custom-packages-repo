# custom-packages-repo

Кастомный фид пакетов для сборки прошивок OpenWrt 23.05+.

## Структура

```
custom-packages-repo/
├── aarch64_cortex-a53/
│   ├── Packages.gz
│   └── *.ipk
├── aarch64_cortex-a72/
│   ├── Packages.gz
│   └── *.ipk
├── arm_arm1176jzf-s_vfp/
│   ├── Packages.gz
│   └── *.ipk
├── arm_arm926ej-s/
│   ├── Packages.gz
│   └── *.ipk
├── arm_cortex-a15_neon-vfpv4/
│   ├── Packages.gz
│   └── *.ipk
├── arm_cortex-a7/
│   ├── Packages.gz
│   └── *.ipk
├── arm_cortex-a7_neon-vfpv4/
│   ├── Packages.gz
│   └── *.ipk
├── arm_cortex-a8_vfpv3/
│   ├── Packages.gz
│   └── *.ipk
├── arm_cortex-a9/
│   ├── Packages.gz
│   └── *.ipk
├── arm_fa526/
│   ├── Packages.gz
│   └── *.ipk
├── arm_xscale/
│   ├── Packages.gz
│   └── *.ipk
├── armeb_xscale/
│   ├── Packages.gz
│   └── *.ipk
├── mips64_octeonplus/
│   ├── Packages.gz
│   └── *.ipk
├── mips_24kc/
│   ├── Packages.gz
│   └── *.ipk
├── mips_mips32/
│   ├── Packages.gz
│   └── *.ipk
├── mipsel_24kc/
│   ├── Packages.gz
│   └── *.ipk
├── mipsel_74kc/
│   ├── Packages.gz
│   └── *.ipk
├── powerpc_464fp/
│   ├── Packages.gz
│   └── *.ipk
├── manifest.json       # список пакетов и архитектур (читает app.py)
├── arch_map.json       # карта target/subtarget -> CPU-архитектура
└── README.md
```

## Как это работает

1. GitHub Actions (`.github/workflows/build-packages.yml`) собирает `.ipk`
   через `openwrt/gh-action-sdk` под каждую архитектуру из `matrix.arch`.
2. Action с `INDEX: 1` генерирует индекс `Packages.gz`.
3. Готовые `.ipk` и `Packages.gz` автоматически коммитятся в папки архитектур.
4. `openwrt-firmware-builder/build.yml` подключает этот фид как `src custom`
   в `repositories.conf`, используя переменную `$ARCH`.
5. `app.py` читает `manifest.json` и показывает только те пакеты,
   которые поддерживают выбранную архитектуру устройства.

## Архитектуры

- `aarch64_cortex-a53`
- `aarch64_cortex-a72`
- `arm_arm1176jzf-s_vfp`
- `arm_arm926ej-s`
- `arm_cortex-a15_neon-vfpv4`
- `arm_cortex-a7`
- `arm_cortex-a7_neon-vfpv4`
- `arm_cortex-a8_vfpv3`
- `arm_cortex-a9`
- `arm_fa526`
- `arm_xscale`
- `armeb_xscale`
- `mips64_octeonplus`
- `mips_24kc`
- `mips_mips32`
- `mipsel_24kc`
- `mipsel_74kc`
- `powerpc_464fp`
