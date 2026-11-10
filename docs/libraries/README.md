---
icon: lucide/library
---

# Libraries

The public libraries are the first face of ocai: one implementation per
language of the same contracts, all passing the same golden fixtures from
[`spec/`](../spec/README.md). A port is not "done" when it compiles; it is
done when the conformance suite that certifies the Python implementation
passes unchanged against it.

| Library | Status | Where |
|---|---|---|
| [Python](python/README.md) | **Implemented** — M1–M3: unary and streaming chat on OpenAI Chat Completions and Anthropic Messages, cross-conversion fidelity reports, front doors | `python/` (uv workspace: `ocai`, `ocai-openai`, `ocai-anthropic`) |
| [TypeScript](typescript.md) | Deferred — placeholder only | `typescript/` |
| [Go](go.md) | Deferred — placeholder only | `go/` |

What every library shares, whatever the language:

- the four-level identity (`Capability` → interface → dated tag → `Shape`)
  and the canonical IR, which is itself the interface named `ocai`;
- `CallResult(value, route, report, usage, raw)` on every port — the
  `FidelityReport` lives there and only there;
- total decode: no unknown input ever raises;
- the stream-first law `fold(stream(request)) == complete(request)`.

The language-neutral statement of those rules is the
[architecture](../architecture.md); the executable statement is `spec/`.
