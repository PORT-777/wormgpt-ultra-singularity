---
name: int-scanners-box-ai-agent-runtime-controls
description: "Scanner collection: AI Agent Runtime Controls (We5ter/Scanners-Box)"
trigger_when: "scanners-box,agent,runtime,controls"
source: Scanners-Box
---
## AI Agent Runtime Controls


*Sandboxes, policy engines and approval gates that bound what agents can do.*


- https://github.com/NVIDIA/OpenShell - **Sandboxed runtime for autonomous AI agents — declarative YAML policies enforce boundaries across filesystem, network, process and provider access, block data exfiltration and unauthorized egress, and inject credentials only into policy-admitted endpoints; runs Claude Code, Codex, OpenCode and Copilot CLI in isolated containers on Docker, Podman, MicroVM or Kubernetes**

> ![](https://img.shields.io/badge/MainLanguage-Rust-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/NVIDIA/OpenShell?style=for-the-badge)  ![GitHub stars](https://img.shields.io/github/stars/NVIDIA/OpenShell.svg?style=for-the-badge)  ![GitHub](https://img.shields.io/github/license/NVIDIA/OpenShell?style=for-the-badge)

- https://github.com/microsoft/agent-governance-toolkit - **Microsoft's governance toolkit for autonomous AI agents — a policy engine authorizing tools and actions, zero-trust agent identity with short-lived scoped credentials, OS-level execution sandboxing, plus reliability engineering (circuit breakers, budget caps, audit trails); ships reference policy packs mapped to all 10 OWASP Agentic Top 10 categories**

> ![](https://img.shields.io/badge/MainLanguage-Python-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/microsoft/agent-governance-toolkit?style=for-the-badge)  ![GitHub stars](https://img.shields.io/github/stars/microsoft/agent-governance-toolkit.svg?style=for-the-badge)  ![GitHub](https://img.shields.io/github/license/microsoft/agent-governance-toolkit?style=for-the-badge)

- https://github.com/agentkitai/agentgate - **Approval workflow engine for AI agents — define policies to auto-approve safe actions, auto-deny dangerous ones, and route the rest to a human via dashboard, Slack, Discord, or email**

> ![](https://img.shields.io/badge/MainLanguage-TypeScript-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/agentkitai/agentgate?style=for-the-badge)  ![GitHub stars](https://img.shields.io/github/stars/agentkitai/agentgate.svg?style=for-the-badge)  ![GitHub](https://img.shields.io/github/license/agentkitai/agentgate?style=for-the-badge)

- https://github.com/kubernetes-sigs/agent-sandbox - **Kubernetes-native sandbox for AI agent workloads — the Sandbox CRD manages isolated, stateful, singleton pods with stable identity and persistent storage, supports gVisor/Kata secure runtimes, deep hibernation and auto-resume, plus SandboxTemplate/SandboxClaim/SandboxWarmPool extensions and Go/Python SDKs**

> ![](https://img.shields.io/badge/MainLanguage-Go-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/kubernetes-sigs/agent-sandbox?style=for-the-badge)  ![GitHub stars](https://img.shields.io/github/stars/kubernetes-sigs/agent-sandbox.svg?style=for-the-badge)  ![GitHub](https://img.shields.io/github/license/kubernetes-sigs/agent-sandbox?style=for-the-badge)


---

(cn: AI Agent运行时管控; cn body follows)

*沙箱、策略引擎与审批门禁，圈定 Agent 能做什么。*


- https://github.com/NVIDIA/OpenShell - **面向自主 AI Agent 的安全私有运行时——用声明式 YAML 策略在文件系统、网络、进程与凭证四个维度设界，阻断数据外泄与越权出站，凭证只在策略放行后按授权端点注入，可在 Docker、Podman、MicroVM、Kubernetes 上为 Claude Code、Codex、OpenCode、Copilot CLI 等 Agent 提供隔离容器**

> ![](https://img.shields.io/badge/主语言-Rust-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/NVIDIA/OpenShell?style=for-the-badge&label=上次提交)  ![GitHub stars](https://img.shields.io/github/stars/NVIDIA/OpenShell.svg?style=for-the-badge&label=star数量)  ![GitHub](https://img.shields.io/github/license/NVIDIA/OpenShell?style=for-the-badge&label=开源协议)

- https://github.com/microsoft/agent-governance-toolkit - **微软出品的自主 AI Agent 治理工具包——策略引擎负责工具与动作的授权，零信任身份配发短期受限凭证，OS 级执行沙箱做隔离，另有可靠性工程（熔断、预算上限、审计留痕）；自带映射到 OWASP Agentic Top 10 全部 10 个类别的参考策略集**

> ![](https://img.shields.io/badge/主语言-Python-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/microsoft/agent-governance-toolkit?style=for-the-badge&label=上次提交)  ![GitHub stars](https://img.shields.io/github/stars/microsoft/agent-governance-toolkit.svg?style=for-the-badge&label=star数量)  ![GitHub](https://img.shields.io/github/license/microsoft/agent-governance-toolkit?style=for-the-badge&label=开源协议)

- https://github.com/agentkitai/agentgate - **AI Agent 行为审批工作流引擎——通过策略自动放行安全操作、拦截危险操作，其余路由给人工通过 Dashboard、Slack、Discord 或 Email 审批**

> ![](https://img.shields.io/badge/主语言-TypeScript-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/agentkitai/agentgate?style=for-the-badge&label=上次提交)  ![GitHub stars](https://img.shields.io/github/stars/agentkitai/agentgate.svg?style=for-the-badge&label=star数量)  ![GitHub](https://img.shields.io/github/license/agentkitai/agentgate?style=for-the-badge&label=开源协议)

- https://github.com/kubernetes-sigs/agent-sandbox - **Kubernetes 原生 AI Agent 沙箱——Sandbox CRD 管理隔离、有状态、单实例的 Pod，提供稳定身份与持久化存储，支持 gVisor/Kata 安全运行时、深度休眠与自动恢复，附带 SandboxTemplate/SandboxClaim/SandboxWarmPool 扩展及 Go/Python SDK**

> ![](https://img.shields.io/badge/主语言-Go-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/kubernetes-sigs/agent-sandbox?style=for-the-badge&label=上次提交)  ![GitHub stars](https://img.shields.io/github/stars/kubernetes-sigs/agent-sandbox.svg?style=for-the-badge&label=star数量)  ![GitHub](https://img.shields.io/github/license/kubernetes-sigs/agent-sandbox?style=for-the-badge&label=开源协议)


