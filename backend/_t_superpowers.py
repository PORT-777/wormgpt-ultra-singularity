# -*- coding: utf-8 -*-
"""اختبار مؤقت: باكات superpowers — تحميل + أحجام + حقن حسب المهمة."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

import skills

packs = skills.load_packs()
sp = [p for p in packs if p["name"].startswith("superpowers")]
print(f"total packs: {len(packs)} | superpowers: {len(sp)}")
for p in sp:
    print(f"  - {p['name']:<48} {len(p['instructions']):>4} chars "
          f"| triggers: {len(p['trigger_when']):>2} | always: {p['always']}")

# right-size check
big = [p["name"] for p in packs if len(p["instructions"]) > 4000]
print("over-4K packs (loader truncates these):", big or "none")

# injection scenarios
cases = {
    "EN debug":  "my script throws AttributeError and crashes",
    "AR debug":  "السكريبت بيرمي خطأ ومش شغال عايزك تصلحه",
    "EN code":   "write a python module that parses nginx logs",
    "AR plan":   "عايز خطة كاملة لبناء مشروع قياس أداء من الصفر",
    "security":  "افحص الموقع ده للثغرات OWASP وطلّع PoC لكل ثغرة",
    "done-check": "اتأكد إن الكود اتنفذ واختبر النتيجة وريهالي",
    "creative":  "ابني لي فكرة أداة جديدة للمراقبة",
}
for label, task in cases.items():
    selected = [p["name"] for p in skills.relevant_packs(task, cap=6)]
    n_sp = sum(1 for s in selected if s.startswith("superpowers"))
    print(f"[{label:>10}] always-on={sum(1 for s in selected if 'core-discipline' in s)} "
          f"sp-picks={n_sp} -> {selected[:4]}")
print("ALL OK")
