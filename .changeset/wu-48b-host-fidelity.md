---
ocai: minor
---

#### Account for host effects in the existing fidelity report

Add HostEffectReport and an optional hosts lane to FidelityReport. Aggregate
findings and fidelity policies include host field losses and semantic shifts while
graph paths remain unchanged. Empty host lanes preserve existing report wire forms.
This adds the vocabulary; automatic host emission follows separately. (WU-48b, #114)
