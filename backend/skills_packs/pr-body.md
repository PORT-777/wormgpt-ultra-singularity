---
name: pr-body
description: شكل Pull Request المحترف — ملخص/إثبات قبل-بعد/مخاطر الدمج
trigger_when:
  - "pr"
  - "pull request"
  - "commit message"
  - "merge"
  - "diff للنشر"
always: false
---

# PR Body Playbook (mattpocock pr)

عند تجهيز تغييرات للنشر:

1. **الملخص = أصغر صورة تجعل التغيير واضحاً** (سطران مثالية).
2. **إثبات قبل/بعد**: أمر أو مخطط يثبت أن التغيير يعمل (اختبار مرّ).
3. **Merge-danger**: هل هو one-way door (يصعب التراجع) أم two-way؟
   حدد blast radius: ما يكسره لو فشل.
4. **المراجعون بحاجة**: أي مسار قرروا بالنظر؟ اذكره في الـ body.

قاعدة: الـ body يعود بالتفاصيل الدقيقة إلى الـ diff، لا يكررها.
