---
name: agx-hypervisor-vm-escape
description: "hypervisor-vm-escape"
trigger_when: "hypervisor-vm-escape,hypervisor,security,escape,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: hypervisor-vm-escape
description: >-
  Use this skill when analyzing Virtual Machine hypervisors (VMware, VirtualBox, KVM, QEMU), researching guest-to-host escapes,
  or analyzing virtualized device drivers. Covers QEMU device escapes, VMware backdoor I/O ports, and VMXNET3 vulnerabilities.
---

## Hypervisor Security & VM Escape Skill

Guest-to-host virtual machine breakouts, hypervisor attack surfaces, and virtual hardware driver research.

### Coverage Map

| Reference File | Contents |
|---|---|
| [qemu-vmware-escapes.md](references/qemu-vmware-escapes.md) | Virtual device vulnerabilities (e1000, vmxnet3, floppy, virtio) and escape mechanics |
