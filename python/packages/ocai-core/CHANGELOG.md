# Changelog — ocai

All notable changes to the `ocai` distribution. Generated from the change files in
`.changeset/` by the release workflow (ADR 0010); do not edit released sections by hand.
## 0.1.2 (2026-11-11)

### Features

#### Add a sans-io Amazon EventStream parser with typed frames, CRC validation,

explicit local frame limits and preserved prefix evidence on framing failure.
Provide a public StreamFraming factory; semantic Bedrock streaming remains
separate and disabled until its conversion/evidence path is qualified (WU-49).

#### Preserve response identity through canonical streams

Add optional streamed ResponseInfo, detached partial accumulation and reported
conflict/malformed evidence. OpenAI and Anthropic fold comparisons now include
response identity; client stream conversion reports unsupported source metadata.
(WU-46a, #101)

#### Preserve native HTTP failures for reusable host classification

Expose detached response headers and bytes on ocai errors and allow optional host
mappers to classify failures before retry policies, across sync/async unary and
streaming. Prepared calls validate mapping configuration; observers omit response
payloads and headers. No new dependency. (WU-48a, #112)

#### Account for host effects in the existing fidelity report

Add HostEffectReport and an optional hosts lane to FidelityReport. Aggregate
findings and fidelity policies include host field losses and semantic shifts while
graph paths remain unchanged. Empty host lanes preserve existing report wire forms.
This adds the vocabulary; automatic host emission follows separately. (WU-48b, #114)

#### Preserve governed host response evidence through public execution

Add unary HostResponseAdapter declarations, public driver response envelopes and
HostEvidence on results. Inspect declared host effects, validate preparation and
retain usage/fidelity on rejection without provider-specific kernel code. Selected
unary-only adapters reject streaming before I/O. (WU-48c, #116)

### Fixes

#### Add an explicit Bedrock InvokeModel host for Anthropic unary calls, native errors,

and governed host metadata/guardrail effects through public ocai contracts. Keep
AWS authentication in ocai-aws and semantic conversion in ocai-anthropic (WU-48).

Strengthen package boundary checks for the independent cloud service adapter;
no kernel runtime or canonical contract changes.

#### Add offline packaging-gate coverage for credential and service-host distribution

roles while retaining codec and shared package requirements. No kernel runtime
or public contract change (WU-47a).

#### Authenticate explicit AWS requests through the existing credential contract

Add SigV4Credential backed by AWS-maintained signing, with per-attempt request
isolation and no SDK objects in the public API. The AWS dependency stays in the
external ocai-aws package; core dependencies are unchanged. (WU-47, #106)

Extend the import-contract regression count for the explicit credential boundary;
no kernel runtime or dependency change.

## 0.1.1 (2026-11-11)

### Features

#### Compose explicit host endpoints and profile aliases

Compose explicit host endpoints and profile aliases. (WU-38, #35)

#### Select stream framing independently of semantic conversion

Select stream framing independently of semantic conversion. (WU-39, #69)

#### Validate and preserve canonical URL citations

Validate and preserve canonical URL citations. (WU-40, #77)

#### Admit provider-executed server-tool definitions with honest support reports

Admit provider-executed server-tool definitions with honest support reports. (WU-41, #80)

#### Preserve scoped request and replay anchors

Preserve scoped request and replay anchors. (WU-42, #83)

#### Qualify basic Anthropic web search with replay and measured accounting

Qualify basic Anthropic web search with replay and measured accounting. (WU-43, #87)

### Fixes

#### Package metadata points at the real repository and the DeepSeek plugin has an extra

Homepage, Source, Documentation and Changelog URLs now point at `github.com/ocarinow/ocai` and the docs site. `ocai[deepseek]` installs the DeepSeek plugin and `ocai[all]` includes it. No runtime behavior changed.
