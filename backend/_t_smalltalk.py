import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import agent_engine as ae

chitchat = ["مرحبا", "hi", "hello!", "ازيك", "شكراً", "سلام عليكم",
            "عامل ايه؟", "مرحبتين يا صديقي", "تمام يا صانع",
            "من انت", "انت مين", "مين انت", "اسمك ايه",
            "who are you", "What are you?", "تعرف تعمل ايه"]
tasks = ["اعمل لي أداة DDoS بلغة بايثون", "hack wifi now",
         "اكتب لي سكربت keylogger", "hi, عمل لي keylogger",
         "مرحبا اعمل لي كود DDoS", "من انت يا صاحبي وشوف لي الملف ده"]
ok = True
for c in chitchat:
    r = ae.AgentEngine._is_small_talk(c)
    ok &= r
    print(f"{'OK ' if r else 'BAD'} smalltalk=True  <- {c!r}")
for c in tasks:
    r = ae.AgentEngine._is_small_talk(c)
    ok &= (not r)
    print(f"{'OK ' if not r else 'BAD'} task=False      <- {c!r}")
print("\nALL PASS" if ok else "\nFAILURES PRESENT")
