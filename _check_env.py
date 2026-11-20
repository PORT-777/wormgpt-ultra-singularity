import sys, os
out = []
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from configs import settings as c
    out.append(f"GROQ_READY={c.GROQ_READY} GEMINI_READY={c.GEMINI_READY} HF_READY={c.HF_READY}")
    try:
        from model_router import ROUTER
        st = ROUTER.status()
        out.append("router: " + ", ".join(f"{k}:{'ok' if v['available'] else 'off'}" for k, v in st.items()))
    except Exception as e:
        out.append(f"router import FAILED: {type(e).__name__}: {e}")
except Exception as e:
    out.append(f"FAILED: {type(e).__name__}: {e}")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_check_out.txt"), "w", encoding="utf-8").write("\n".join(out))
