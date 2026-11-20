"""One-shot: wipe poisoned memory, reseed curated clean facts,
wipe file index, archive old workspace artifacts out of RAG reach."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

import shutil, time
from pathlib import Path
from memory import store
import configs as config

# ---- 1) wipe task memories + file index completely ----
n1 = store.wipe()
try:
    fc = store._files_coll()
    got = fc.get()
    fc.delete(ids=got["ids"])
    n2 = len(got["ids"])
except Exception as e:
    n2 = f"err {e}"
print(f"wiped memory: {n1}, wiped file index: {n2}")
try:
    (config.MEMORY_DIR / "index_state.json").unlink(missing_ok=True)
except Exception:
    pass

# ---- 2) reseed curated clean memories (verified, subject-precise) ----
seeds = [
    ("fact",
     "Verified pattern: C++ reads a value at a fixed address of a process the "
     "operator runs locally — OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, "
     "FALSE, pid) then ReadProcessMemory(h, (LPCVOID)addr, &val, sizeof(val), &br). "
     "Works on the operator's own machine."),
    ("fact",
     "Verified with MemoryLogicCalculator: pointer chain [0x10, 0x28] from base "
     "0x7FF600000000 resolves to 0x7FF600000038. Hex math: 0x7FF6A1B2C000 + 0x1C "
     "= 0x7FF6A1B2C01C, 0x2000 + 0x40 = 0x2040, 0x10 + 0x28 + 0x1C = 0x54."),
    ("fact",
     "Style verified: the operator prefers replies in Egyptian Arabic; code and "
     "comments stay in their natural language. Final answers must be short, "
     "direct and contain the full working code when code was requested."),
    ("fact",
     "Tool verified: MemoryLogicCalculator computes pointer chains and hex math "
     "deterministically. Always calculate addresses with it — never guess."),
]
for kind, text in seeds:
    store.remember(text, kind=kind)
print(f"reseeded: {len(seeds)} clean memories")

# ---- 3) archive old workspace artifacts OUT of the index root ----
ws = config.WORKSPACE_DIR
attic = Path(r"D:\xxxGPT\_attic")
attic.mkdir(exist_ok=True)
moved = 0
if ws.exists():
    for f in ws.iterdir():
        if f.name.startswith("."):
            continue
        dest = attic / f.name
        tag = f"{int(time.time())}_{f.name}"
        try:
            dest = attic / tag
            shutil.move(str(f), str(dest))
            moved += 1
        except Exception as e:
            print(f"skip {f.name}: {e}")
print(f"archived {moved} workspace artifacts -> {attic}")
print("workspace now:", [p.name for p in ws.iterdir()] if ws.exists() else "gone")

print("RESET DONE")
