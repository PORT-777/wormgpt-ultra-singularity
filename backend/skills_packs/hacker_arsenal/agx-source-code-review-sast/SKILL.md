---
name: agx-source-code-review-sast
description: "source-code-review-sast"
trigger_when: "source-code-review-sast,source,code,review,sast,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: source-code-review-sast
description: >-
  Use this skill when auditing source code for security vulnerabilities, conducting Static Application Security Testing (SAST),
  or reviewing codebases in C/C++, Java, Python, Go, Node.js, and PHP. Covers vulnerability patterns (SQLi, Command Injection,
  Memory Corruption, Insecure Deserialization, SSRF), SAST tools (Semgrep, SonarQube, CodeQL, Joern), and manual code review methodology.
---

## Source Code Review & SAST Skill

Comprehensive skill for manual source code auditing, static code analysis, and rule authoring across major programming languages.

### Coverage Map

| Reference File | Contents |
|---|---|
| [sast-methodology.md](references/sast-methodology.md) | Code review workflow, source-to-sink tracking, data flow analysis |
| [c-cpp-code-review.md](references/c-cpp-code-review.md) | C/C++ vulnerabilities: buffer overflows, integer issues, use-after-free, format strings |
| [java-code-review.md](references/java-code-review.md) | Java security: deserialization, XXE, SQLi, Spring security flaws, reflection abuse |
| [python-code-review.md](references/python-code-review.md) | Python security: eval/exec, pickle, SSTI, shell injection, subprocess misuse |
| [go-node-code-review.md](references/go-node-code-review.md) | Go & Node.js security: prototype pollution, goroutine leaks, SSRF, path traversal |
| [semgrep-rules.md](references/semgrep-rules.md) | Writing custom Semgrep rules for automated static vulnerability finding |
| [codeql-queries.md](references/codeql-queries.md) | CodeQL query authoring, taint tracking, and AST analysis |
