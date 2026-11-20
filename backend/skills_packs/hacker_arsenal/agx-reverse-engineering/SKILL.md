---
name: agx-reverse-engineering
description: "reverse-engineering"
trigger_when: "reverse-engineering,reverse,engineering,skill,coverage,map,quick,reference,identify,binary,ghidra,headless"
source: antigravity-pentest-skills/
---
---
name: reverse-engineering
description: >-
  Use this skill when performing reverse engineering of binaries, malware, firmware,
  or applications; when analyzing crackmes, CTF reversing challenges, or protected
  software; when working with Ghidra, IDA Pro, Binary Ninja, Radare2, x64dbg, or GDB;
  when writing Ghidra scripts, YARA rules for RE, or decompiling/disassembling PE/ELF
  binaries; when bypassing anti-debug/anti-analysis protections, unpacking malware,
  analyzing ROP gadgets, or studying obfuscation techniques. Covers static analysis,
  dynamic analysis, firmware extraction, patching, keygen/crackme methodology, and
  decompiler-assisted reverse engineering. All content is for authorized security
  research, CTF competitions, and educational purposes only.
---

## Reverse Engineering Skill

Comprehensive guide for reverse engineering binaries, malware, firmware, and
protected software using industry-standard tools and techniques.

### Coverage Map

| Reference File | Contents |
|---------------|----------|
| [ghidra-guide.md](references/ghidra-guide.md) | Ghidra setup, scripting, analysis, extensions |
| [dynamic-analysis-re.md](references/dynamic-analysis-re.md) | x64dbg, GDB, WinDbg, Frida for RE |
| [static-analysis-re.md](references/static-analysis-re.md) | Radare2, Binary Ninja, strings, readelf, objdump |
| [anti-analysis-bypass.md](references/anti-analysis-bypass.md) | Anti-debug, anti-VM, packing detection, unpacking |
| [rop-gadgets.md](references/rop-gadgets.md) | ROPgadget, ropper, pwntools ROP, miasm ROP |
| [firmware-re.md](references/firmware-re.md) | Firmware extraction, binwalk, emulation with QEMU |
| [crackme-methodology.md](references/crackme-methodology.md) | Crackme solving workflow, keygen writing, license bypass |
| [obfuscation.md](references/obfuscation.md) | Code obfuscation types, deobfuscation techniques |
| [decompiler-tricks.md](references/decompiler-tricks.md) | Getting the most from Ghidra/IDA decompilers |
| [windows-internals-re.md](references/windows-internals-re.md) | PE format, Windows structures for RE, rootkit analysis |

### Quick Reference

```bash
## Identify binary
file binary && strings binary | head -50
hexdump -C binary | head -20
readelf -h binary        # ELF
dumpbin /headers pe.exe  # PE (Windows)

## Ghidra headless (automated analysis)
analyzeHeadless /projects ProjectName -import binary.exe -postScript PrintTrees.java

## Radare2 quick analysis
r2 -A binary          # Auto-analyze
r2 -c "aaa;pdf @main" binary  # Disassemble main
r2 -c "izz" binary    # All strings

## ROPgadget
ROPgadget --binary binary --rop
ROPgadget --binary binary --string "/bin/sh"

## miasm symbolic execution
python3 miasm_example.py
```
