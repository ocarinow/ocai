# `ocai.aws` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.aws`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-aws/src/ocai/aws/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-aws-sigv4credential"></span>`SigV4Credential` | [`ocai.aws.credentials.SigV4Credential`](ocai-aws.md#ocai-aws-credentials-sigv4credential) |

## `ocai.aws.credentials`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-aws/src/ocai/aws/credentials.py)

### `SigV4Credential` { #ocai-aws-credentials-sigv4credential }

```python
class SigV4Credential
```

````text
Sign a serialized request with explicit AWS credentials using AWS CRT.

No default chain, environment, profile, network client or token refresh is
used. The default service is Bedrock; region must be supplied explicitly.
General SigV4 header signing is supported, not S3-specific signing, SigV4a,
presigned URLs or streamed request bodies. Response streaming is supported.
````

#### `SigV4Credential.__init__` { #ocai-aws-credentials-sigv4credential---init-- }

```python
def __init__(self, access_key: str, secret_key: str, *, region: str, session_token: str | None=None, service: str='bedrock', clock: Callable[[], datetime]=_now) -> None
```

````text
Create a credential without discovering or retrieving any secrets.

Args:
    access_key: Explicit AWS access key identifier.
    secret_key: Explicit AWS secret access key.
    region: Region used in the signature scope.
    session_token: Optional explicit temporary session token.
    service: AWS signing service name; defaults to bedrock.
    clock: Aware UTC-compatible time source, read once per attempt.

Raises:
    CredentialError: If inputs are empty or SDK initialization fails.
````

#### `SigV4Credential.apply` { #ocai-aws-credentials-sigv4credential-apply }

```python
def apply(self, request: HttpRequest) -> None
```

````text
Sign a private SDK request, then copy its headers to the transport copy.

The drivers must supply their independent transport request. Authentication
headers are replaced on repeated application; request body, URL, timeout,
attempt and governance context are not modified or passed to the SDK.

Args:
    request: The detached, fully serialized transport request.

Raises:
    CredentialError: If the URL, clock or signing operation is invalid.
````
