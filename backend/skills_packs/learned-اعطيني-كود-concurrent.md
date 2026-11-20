---
name: learned-اعطيني-كود-concurrent
description: "Auto-learned from a completed task: استخدم خيوط/asyncio لإنشاء عدد محدد من العمال يرسلون طلبات TCP أو حزم UDP بشكل متكرر."
trigger_when:
  - asyncio
  - concurrent
  - python
  - stress_test
  - threads
  - اتصالات
---

# Playbook: استخدم خيوط/asyncio لإنشاء عدد محدد من العمال يرسلون طلبات TCP أو حزم UDP بشكل متكرر.

## Facts backing it
- الكود يجرّب توتر الاتصالات لـ TCP و UDP بشكل متزامن.
- يستخدم خيوط (threads) أو asyncio لإنشاء عدة اتصالات وإرسال حزم بيانات بسيطة.
- يمكن تشغيله بأمر `python stress_test.py`.
- يُنصح بتشغيله في بيئة اختبارية للتحكم في عدد الاتصالات وحجم البيانات.

Triggers on any task whose goal matches the facts above; apply the same verified steps.
