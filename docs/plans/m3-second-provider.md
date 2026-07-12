# M3 — The second provider and the proofs

Goal: Anthropic end-to-end **with zero changes to `ocai/chat/model.py`** (the
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
  `ocai/chat/model.py`** — assert the pattern holds; this is the "adding
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

## WU-16 — Composition ergonomics

- **Scope:** `ocai/runtime/binding.py` — `Workspace.chat` (resolve + facade
  construction + `CallInterceptor` chain application);
  `ocai/runtime/dual.py` — `from_sync`/`from_async`; plugin pyprojects declare
  the `ocai.fragments` entry points (already configured — verify) and add a
  `Catalog.discover()` integration test; `Binding.validate` mismatch coverage.
- **Done:** `Workspace.chat` returns a `CallResult` through a bound provider
  with a test interceptor observing the call; dual adapters pass sync↔async
  port round-trips; `Catalog.discover()` composes installed fragments in a
  test; pytest green.
- **Deps:** WU-07 (facade); the dual/discover halves float freely.
