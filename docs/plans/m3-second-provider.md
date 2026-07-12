# M3 — The second provider and the proofs

Goal: Anthropic end-to-end **with zero changes to `ocai/chat/facade.py`** (the
pattern-replay claim, tested), plus the cross-conversion fidelity report demo
— flagship demo #1. Architecture refs: §7 (plugin shape), §8 (lifecycle), §2.2
(SemanticShift), §2.4 (ProviderRef crossing rule).

---

## WU-13 — Anthropic messages unary certification

- **Scope:** pattern replay of WU-06. `spec/fixtures/anthropic/messages/` —
  ≥5 fixtures: system-hoist with declared `SemanticShift(relocation)`; tool
  round; required `max_tokens` injection (+ shift); out-of-range APPROXIMATED
  per the WU-06 census-upper-bound decision; extensions sweep incl. the
  `cache_creation_input_tokens` dimension decision (codec.py:232). Census
  truth-up in `edges.py`; new
  `python/packages/ocai-anthropic/tests/test_conformance.py`; anthropic
  unknown-X vectors.
- **Done:** ocai-anthropic suite collected and green; `certify_edge` returns
  `[]`; the system hoist appears in `expect_shifts` and matches runtime;
  fixtures validate against schemas; ruff clean.
- **Deps:** WU-02/03/04 (hard); WU-06 (pattern, soft). Parallel with M2.

## WU-14a — Anthropic unary end-to-end (the pattern proof)

- **Scope:** extend `tests/http/anthropic_messages.json` with tool-call and
  error pairs; facade unary tests for anthropic mirroring
  `test_facade_unary.py`.
- **Done:** chat/achat e2e green **with zero changes to
  `ocai/chat/facade.py`** — assert the pattern holds; this is the "adding
  providers follows the same pattern" proof. pytest green.
- **Deps:** WU-07, WU-13.

## WU-14b — Anthropic streaming end-to-end — **MILESTONE M3**

- **Scope:** close anthropic streaming TODOs: fold `message_delta`
  usage/finish into the terminal STREAM_STOP (codec.py:1007); typed mid-stream
  error shape — canonical code + native + detail (codec.py:925). ≥3 anthropic
  fold triples in `spec/fixtures/anthropic/messages/streams/`; facade stream
  e2e.
- **Done:** `check_fold_triples` green; fold-equals-unary on a paired recorded
  exchange; pytest green.
- **Deps:** WU-11, WU-14a.

## WU-15 — Cross-conversion fidelity proof (flagship demo #1)

- **Scope:** pure `ocai.convert`, **no wire needed** (can land before WU-14):
  convert a recorded openai/chat_completions request → canonical →
  anthropic/messages, and a response leg in reverse, via two-hop planning
  through the canonical backbone. `spec/fixtures/cross/` pinning the
  expectation. A runnable example (docs snippet or `examples/`) that prints
  the `FidelityReport` — the system hoist shift, tool-id regeneration, the
  `is_error` drop. Test that a `ProviderRef` crossing `(provider, interface)`
  is UNSUPPORTED-and-reported (§2.4).
- **Done:** `tests/test_cross_conversion.py` asserts the planner chose the
  2-hop path, the merged per-edge report contents, and `semantic_equal`
  against the cross fixture; the example's printed report is asserted in a
  test; pytest green.
- **Deps:** WU-06 + WU-13 only.

## WU-16 — The front doors wired end-to-end (§3.4)

Maintainer-refined design (2026-07-13): TWO equivalent doors, neither forced —
the core string door for data-driven switching, and the plugin helper as
sanctioned sugar over the same machinery. Installing a provider dist has
exactly one structural effect: graph augmentation. No framework containers.

- **Scope:** (1) NEW `ocai.chat.model(provider, model_name, *, credentials,
  host=None, catalog=None, transport=None, interceptors=())` per §3.4 —
  resolves against the discovered default catalog (or an explicit one), builds
  the codec via the fragment's component factory, composes the `Binding`
  internally (`Direct` from the fragment's first-party endpoint data), returns
  a `ChatModel` bound to `model_name`. Lives in `ocai/chat/__init__.py` (the
  facade module is `chat/facade.py` — never shares the factory's name).
  (2) Move first-party endpoint data (base URL) into the fragment (extend
  `DialectTraits` or the `Component` descriptor — decide in-WU) so the core
  door never imports a plugin. (3) WIRE the plugin `chat_model()` helpers
  (currently NotImplementedError stubs) as thin wrappers over the exact same
  fragment + facade path — deferred imports per the documented seam.
  (4) DELETE the `Workspace` class from `ocai/runtime/binding.py` (keep
  `Binding` + `validate()`; scrub Workspace from runtime docstrings and the
  catalog.py docstring). (5) `ocai/runtime/dual.py` — `from_sync`/`from_async`.
  (6) `Catalog.discover()` integration test (entry points already declared).
- **Done:** the §3.4 five-liner works end-to-end on a recorded pair with zero
  provider imports; `ocai.openai.chat_model("gpt-5", credentials=...)` returns
  the identical composition (asserted); grep proves no `Workspace` remains;
  dual adapters pass sync↔async round-trips; the discovery test composes both
  installed fragments; pytest green.
- **Deps:** WU-07 (facade); pull EARLY — right after WU-07 — so examples and
  tests teach the real doors from the start.
