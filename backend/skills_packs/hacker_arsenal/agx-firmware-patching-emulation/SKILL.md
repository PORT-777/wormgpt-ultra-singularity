---
name: agx-firmware-patching-emulation
description: "firmware-patching-emulation"
trigger_when: "firmware-patching-emulation,firmware,patching,emulation,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: firmware-patching-emulation
description: >-
  Use this skill when modifying firmware binaries, repacking SquashFS/UBI filesystems, or emulating full IoT devices.
  Covers QEMU system/user mode emulation, Firmadyne/FAT, binary patching in MIPS/ARM, and CRC checksum recalculation.
---

## Firmware Patching & Emulation Skill

Advanced IoT/firmware modification, binary patching for embedded architectures, and virtual device emulation.

### Coverage Map

| Reference File | Contents |
|---|---|
| [firmware-repacking.md](references/firmware-repacking.md) | Extracting, modifying, and rebuilding SquashFS/UBI images with sasquatch/mksquashfs |
