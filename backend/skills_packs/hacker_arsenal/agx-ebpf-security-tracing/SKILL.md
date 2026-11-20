---
name: agx-ebpf-security-tracing
description: "ebpf-security-tracing"
trigger_when: "ebpf-security-tracing,ebpf,security,tracing,rootkits,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: ebpf-security-tracing
description: >-
  Use this skill when developing eBPF-based security sensors, analyzing eBPF rootkits, or tracing Linux kernel behavior.
  Covers eBPF probe types (kprobe, tracepoint, socket_filter), bpftrace scripting, libbpf development, and eBPF security tools.
---

## eBPF Security, Tracing & Rootkits Skill

Linux kernel instrumentation via extended Berkeley Packet Filter for runtime security monitoring and offensive rootkits.

### Coverage Map

| Reference File | Contents |
|---|---|
| [bpftrace-scripting.md](references/bpftrace-scripting.md) | One-liners and scripts for tracing syscalls, file accesses, and process execution |
| [ebpf-rootkits-defense.md](references/ebpf-rootkits-defense.md) | Analyzing eBPF rootkit mechanics (override return values, hide processes) and detection |
