---
ocai: minor
---

#### Preserve native HTTP failures for reusable host classification

Expose detached response headers and bytes on ocai errors and allow optional host
mappers to classify failures before retry policies, across sync/async unary and
streaming. Prepared calls validate mapping configuration; observers omit response
payloads and headers. No new dependency. (WU-48a, #112)
