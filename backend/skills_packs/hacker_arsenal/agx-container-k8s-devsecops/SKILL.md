---
name: agx-container-k8s-devsecops
description: "container-k8s-devsecops"
trigger_when: "container-k8s-devsecops,container,kubernetes,devsecops,security,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: container-k8s-devsecops
description: >-
  Use this skill when pentesting containerized environments, Kubernetes clusters, Docker configurations, CI/CD pipelines,
  and Cloud-Native DevSecOps workflows. Covers Docker escape techniques, Kubernetes RBAC abuse, Kubelet/API server exploitation,
  Helm/Istio misconfigurations, and supply chain pipeline attacks.
---

## Container, Kubernetes & DevSecOps Security Skill

Deepdive reference for attacking and securing Docker containers, Kubernetes infrastructure, and CI/CD security.

### Coverage Map

| Reference File | Contents |
|---|---|
| [docker-security-escape.md](references/docker-security-escape.md) | Docker container breakout, privileged containers, socket abuse, cgroups |
| [k8s-exploitation.md](references/k8s-exploitation.md) | Kubernetes cluster attacks, RBAC escalation, Kubelet abuse, API server takeover |
| [cicd-pipeline-attacks.md](references/cicd-pipeline-attacks.md) | GitHub Actions injection, GitLab CI exploitation, supply chain attacks |
| [cloud-native-tools.md](references/cloud-native-tools.md) | Trivy, Grype, Kube-bench, Peirates, CD K8s security tools |
