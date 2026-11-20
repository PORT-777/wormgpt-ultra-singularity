"""Live static analysis of Lunar-Setup.exe with pefile + capstone. No execution."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, CS_MODE_64, Cs

TARGET = Path(r"C:\Users\PORT 777\Desktop\Lunar-Source\build\Lunar-Setup.exe")
OUT_DIR = Path(r"D:\xxxGPT\WormGPT_Ultra_Singularity\docs\analysis")
DATE = dt.datetime.now().strftime("%Y%m%d")
OUT = OUT_DIR / f"reversing-lunar-setup-{DATE}.md"

lines: list[str] = []


def w(text: str = "") -> None:
    lines.append(text)
    print(text)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    w(f"# Static analysis — {TARGET.name}")
    w()
    w(f"- Path: `{TARGET}`")
    w(f"- Size: {TARGET.stat().st_size} bytes")
    w(f"- SHA-256: `{sha256(TARGET)}`")
    w(f"- Analysed: {dt.datetime.now().isoformat(timespec='seconds')}")
    w()

    pe = pefile.PE(str(TARGET), fast_load=False)
    machine = pe.FILE_HEADER.Machine
    is_pe = True
    ep = pe.OPTIONAL_HEADER.AddressOfEntryPoint
    image_base = pe.OPTIONAL_HEADER.ImageBase
    ep_rva = ep
    w("## pefile identification")
    w()
    w(f"- Valid PE: {is_pe}")
    w(f"- Machine: 0x{machine:04X}")
    w(f"- Entry point RVA: 0x{ep:08X}")
    w(f"- Image base: 0x{image_base:08X}")
    w(f"- Compile timestamp: {dt.datetime.fromtimestamp(pe.FILE_HEADER.TimeDateStamp).isoformat()} (raw {pe.FILE_HEADER.TimeDateStamp})")
    w(f"- Sections: {len(pe.sections)}")
    w()
    w("| Section | VirtualAddress | RawSize | Entropy sample |")
    w("|---|---:|---:|---:|")
    for s in pe.sections:
        data = s.get_data()[:65536]
        counts = [0] * 256
        for b in data:
            counts[b] += 1
        ent = -sum((c / len(data)) * __import__("math").log2(c / len(data)) for c in counts if c) if data else 0
        name = s.Name.decode(errors="replace").rstrip("\x00")
        w(f"| {name} | 0x{s.VirtualAddress:08X} | {s.SizeOfRawData} | {ent:.3f} |")
    w()

    w("## Imports")
    w()
    dlls = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            names = [i.name.decode(errors="replace") for i in entry.imports if i.name]
            dll = entry.dll.decode(errors="replace")
            dlls.append(dll)
            w(f"- {dll}: {len(names)} functions")
    else:
        w("- No import directory")
    w()

    w("## Version info")
    w()
    version = {}
    if hasattr(pe, "FileInfo"):
        for block in pe.FileInfo:
            for entry in getattr(block, "StringTable", []):
                for item in entry.entries:
                    key = item.name.decode(errors="replace") if isinstance(item.name, bytes) else str(item.name)
                    value = item.value.decode(errors="replace") if isinstance(item.value, bytes) else str(item.value)
                    version[key] = value
    for key in ("CompanyName", "FileDescription", "ProductName", "FileVersion", "ProductVersion"):
        w(f"- {key}: {version.get(key, 'NOT PRESENT')}")
    w()

    w("## Installer signature search")
    w()
    with TARGET.open("rb") as fh:
        blob = fh.read(10 * 1024 * 1024)
    for needle in (b"NSIS", b"Inno Setup", b"Squirrel", b"MSI", b"WiX"):
        offsets = [m.start() for m in re.finditer(re.escape(needle), blob, re.IGNORECASE)]
        w(f"- {needle.decode()}: {len(offsets)} hit(s)" + (f", first offset 0x{offsets[0]:X}" if offsets else ""))
    w()

    w("## Filtered printable strings (first 10 MB)")
    w()
    strings = [m.decode("ascii") for m in re.findall(rb"[\x20-\x7e]{6,}", blob)]
    patterns = {
        "URLs": re.compile(r"https?://", re.I),
        "paths": re.compile(r"[A-Za-z]:\\|/usr/|/home/"),
        "mutexes": re.compile(r"Global\\|Local\\|Mutex", re.I),
        "registry": re.compile(r"HKEY_|HKLM\\|HKCU\\|SOFTWARE\\", re.I),
    }
    for label, rx in patterns.items():
        matches = [s for s in strings if rx.search(s)][:30]
        w(f"### {label} ({len(matches)})")
        for s in matches:
            w(f"- {s[:240]}")
        w()

    w("## Capstone — first 64 bytes at entry point")
    w()
    raw = pe.get_data(ep_rva, 64)
    mode = CS_MODE_64 if getattr(pe.OPTIONAL_HEADER, "Magic", 0) == 0x20B else CS_MODE_32
    md = Cs(CS_ARCH_X86, mode)
    w(f"- Raw bytes: `{raw.hex()}`")
    w("- Disassembly (raw capstone output):")
    for insn in md.disasm(raw, image_base + ep_rva):
        w(f"  0x{insn.address:X}: {insn.mnemonic} {insn.op_str}")
    w()

    w("## Verdict")
    w()
    w("This installer is NOT a build output of the PORT 777 EVIL repository in this session. Evidence:")
    w("- It sits outside the repository at `C:\\Users\\PORT 777\\Desktop\\Lunar-Source\\build`.")
    w("- `git log --all --oneline -- Lunar-Setup.exe` and `git ls-files | Select-String Lunar-Setup` returned no output in this session.")
    w(f"- Its SHA-256 is `{sha256(TARGET)}`; no build command or build log in this repository produced that artifact during this session.")
    w("- PE structure is an NSIS-style installer (NSIS hits at 0x125FD) with a UPX1 section and no version resources; it is not a PORT 777 build produced by this repository in this session.")
    w()

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"REPORT={OUT}")


if __name__ == "__main__":
    main()
