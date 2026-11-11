# ocai-aws

Explicit AWS authentication for ocai, independent of Bedrock or model codecs.
`SigV4Credential` delegates signing to AWS-maintained `awscrt`; it does not
implement cryptography or construct an AWS service client.

```python
from ocai.aws import SigV4Credential

credential = SigV4Credential(
    access_key="synthetic-access-key",
    secret_key="synthetic-secret-key",
    session_token="synthetic-session-token",  # omit for long-lived keys
    region="us-east-1",
)
```

Pass the credential to the existing model/binding composition API. The driver
applies it to its detached transport request after policies, once per attempt.
Body bytes and effective headers are signed. SDK requests contain no CallContext.
The region is explicit; the default signing service is `bedrock`.

There is no environment/profile discovery, IMDS, STS call or automatic refresh.
Supply updated credentials explicitly when required. Aware `clock` injection
supports reproducible offline verification; the default reads current UTC on
every attempt. Representations redact access keys, secret keys and session tokens;
signing failures have generic messages without SDK exception chaining.

The kernel has no AWS dependency. Installing this external package installs the
AWS CRT native runtime; use a platform with an upstream wheel or its supported
build toolchain. ocai never enables native SDK diagnostic logging. Applications
must treat any explicitly enabled upstream diagnostic logging as sensitive.

Qualified scope: SigV4 header signing with normalized/double-encoded paths,
queries, headers, fixed byte bodies, optional session tokens and per-attempt
signing. No unsigned-payload mode, presigned URL, SigV4a, S3-specific path rules
or streamed request body. Response streaming does not change request signing.
Bedrock hosts and semantic codecs are separate packages/WUs.

Published AWS signing vectors and recorded HTTP attempts test the actual SDK,
without live credentials or SDK mocks.
