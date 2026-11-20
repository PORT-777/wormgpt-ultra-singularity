---
name: research-notes
description: بحث موثّق يُخزن نتائجه في ملف markdown داخل workspace/research
trigger_when:
  - "research"
  - "بحث"
  - "ابحث عن"
  - "sources"
  - "who is"
  - "latest news"
  - "price of"
always: false
---

# Research Playbook (mattpocock research + citations)

عند أي بحث:

1. **مصادر أساسية أولاً**: WebSearch ثم Browser للصفحات التفاعلية.
   فضّل المستند الأصلي على مقال يلخّصه.
2. **كُل حقيقة مع عنوانها**: كل سطر = حقيقة + URL مصدره. لا مصادر
   مختلقة أبداً — لو لم تجد مصدراً، اقل ما تحتاجه وصنفه "غير مؤكد".
3. **اترك أثراً**: خزّن النتائج النهائية في ملف
   `backend/workspace/research/<الموضوع>.md` عبر UniversalFileManager:
   - سطر الموضوع + التاريخ
   - Findings (كل واحدة بمصدرها)
   - Open questions
4. Final Answer: خلاصة 5 أسطر + المسار + أفضل 3 مصادر.
