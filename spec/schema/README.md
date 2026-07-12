# `spec/schema/` — JSON Schema for the canonical contracts

One hand-authored JSON Schema per core contract and per capability IR shape.
The schemas are the neutral source of truth: language dataclasses/structs are
**conformance-tested against them**, never generated from them (nor they from
the code).

Naming and identity conventions:

- The schema file for shape token `x.y` is `x_y.schema.json` (dots become
  underscores): `chat.request` → `chat_request.schema.json`. This mapping is
  what the fixture validation harness relies on — see "How fixtures map to
  schemas" in [`../README.md`](../README.md).
- Every schema carries an `$id` of the form
  `https://ocai.dev/spec/schema/<filename>`; cross-file `$ref`s are relative
  and resolve against those ids.
- Every schema carries a top-level `$comment` explaining its role and naming
  the code it mirrors.
- Shared building blocks (the IR envelope, `ProviderRef`, the `Source`
  union, `Span`/`Annotation`, `CacheHint`) live in the `$defs` of
  [`parts.schema.json`](parts.schema.json) and are referenced from the other
  schemas.
- [`usage.schema.json`](usage.schema.json) and
  [`finish.schema.json`](finish.schema.json) are **core contracts**
  (capability-neutral), not chat-local: the vocabulary they serialize lives
  in `ocai.core` (`ocai/core/usage.py`, `ocai/core/finish.py`) and is shared
  by every capability — chat delivers them on responses and stream ends,
  embedding on its response, future capabilities on theirs.

Schema rules:

- **Additive-only, tolerant readers.** Never rename, remove, or repurpose a
  member; new members are optional; `additionalProperties` stays permissive
  where the IR sweeps unknowns into `extensions`.
- **Omit-absent.** Schemas must not require members an omit-absent encoder
  drops (empty bags, unset optionals) — see `spec/canonical-json.md` §6.
- **Open string codes.** Enum-like members (`role`, `finish.reason`, part
  `type`, `status`) are typed as strings with documented canonical constants,
  never closed `enum` lists — decode is total by construction.
