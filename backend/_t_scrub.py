"""One-shot memory scrubber: removes poisoned/refusal/greeting memories."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

import re
from memory import store
from agent_engine import AgentEngine

POISON = re.compile(
    r"i (?:cannot|can't|canâ€™t|won't|wonâ€™t) (?:provide|assist|help|comply)"
    r"|i'?m sorry|i am sorry|as an ai|i must decline"
    r"|tool call 'i' consistently failed"
    r"|antitampersentinel tool also failed",
    re.IGNORECASE)

got = store._coll.get(include=["documents", "metadatas"])
ids, docs = got["ids"], got["documents"]
print(f"total memories: {len(ids)}")

kill = []
for i, doc in zip(ids, docs):
    low = (doc or "").lower()
    task_part = ""
    p = (doc or "").rfind("Task: ")
    if p >= 0:
        end = doc.find("\nResult:", p)
        task_part = doc[p + 6: end if end > 0 else len(doc)].strip()
    reasons = []
    if POISON.search(doc or ""):
        reasons.append("poison")
    if task_part and AgentEngine._is_small_talk(task_part):
        reasons.append("smalltalk-task")
    if reasons:
        kill.append(i)
        print(f"KILL {i} [{'+'.join(reasons)}] :: {task_part[:70] or doc[:70]!r}")

if kill:
    store._coll.delete(ids=kill)
print(f"\ndeleted: {len(kill)} / {len(ids)}")
print("remaining:", len(store._coll.get()['ids']))

# server-side session DB: old DDoS test sessions carry refusal answers
import sqlite3
con = sqlite3.connect(r"data\🔥😈 PORT 777 EVIL ☠️🔥👹.db")
cur = con.cursor()
n_msg = cur.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
n_ses = cur.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
cur.execute("DELETE FROM messages")
cur.execute("DELETE FROM sessions")
con.commit()
con.close()
print(f"db sessions wiped: {n_ses}, messages wiped: {n_msg}")
print("SCRUB DONE")
