# 0016 — Delegate authentication within external provider packages

- **Status:** accepted direction; WU-47 implementation for review
- **Date:** 2026-11-11
- **Deciders:** maintainer

## Context

The integration program originally proposed implementing SigV4 with stdlib
cryptography. The maintainer rejected rebuilding provider authentication and
required maintained provider libraries in the relevant external packages, while
keeping third-party additions out of core unless explicitly approved.

## Decision

Delegate authentication to provider-maintained libraries behind the existing
Credential seam. WU-47 uses AWS CRT Python (`awscrt`) in `ocai-aws`; AWS owns
canonicalization, signing and cryptography. ocai adapts the detached serialized
request and supplies explicit credentials, region, service and attempt time.
It never creates an SDK client or invokes a discovery chain.

Dependencies remain local to the external package. Core contracts, runtime and
wire acquire no new dependency or reverse import. Separate cloud access from
service hosting and model dialect conversion: `ocai-aws` never imports Bedrock;
a Bedrock host can be composed with its credential by the application. The same
principle applies to future Google authentication, Vertex hosting and Gemini
conversion packages. This ADR does not implement those packages or approve any
non-chat canonical interface design.

Users install the ocai provider package; its SDK dependency installs transitively.
They never import SDK clients, sessions, credentials or exceptions. Public APIs
accept ocai types and plain configuration values; SDK objects remain private.
The driver invokes existing contracts without provider-specific branches. A
missing capability becomes a separately reviewed reusable contract gap.

AI SDK clients remain excluded from conversion and execution: ocai owns the wire
and per-edge fidelity. Explicit credential sourcing, per-attempt leaf application,
redacted representations, and hook/observer isolation remain unchanged. Sanitize
signer failures without retaining secret-bearing exception messages in public
results. Do not enable SDK diagnostic payload logging.

## Alternatives considered

- Implement SigV4 locally: rejected by the maintainer; it duplicates mature
  authentication code and its security maintenance.
- Install cloud SDKs in core: rejected; applications that use another provider
  must not acquire these dependencies.
- Use an AI SDK client for Bedrock execution: outside the authentication exception
  and would bypass ocai's owned transport/conversion evidence.
- Use botocore's broad SDK foundation: also maintained by AWS, but AWS CRT offers
  a focused signing entry point and explicit signing date for deterministic tests.

## Consequences

The auth adapter has a binary AWS runtime dependency. Supported Python/platform
wheels and strict typing at its boundary are verified in WU-47; a new platform
requires checking upstream availability. Fixed-clock tests execute the actual
signer against published vectors; HTTP tests replay recordings, never SDK mocks.
No frozen-candidate shape changes. This supersedes the stdlib-only WU-47
implementation choice, not the kernel's zero-dependency contract.
