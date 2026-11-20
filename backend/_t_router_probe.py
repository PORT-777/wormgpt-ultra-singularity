# -*- coding: utf-8 -*-
import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from model_router import ROUTER


async def main():
    route, brain = ROUTER.resolve("groq")
    print("resolved route:", route)
    try:
        r = await brain.ainvoke([("user", "Reply with exactly: OK")])
        out = r.content if isinstance(r.content, str) else str(r.content)
        print("groq brain replied:", out.strip()[:80])
    except Exception as exc:
        print("groq chain failed:", str(exc)[:200])
        local = ROUTER.resolve("local")
        print("local route:", local[0])

asyncio.run(main())
