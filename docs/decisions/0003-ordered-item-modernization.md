# 0003 — Ordered-item modernization before the next contract freeze

- **Status:** proposed
- **Date:** 2026-11-10
- **Deciders:** maintainer review pending for the candidate shape

## Context

The platform needs replayable interactions and honest conversion reports.
A single response message cannot retain multiple message identities, phases,
and interleaved actions without hiding their structure in extensions.

## Proposed decision

Exercise a shared ordered-item vocabulary for request history and responses.
Distinguish message content from reasoning, calls, results, and approvals;
preserve native message grouping as well as order. Keep the candidate under
`spec/proposals/ordered-items` and retain the active `2026-07` runtime revision.

## Alternatives considered

Keeping one message loses boundaries. A messages-only array still hides tool
and approval interleavings. Replacing runtime contracts immediately would
precede the necessary migration and streaming evidence.

## Consequences

The proposal has schema tests and synthetic fixtures, not implemented
conversion or replay. Promotion requires dated migration edges with explicit
losses, item-addressed streaming, fold parity, and provider-backed evidence.
Reasoning representation, grouping, evidence/resources, and approval scope
remain open. Enterprise services consume the kernel through separate libraries.

See [the proposal](https://github.com/ocarinow/ocai/blob/main/spec/proposals/ordered-items/README.md) and
[the work plan](../plans/core-modernization.md).
