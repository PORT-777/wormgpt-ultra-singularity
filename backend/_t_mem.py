import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from memory import store
got = store._coll.get(include=["documents", "metadatas"])
print(f"== 🔥😈 PORT 777 EVIL ☠️🔥👹_memory: {len(got['ids'])} docs ==")
for i, d in zip(got["ids"], got["documents"]):
    print("---", i)
    print((d or "")[:150].replace("\n", " âŽ "))

try:
    fc = store._files_coll()
    fgot = fc.get(include=["documents", "metadatas"])
    print(f"\n== 🔥😈 PORT 777 EVIL ☠️🔥👹_files index: {len(fgot['ids'])} chunks ==")
    seen = set()
    for m in fgot["metadatas"]:
        p = (m or {}).get("path", "?")
        seen.add(p)
    for p in sorted(seen):
        print("   file:", p)
except Exception as e:
    print("files coll err:", e)

import configs as config
print("\nWORKSPACE_DIR:", config.WORKSPACE_DIR)
