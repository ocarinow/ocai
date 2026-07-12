# `spec/interfaces/` — catalog descriptors as data

**Status: placeholder — format normative, descriptor population pending.**

One JSON document per **provider interface** — the wire protocols the
conversion catalog is built from (`openai/chat_completions`,
`openai/responses`, `anthropic/messages`, and the canonical `ocai/ocai`
interface itself). These are the language-neutral registry the four-level
identity model ([`docs/architecture.md`](../../docs/architecture.md) §2.1)
serializes to: every `NodeId` coordinate that appears in a fixture's
`src`/`dst` must resolve against a descriptor here, which is how CI catches a
fixture naming a tag that was never declared.

## Descriptor format

```
spec/interfaces/<provider>.<interface>.json
```

```jsonc
{
  "provider": "openai",
  "interface": "chat_completions",
  "capability": "chat",
  "description": "OpenAI POST /v1/chat/completions",
  "docs_url": "https://platform.openai.com/docs/api-reference/chat",
  "shapes": ["chat.request", "chat.response", "chat.chunk"],
  "tags": [
    {
      "tag": "2026-01",            // opaque; never parsed
      "released": "2026-01-15",    // the ordering key, ISO date
      "status": "stable"           // stable | preview | deprecated | retired
    }
  ]
}
```

Semantics (mirroring `ocai.core.identity`):

- `tag` is an **opaque** revision token — implementations MUST order a
  descriptor's revisions by `released`, never by parsing `tag`, and MUST NOT
  compare dates across providers.
- `status` drives catalog resolution: only `stable` tags are auto-selected;
  `preview` requires an explicit pin; `deprecated` resolves only when
  pinned; `retired` exists so archived traffic can still be re-converted
  through migration edges.
- Sibling interfaces of one provider (`chat_completions`, `responses`) are
  **concurrent**, not versions of each other — each gets its own descriptor.
- Descriptors are additive-only: tags are appended, statuses are updated,
  nothing is deleted.

## Worked example

`spec/interfaces/ocai.ocai.json` — the canonical IR is just another
interface:

```json
{
  "provider": "ocai",
  "interface": "ocai",
  "capability": "chat",
  "description": "The canonical ocai IR, dated revisions; migration between revisions is ordinary graph conversion.",
  "shapes": ["chat.request", "chat.response", "chat.chunk"],
  "tags": [
    { "tag": "2026-07", "released": "2026-07-01", "status": "stable" }
  ]
}
```
