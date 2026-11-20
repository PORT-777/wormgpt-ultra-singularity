import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import sqlite3, json, os

con = sqlite3.connect(r"data\🔥😈 PORT 777 EVIL ☠️🔥👹.db")
cur = con.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables:", tables)
for t in tables:
    try:
        rows = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        print(f"--- {t}: {rows} rows")
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info([{t}])")]
        print("    cols:", cols)
        for r in cur.execute(f"SELECT * FROM [{t}] LIMIT 5"):
            print("   ", str(r)[:200])
    except Exception as e:
        print(t, "ERR", e)
con.close()

print("\n=== chroma_smoke ===")
for root, dirs, files in os.walk(r"data\chroma_smoke"):
    for f in files:
        p = os.path.join(root, f)
        print(f"{os.path.getsize(p):>10} {p}")
