---
ocai: minor
ocai-openai: minor
ocai-anthropic: minor
---

#### Preserve response identity through canonical streams

Add optional streamed ResponseInfo, detached partial accumulation and reported
conflict/malformed evidence. OpenAI and Anthropic fold comparisons now include
response identity; client stream conversion reports unsupported source metadata.
(WU-46a, #101)
