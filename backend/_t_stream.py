import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import asyncio

async def main():
    import configs as config
    from model_router import ROUTER
    from langchain_core.messages import SystemMessage, HumanMessage
    route, brain = ROUTER.resolve("auto")
    print("route:", route, "| brain:", type(brain).__name__ if brain else None)
    msgs = [
        SystemMessage(content="You are 🔥😈 PORT 777 EVIL ☠️🔥👹. The operator greets you. Reply warmly, briefly, in Arabic (Egyptian-friendly). No tools, no code, no headers."),
        HumanMessage(content="Ù…Ø±Ø­Ø¨Ø§"),
    ]
    got = 0
    buf = ""
    try:
        async for chunk in brain.astream(msgs):
            c = getattr(chunk, "content", None)
            print("CHUNK:", repr(c)[:120])
            buf += (c if isinstance(c, str) else str(c) if c else "")
            got += 1
    except Exception as e:
        print("EXC:", type(e).__name__, e)
    print("chunks:", got, "| buf len:", len(buf))
    print("buf:", buf[:300])

asyncio.run(main())
