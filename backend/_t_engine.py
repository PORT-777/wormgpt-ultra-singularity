import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
sys.path.insert(0, "..")
import asyncio

async def main():
    from agent_engine import ENGINE
    task = "مرحبا"
    print("is_small_talk:", ENGINE._is_small_talk(task))
    out = ""
    async for ev in ENGINE.run_stream(task, history=None, model_route="auto"):
        t = ev.get("type")
        d = ev.get("data")
        if t == "stream":
            out += str(d)
        elif t == "final":
            out = str(d)
        print(f"[{t}]", str(d)[:80].replace("\n", " "))
    print("=== ANSWER ===")
    print(out[:300])

asyncio.run(main())
