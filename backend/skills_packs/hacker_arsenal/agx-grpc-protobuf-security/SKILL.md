---
name: agx-grpc-protobuf-security
description: "grpc-protobuf-security"
trigger_when: "grpc-protobuf-security,grpc,protocol,buffers,security,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: grpc-protobuf-security
description: >-
  Use this skill when security testing gRPC services, analyzing Protocol Buffers (Protobuf) payloads, or reverse engineering gRPC endpoints.
  Covers gRPC reflection, Protobuf serialization flaws, grpc-ui / ghz fuzzing, and authentication interceptors.
---

## gRPC & Protocol Buffers Security Skill

Security auditing of modern gRPC microservices and Protobuf data formats.

### Coverage Map

| Reference File | Contents |
|---|---|
| [grpc-testing-methodology.md](references/grpc-testing-methodology.md) | Enumerate gRPC services with grpcurl, fuzzing with ghz, reflection attacks |
