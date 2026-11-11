---
ocai: minor
---

#### Preserve governed host response evidence through public execution

Add unary HostResponseAdapter declarations, public driver response envelopes and
HostEvidence on results. Inspect declared host effects, validate preparation and
retain usage/fidelity on rejection without provider-specific kernel code. Selected
unary-only adapters reject streaming before I/O. (WU-48c, #116)
