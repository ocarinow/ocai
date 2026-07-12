# `spec/schema/` — JSON Schema for the canonical contracts

One hand-authored JSON Schema per core contract and per capability IR shape.
The schemas are the neutral source of truth: language dataclasses/structs are
**conformance-tested against them**, never generated from them (nor they from
the code).

> **STALE-PENDING-REGENERATION.** The three schemas currently here —
> `message.schema.json`, `chat_request.schema.json`,
> `chat_response.schema.json` — describe the pre-July-2026 IR (flat
> `content` field, `ir_version: "0.1"`, no parts taxonomy). They are being
> regenerated against the re-architected IR of
> [`docs/architecture.md`](../../docs/architecture.md) §3.1 (parts-only
> `Message`, `FinishInfo`, `ChatChunk`/`StreamEnd`, `Consumption` usage,
> omit-absent encoding, dated `ocai@2026-07` revision). They are kept — not
> deleted — until the regenerated set lands, so the change is diffable; do
> not extend them and do not validate new fixtures against them.

Schema rules (unchanged by the re-architecture):

- **Additive-only, tolerant readers.** Never rename, remove, or repurpose a
  member; new members are optional; `additionalProperties` stays permissive
  where the IR sweeps unknowns into `extensions`.
- **Omit-absent.** Schemas must not require members an omit-absent encoder
  drops (empty bags, unset optionals) — see `spec/canonical-json.md` §6.
- **Open string codes.** Enum-like members (`role`, `finish.reason`, part
  `type`, `status`) are typed as strings with documented canonical constants,
  never closed `enum` lists — decode is total by construction.
