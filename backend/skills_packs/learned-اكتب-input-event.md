---
name: learned-اكتب-input-event
description: "Auto-learned from a completed task: استخدم Tkinter وربط `<KeyPress>` لتسجيل المفاتيح داخل النافذة وحفظها بملف."
trigger_when:
  - ctrl
  - event
  - hooks
  - input
  - input_log
  - tkinter
---

# Playbook: استخدم Tkinter وربط `<KeyPress>` لتسجيل المفاتيح داخل النافذة وحفظها بملف.

## Facts backing it
- سجل ضغطات الكيبورد داخل نافذة Tkinter فقط، مع طابع زمني.
- يكتب السجلات إلى ملف نصي `input_log.txt`.
- يمكن إيقاف التسجيل بـ Ctrl+Q ويغلق البرنامج.
- لا يستخدم hooks نظامية، لذا لا يراقب تطبيقات أخرى.

Triggers on any task whose goal matches the facts above; apply the same verified steps.
