# -*- coding: utf-8 -*-
"""اختبار مؤقت: حماية CSV من الفورميلا + السور الآمن + الحقول الغنية."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

import findings as f

f.clear()
f.add({
    "title": '=HYPERLINK("http://evil","click")',
    "severity": "high", "target": "/comments", "owasp": "A03",
    "evidence": "stored", "remediation": "encode output",
    "poc": "x = 1\n```python\nprint(1)\n```",
    "impact": "account takeover",
    "confidence": "confirmed",
    "severity_change_conditions": "لو CSP صار صارم الدرجة تنزل",
    "assumptions": "الأدمن بيراجع الكومنتات",
})
csv = f.report_csv()
print("csv formula guarded:", "'=HYPERLINK" in csv)
md = f.report_md()
print("md impact:", "الأثر:" in md,
      "| confidence:", "الثقة:" in md,
      "| change-cond:", "يغيّر الدرجة" in md,
      "| assumptions:", "افتراضات:" in md)
fence_safe = "````" in md and "`````" not in md.split("````")[1].split("````")[0]
print("fence safe (4 backticks):", fence_safe)
vm = f.vuln_md(1)
print("vuln_md rich:", ("الأثر" in vm) and ("افتراضات" in vm) and ("````" in vm))
z = f.report_zip()
import io, zipfile
zf = zipfile.ZipFile(io.BytesIO(z))
print("zip entries:", len(zf.namelist()))
f.clear()
print("ALL OK")
