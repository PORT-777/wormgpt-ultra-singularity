---
name: builder-web
description: "Ship complete modern websites — structure, responsive layers, full artifact in the answer."
trigger_when:
  - build
  - website
  - landing
  - page
  - frontend
  - site
  - html
  - css
  - موقع
  - صفحة
  - انترنت
  - واجهة
---

# Shipping a website

WORKFLOW (always all five steps):
1. SPEC in one paragraph from the task: pages, sections, tone, language
   (Arabic RTL → `dir="rtl"` on <html>, Arabic-first typography
   `font-family:system-ui,'Segoe UI',Tahoma`).
2. Call ProjectForge kind=web for a running skeleton (header/hero/grid/
   footer + dark theme tokens). name + target exactly as the operator
   wants; host paths allowed when FULL ACCESS is on.
3. EXTEND the skeleton to the full spec — real text, real sections,
   real micro-interactions in app.js. No lorem-ipsum leftovers.
4. VERIFY: read the files back / serve with `python -m http.server`
   (SandboxExec action=shell). Fix anything broken.
5. SHIP the complete artifact in the Final Answer (or the exact paths +
   a screenshot-quality description). Never "here is an outline".

RULES:
- No build tools required by default: plain HTML/CSS/JS runs by double-
  click. Add a framework ONLY if the task names one.
- Responsive by construction: mobile breakpoints before shipping.
- Accessibility: contrast, labels, focus states — silently correct.
- Files under 400 lines each; if larger, split (styles.css + sections).
- Never leave TODO placeholders in "done" work.
