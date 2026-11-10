# ocai roadmap

**Current direction (November 2026):** implement the Python
[governed gateway program](gateway-readiness.md), following merged WU-17–20.
The release gate remains [ADR 0005](../decisions/0005-revised-freeze-gate.md).
The platform vision includes agent execution/management, telemetry, auditing,
evaluation, and typed registries. Other language implementations are deferred.
The July table below preserves completed M1–M3 history; its original horizon
ordering is superseded by the new program.

The implementation roadmap for the July 2026 re-architecture. The structural
contract every WU implements is [`docs/architecture.md`](../architecture.md);
the rules are [`AGENTS.md`](https://github.com/ocarinow/ocai/blob/main/AGENTS.md). **One WU = one session = one PR**
(rule 17). Near-term WUs are fully specified; horizon milestones are one
paragraph each and get detailed only when reached — no pretend-detail a year
out.

Historical July priorities: core machinery first; then **one provider
end-to-end**; providers after the first are pattern replays; the `/responses`
interface and Gemini are horizon items, not the near-term goal.

## Status

| WU | Title | Milestone | File | Status |
|---|---|---|---|---|
| WU-00 | Baseline commit + roadmap replacement | — | [m1](m1-foundations.md) | ✅ done |
| WU-01 | Enforcement becomes executable | — | [m1](m1-foundations.md) | ✅ |
| WU-02 | spec/schema regeneration I (message/parts/request) | M1 | [m1](m1-foundations.md) | ✅ |
| WU-03 | spec/schema regeneration II (response/finish/usage) | M1 | [m1](m1-foundations.md) | ✅ |
| WU-04 | `EdgeContract.certify` | M1 | [m1](m1-foundations.md) | ✅ |
| WU-05 | Unknown-X fixture vocabulary | M1 | [m1](m1-foundations.md) | ✅ |
| WU-05b | Backbone corrections from the capability stress-test (vocab hoist, ProviderRef.scope, SourceRef.mime_type, census token, facade rename, §11) | M1 | [m1](m1-foundations.md) | ✅ |
| WU-05a | API shape correction: `model` off `ChatRequest`; two front doors (§3.4) | M1 | [m1](m1-foundations.md) | ✅ |
| WU-06 | OpenAI chat_completions unary certification | M1 | [m1](m1-foundations.md) | ✅ |
| WU-07 | Facade unary lifecycle — **M1** | M1 | [m1](m1-foundations.md) | ✅ **M1** |
| WU-08 | Fold law hardening + streaming spec shapes | M2 | [m2](m2-streaming.md) | ✅ |
| WU-09 | Stream conversion joins the graph | M2 | [m2](m2-streaming.md) | ✅ |
| WU-10 | OpenAI streaming codec + fold triples | M2 | [m2](m2-streaming.md) | ✅ |
| WU-11 | Facade streaming — **M2** | M2 | [m2](m2-streaming.md) | ✅ **M2** |
| WU-12 | Profile gate | M2 | [m2](m2-streaming.md) | ✅ |
| WU-13 | Anthropic messages unary certification | M3 | [m3](m3-second-provider.md) | ✅ |
| WU-14a | Anthropic unary e2e (the pattern proof) | M3 | [m3](m3-second-provider.md) | ✅ |
| WU-14b | Anthropic streaming e2e — **M3** | M3 | [m3](m3-second-provider.md) | ✅ **M3** |
| WU-15 | Cross-conversion fidelity proof (flagship demo #1) | M3 | [m3](m3-second-provider.md) | ✅ |
| WU-16 | Front doors wired end-to-end: `ocai.chat.model()` + plugin helper + discovery; Workspace removed | M3 | [m3](m3-second-provider.md) | ✅ |
| WU-17 | Architecture/status refresh and release gates | Modernization | [modernization](core-modernization.md) | ✅ complete |
| WU-18 | Independent conversion-plugin repair | Modernization | [modernization](core-modernization.md) | ✅ Complete |
| WU-19 | Ordered-item schema proposal (no runtime migration) | Modernization | [modernization](core-modernization.md) | ✅ Complete |
| WU-20 | Catalog composition and external conformance | Modernization | [WU-20](wu-20-catalog-conformance.md) | ✅ Complete |
| WU-21 | Define the gateway readiness program | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-22 | Isolate transport credentials | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-23 | Propagate context and enforce deadlines | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-24 | Own and terminate streams explicitly | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-25 | Govern streaming through port middleware | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-26 | Emit correlated passive lifecycle events | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-27 | Expose immutable execution inspection | Gateway | [gateway](gateway-readiness.md) | ⬜ Planned |
| WU-28 | Enforce request and response fidelity policy | Gateway | [gateway](gateway-readiness.md) | ⬜ Planned |
| WU-29 | Qualify client request decoding | Gateway | [gateway](gateway-readiness.md) | ⬜ Planned |
| WU-30 | Encode canonical client responses | Gateway | [gateway](gateway-readiness.md) | ⬜ Planned |
| WU-31 | Encode canonical client stream events | Gateway | [gateway](gateway-readiness.md) | ⬜ Planned |
| WU-32 | Prove governed gateway paths | Gateway | [gateway](gateway-readiness.md) | ⬜ Planned |
| H1–H7 | Historical horizon scope; reordered by modernization | — | [horizon](horizon.md) | Superseded order |

## Milestones

- **M1 — one provider end-to-end (unary):** `WireChatModel.chat/achat` returns a
  `CallResult` with a real two-leg `FidelityReport` on a recorded OpenAI wire
  pair. Critical path: WU-00 → 02 → 03 → 06 → 07 (WU-04 parallel, needed before
  06). ~5–6 serial sessions; everything below the facade already exists.
- **M2 — streaming with honesty parity:** the fold law demonstrated at the port
  (`fold(model.stream(req)) == model.chat(req).value` on a paired recording).
- **M3 — the second provider + the proofs:** Anthropic end-to-end with **zero
  facade changes** (the pattern-replay claim, tested), and the cross-conversion
  fidelity report demo.

## Session tracks (what can run in parallel)

```
Track A (spine):        00 → 02 → 03 → 06 → 07 → 11 → 12
Track B (enforcement):  01                    (anytime after 00)
Track C (harness):      04, 05                (after 00/02)
Track D (streaming):    08 → 10 ┐             (08, 09 independent of each other)
                        09 ─────┴→ 11
Track E (anthropic):    13 → 14a → 14b        (13 needs 02/03/04)
Track F (proof):        15 (needs 06+13), 16 (needs 07)
```

Strictly ordered: 02→03, 06→07, {07,09,10}→11, 13→14a→14b. Everything else
floats. Fold law (Track D) deliberately lands *after* the unary spine: unary
needs no fold machinery, the files are disjoint, and no new part types are
introduced on the unary path, so the streaming-first ratchet is not violated.

## How to work a session

1. Pick the first unchecked WU whose dependencies are ✅ (prefer Track A).
2. Read its entry in the milestone file + the architecture.md sections it cites.
3. Implement only that WU; add the tests/fixtures its done-criteria name.
4. `uv run python scripts/check.py` — report results.
5. Check the WU off here and in the milestone file; update any architecture.md
   section the change affected (blueprint law: they must not drift).

Kernel gaps found by consumers (satellites, spikes, ports): [`gaps.md`](gaps.md).
Archived pre-rearchitecture plans: [`archive/`](archive/README.md).
