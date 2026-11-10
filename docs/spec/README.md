---
icon: lucide/file-check
---

# Spec

[`spec/`](https://github.com/ocarinow/ocai/tree/main/spec) is the
language-neutral source of truth. Every library consumes the same normative
documents, JSON Schema, and golden fixtures; if an implementation drifts, its
conformance suite fails, and CI re-runs every language suite whenever
`spec/**` changes. The files live next to the code rather than in this site
so that fixtures and schemas are versioned with the implementations that
must pass them.

| Part | What it holds |
|---|---|
| [`canonical-json.md`](https://github.com/ocarinow/ocai/blob/main/spec/canonical-json.md) | **Normative.** The canonical JSON form and the `semantic_equal` predicate every port must implement first. |
| [`schema/`](https://github.com/ocarinow/ocai/tree/main/spec/schema) | JSON Schema per core contract and capability IR shape (`chat.request`, `chat.response`, `chat.chunk`, parts, deltas, usage, finish, stream end). |
| [`fixtures/`](https://github.com/ocarinow/ocai/tree/main/spec/fixtures) | Golden fixtures: one per conversion edge, fold triples per streaming edge, canonical documents, and the unknown-X vectors for total decode. |
| [`extensions/`](https://github.com/ocarinow/ocai/tree/main/spec/extensions) | The extension census: one schema per registered extension key. An unregistered key fails CI. |
| [`interfaces/`](https://github.com/ocarinow/ocai/tree/main/spec/interfaces) | Catalog descriptors as data, one per `(provider, interface)`. |
| [`proposals/`](https://github.com/ocarinow/ocai/tree/main/spec/proposals) | Draft contracts under design (the ordered-item candidate, [ADR 0003](../decisions/0003-ordered-item-modernization.md)). Schema-tested, not registered runtime revisions. |

The fixture shapes and the conformance obligations are stated in
[`spec/README.md`](https://github.com/ocarinow/ocai/blob/main/spec/README.md).
The provider wire research that informs the canonical IR is in
[Providers](../providers/README.md).
