---
ocai: minor
---

Add a sans-io Amazon EventStream parser with typed frames, CRC validation,
explicit local frame limits and preserved prefix evidence on framing failure.
Provide a public StreamFraming factory; semantic Bedrock streaming remains
separate and disabled until its conversion/evidence path is qualified (WU-49).
