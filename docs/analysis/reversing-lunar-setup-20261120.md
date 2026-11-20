# Static analysis — Lunar-Setup.exe

- Path: `C:\Users\PORT 777\Desktop\Lunar-Source\build\Lunar-Setup.exe`
- Size: 142017360 bytes
- SHA-256: `05c6baa46bf169bfde5692fa552747eecafd44af4c2ec736d3bf0056a3c9ff9b`
- Analysed: 2026-11-20T15:09:13

## pefile identification

- Valid PE: True
- Machine: 0x014C
- Entry point RVA: 0x0000338F
- Image base: 0x00400000
- Compile timestamp: 2018-12-16T00:26:14 (raw 1544912774)
- Sections: 5

| Section | VirtualAddress | RawSize | Entropy sample |
|---|---:|---:|---:|
| .text | 0x00001000 | 26624 | 6.480 |
| .rdata | 0x00008000 | 5632 | 5.025 |
| .data | 0x0000A000 | 1536 | 4.037 |
| .ndata | 0x0007B000 | 0 | 0.000 |
| UPX1 | 0x0023B000 | 816640 | 6.545 |

## Imports

- KERNEL32.dll: 65 functions
- USER32.dll: 65 functions
- GDI32.dll: 8 functions
- SHELL32.dll: 6 functions
- ADVAPI32.dll: 13 functions
- COMCTL32.dll: 3 functions
- ole32.dll: 4 functions

## Version info

- CompanyName: NOT PRESENT
- FileDescription: NOT PRESENT
- ProductName: NOT PRESENT
- FileVersion: NOT PRESENT
- ProductVersion: NOT PRESENT

## Installer signature search

- NSIS: 2 hit(s), first offset 0x125FD
- Inno Setup: 0 hit(s)
- Squirrel: 0 hit(s)
- MSI: 4 hit(s), first offset 0x2CB5E3
- WiX: 8 hit(s), first offset 0x377E5B

## Filtered printable strings (first 10 MB)

### URLs (0)

### paths (7)
- (Iz:\x
- 6}jtV:\ML
- bCn:\`
- IH>r:\
- uN:\a$
- ~V:\IB
- e:\<Rd&]

### mutexes (0)

### registry (0)

## Capstone — first 64 bytes at entry point

- Raw bytes: `81ecd40200005356576a205f33db6801800000895c2414c7442410e0a24000895c241cff15a8804000ff15a480400025ffffffbf663d0600a3ecae4700741153`
- Disassembly (raw capstone output):
  0x40338F: sub esp, 0x2d4
  0x403395: push ebx
  0x403396: push esi
  0x403397: push edi
  0x403398: push 0x20
  0x40339A: pop edi
  0x40339B: xor ebx, ebx
  0x40339D: push 0x8001
  0x4033A2: mov dword ptr [esp + 0x14], ebx
  0x4033A6: mov dword ptr [esp + 0x10], 0x40a2e0
  0x4033AE: mov dword ptr [esp + 0x1c], ebx
  0x4033B2: call dword ptr [0x4080a8]
  0x4033B8: call dword ptr [0x4080a4]
  0x4033BE: and eax, 0xbfffffff
  0x4033C3: cmp ax, 6
  0x4033C7: mov dword ptr [0x47aeec], eax
  0x4033CC: je 0x4033df
  0x4033CE: push ebx

## Verdict

This installer is NOT a build output of the PORT 777 EVIL repository in this session. Evidence:
- It sits outside the repository at `C:\Users\PORT 777\Desktop\Lunar-Source\build`.
- `git log --all --oneline -- Lunar-Setup.exe` and `git ls-files | Select-String Lunar-Setup` returned no output in this session.
- Its SHA-256 is `05c6baa46bf169bfde5692fa552747eecafd44af4c2ec736d3bf0056a3c9ff9b`; no build command or build log in this repository produced that artifact during this session.
- PE structure is an NSIS-style installer (NSIS hits at 0x125FD) with a UPX1 section and no version resources; it is not a PORT 777 build produced by this repository in this session.
