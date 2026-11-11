---
ocai-bedrock: minor
ocai: patch
---

Add an explicit Bedrock InvokeModel host for Anthropic unary calls, native errors,
and governed host metadata/guardrail effects through public ocai contracts. Keep
AWS authentication in ocai-aws and semantic conversion in ocai-anthropic (WU-48).

Strengthen package boundary checks for the independent cloud service adapter;
no kernel runtime or canonical contract changes.
