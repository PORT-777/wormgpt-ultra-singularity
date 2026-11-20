---
name: learned-اكتب-سكربت-بايثون
description: "Auto-learned from a completed task: استعمل pathlib.iterdir() مع فحص .is_file() لجمع الملفات، ثم sorted() لترتيبها وطباعة f.name و f.stat"
trigger_when:
  - downloads
  - pathlib
  - st_size
  - stat
  - أبجدي
  - أسمائها
---

# Playbook: استعمل pathlib.iterdir() مع فحص .is_file() لجمع الملفات، ثم sorted() لترتيبها وطباعة f.name و f.stat().st_size.

## Facts backing it
- يستخدم السكربت مكتبة pathlib للوصول إلى مسار ~/Downloads وتحديد الملفات فقط.
- يتحقق من وجود المجلد ويطبع رسالة إذا لم يكن موجودًا.
- يفرز الملفات أبجديًا قبل طباعة أسمائها وحجمها بالبايت.
- يستخدم f.stat().st_size لاستخراج حجم كل ملف.

Triggers on any task whose goal matches the facts above; apply the same verified steps.
