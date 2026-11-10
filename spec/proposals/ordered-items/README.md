# Ordered items — draft 1

**Status: design proposal, not a runtime API.** The active canonical revision
remains `2026-07`. `ordered-items-draft-1` is a proposal marker, never a graph
node tag. No converters, dataclasses, or stream events are registered by these
files. WU-19 validates this design checkpoint; it does not finish the migration.

## Candidate structure

Both [request](request.schema.json) and [response](response.schema.json) carry
an ordered `items` array. [Items](items.schema.json) distinguish messages,
reasoning, tool calls/results, approval requests/responses, and unknown tags.
A message has a role and [content](content.schema.json); execution events no
longer masquerade as message content. Text convenience views will be derived
and must not erase phase, message boundaries, or tool ordering.

```json
{
  "proposal": "ordered-items-draft-1",
  "items": [
    {"type": "message", "id": "msg_1", "role": "model",
     "phase": "commentary", "content": [{"type": "text", "text": "Checking."}]},
    {"type": "tool_call", "id": "item_2", "call_id": "call_1",
     "name": "lookup", "args_json": "{\"query\":\"ocai\"}"}
  ]
}
```

The same vocabulary represents subsequent request history. An item ID, when
provided, is preserved independently of a tool's correlation ID. IDs are
optional because user-authored history need not have native IDs; ordered array
position is always available. Role, phase, status, and execution-owner codes
are open. `phase: null` is distinct from omission when a provider supplies it.
Cross-item validity and provider restrictions are not established by JSON Schema.

Anthropic can put text and tool use inside one native message. Splitting those
blocks into items needs a reversible grouping lane. The candidate `source_group`
records provider, interface, container identity, and native block index. Its
container is provenance, not a transferable provider handle. Missing native
container IDs will need local grouping identifiers and an explicit migration
rule; this draft does not generate IDs. See [the block fixture](fixtures/anthropic_blocks.json).

Tool arguments retain the verbatim `args_json` lane. Object-only provider input
requires a declared serialization shift. Approval exchanges preserve correlation
but cannot grant application permissions by themselves. Continuation uses a
scoped `ProviderRef`; crossing interfaces will require a supported replay path
or an explicit unsupported report.

## Content and evidence boundaries

The candidate content schema reuses current text/media/refusal/opaque shapes,
including existing citation annotations. It excludes known reasoning and tool
parts from message content. Unknown tags remain legal; malformed known item
variants cannot evade required fields by falling through an unknown branch.
Unknown members remain permitted for forward compatibility. Schema acceptance
does not implement preservation: the eventual decoder needs round-trip tests.

Two candidate parts explore requirements without changing production types:

- `json` requires a `value`, including null, scalars, and arrays. It means native
  structured data, not an automatic parse of generated text.
- `file` uses the existing source union with optional filename, byte length,
  and SHA-256 metadata. Validation does not fetch, upload, decode, or verify bytes.

Code fences remain verbatim text; executed code belongs to tool activity.
Search results and sources need reusable evidence objects. Answer spans and
source locations are distinct: page, time, and image-region selectors should
not be squeezed into text offsets. Those evidence/location schemas, generic
resource ownership, and citation normalization rules are deliberately still
open, tracked in the modernization plan. Existing annotations are not a claim
that the citation gap is solved.

Shared `$ref`s point at active schemas only to avoid duplicating unchanged
vocabulary during review. This is not a frozen, independently versioned schema
bundle. Before promotion, snapshot/version those dependencies and settle nested
revision markers. Config/tool declarations remain the current provisional
shapes; hosted-tool declarations and job lifecycle APIs are not specified here.

## Evidence and verification

All five [fixtures](fixtures/) are labelled **synthetic**. The Anthropic case
reuses an existing synthetic repository fixture. OpenAI cases are small design
excerpts informed by the official [reasoning guide](https://developers.openai.com/api/docs/guides/reasoning)
and [MCP guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp).
They are neither complete provider responses nor live captures. The other cases
exercise canonical-only history, JSON/binary content, and an unknown item.

`test_item_proposal.py` checks schema validity, positive/negative examples,
selected source-to-candidate preservation requirements, tool correlation,
grouping, native JSON null, and byte identity in the sample. These are design
checks, not executed conversions, edge certification, or streaming evidence.

## Promotion gate and unresolved choices

1. Exercise the design against Responses and Gemini Interactions, with complete
   request, response, and SSE fixtures; keep provider provenance explicit.
2. Settle source grouping, reasoning replay/summary representation, hosted-tool
   payloads, item identity and lifecycle rules, and approval scope. In particular,
   the simple reasoning summary string cannot yet represent every provider
   summary block or annotation.
3. Define item-addressed events, JSON/binary/citation deltas, partial/failure
   behavior, and fold parity before shipping any new production part.
4. Implement dated forward/reverse migration edges. Flattening items into the
   old single message must report lost identity, phase, grouping, and ordering
   semantics; an empty loss report is not acceptable when data disappears.
5. Define convenience accessors and replay behavior, validate extension schemas,
   then qualify provider conversion and runtime support separately.

See [the work plan](../../../docs/plans/core-modernization.md) for the remaining
catalog, fidelity, provider, and enterprise-platform work.
