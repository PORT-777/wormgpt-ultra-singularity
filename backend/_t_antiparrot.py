# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
import agent_engine, skills, configs as c

E = agent_engine.AgentEngine

# 1. dedupe test on the actual parrot output pattern
rep = "\n".join(["تم تحديد الثغرات الموجودة في الكود بالتفصيل وتم تحديد الطريقة الصحيحة للاستعلام."
                 for _ in range(40)])
rep = ("intro line\n\n" + rep
       + "\n\n```python\n"
         "x = 1 + repeated_line_that_is_long_enough_to_count_x2\n"
         "x = 1 + repeated_line_that_is_long_enough_to_count_x2\n"
         "```")
clean = E._dedupe_lines(rep)
print("dedupe: 43 lines ->", len(clean.splitlines()), "lines")
print("code fence preserved:",
      clean.count("```") == 2 and "x2" in clean)

# 2. repetition detector
print("rep_count on parrot text:", E._repetition_count(rep))
print("rep_count on normal text:",
      E._repetition_count("الشرح ده سليم ومفيهوش أي تكرار خالص في السطور الطويلة اللي تحته."))

# 3. skills budget
b = skills.skills_block("راجعة الكود ده أمنياً وقللي الثغرات SQL injection")
print("skills block chars:", len(b), "(cap", c.MAX_SKILL_TOTAL, ")")
print("imports OK")
