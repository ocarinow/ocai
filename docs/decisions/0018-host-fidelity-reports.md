# 0018 — Keep host effects separate from conversion edges

- **Status:** accepted; corresponding implementation merged on main
- **Date:** 2026-11-11
- **Deciders:** maintainer

## Context

The approved reusable host outcome remediation must report effects such as output
masking without pretending the codec caused them. Current EdgeReport requires
source/destination graph nodes. Host execution is not another semantic interface;
creating an identity edge merely to hold an effect would misstate the route.

## Decision

Add core HostEffectReport(host, adapter, contract_id, phase, losses, shifts) and a
keyword-only hosts list on FidelityReport. Host, adapter and contract_id identify
the effect producer and its declaration; phase is an open code, initially request
or response. These are actual findings, never declarations or a qualification
verdict. A later execution WU defines declaration hashing and conformance.

The graph path and edges remain graph-only. Aggregate losses, shifts, dropped,
lossless and diagnostic cost include both lanes. FidelityPolicy evaluates both
lanes through those aggregates, retaining complete evidence and known usage on
rejection. Semantic shifts retain their existing distinction from field loss.
Report order is per-lane insertion order, not a global execution chronology.

Merge appends both lanes; it does not deduplicate equal findings because identical
records can represent separate effects. Producers insert once. Serialization
omits an empty hosts lane, preserving existing report bytes. Deserialization
preserves open phase/shift codes and recomputes derived properties. StreamEnd uses
the same report schema; no new event/part/node or revision is introduced.

## Alternatives considered

A synthetic graph edge gives host effects false conversion provenance. A raw
metadata extension preserves facts but bypasses conversion policy. A second report
on the response would split the user guarantee and require a second policy stack.
A distinct lane in the existing report preserves attribution and policy reuse.

## Boundaries and consequences

This is additive frozen-candidate core vocabulary/schema under ADR 0005. Core
remains stdlib-only. It does not implement response adaptation, streaming transport
metadata, host declaration qualification, or any provider. Those are subsequent
G-14 slices and must be tested before WU-48 can claim host fidelity.

New policies must use the aggregate API; inspecting edges alone intentionally
sees only graph findings. Older readers may ignore the new lane, so an old-reader
round-trip must not serve as approval for a host-effect-bearing execution.
