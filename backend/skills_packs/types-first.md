---
name: types-first
description: Design contracts/types/schemas before writing code — mattpocock methodology, polyglot edition
trigger_when:
  - "typescript"
  - "interface"
  - "api design"
  - "schema"
  - "types"
  - "pydantic"
  - "struct"
  - "design"
always: false
---

# Types-First Design (mattpocock methodology, polyglot)

Before writing implementation code for anything with a boundary —
API, module, parser, config — define the CONTRACT first.

**1. Model the domain, not the JSON.** Write the types that describe
truth: TypeScript interfaces / pydantic models / C structs / protobuf
schemas — whichever the target language speaks natively.

**2. Make invalid states unrepresentable.** Prefer unions/enums over
boolean flags; required fields over optional-with-default-chaos;
branded/newtype wrappers over raw strings for IDs.

**3. The boundary is the only place validation lives.** Parse, don't
validate: input crosses the boundary ONCE into typed land; after
that, functions trust their types.

**4. Implement against the contract.** The compiler/validator is the
first reviewer. If the implementation fights the types, the types are
wrong — fix the types, not the call sites.

**5. Ship both.** Final Answer shows: the contract (types), then the
implementation, then one usage example. Reviewer reads the contract
and knows the whole design in 30 seconds.
