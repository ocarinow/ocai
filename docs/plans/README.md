# ocai roadmap

**Current direction (November 2026):** the Python
[governed gateway program](gateway-readiness.md) is merged, following WU-17–20;
see the [integration guide](../gateway-integration.md). The proposed
[tier 1–2 integration program](integration-program.md) sequences host foundations,
chat completeness, provider qualification and the first telemetry/cost libraries.
Its plan must merge before implementation; each WU then branches from current
main and waits for review and merge before the next starts.
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
| WU-27 | Expose immutable execution inspection | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-28 | Enforce request and response fidelity policy | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-29 | Qualify client request decoding | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-30 | Encode canonical client responses | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-31 | Encode canonical client stream events | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-32 | Prove governed gateway paths | Gateway | [gateway](gateway-readiness.md) | ✅ Complete |
| WU-33 | Publish the platform and gateway design | Platform design | [platform design](platform-design.md) | ✅ Complete |
| WU-34 | Define the first MVP implementation slice | Platform MVP | [MVP](platform-mvp.md) | ✅ Complete |
| WU-35 | Connect the console through reusable platform layers | Platform MVP | [MVP](platform-mvp.md) | ✅ Complete |
| WU-36 | Define the tier 1–2 integration program | Integration | [integration](integration-program.md) | ✅ Complete (plan) |
| WU-37 | Declare host-specific dialect versions | Integration | [integration](integration-program.md) | ✅ Complete (PR #30 merged) |
| WU-38 | Compose explicit host endpoints and profiles | Integration | [integration](integration-program.md) | ✅ Complete (review pending) |
| WU-39 | Select framing independently of semantic conversion | Integration | [integration](integration-program.md) | ✅ Complete (review pending; stacked on WU-38) |
| WU-40 | Qualify URL citations on canonical text | Integration | [integration](integration-program.md) | ✅ |
| WU-41 | Admit server-tool definitions on ChatRequest | Integration | [integration](integration-program.md) | ✅ |
| WU-42 | Preserve required server-tool replay anchors | Integration | [integration](integration-program.md) | ✅ |
| WU-43 | Account for provider-executed search requests | Integration | [integration](integration-program.md) | ✅ |
| WU-44a | Declare the DeepSeek compatible interface variant | Integration | [integration](integration-program.md) | ✅ |
| WU-44b | Certify the DeepSeek compatible dialect variant | Integration | [integration](integration-program.md) | ✅ Complete (review pending; PR #91) |
| WU-45 | Qualify DeepSeek unary execution | Integration | [integration](integration-program.md) | ✅ Complete (review pending; PR #99) |
| WU-46a | Preserve response identity through canonical streams ([PR #101](https://github.com/ocarinow/ocai/pull/101)) | Integration | [integration](integration-program.md) | ✅ |
| WU-46 | Qualify DeepSeek streaming ([#100](https://github.com/ocarinow/ocai/pull/100)) | Integration | [integration](integration-program.md) | ✅ |
| WU-47a | Validate credential and host distribution roles | Integration | [integration](integration-program.md) | ⬜ |
| WU-47 | Sign independent transport attempts with SigV4 | Integration | [integration](integration-program.md) | ⬜ |
| WU-48 | Host Anthropic unary calls on Bedrock InvokeModel | Integration | [integration](integration-program.md) | ⬜ |
| WU-49 | Parse AWS EventStream without I/O | Integration | [integration](integration-program.md) | ⬜ |
| WU-50 | Stream Anthropic through Bedrock envelopes | Integration | [integration](integration-program.md) | ⬜ |
| WU-51 | Declare the Bedrock Converse interface | Integration | [integration](integration-program.md) | ⬜ |
| WU-52 | Certify Converse unary conversion | Integration | [integration](integration-program.md) | ⬜ |
| WU-53 | Execute Converse unary through public APIs | Integration | [integration](integration-program.md) | ⬜ |
| WU-54 | Certify Converse streaming conversion | Integration | [integration](integration-program.md) | ⬜ |
| WU-55 | Host Chat Completions on Azure v1 | Integration | [integration](integration-program.md) | ⬜ |
| WU-56 | Preserve Azure content-filter evidence in streams | Integration | [integration](integration-program.md) | ⬜ |
| WU-57 | Honor Azure millisecond retry hints | Integration | [integration](integration-program.md) | ⬜ |
| WU-58 | Qualify vLLM as an existing-codec host | Integration | [integration](integration-program.md) | ⬜ |
| WU-59 | Distinguish exhausted credit from authentication failure | Integration | [integration](integration-program.md) | ⬜ |
| WU-60 | Qualify OpenRouter as an existing-codec host | Integration | [integration](integration-program.md) | ⬜ |
| WU-61 | Carry inbound trace context explicitly | Integration | [integration](integration-program.md) | ⬜ |
| WU-62 | Observe stream progress and terminal evidence | Integration | [integration](integration-program.md) | ⬜ |
| WU-63 | Export metadata through the first OTel satellite | Integration | [integration](integration-program.md) | ⬜ |
| WU-64 | Load model descriptors as attributable profile data | Integration | [integration](integration-program.md) | ⬜ |
| WU-65 | Refresh model facts into reviewable diffs | Integration | [integration](integration-program.md) | ⬜ |
| WU-66 | Name cache-write consumption explicitly | Integration | [integration](integration-program.md) | ⬜ |
| WU-67 | Add a request-level cache hint without replacing CacheConfig | Integration | [integration](integration-program.md) | ⬜ |
| WU-68 | Execute Anthropic prompt-cache intent honestly | Integration | [integration](integration-program.md) | ⬜ |
| WU-69 | Price measured usage in a cost satellite | Integration | [integration](integration-program.md) | ⬜ |
| WU-70 | Pace requests from measured rate-limit signals | Integration | [integration](integration-program.md) | ⬜ |
| WU-71 | Record platform identity and access design | Platform MVP | [MVP](platform-mvp.md) | ✅ Complete (documentation; review pending) |
| WU-72 | Define the authenticated console program | Platform identity | [identity](platform-identity.md) | ✅ Complete (plan; review pending) |
| WU-73 | Persist organization identity and transactional audit | Platform identity | [identity](platform-identity.md) | ✅ Complete (implementation; review pending) |
| WU-74 | Authenticate API callers through the reference issuer | Platform identity | [identity](platform-identity.md) | ✅ |
| WU-75 | Bootstrap an organization with synchronized access | Platform identity | [identity](platform-identity.md) | ✅ Complete (implementation; review pending) |
| WU-76 | Establish durable OIDC console sessions | Platform identity | [identity](platform-identity.md) | ⬜ |
| WU-77 | Update an organization through the authenticated console | Platform identity | [identity](platform-identity.md) | ⬜ |
| WU-78 | Administer owned service-account principals | Platform identity | [identity](platform-identity.md) | ⬜ |
| WU-79 | Bind OAuth workloads to service accounts | Platform identity | [identity](platform-identity.md) | ⬜ |
| WU-80 | Issue and revoke scoped platform API keys | Platform identity | [identity](platform-identity.md) | ⬜ |
| WU-81 | Integrate the full shadcn-vue component layer | Platform identity | [identity](platform-identity.md) | ✅ |
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
