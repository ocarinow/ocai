# `ocai.core` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

## `ocai.core`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/__init__.py)

Public re-exports resolve to the definitions named below.

| Export | Definition |
|---|---|
| <span id="ocai-core-canonical"></span>`canonical` | [`ocai.core.canonjson.canonical`](ocai-core.md#ocai-core-canonjson-canonical) |
| <span id="ocai-core-semantic-equal"></span>`semantic_equal` | [`ocai.core.canonjson.semantic_equal`](ocai-core.md#ocai-core-canonjson-semantic-equal) |
| <span id="ocai-core-apikey"></span>`ApiKey` | [`ocai.core.credentials.ApiKey`](ocai-core.md#ocai-core-credentials-apikey) |
| <span id="ocai-core-credential"></span>`Credential` | [`ocai.core.credentials.Credential`](ocai-core.md#ocai-core-credentials-credential) |
| <span id="ocai-core-credentialerror"></span>`CredentialError` | [`ocai.core.credentials.CredentialError`](ocai-core.md#ocai-core-credentials-credentialerror) |
| <span id="ocai-core-nocredential"></span>`NoCredential` | [`ocai.core.credentials.NoCredential`](ocai-core.md#ocai-core-credentials-nocredential) |
| <span id="ocai-core-require-credential"></span>`require_credential` | [`ocai.core.credentials.require_credential`](ocai-core.md#ocai-core-credentials-require-credential) |
| <span id="ocai-core-autherror"></span>`AuthError` | [`ocai.core.errors.AuthError`](ocai-core.md#ocai-core-errors-autherror) |
| <span id="ocai-core-contentfiltererror"></span>`ContentFilterError` | [`ocai.core.errors.ContentFilterError`](ocai-core.md#ocai-core-errors-contentfiltererror) |
| <span id="ocai-core-contextlengtherror"></span>`ContextLengthError` | [`ocai.core.errors.ContextLengthError`](ocai-core.md#ocai-core-errors-contextlengtherror) |
| <span id="ocai-core-ocaierror"></span>`OcaiError` | [`ocai.core.errors.OcaiError`](ocai-core.md#ocai-core-errors-ocaierror) |
| <span id="ocai-core-ratelimiterror"></span>`RateLimitError` | [`ocai.core.errors.RateLimitError`](ocai-core.md#ocai-core-errors-ratelimiterror) |
| <span id="ocai-core-transienterror"></span>`TransientError` | [`ocai.core.errors.TransientError`](ocai-core.md#ocai-core-errors-transienterror) |
| <span id="ocai-core-unsupportedfeatureerror"></span>`UnsupportedFeatureError` | [`ocai.core.errors.UnsupportedFeatureError`](ocai-core.md#ocai-core-errors-unsupportedfeatureerror) |
| <span id="ocai-core-error-from-response"></span>`error_from_response` | [`ocai.core.errors.error_from_response`](ocai-core.md#ocai-core-errors-error-from-response) |
| <span id="ocai-core-hostevidence"></span>`HostEvidence` | [`ocai.core.evidence.HostEvidence`](ocai-core.md#ocai-core-evidence-hostevidence) |
| <span id="ocai-core-disposition"></span>`Disposition` | [`ocai.core.fidelity.Disposition`](ocai-core.md#ocai-core-fidelity-disposition) |
| <span id="ocai-core-edgereport"></span>`EdgeReport` | [`ocai.core.fidelity.EdgeReport`](ocai-core.md#ocai-core-fidelity-edgereport) |
| <span id="ocai-core-fidelityreport"></span>`FidelityReport` | [`ocai.core.fidelity.FidelityReport`](ocai-core.md#ocai-core-fidelity-fidelityreport) |
| <span id="ocai-core-fieldloss"></span>`FieldLoss` | [`ocai.core.fidelity.FieldLoss`](ocai-core.md#ocai-core-fidelity-fieldloss) |
| <span id="ocai-core-hosteffectreport"></span>`HostEffectReport` | [`ocai.core.fidelity.HostEffectReport`](ocai-core.md#ocai-core-fidelity-hosteffectreport) |
| <span id="ocai-core-route"></span>`Route` | [`ocai.core.fidelity.Route`](ocai-core.md#ocai-core-fidelity-route) |
| <span id="ocai-core-semanticshift"></span>`SemanticShift` | [`ocai.core.fidelity.SemanticShift`](ocai-core.md#ocai-core-fidelity-semanticshift) |
| <span id="ocai-core-shiftkind"></span>`ShiftKind` | [`ocai.core.fidelity.ShiftKind`](ocai-core.md#ocai-core-fidelity-shiftkind) |
| <span id="ocai-core-detail-registry"></span>`DETAIL_REGISTRY` | [`ocai.core.finish.DETAIL_REGISTRY`](ocai-core.md#ocai-core-finish-detail-registry) |
| <span id="ocai-core-detailopaque"></span>`DetailOpaque` | [`ocai.core.finish.DetailOpaque`](ocai-core.md#ocai-core-finish-detailopaque) |
| <span id="ocai-core-detailtype"></span>`DetailType` | [`ocai.core.finish.DetailType`](ocai-core.md#ocai-core-finish-detailtype) |
| <span id="ocai-core-errordetail"></span>`ErrorDetail` | [`ocai.core.finish.ErrorDetail`](ocai-core.md#ocai-core-finish-errordetail) |
| <span id="ocai-core-finishdetail"></span>`FinishDetail` | [`ocai.core.finish.FinishDetail`](ocai-core.md#ocai-core-finish-finishdetail) |
| <span id="ocai-core-finishinfo"></span>`FinishInfo` | [`ocai.core.finish.FinishInfo`](ocai-core.md#ocai-core-finish-finishinfo) |
| <span id="ocai-core-finishreason"></span>`FinishReason` | [`ocai.core.finish.FinishReason`](ocai-core.md#ocai-core-finish-finishreason) |
| <span id="ocai-core-incompletedetail"></span>`IncompleteDetail` | [`ocai.core.finish.IncompleteDetail`](ocai-core.md#ocai-core-finish-incompletedetail) |
| <span id="ocai-core-refusaldetail"></span>`RefusalDetail` | [`ocai.core.finish.RefusalDetail`](ocai-core.md#ocai-core-finish-refusaldetail) |
| <span id="ocai-core-safetydetail"></span>`SafetyDetail` | [`ocai.core.finish.SafetyDetail`](ocai-core.md#ocai-core-finish-safetydetail) |
| <span id="ocai-core-safetyrating"></span>`SafetyRating` | [`ocai.core.finish.SafetyRating`](ocai-core.md#ocai-core-finish-safetyrating) |
| <span id="ocai-core-cast-detail"></span>`cast_detail` | [`ocai.core.finish.cast_detail`](ocai-core.md#ocai-core-finish-cast-detail) |
| <span id="ocai-core-canonical-interface"></span>`CANONICAL_INTERFACE` | [`ocai.core.identity.CANONICAL_INTERFACE`](ocai-core.md#ocai-core-identity-canonical-interface) |
| <span id="ocai-core-canonical-provider"></span>`CANONICAL_PROVIDER` | [`ocai.core.identity.CANONICAL_PROVIDER`](ocai-core.md#ocai-core-identity-canonical-provider) |
| <span id="ocai-core-canonical-revision"></span>`CANONICAL_REVISION` | [`ocai.core.identity.CANONICAL_REVISION`](ocai-core.md#ocai-core-identity-canonical-revision) |
| <span id="ocai-core-chat"></span>`CHAT` | [`ocai.core.identity.CHAT`](ocai-core.md#ocai-core-identity-chat) |
| <span id="ocai-core-chat-chunk"></span>`CHAT_CHUNK` | [`ocai.core.identity.CHAT_CHUNK`](ocai-core.md#ocai-core-identity-chat-chunk) |
| <span id="ocai-core-chat-request"></span>`CHAT_REQUEST` | [`ocai.core.identity.CHAT_REQUEST`](ocai-core.md#ocai-core-identity-chat-request) |
| <span id="ocai-core-chat-response"></span>`CHAT_RESPONSE` | [`ocai.core.identity.CHAT_RESPONSE`](ocai-core.md#ocai-core-identity-chat-response) |
| <span id="ocai-core-embedding"></span>`EMBEDDING` | [`ocai.core.identity.EMBEDDING`](ocai-core.md#ocai-core-identity-embedding) |
| <span id="ocai-core-vectorstore"></span>`VECTORSTORE` | [`ocai.core.identity.VECTORSTORE`](ocai-core.md#ocai-core-identity-vectorstore) |
| <span id="ocai-core-capability"></span>`Capability` | [`ocai.core.identity.Capability`](ocai-core.md#ocai-core-identity-capability) |
| <span id="ocai-core-nodeid"></span>`NodeId` | [`ocai.core.identity.NodeId`](ocai-core.md#ocai-core-identity-nodeid) |
| <span id="ocai-core-origin"></span>`Origin` | [`ocai.core.identity.Origin`](ocai-core.md#ocai-core-identity-origin) |
| <span id="ocai-core-shape"></span>`Shape` | [`ocai.core.identity.Shape`](ocai-core.md#ocai-core-identity-shape) |
| <span id="ocai-core-status"></span>`Status` | [`ocai.core.identity.Status`](ocai-core.md#ocai-core-identity-status) |
| <span id="ocai-core-canonical-node"></span>`canonical_node` | [`ocai.core.identity.canonical_node`](ocai-core.md#ocai-core-identity-canonical-node) |
| <span id="ocai-core-dataclassproto"></span>`DataClassProto` | [`ocai.core.ir.DataClassProto`](ocai-core.md#ocai-core-ir-dataclassproto) |
| <span id="ocai-core-irobject"></span>`IRObject` | [`ocai.core.ir.IRObject`](ocai-core.md#ocai-core-ir-irobject) |
| <span id="ocai-core-tagregistry"></span>`TagRegistry` | [`ocai.core.ir.TagRegistry`](ocai-core.md#ocai-core-ir-tagregistry) |
| <span id="ocai-core-missing"></span>`MISSING` | [`ocai.core.jsonschema.MISSING`](ocai-core.md#ocai-core-jsonschema-missing) |
| <span id="ocai-core-jsonschema"></span>`JsonSchema` | [`ocai.core.jsonschema.JsonSchema`](ocai-core.md#ocai-core-jsonschema-jsonschema) |
| <span id="ocai-core-schema"></span>`Schema` | [`ocai.core.jsonschema.Schema`](ocai-core.md#ocai-core-jsonschema-schema) |
| <span id="ocai-core-decode-schema"></span>`decode_schema` | [`ocai.core.jsonschema.decode_schema`](ocai-core.md#ocai-core-jsonschema-decode-schema) |
| <span id="ocai-core-encode-schema"></span>`encode_schema` | [`ocai.core.jsonschema.encode_schema`](ocai-core.md#ocai-core-jsonschema-encode-schema) |
| <span id="ocai-core-primitive"></span>`Primitive` | [`ocai.core.primitives.Primitive`](ocai-core.md#ocai-core-primitives-primitive) |
| <span id="ocai-core-value"></span>`Value` | [`ocai.core.primitives.Value`](ocai-core.md#ocai-core-primitives-value) |
| <span id="ocai-core-valuetype"></span>`ValueType` | [`ocai.core.primitives.ValueType`](ocai-core.md#ocai-core-primitives-valuetype) |
| <span id="ocai-core-capabilityprofile"></span>`CapabilityProfile` | [`ocai.core.profile.CapabilityProfile`](ocai-core.md#ocai-core-profile-capabilityprofile) |
| <span id="ocai-core-support"></span>`Support` | [`ocai.core.profile.Support`](ocai-core.md#ocai-core-profile-support) |
| <span id="ocai-core-resolve-support"></span>`resolve_support` | [`ocai.core.profile.resolve_support`](ocai-core.md#ocai-core-profile-resolve-support) |
| <span id="ocai-core-providerref"></span>`ProviderRef` | [`ocai.core.refs.ProviderRef`](ocai-core.md#ocai-core-refs-providerref) |
| <span id="ocai-core-replay"></span>`Replay` | [`ocai.core.refs.Replay`](ocai-core.md#ocai-core-refs-replay) |
| <span id="ocai-core-callcontext"></span>`CallContext` | [`ocai.core.result.CallContext`](ocai-core.md#ocai-core-result-callcontext) |
| <span id="ocai-core-callresult"></span>`CallResult` | [`ocai.core.result.CallResult`](ocai-core.md#ocai-core-result-callresult) |
| <span id="ocai-core-source-registry"></span>`SOURCE_REGISTRY` | [`ocai.core.sources.SOURCE_REGISTRY`](ocai-core.md#ocai-core-sources-source-registry) |
| <span id="ocai-core-source"></span>`Source` | [`ocai.core.sources.Source`](ocai-core.md#ocai-core-sources-source) |
| <span id="ocai-core-sourcebase64"></span>`SourceBase64` | [`ocai.core.sources.SourceBase64`](ocai-core.md#ocai-core-sources-sourcebase64) |
| <span id="ocai-core-sourceref"></span>`SourceRef` | [`ocai.core.sources.SourceRef`](ocai-core.md#ocai-core-sources-sourceref) |
| <span id="ocai-core-sourcetype"></span>`SourceType` | [`ocai.core.sources.SourceType`](ocai-core.md#ocai-core-sources-sourcetype) |
| <span id="ocai-core-sourceunknown"></span>`SourceUnknown` | [`ocai.core.sources.SourceUnknown`](ocai-core.md#ocai-core-sources-sourceunknown) |
| <span id="ocai-core-sourceurl"></span>`SourceUrl` | [`ocai.core.sources.SourceUrl`](ocai-core.md#ocai-core-sources-sourceurl) |
| <span id="ocai-core-cast-source"></span>`cast_source` | [`ocai.core.sources.cast_source`](ocai-core.md#ocai-core-sources-cast-source) |
| <span id="ocai-core-dialecttraits"></span>`DialectTraits` | [`ocai.core.traits.DialectTraits`](ocai-core.md#ocai-core-traits-dialecttraits) |
| <span id="ocai-core-headerbodymapping"></span>`HeaderBodyMapping` | [`ocai.core.traits.HeaderBodyMapping`](ocai-core.md#ocai-core-traits-headerbodymapping) |
| <span id="ocai-core-consumption"></span>`Consumption` | [`ocai.core.usage.Consumption`](ocai-core.md#ocai-core-usage-consumption) |
| <span id="ocai-core-usage"></span>`Usage` | [`ocai.core.usage.Usage`](ocai-core.md#ocai-core-usage-usage) |
| <span id="ocai-core-usagemodality"></span>`UsageModality` | [`ocai.core.usage.UsageModality`](ocai-core.md#ocai-core-usage-usagemodality) |
| <span id="ocai-core-usagesource"></span>`UsageSource` | [`ocai.core.usage.UsageSource`](ocai-core.md#ocai-core-usage-usagesource) |
| <span id="ocai-core-usageunit"></span>`UsageUnit` | [`ocai.core.usage.UsageUnit`](ocai-core.md#ocai-core-usage-usageunit) |

## `ocai.core.canonjson`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/canonjson.py)

### `canonical` { #ocai-core-canonjson-canonical }

```python
def canonical(obj: Any) -> str
```

````text
Serialize `obj` to its one canonical JSON string.

The normative encoding fixtures are compared against: sorted keys,
minimal separators, non-ASCII characters unescaped (NFC-normalized),
integral floats as integers, embedded `*_json` strings preserved
verbatim (rule 5's preserve half).

Args:
    obj: JSON-shaped data, or any object exposing `to_dict`.

Returns:
    The canonical JSON text.

Raises:
    TypeError: If `obj` is not JSON-shaped.
    ValueError: If `obj` contains a non-finite float.
````

### `semantic_equal` { #ocai-core-canonjson-semantic-equal }

```python
def semantic_equal(a: Any, b: Any) -> bool
```

````text
Return whether `a` and `b` are the same document, semantically.

The single equality predicate conformance asserts with: both sides are
normalized under the full rule set — including the parse-compare half of
rule 5, so `{"args_json": "{\\"a\\": 1}"}` equals
`{"args_json": "{\\"a\\":1}"}` — and compared structurally. Absent and
null remain distinct (rule 4).

Args:
    a: One side; JSON-shaped data or an object exposing `to_dict`.
    b: The other side, likewise.

Returns:
    True when the two normalize to the same structure.
````

## `ocai.core.credentials`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/credentials.py)

### `CredentialError` { #ocai-core-credentials-credentialerror }

```python
class CredentialError(OSError)
```

````text
Raised when a credential cannot be supplied or located.

A subclass of `OSError` (not `ocai.core.errors.OcaiError`)
because it is a *configuration* problem at construction time, not a provider
request failure.
````

### `Credential` { #ocai-core-credentials-credential }

```python
class Credential(Protocol)
```

````text
A credential that knows how to authenticate an outgoing request.

Implementations mutate the transport-only request's headers in place
(typically setting an auth header). Drivers copy the request and its mutable
headers first; this object is never the one exposed to hooks. `apply` is
called **once per attempt**, just before send, so
a short-lived/rotating credential can resolve its current value at send time.
Because it is applied at the driver leaf, the secret never enters a policy
hook, an interceptor, the `raw` response, the `FidelityReport`, or logs.
````

#### `Credential.apply` { #ocai-core-credentials-credential-apply }

```python
def apply(self, request: HttpRequest) -> None
```

````text
Inject auth into `request` (an `HttpRequest`) in place.
````

### `NoCredential` { #ocai-core-credentials-nocredential }

```python
class NoCredential
```

````text
Explicit anonymous execution; never discover or inject authentication.
````

#### `NoCredential.apply` { #ocai-core-credentials-nocredential-apply }

```python
def apply(self, request: HttpRequest) -> None
```

````text
Leave the transport request unchanged.
````

### `ApiKey` { #ocai-core-credentials-apikey }

```python
class ApiKey
```

````text
A bearer/API-key credential.

Construct it explicitly — `ApiKey("sk-...")` — or via an opt-in named
source: `ApiKey.from_env("OPENAI_API_KEY")` / `ApiKey.from_file(path)`.
Constructing it with an empty key raises immediately; ocai never treats a
missing key as "anonymous".
````

#### `ApiKey.__init__` { #ocai-core-credentials-apikey---init-- }

```python
def __init__(self, key: str, *, header: str='Authorization', scheme: str='Bearer') -> None
```

````text
Construct a bearer/API-key credential.

Args:
    key: The secret key. Must be a non-empty, non-whitespace string;
        anything else raises immediately.
    header: The request header to set when applying the credential.
        Defaults to `"Authorization"`.
    scheme: The auth scheme prefix written before the key (e.g.
        `"Bearer <key>"`). Pass an empty string to send the bare key with
        no prefix. Defaults to `"Bearer"`.

Raises:
    CredentialError: If `key` is empty, not a string, or only whitespace.
````

#### `ApiKey.from_env` { #ocai-core-credentials-apikey-from-env }

```python
@classmethod
def from_env(cls, var: str, **kwargs: Any) -> ApiKey
```

````text
Read the key from environment variable `var` (the only env read).
````

#### `ApiKey.from_file` { #ocai-core-credentials-apikey-from-file }

```python
@classmethod
def from_file(cls, path: str | Path, **kwargs: Any) -> ApiKey
```

````text
Read the key from a file (the only filesystem read), stripped.
````

#### `ApiKey.apply` { #ocai-core-credentials-apikey-apply }

```python
def apply(self, request: HttpRequest) -> None
```

````text
Inject the auth header into `request` in place.

Sets `request.headers[header]` to `"<scheme> <key>"`, or to the bare key
when `scheme` is empty. Called once per attempt by the driver at the
leaf so the secret never enters a hook or interceptor.

Args:
    request: The outgoing `HttpRequest` whose headers are mutated.
````

### `require_credential` { #ocai-core-credentials-require-credential }

```python
def require_credential(credentials: Credential | None) -> Credential
```

````text
Return `credentials` or raise a clear error naming how to supply one.

Adapters call this in their constructor so that omitting a credential fails
loudly instead of silently producing an unauthenticated client.
````

## `ocai.core.errors`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/errors.py)

### `OcaiError` { #ocai-core-errors-ocaierror }

```python
class OcaiError(Exception)
```

````text
Base class for every error ocai raises.

Carries optional neutral context so callers/middleware can inspect a failure
without parsing a message string. `provider` / `status` / `retry_after`
are populated by the transport when available. `raw` holds the provider's
parsed error body when one was returned — **never** an auth header or secret.

Attributes:
    provider: The provider name the failure came from, if known.
    status: The HTTP status code associated with the failure, if any.
    retry_after: Seconds to wait before retrying, when the provider supplied
        a `Retry-After` hint.
    code: The provider's machine-readable error code, when a dialect mapper
        extracted one (e.g. `"context_length_exceeded"`). The extension point
        for conditions that don't have a dedicated subclass.
    raw: The provider's parsed error body, when one was returned. Never holds
        an outgoing auth header or secret.
    response_headers: Detached incoming HTTP headers, or None if unavailable.
        Application evidence; never automatically exported to observers.
    response_body: Exact incoming body bytes, or None if unavailable.
    report: Known conversion/host accounting for a rejected execution.
    usage: Known consumption for a rejected execution; None means unknown.
    host_evidence: Optional detached host outcome evidence for application use.
````

#### `OcaiError.__init__` { #ocai-core-errors-ocaierror---init-- }

```python
def __init__(self, message: str, *, provider: str | None=None, status: int | None=None, retry_after: float | None=None, code: str | None=None, raw: dict[str, Any] | None=None, response_headers: Mapping[str, str] | None=None, response_body: bytes | None=None, report: FidelityReport | None=None, usage: Usage | None=None, host_evidence: HostEvidence | None=None) -> None
```

````text
Construct an error with optional neutral provider context.

Args:
    message: The human-readable error message passed to `Exception`.
    provider: The provider name the failure came from, if known.
    status: The HTTP status code associated with the failure, if any.
    retry_after: Seconds to wait before retrying, when known.
    code: The provider's machine-readable error code, if known.
    raw: The provider's parsed error body, if one was returned. Must
        never contain an auth header or secret.
    response_headers: Detached native response headers, or None when unavailable.
        Never outgoing authentication headers; not automatically logged.
    response_body: Exact native response bytes, or None when unavailable.
    report: Known conversion and host findings on a rejected outcome.
    usage: Known consumption on a rejected outcome, never assumed zero.
    host_evidence: Detached host outcome evidence, never automatically logged.
````

### `StreamProtocolError` { #ocai-core-errors-streamprotocolerror }

```python
class StreamProtocolError(OcaiError)
```

````text
A stream failed, was malformed, or ended without successful termination.
````

### `DeadlineExceededError` { #ocai-core-errors-deadlineexceedederror }

```python
class DeadlineExceededError(OcaiError)
```

````text
The whole-call execution budget expired; retrying cannot extend it.
````

### `TransientError` { #ocai-core-errors-transienterror }

```python
class TransientError(OcaiError)
```

````text
A retryable failure: 5xx, connection reset, timeout, overloaded (529).
````

### `RateLimitError` { #ocai-core-errors-ratelimiterror }

```python
class RateLimitError(TransientError)
```

````text
Rate limited (HTTP 429). Retryable; honor `retry_after` when present.
````

### `AuthError` { #ocai-core-errors-autherror }

```python
class AuthError(OcaiError)
```

````text
Authentication/authorization failed (HTTP 401/403). Not retryable.
````

### `ContextLengthError` { #ocai-core-errors-contextlengtherror }

```python
class ContextLengthError(OcaiError)
```

````text
The request exceeded the model's context window. Not retryable as-is.
````

### `ContentFilterError` { #ocai-core-errors-contentfiltererror }

```python
class ContentFilterError(OcaiError)
```

````text
The request/response was blocked by a provider content filter/safety system.
````

### `UnsupportedFeatureError` { #ocai-core-errors-unsupportedfeatureerror }

```python
class UnsupportedFeatureError(OcaiError)
```

````text
A profile-gated feature is declared `ABSENT` for the bound model.

Raised by the facade's feature gate in **strict** mode, before the
request is encoded and before any wire attempt — the request never
leaves the process. The gate checked the request's feature keys against
the catalog's `CapabilityProfile` facts for the resolved
`(provider, interface)` and the bound model name, and at least one key
resolved to `Support.ABSENT`. Annotate mode (the default) records the
same facts as `UNSUPPORTED` field losses on the call's `FidelityReport`
instead of raising.

Attributes:
    features: The namespaced feature keys that resolved `ABSENT`.
    model: The bound model name the profile facts were checked against.
````

#### `UnsupportedFeatureError.__init__` { #ocai-core-errors-unsupportedfeatureerror---init-- }

```python
def __init__(self, message: str, *, features: tuple[str, ...]=(), model: str | None=None, provider: str | None=None) -> None
```

````text
Construct the strict-mode refusal.

Args:
    message: The human-readable error message, naming the features
        and the model.
    features: The namespaced feature keys that resolved `ABSENT`.
    model: The bound model name the facts were checked against.
    provider: The provider the resolved route targets.
````

### `error_from_response` { #ocai-core-errors-error-from-response }

```python
def error_from_response(status: int, body: dict[str, Any] | None, *, provider: str | None=None, retry_after: str | None=None) -> OcaiError
```

````text
Map an HTTP status onto the coarse taxonomy — the neutral layer.

The provider-agnostic, status-based half of error mapping (layer 1). It is the
single source of truth for status → taxonomy and is what the wire layer raises,
so retry policies can branch on `TransientError` without re-reading codes. A
dialect's `map_error` refines the result from the body afterward (layer 2); it
does not re-map status here.

Args:
    status: The HTTP status code of the failed response.
    body: The provider's parsed error body, if any (attached as `raw`).
    provider: The provider name to stamp onto the error, if known.
    retry_after: The raw `Retry-After` header value, if present.

Returns:
    The coarse `OcaiError` (subclass) for `status`.
````

## `ocai.core.evidence`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/evidence.py)

### `HostEvidence` { #ocai-core-evidence-hostevidence }

```python
class HostEvidence:
    host: str
    adapter: str
    response_status: int | None = None
    response_headers: dict[str, str] | None = None
    response_body: bytes | None = None
    metadata: dict[str, Any] = field(default_factory=dict[str, Any])
```

````text
Native response facts and adapter metadata for authorized application use.

None means unavailable; an empty body/header map is known empty evidence.
Values are detached, never SDK objects or outgoing credentials. This carrier
is not exported by passive observers and is not a canonical capability payload.
````

## `ocai.core.fidelity`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/fidelity.py)

### `Disposition` { #ocai-core-fidelity-disposition }

```python
class Disposition(str, Enum):
    EXACT = 'exact'
    RENAMED = 'renamed'
    APPROXIMATED = 'approximated'
    EMULATED = 'emulated'
    EXTENSIONS = 'extensions'
    DROPPED = 'dropped'
    UNSUPPORTED = 'unsupported'
```

````text
What became of one field as a conversion edge crossed it.

Attributes:
    EXACT: Carried through unchanged.
    RENAMED: Mapped to a differently-named field with the same meaning.
    APPROXIMATED: Mapped to a near-equivalent that is not exact
        (including out-of-range values passed verbatim).
    EMULATED: The destination has no native support; the effect is
        reproduced by other means (see `SemanticShift` for the how).
    EXTENSIONS: Preserved in the `extensions` bag — recoverable, but not
        a first-class canonical field. Distinct from `DROPPED`.
    DROPPED: Discarded; the destination cannot represent it. Lost.
    UNSUPPORTED: The destination rejects the field outright (a hard gap —
        e.g. a `ProviderRef` crossing its minting interface).
````

### `ShiftKind` { #ocai-core-fidelity-shiftkind }

```python
class ShiftKind:
    RELOCATION: Final = 'relocation'
    EMULATION: Final = 'emulation'
    ID_REGENERATED: Final = 'id_regenerated'
    RANGE_PASSTHROUGH: Final = 'range_passthrough'
```

````text
Canonical constants for `SemanticShift.kind` — an **open** vocabulary.

`kind` is an open string code, not an enum: edges may mint new kinds
(namespaced for plugins) without a core release. These constants name the
kinds core itself emits.

Attributes:
    RELOCATION: Content moved to a structurally different home with the
        same meaning (system role → `systemInstruction`).
    EMULATION: Behavior reproduced by different mechanics (server-side
        conversation state emulated by transcript replay).
    ID_REGENERATED: A correlation id could not survive the boundary and
        was re-minted (tool-call ids across providers).
    RANGE_PASSTHROUGH: A value outside the destination's documented range
        was passed verbatim — never rescaled, never clamped.
````

### `FieldLoss` { #ocai-core-fidelity-fieldloss }

```python
class FieldLoss:
    path: str
    disposition: Disposition
    severity: float = 0.0
    note: str = ''
```

````text
One field-level record of what a conversion edge did to a field.

Attributes:
    path: A dotted/bracketed path to the field
        (e.g. `"messages[0].parts[2].args_json"`).
    disposition: What happened to the field.
    severity: A diagnostic information-cost weight (0.0 == lossless).
        Report views sum it; the *planner* weight comes from the edge's
        declared `EdgeContract` LossGrade, never from this number.
    note: A human-readable explanation of the mapping or the loss.
````

#### `FieldLoss.lossy` { #ocai-core-fidelity-fieldloss-lossy }

```python
@property
def lossy(self) -> bool
```

````text
Return whether this record degrades information or behavior.
````

#### `FieldLoss.to_dict` { #ocai-core-fidelity-fieldloss-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the record to a plain JSON-compatible dict.

Returns:
    A dict with `path`, the `disposition` value, `severity`, and
    `note`.
````

#### `FieldLoss.from_dict` { #ocai-core-fidelity-fieldloss-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `FieldLoss` from a serialized dict, totally.

An unrecognized disposition code decodes to `Disposition.DROPPED`
(see `_decode_disposition`); a non-numeric severity decodes to 0.0.

Args:
    data: A mapping with `path`, `disposition`, and the optional
        `severity`/`note`.

Returns:
    The decoded `FieldLoss`.
````

### `SemanticShift` { #ocai-core-fidelity-semanticshift }

```python
class SemanticShift:
    kind: str
    path: str = ''
    note: str = ''
```

````text
A semantics-level divergence record, distinct from field mapping.

Emitted alongside `FieldLoss` records when an edge changed *how* something
works rather than *what data* a field holds. Shifts do not flip the
derived `lossless` flag (the information survived); they are surfaced
separately so a migration's behavioral cost is never understated.

Attributes:
    kind: The open shift-kind code; canonical constants on `ShiftKind`.
        Plugin-minted kinds must be namespaced (`"anthropic.xyz"`).
    path: A dotted/bracketed path to the affected location, when one
        location is identifiable.
    note: A human-readable explanation of the divergence.
````

#### `SemanticShift.to_dict` { #ocai-core-fidelity-semanticshift-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the shift to a plain JSON-compatible dict.

Returns:
    A dict with `kind`, `path`, and `note`.
````

#### `SemanticShift.from_dict` { #ocai-core-fidelity-semanticshift-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `SemanticShift` from a serialized dict, totally.

`kind` is an open code, so any string passes through verbatim.

Args:
    data: A mapping with `kind` and the optional `path`/`note`.

Returns:
    The decoded `SemanticShift`.
````

### `EdgeReport` { #ocai-core-fidelity-edgereport }

```python
class EdgeReport:
    src: NodeId
    dst: NodeId
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()
    note: str = ''
```

````text
The losses and shifts incurred by traversing one conversion edge.

Produced by an edge's conversion function; the conformance harness
certifies at build time that these runtime records never exceed the
edge's declared `EdgeContract` census.

Attributes:
    src: The edge's source node.
    dst: The edge's destination node.
    losses: The per-field records this edge emitted, in order.
    shifts: The semantics-level records this edge emitted, in order.
    note: A human-readable description of the edge's conversion.
````

#### `EdgeReport.cost` { #ocai-core-fidelity-edgereport-cost }

```python
@property
def cost(self) -> float
```

````text
Return the summed diagnostic `severity` across this edge's losses.

A report view, not a planner input — planner weight is derived from
the edge's `EdgeContract`.
````

#### `EdgeReport.lossless` { #ocai-core-fidelity-edgereport-lossless }

```python
@property
def lossless(self) -> bool
```

````text
Return whether this edge preserved all information and behavior.
````

#### `EdgeReport.to_dict` { #ocai-core-fidelity-edgereport-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the edge report to a plain JSON-compatible dict.

Returns:
    A dict with `src`/`dst` labels, the `note`, the summed `cost`,
    and the serialized `losses` and `shifts`.
````

#### `EdgeReport.from_dict` { #ocai-core-fidelity-edgereport-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `EdgeReport` from a serialized dict, totally.

The `src`/`dst` node labels decode via `_node_from_label`; the
serialized `cost` is ignored — it is derived from the loss records,
never trusted from data (`lossless` honesty applies to replay too).

Args:
    data: A mapping with the `src`/`dst` labels and the optional
        `losses`/`shifts`/`note`.

Returns:
    The decoded `EdgeReport`.
````

### `HostEffectReport` { #ocai-core-fidelity-hosteffectreport }

```python
class HostEffectReport:
    host: str
    adapter: str
    contract_id: str
    phase: str
    losses: tuple[FieldLoss, ...] = ()
    shifts: tuple[SemanticShift, ...] = ()
```

````text
Actual host effects, separate from graph edges and qualification evidence.

Attributes:
    host: Non-secret host identity supplied by the adapter.
    adapter: Versioned adapter identity responsible for these findings.
    contract_id: Identity of the declaration governing these effects, not certification.
    phase: Open execution phase code, initially request or response.
    losses: Field effects recorded by this adapter invocation.
    shifts: Semantic effects recorded by this adapter invocation.
````

#### `HostEffectReport.cost` { #ocai-core-fidelity-hosteffectreport-cost }

```python
@property
def cost(self) -> float
```

````text
Return diagnostic severity, never graph planner weight.
````

#### `HostEffectReport.lossless` { #ocai-core-fidelity-hosteffectreport-lossless }

```python
@property
def lossless(self) -> bool
```

````text
Return whether field information survived; shifts remain separate.
````

#### `HostEffectReport.to_dict` { #ocai-core-fidelity-hosteffectreport-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize provenance and findings without inventing graph coordinates.
````

#### `HostEffectReport.from_dict` { #ocai-core-fidelity-hosteffectreport-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Decode findings totally, preserving open phase and semantic codes.
````

### `FidelityReport` { #ocai-core-fidelity-fidelityreport }

```python
class FidelityReport:
    edges: list[EdgeReport] = field(default_factory=list[EdgeReport])
    hosts: list[HostEffectReport] = field(default_factory=list[HostEffectReport], kw_only=True)
```

````text
The accumulated graph conversion and host-effect account of one call.

The single report type the library speaks. It lives on
`CallResult.report` and on the terminal `StreamEnd` of a stream — and
only there; IR payloads never carry a report. Built by appending one
`EdgeReport` per traversed edge; the request leg and the response leg of
a call are folded together with `merge`.

`lossless` is **derived, never asserted**: it is recomputed from the
records every time, so no edge can claim fidelity its records contradict.

Attributes:
    edges: One `EdgeReport` per traversed edge, in traversal order.
    hosts: Actual host effects, in insertion order, separate from graph traversal.
````

#### `FidelityReport.path` { #ocai-core-fidelity-fidelityreport-path }

```python
@property
def path(self) -> list[NodeId]
```

````text
Return the ordered nodes visited, derived from the edge records.

Empty when no edge was traversed (an identity conversion).
````

#### `FidelityReport.losses` { #ocai-core-fidelity-fidelityreport-losses }

```python
@property
def losses(self) -> list[FieldLoss]
```

````text
Return graph then host field records, preserving order within each lane.
````

#### `FidelityReport.shifts` { #ocai-core-fidelity-fidelityreport-shifts }

```python
@property
def shifts(self) -> list[SemanticShift]
```

````text
Return graph then host semantic records, preserving order within each lane.
````

#### `FidelityReport.dropped` { #ocai-core-fidelity-fidelityreport-dropped }

```python
@property
def dropped(self) -> list[FieldLoss]
```

````text
Return the records for fields that were dropped or unsupported.
````

#### `FidelityReport.lossless` { #ocai-core-fidelity-fidelityreport-lossless }

```python
@property
def lossless(self) -> bool
```

````text
Return whether the whole conversion preserved all information.

Derived from the field records (`SemanticShift`s do not flip it —
they are reported in their own lane via `shifts`).
````

#### `FidelityReport.total_cost` { #ocai-core-fidelity-fidelityreport-total-cost }

```python
@property
def total_cost(self) -> float
```

````text
Return diagnostic cost across graph and host records, never planner weight.
````

#### `FidelityReport.merge` { #ocai-core-fidelity-fidelityreport-merge }

```python
def merge(self, other: Self) -> Self
```

````text
Fold `other` into `self` (in place) and return `self`.

Both lanes concatenate without deduplication — typically the response leg
folded onto the request leg by the facade before it assembles the
`CallResult`.

Args:
    other: The report to fold in.

Returns:
    `self`, after folding in `other`.
````

#### `FidelityReport.to_dict` { #ocai-core-fidelity-fidelityreport-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the report to a plain JSON-compatible dict.

Returns:
    A dict with the `path` (node labels), `lossless`, `total_cost`,
    and the serialized `edges`.
````

#### `FidelityReport.from_dict` { #ocai-core-fidelity-fidelityreport-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `FidelityReport` from a serialized dict, totally.

Only `edges` and `hosts` are read: `path`, `lossless`, and `total_cost` are
derived views, recomputed from the decoded records every time — a
replayed report can no more assert fidelity its records contradict
than a live one can. This is what lets a recorded `StreamEnd`
replay with its report intact.

Args:
    data: A mapping with serialized edges and optional host effects.

Returns:
    The decoded `FidelityReport`.
````

### `Route` { #ocai-core-fidelity-route }

```python
class Route:
    capability: Capability
    node: NodeId
    requested_interface: str | None = None
    requested_tag: str | None = None
    reason: str = ''
    catalog_hash: str = ''
    host: str | None = None
```

````text
What ocai *decided* for one call — the audit joint.

Records the resolution `Catalog.resolve(capability, provider, pins)`
performed: the chosen node (interface + tag), what the caller pinned,
the human-readable reason, and the hash of the catalog lockfile the
decision was made under. A `Route` plus that lockfile reconstructs
exactly which conversion logic (down to plugin distribution versions)
served a call. Delivered on `CallResult.route`.

Attributes:
    capability: The capability the call was made against.
    node: The chosen graph node (provider, interface, tag, shape, …).
    requested_interface: The interface the caller pinned, or None for
        "let ocai choose".
    requested_tag: The revision tag the caller pinned, or None for
        "latest stable".
    reason: A human-readable resolution explanation
        (e.g. `"latest stable, released 2026-01-15"`).
    catalog_hash: The hash of the `Catalog.lock()` lockfile the
        resolution was made under; empty for catalog-less adapters.
    host: Where the call was physically sent — a host label or
        `"in-process"` for local adapters. Stamped after host resolution
        (hosting lives below the graph), so resolution itself never
        knows clouds exist.
````

#### `Route.to_dict` { #ocai-core-fidelity-route-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the route to a plain JSON-compatible dict.

Returns:
    A dict with the `capability`, the `node` label, the requested
    pins, the `reason`, the `catalog_hash`, and the `host` when set.
````

### `FidelityPolicyError` { #ocai-core-fidelity-fidelitypolicyerror }

```python
class FidelityPolicyError(OcaiError)
```

````text
Conversion policy rejected execution; accounting survives without payloads.
````

#### `FidelityPolicyError.__init__` { #ocai-core-fidelity-fidelitypolicyerror---init-- }

```python
def __init__(self, *, phase: str, report: FidelityReport, usage: Usage | None=None, route: Route | None=None, delivered_events: int=0) -> None
```

````text
Retain detached evidence, never the rejected response or raw body.
````

### `FidelityPolicy` { #ocai-core-fidelity-fidelitypolicy }

```python
class FidelityPolicy:
    forbidden_dispositions: frozenset[Disposition] = frozenset()
    forbidden_shifts: frozenset[str] = frozenset()
    allow_loss: Callable[[FieldLoss], bool] | None = None
    allow_shift: Callable[[SemanticShift], bool] | None = None
```

````text
Caller-defined acceptance over both field records and semantic shifts.

Predicates receive detached records and must be pure. A raising predicate
rejects execution. Predicates are re-evaluated before every physical attempt;
closures are application policy code, not portable conformance evidence.
Neither semantic acceptance nor coverage is inferred from report.lossless.
````

#### `FidelityPolicy.enforce` { #ocai-core-fidelity-fidelitypolicy-enforce }

```python
def enforce(self, report: FidelityReport, *, phase: str, usage: Usage | None=None, route: Route | None=None, delivered_events: int=0) -> None
```

````text
Reject forbidden findings while retaining usage and the complete ledger.
````

## `ocai.core.finish`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/finish.py)

### `FinishReason` { #ocai-core-finish-finishreason }

```python
class FinishReason:
    COMPLETE: Final = 'complete'
    MAX_TOKENS: Final = 'max_tokens'
    STOP_SEQUENCE: Final = 'stop_sequence'
    TOOL_CALL: Final = 'tool_call'
    CONTENT_FILTER: Final = 'content_filter'
    REFUSAL: Final = 'refusal'
    RECITATION: Final = 'recitation'
    PAUSED: Final = 'paused'
    MALFORMED: Final = 'malformed'
    ERROR: Final = 'error'
    UNKNOWN: Final = 'unknown'
```

````text
Canonical constants for the open `FinishInfo.reason` code.

Attributes:
    COMPLETE: The model finished its turn naturally.
    MAX_TOKENS: The output token ceiling was hit; the reply is
        truncated.
    STOP_SEQUENCE: A configured stop sequence was emitted.
    TOOL_CALL: The model stopped to have tools executed.
    CONTENT_FILTER: Generation was cut off by a safety system
        mid-stream (`detail` typically carries a `SafetyDetail`).
    REFUSAL: The model refused mid-generation (pairs with
        `PartRefusal`).
    RECITATION: Output was stopped for reciting training/source
        material (Gemini's recitation stop).
    PAUSED: The provider paused a long-running turn for the caller to
        resume (Anthropic `pause_turn`).
    MALFORMED: The model produced output the provider could not
        represent (e.g. a malformed function call).
    ERROR: Generation ended in a provider-reported error (`detail`
        carries an `ErrorDetail`).
    UNKNOWN: The wire value was not recognized; `FinishInfo.native`
        preserves it verbatim.
````

### `DetailType` { #ocai-core-finish-detailtype }

```python
class DetailType(str, Enum):
    UNDEFINED = 'undefined'
    SAFETY = 'safety'
    REFUSAL = 'refusal'
    INCOMPLETE = 'incomplete'
    ERROR = 'error'
```

````text
Canonical discriminator tags for the core `FinishDetail` variants.

Constants for the tags core ships — the union stays open through
`DETAIL_REGISTRY` (unknown tags decode to `DetailOpaque`).

Attributes:
    UNDEFINED: No detail kind set (the unknown/placeholder tag).
    SAFETY: A safety-system elaboration (`SafetyDetail`).
    REFUSAL: A refusal elaboration (`RefusalDetail`).
    INCOMPLETE: An incomplete-output elaboration (`IncompleteDetail`).
    ERROR: A mid-generation error elaboration (`ErrorDetail`).
````

### `SafetyRating` { #ocai-core-finish-safetyrating }

```python
class SafetyRating:
    category: str
    level: str | None = None
    blocked: bool | None = None
```

````text
One per-category safety assessment inside a `SafetyDetail`.

Attributes:
    category: The open safety-category code, provider-verbatim
        (e.g. `"HARM_CATEGORY_DANGEROUS_CONTENT"`).
    level: The open severity/probability code, provider-verbatim
        (e.g. `"HIGH"`), or None when the provider gives none.
    blocked: Whether this category triggered the block, when the
        provider says so.
````

#### `SafetyRating.to_dict` { #ocai-core-finish-safetyrating-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the rating to a plain JSON-compatible dict.

Returns:
    A dict with `category` and the optional `level`/`blocked` when
    set.
````

#### `SafetyRating.from_dict` { #ocai-core-finish-safetyrating-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `SafetyRating` from a serialized dict, totally.

Args:
    data: A mapping with `category` and the optional
        `level`/`blocked`.

Returns:
    The decoded `SafetyRating`.
````

### `SafetyDetail` { #ocai-core-finish-safetydetail }

```python
class SafetyDetail(IRObject):
    ratings: list[SafetyRating] = field(default_factory=list[SafetyRating])
    block_source: str | None = None
    type: Literal[DetailType.SAFETY] = field(default=DetailType.SAFETY)
```

````text
Elaboration for safety-driven stops (`reason == "content_filter"`).

Attributes:
    ratings: The per-category assessments the provider reported.
    block_source: The open code for which safety layer blocked
        (e.g. `"provider"`, `"platform"`), when distinguishable.
    type: The detail discriminator, fixed to `DetailType.SAFETY`.
````

#### `SafetyDetail.from_dict` { #ocai-core-finish-safetydetail-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `SafetyDetail` from a serialized dict, totally.

Args:
    data: A mapping with `ratings`, an optional `block_source`, and
        the common IR envelope keys.

Returns:
    The decoded `SafetyDetail`.
````

### `RefusalDetail` { #ocai-core-finish-refusaldetail }

```python
class RefusalDetail(IRObject):
    category: str | None = None
    explanation: str | None = None
    type: Literal[DetailType.REFUSAL] = field(default=DetailType.REFUSAL)
```

````text
Elaboration for refusal stops (`reason == "refusal"`).

Attributes:
    category: The open refusal-category code, provider-verbatim, when
        given.
    explanation: The provider's human-readable explanation, when given.
    type: The detail discriminator, fixed to `DetailType.REFUSAL`.
````

#### `RefusalDetail.from_dict` { #ocai-core-finish-refusaldetail-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `RefusalDetail` from a serialized dict, totally.

Args:
    data: A mapping with the optional `category`/`explanation` and
        the common IR envelope keys.

Returns:
    The decoded `RefusalDetail`.
````

### `IncompleteDetail` { #ocai-core-finish-incompletedetail }

```python
class IncompleteDetail(IRObject):
    note: str | None = None
    type: Literal[DetailType.INCOMPLETE] = field(default=DetailType.INCOMPLETE)
```

````text
Elaboration for truncated/paused stops (`max_tokens`, `paused`).

Attributes:
    note: The provider's explanation of what was cut short or how to
        resume, when given.
    type: The detail discriminator, fixed to `DetailType.INCOMPLETE`.
````

#### `IncompleteDetail.from_dict` { #ocai-core-finish-incompletedetail-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `IncompleteDetail` from a serialized dict, totally.

Args:
    data: A mapping with the optional `note` and the common IR
        envelope keys.

Returns:
    The decoded `IncompleteDetail`.
````

### `ErrorDetail` { #ocai-core-finish-errordetail }

```python
class ErrorDetail(IRObject):
    code: str | None = None
    message: str | None = None
    type: Literal[DetailType.ERROR] = field(default=DetailType.ERROR)
```

````text
Elaboration for error stops (`reason == "error"`).

Distinct from the exception taxonomy: this is a *finish record* on a
response that partially exists; a call that produced nothing raises
instead.

Attributes:
    code: The canonical error-taxonomy code, when mappable
        (e.g. `"transient"`).
    message: The provider's error message, verbatim.
    type: The detail discriminator, fixed to `DetailType.ERROR`.
````

#### `ErrorDetail.from_dict` { #ocai-core-finish-errordetail-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an `ErrorDetail` from a serialized dict, totally.

Args:
    data: A mapping with the optional `code`/`message` and the
        common IR envelope keys.

Returns:
    The decoded `ErrorDetail`.
````

### `DetailOpaque` { #ocai-core-finish-detailopaque }

```python
class DetailOpaque(IRObject):
    data: dict[str, Any] = field(default_factory=dict[str, Any])
    type: str = DetailType.UNDEFINED.value
```

````text
Verbatim finish detail: deliberate opaque AND the unknown fallback.

Serves two jobs the way `PartOpaque`/`PartUnknown` split them — kept as
one type here because finish details are terminal metadata, never
re-encoded into requests: a codec may deliberately park a
provider-unique elaboration here, and `DETAIL_REGISTRY` falls back to it
for tags this revision does not know. Byte-faithful through `to_dict`.

Attributes:
    data: The verbatim serialized payload, including its original tag.
    type: The original discriminator value, preserved verbatim.
````

#### `DetailOpaque.to_dict` { #ocai-core-finish-detailopaque-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize back to the verbatim payload this instance preserved.

Returns:
    A copy of the original serialized mapping, untouched.
````

#### `DetailOpaque.from_dict` { #ocai-core-finish-detailopaque-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Preserve a finish-detail payload verbatim.

Args:
    data: The serialized mapping whose tag no registered detail
        matched (or that a codec deliberately parked here).

Returns:
    A new `DetailOpaque` carrying the payload untouched.
````

### `FinishDetail` { #ocai-core-finish-finishdetail }

```python
type FinishDetail = SafetyDetail | RefusalDetail | IncompleteDetail | ErrorDetail | DetailOpaque
```

### `DETAIL_REGISTRY` { #ocai-core-finish-detail-registry }

```python
DETAIL_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=DetailOpaque)
```

### `cast_detail` { #ocai-core-finish-cast-detail }

```python
def cast_detail(data: dict[str, Any]) -> FinishDetail
```

````text
Decode a serialized detail into its concrete `FinishDetail` variant.

Dispatches on the `type` tag via `DETAIL_REGISTRY`; unknown tags decode
to `DetailOpaque` — this function never raises on unknown input.

Args:
    data: The serialized detail mapping, including its `type`
        discriminator.

Returns:
    The decoded `FinishDetail` variant.
````

### `FinishInfo` { #ocai-core-finish-finishinfo }

```python
class FinishInfo(IRObject):
    object: ClassVar[str] = 'finish'
    reason: str = FinishReason.UNKNOWN
    native: str | None = None
    detail: FinishDetail | None = None
```

````text
Why generation stopped — canonical code, native value, typed detail.

Delivered on `ChatResponse.finish` and, for streams, on the terminal
`StreamEnd.finish` (the authoritative one). The `StreamAccumulator`
carries the last-seen finish into the folded response.

Attributes:
    reason: The canonical open stop code; constants on `FinishReason`.
        Unknown wire values decode to `"unknown"`.
    native: The provider's verbatim wire value (e.g. `"length"`,
        `"end_turn"`, `"RECITATION"`), always preserved.
    detail: The typed elaboration, when the reason warrants one.
````

#### `FinishInfo.from_dict` { #ocai-core-finish-finishinfo-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `FinishInfo` from a serialized dict, totally.

Args:
    data: A mapping with `reason`, the optional `native`, the
        nested `detail`, and the common IR envelope keys.

Returns:
    The decoded `FinishInfo`.
````

## `ocai.core.identity`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/identity.py)

### `CANONICAL_PROVIDER` { #ocai-core-identity-canonical-provider }

```python
CANONICAL_PROVIDER = 'ocai'
```

### `CANONICAL_INTERFACE` { #ocai-core-identity-canonical-interface }

```python
CANONICAL_INTERFACE = 'ocai'
```

### `CANONICAL_REVISION` { #ocai-core-identity-canonical-revision }

```python
CANONICAL_REVISION = '2026-07'
```

### `Capability` { #ocai-core-identity-capability }

```python
class Capability:
    name: str
```

````text
The semantic job a user programs against.

One canonical IR and one port `Protocol` exist per capability; the
capability is the top of the identity hierarchy and the first argument to
`Catalog.resolve`. An open value object rather than a closed enum so a
contrib distribution can mint `Capability("rerank")` without touching
`ocai.core`.

Attributes:
    name: The capability's stable identifier (e.g. `"chat"`).
````

### `CHAT` { #ocai-core-identity-chat }

```python
CHAT = Capability('chat')
```

### `EMBEDDING` { #ocai-core-identity-embedding }

```python
EMBEDDING = Capability('embedding')
```

### `VECTORSTORE` { #ocai-core-identity-vectorstore }

```python
VECTORSTORE = Capability('vectorstore')
```

### `Shape` { #ocai-core-identity-shape }

```python
class Shape:
    capability: Capability
    role: str
```

````text
A message schema role within a capability — the graph partition key.

A `Shape` pairs a `Capability` with an open `role` code and renders as a
dotted token (`"chat.request"`). Because the role is qualified by
capability, a chat request and an embedding request are different shapes
and live in different graphs; the planner never mixes shapes on one path.

Attributes:
    capability: The capability this message belongs to.
    role: The message's role within its capability — an open string code
        with canonical constants `request`, `response`, `chunk`.
````

### `CHAT_REQUEST` { #ocai-core-identity-chat-request }

```python
CHAT_REQUEST = Shape(CHAT, 'request')
```

### `CHAT_RESPONSE` { #ocai-core-identity-chat-response }

```python
CHAT_RESPONSE = Shape(CHAT, 'response')
```

### `CHAT_CHUNK` { #ocai-core-identity-chat-chunk }

```python
CHAT_CHUNK = Shape(CHAT, 'chunk')
```

### `Status` { #ocai-core-identity-status }

```python
class Status(str, Enum):
    STABLE = 'stable'
    PREVIEW = 'preview'
    DEPRECATED = 'deprecated'
    RETIRED = 'retired'
```

````text
The release channel a `NodeId` belongs to; drives catalog resolution.

Attributes:
    STABLE: Generally available; eligible to be auto-selected as "latest".
    PREVIEW: Pre-release; reachable only when pinned explicitly by tag.
    DEPRECATED: Superseded; still reachable when pinned, never
        auto-selected.
    RETIRED: No longer served by the provider; kept so archived traffic
        can still be re-converted through migration edges.
````

### `NodeId` { #ocai-core-identity-nodeid }

```python
class NodeId:
    provider: str
    interface: str
    tag: str
    shape: Shape
    released: date
    status: Status = Status.STABLE
```

````text
The conversion-graph node: one interface revision of one shape.

A node is the full six-coordinate identity of a message schema. `Catalog`s
key nodes and edges by it, the planner searches over it, `Route` records
the one that was chosen, and every conversion `EdgeReport` names its `src`
and `dst` with it.

The `tag` is an opaque dated revision token — **never parsed**; ordering
among one `(provider, interface)`'s revisions comes from `released`
instead, and cross-provider date comparison is meaningless. `status` is
the resolution channel (`Catalog.resolve` auto-selects only `STABLE`).

Attributes:
    provider: The provider label (`"openai"`, or `"ocai"` for canonical).
    interface: The wire protocol within the provider
        (`"chat_completions"`, `"responses"`, `"ocai"`). Sibling
        interfaces are concurrent, not versions of each other.
    tag: The interface's opaque dated revision token (e.g. `"2026-01"`).
    shape: Which message this schema is (`chat.request`, …).
    released: The internal sort key — the revision's release date,
        compared only within one `(provider, interface)`.
    status: The release channel; defaults to `Status.STABLE`.
````

#### `NodeId.capability` { #ocai-core-identity-nodeid-capability }

```python
@property
def capability(self) -> Capability
```

````text
Return the capability this node's `shape` belongs to.
````

### `Origin` { #ocai-core-identity-origin }

```python
class Origin:
    distribution: str
    version: str
```

````text
Provenance stamp: which distribution registered a node or edge.

Carried by every node/edge a plugin registers into a `CatalogFragment`,
threaded through the `Catalog` into lockfiles and audit records, so a
`Route` plus a catalog lockfile reconstructs exactly whose conversion
logic served a call.

Attributes:
    distribution: The distribution name (e.g. `"ocai-openai"`).
    version: The distribution's installed version (e.g. `"0.1.0"`).
````

### `canonical_node` { #ocai-core-identity-canonical-node }

```python
def canonical_node(shape: Shape, tag: str=CANONICAL_REVISION, released: date | None=None) -> NodeId
```

````text
Return the canonical IR node for `shape` at a canonical revision.

Canonical nodes are ordinary nodes under provider/interface `ocai`; the
graph treats them like any other, which is what makes IR self-migration
(`ocai@2026-07 → ocai@2027-01`) ordinary edge traversal.

Args:
    shape: The message shape whose canonical node is wanted.
    tag: The canonical revision tag; defaults to `CANONICAL_REVISION`.
        Canonical tags are always dated `YYYY-MM` tokens.
    released: The revision's release date. When omitted it is derived
        from `tag` (the first day of the revision month) — safe because
        canonical tags are ocai-owned and dated by construction.

Returns:
    The `NodeId` identifying the canonical IR schema for `shape`.
````

## `ocai.core.ir`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/ir.py)

### `DataClassProto` { #ocai-core-ir-dataclassproto }

```python
class DataClassProto(Protocol)
```

````text
The structural serialization contract every IR dataclass satisfies.

`TagRegistry` and the encoder dispatch on this shape rather than on a
base class, so plugin-defined IR types (and core types that do not extend
`IRObject`, like `ProviderRef`) participate equally.
````

#### `DataClassProto.to_dict` { #ocai-core-ir-dataclassproto-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the object to a plain JSON-compatible dict.

Returns:
    The serialized mapping, omit-absent.
````

#### `DataClassProto.from_dict` { #ocai-core-ir-dataclassproto-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build an instance from a serialized dict, totally (never raises on unknown input).

Args:
    data: The serialized mapping to decode.

Returns:
    The decoded instance.
````

### `is_json_object` { #ocai-core-ir-is-json-object }

```python
def is_json_object(value: object) -> TypeIs[dict[str, Any]]
```

````text
Narrow `value` to a JSON object (a dict) for tolerant decoding.

The typed form of the `isinstance(value, dict)` check every `from_dict`
performs: a decoded JSON object is a `dict` whose keys are strings and
whose values are dynamic, and the narrowing says exactly that instead of
leaving the element types unknown. Only the container is checked; keys
are assumed to be strings, as JSON guarantees.

Args:
    value: The dynamic value under inspection.

Returns:
    Whether `value` is a dict.
````

### `is_json_array` { #ocai-core-ir-is-json-array }

```python
def is_json_array(value: object) -> TypeIs[list[Any]]
```

````text
Narrow `value` to a JSON array (a list) for tolerant decoding.

The list counterpart of `is_json_object`: the narrowed element type is
dynamic, never unknown.

Args:
    value: The dynamic value under inspection.

Returns:
    Whether `value` is a list.
````

### `IRObject` { #ocai-core-ir-irobject }

```python
class IRObject:
    version: str = field(default=CANONICAL_REVISION, kw_only=True)
    provider_options: dict[str, Any] = field(default_factory=dict[str, Any], kw_only=True)
    extensions: dict[str, Any] = field(default_factory=dict[str, Any], kw_only=True)
```

````text
Common base for canonical IR dataclasses — the envelope.

Carries the three cross-cutting fields every IR object shares, all
keyword-only, and implements the two normative (de)serialization halves:
omit-absent `to_dict` and the tolerant `_from_dict_common` sweep that
subclasses' `from_dict` build on.

Attributes:
    version: The canonical IR revision this object conforms to; defaults
        to `CANONICAL_REVISION`. A dated tag on the `ocai` interface —
        never the library semver, never a provider tag.
    provider_options: Request passthrough, **namespaced by destination
        interface** (`{"openai.chat_completions": {...}}`). A codec
        expands only its own namespace; foreign namespaces are never
        forwarded.
    extensions: The namespaced bag for unmapped-but-preserved provider
        data (`extensions["openai.logit_bias"]`). Censused: every key's
        schema is registered in `spec/extensions/`.
````

#### `IRObject.to_dict` { #ocai-core-ir-irobject-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize to a plain dict, omitting absent fields.

Omit-absent is the normative encoding rule: None-valued fields and
empty containers whose declared default is also empty are not
emitted. This is what keeps fixtures stable as optional fields are
added, and it pairs with `canonjson`'s absent-vs-null distinction
(an emitted `null` is meaningful; an omitted key is absent).

Returns:
    A dict keyed by field name with recursively encoded values.
````

### `TagRegistry` { #ocai-core-ir-tagregistry }

```python
class TagRegistry
```

````text
Open registration for one tagged union (parts, deltas, details, …).

Each tagged union in the IR owns one registry instance. Core registers
its bare tags at import of the type module; plugins register namespaced
tags (`"anthropic.mid_conv_system"`) from their `CatalogFragment` —
bare tags are reserved for core.

Decoding is **total**: an unknown or missing tag falls back to the
registered Unknown type (`PartUnknown`, `DeltaUnknown`, …), which
preserves the payload verbatim for later upgrade via IR self-migration
edges. A registry with no Unknown fallback is a configuration error, not
a decode-time surprise.
````

#### `TagRegistry.__init__` { #ocai-core-ir-tagregistry---init-- }

```python
def __init__(self, *, tag_key: str='type', unknown: type[T] | None=None) -> None
```

````text
Create a registry for one tagged union.

Args:
    tag_key: The discriminator key read from payloads.
    unknown: The fallback type decoded when the tag is unknown; may
        also be supplied later via `register_unknown`.
````

#### `TagRegistry.register` { #ocai-core-ir-tagregistry-register }

```python
def register(self, tag: str, cls: type[T]) -> type[T]
```

````text
Register `cls` as the decoder for `tag`.

Idempotent for the same class; re-registering a tag to a *different*
class raises, because silently shadowing another distribution's tag
is exactly the governance failure catalogs exist to prevent.

Args:
    tag: The discriminator value (bare for core, namespaced for
        plugins).
    cls: The dataclass whose `from_dict` decodes payloads so tagged.

Returns:
    `cls`, so the call can be used as a registration helper.

Raises:
    ValueError: If `tag` is already registered to a different class.
````

#### `TagRegistry.register_unknown` { #ocai-core-ir-tagregistry-register-unknown }

```python
def register_unknown(self, cls: type[T]) -> type[T]
```

````text
Register the Unknown fallback type decoded for unrecognized tags.

Args:
    cls: The fallback dataclass; its `from_dict` must preserve the
        payload verbatim.

Returns:
    `cls`, so the call can be used as a registration helper.
````

#### `TagRegistry.decode` { #ocai-core-ir-tagregistry-decode }

```python
def decode(self, data: dict[str, Any]) -> T
```

````text
Decode a tagged payload into its registered type — totally.

Reads `data[tag_key]`, dispatches to the registered class, and falls
back to the Unknown type for missing/unrecognized/non-string tags.
This replaces the old `decode_tagged`, which raised `KeyError` on
unknown tags.

Args:
    data: The serialized mapping, including its discriminator.

Returns:
    The decoded instance.

Raises:
    LookupError: Only when the tag is unknown AND no Unknown
        fallback was registered — a registry configuration error;
        every core registry registers a fallback.
````

#### `TagRegistry.tags` { #ocai-core-ir-tagregistry-tags }

```python
@property
def tags(self) -> frozenset[str]
```

````text
Return the currently registered discriminator values.
````

## `ocai.core.jsonschema`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/jsonschema.py)

### `MISSING` { #ocai-core-jsonschema-missing }

```python
MISSING: Any = _Missing()
```

### `encode_schema` { #ocai-core-jsonschema-encode-schema }

```python
def encode_schema(value: Any) -> Any
```

````text
Recursively encode a value to its plain JSON form.

`JsonSchema` instances become dicts; lists and dicts recurse; everything
else passes through unchanged (raw JSON in `enum` / `const` / `default` /
`examples` is copied structurally, never reinterpreted).
````

### `decode_schema` { #ocai-core-jsonschema-decode-schema }

```python
def decode_schema(value: Any) -> Schema
```

````text
Decode a wire (sub)schema into `Schema` (`JsonSchema | bool`).

Tolerant: a boolean stays a boolean, a mapping becomes a `JsonSchema`,
and anything else is returned unchanged rather than raising.
````

### `JsonSchema` { #ocai-core-jsonschema-jsonschema }

```python
class JsonSchema:
    schema: str | None = None
    vocabulary: dict[str, bool] | None = None
    id: str | None = None
    anchor: str | None = None
    dynamic_anchor: str | None = None
    ref: str | None = None
    dynamic_ref: str | None = None
    defs: dict[str, Schema] | None = None
    comment: str | None = None
    all_of: list[Schema] | None = None
    any_of: list[Schema] | None = None
    one_of: list[Schema] | None = None
    not_: Schema | None = None
    if_: Schema | None = None
    then: Schema | None = None
    else_: Schema | None = None
    dependent_schemas: dict[str, Schema] | None = None
    prefix_items: list[Schema] | None = None
    items: Schema | None = None
    contains: Schema | None = None
    properties: dict[str, Schema] | None = None
    pattern_properties: dict[str, Schema] | None = None
    additional_properties: Schema | None = None
    property_names: Schema | None = None
    unevaluated_items: Schema | None = None
    unevaluated_properties: Schema | None = None
    type: str | list[str] | None = None
    enum: list[Any] | None = None
    const: Any = MISSING
    multiple_of: float | int | None = None
    maximum: float | int | None = None
    exclusive_maximum: float | int | None = None
    minimum: float | int | None = None
    exclusive_minimum: float | int | None = None
    max_length: int | None = None
    min_length: int | None = None
    pattern: str | None = None
    max_items: int | None = None
    min_items: int | None = None
    unique_items: bool | None = None
    max_contains: int | None = None
    min_contains: int | None = None
    max_properties: int | None = None
    min_properties: int | None = None
    required: list[str] | None = None
    dependent_required: dict[str, list[str]] | None = None
    title: str | None = None
    description: str | None = None
    default: Any = MISSING
    deprecated: bool | None = None
    read_only: bool | None = None
    write_only: bool | None = None
    examples: list[Any] | None = None
    format: str | None = None
    content_encoding: str | None = None
    content_media_type: str | None = None
    content_schema: Schema | None = None
    extra: dict[str, Any] = field(default_factory=dict[str, Any])
```

````text
An object-form JSON Schema (Draft 2020-12).

All keywords are optional. `None` marks an absent keyword for every field
except `const` / `default`, which use `MISSING` so that an explicit
JSON `null` is representable. Unknown keywords survive in `extra`.
````

#### `JsonSchema.to_dict` { #ocai-core-jsonschema-jsonschema-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize to a plain JSON Schema dict, omitting absent keywords.
````

#### `JsonSchema.from_dict` { #ocai-core-jsonschema-jsonschema-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> JsonSchema
```

````text
Build from a plain JSON Schema dict; unknown keys land in `extra`.
````

### `Schema` { #ocai-core-jsonschema-schema }

```python
type Schema = JsonSchema | bool
```

### `DataSchema` { #ocai-core-jsonschema-dataschema }

```python
type DataSchema = Schema
```

## `ocai.core.primitives`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/primitives.py)

### `ValueType` { #ocai-core-primitives-valuetype }

```python
class ValueType(str, Enum):
    NULL = 'NULL'
    NUMBER = 'NUMBER'
    INTEGER = 'INTEGER'
    STRING = 'STRING'
    BOOLEAN = 'BOOLEAN'
    OBJECT = 'OBJECT'
    ARRAY = 'ARRAY'
```

````text
Enumeration of the JSON value categories a `Value` can carry.

Members mirror the JSON type system; each maps to a concrete Python type
via the module-level `_VALUE_TYPE_MAPPER`.

Attributes:
    NULL: The JSON null value (`None` in Python).
    NUMBER: A floating-point number.
    INTEGER: An integer.
    STRING: A text string.
    BOOLEAN: A boolean.
    OBJECT: A JSON object (a `dict`).
    ARRAY: A JSON array (a `list`).
````

### `Primitive` { #ocai-core-primitives-primitive }

```python
type Primitive = int | float | bool | str | dict[str, Any] | list[Any] | None
```

### `Value` { #ocai-core-primitives-value }

```python
class Value:
    type: ValueType
    value: T
```

````text
A primitive value paired with its declared `ValueType` tag.

The generic parameter `T` records the Python type of the carried value; it
defaults to the full `Primitive` union.

Attributes:
    type: The declared `ValueType` describing the value's category.
    value: The carried primitive data.
````

#### `Value.to_dict` { #ocai-core-primitives-value-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize to a plain dict with the tag's string value.

Returns:
    A dict with `type` (the enum's string value) and the raw `value`.
````

#### `Value.from_dict` { #ocai-core-primitives-value-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Value` from a serialized dict.

Args:
    data: A mapping with `type` (a `ValueType` string) and `value`.

Returns:
    A new `Value` with the parsed type tag and carried value.
````

#### `Value.is_valid` { #ocai-core-primitives-value-is-valid }

```python
def is_valid(self, *, error: bool=False) -> bool
```

````text
Check that the carried value matches its declared `type`.

Args:
    error: If true, raise instead of returning False on a mismatch.

Returns:
    True if `value` is an instance of the Python type mapped from
    `type`, otherwise False.

Raises:
    TypeError: If the value does not match its declared type and
        `error` is true.
````

## `ocai.core.profile`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/profile.py)

### `Support` { #ocai-core-profile-support }

```python
class Support(str, Enum):
    NATIVE = 'native'
    EMULATED = 'emulated'
    ABSENT = 'absent'
```

````text
How a provider interface supports one feature for a model family.

Attributes:
    NATIVE: The interface implements the feature first-class.
    EMULATED: ocai can reproduce the effect by other means; using it
        emits an `EMULATED` disposition (and usually a `SemanticShift`).
    ABSENT: Not available and not emulable; strict mode refuses, annotate
        mode reports the loss.
````

### `CapabilityProfile` { #ocai-core-profile-capabilityprofile }

```python
class CapabilityProfile:
    provider: str
    interface: str
    model_pattern: str
    features: dict[str, Support] = field(default_factory=dict[str, Support])
```

````text
Declared feature support for one `(provider, interface, model_pattern)`.

A frozen fact sheet, registered via a plugin's `CatalogFragment` and
looked up by the feature gate with the concrete model name at call time.
Multiple profiles for one interface may coexist with different
`model_pattern`s; the catalog ranks the matches most-specific-first
(`Catalog.profiles_for`) and the gate layers them — the first profile
declaring a feature key wins (`resolve_support`).

Attributes:
    provider: The provider the facts are about (e.g. `"anthropic"`).
    interface: The interface within the provider (e.g. `"messages"`).
    model_pattern: A glob-style pattern selecting the models the facts
        apply to (e.g. `"claude-4*"`, `"*"` for interface-wide facts).
    features: The declared mapping from namespaced feature key to its
        `Support` level. Treat as immutable — profiles are facts, not
        state.
````

#### `CapabilityProfile.matches` { #ocai-core-profile-capabilityprofile-matches }

```python
def matches(self, model: str) -> bool
```

````text
Return whether this profile's `model_pattern` covers `model`.

Args:
    model: The concrete model name from the request.

Returns:
    True when `model` falls inside `model_pattern`.
````

#### `CapabilityProfile.check_feature` { #ocai-core-profile-capabilityprofile-check-feature }

```python
def check_feature(self, feature: str, model: str) -> Support
```

````text
Return the declared support level for `feature` on `model`.

The single-profile half of the feature gate: called before payload
conversion so an `ABSENT` feature can be refused (strict) or
loss-recorded (annotate) without ever building a doomed request.

Undeclared policy (normative): a feature key absent from `features`
resolves to `Support.NATIVE`. Profiles declare *exceptions* — the
absence of a declared limitation is not a limitation. Defaulting the
other way would force every profile to enumerate the whole open
feature universe (impossible: keys are namespaced open data), and
this default is what keeps profiles additive — declaring a new fact
never changes the meaning of the ones already shipped.

Args:
    feature: The namespaced feature key (e.g.
        `"chat.config.temperature"`).
    model: The concrete model name the request targets.

Returns:
    The declared `Support` for the feature, or `Support.NATIVE` when
    this profile declares nothing about it.

Raises:
    LookupError: When `model` does not match this profile's pattern.
````

### `resolve_support` { #ocai-core-profile-resolve-support }

```python
def resolve_support(profiles: Sequence[CapabilityProfile], feature: str) -> Support
```

````text
Resolve one feature key across specificity-ranked profiles.

The layering rule of the feature gate: `profiles` is expected
most-specific-first (the order `Catalog.profiles_for` returns), the first
profile that *declares* `feature` wins, and a key no profile declares
resolves to `Support.NATIVE` — the same undeclared policy as
`CapabilityProfile.check_feature`, applied across the stack (a specific
sheet that is silent about a key never masks the interface-wide sheet
that declares it).

Args:
    profiles: The matching profiles, most specific first.
    feature: The namespaced feature key to resolve.

Returns:
    The first declared `Support`, or `Support.NATIVE` when undeclared
    everywhere.
````

### `declared_support` { #ocai-core-profile-declared-support }

```python
def declared_support(profiles: Sequence[CapabilityProfile], feature: str) -> Support | None
```

````text
Return an explicit declaration, or None for unqualified/unknown coverage.

Unlike the legacy permissive gate, public inspection never treats silence
as proof of native support. Profiles must already be specificity-ranked.
````

## `ocai.core.refs`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/refs.py)

### `Replay` { #ocai-core-refs-replay }

```python
class Replay(str, Enum):
    OPTIONAL = 'optional'
    REQUIRED = 'required'
```

````text
Whether a provider requires an anchor to be replayed verbatim.

Attributes:
    OPTIONAL: The anchor is useful context (an id the caller *may* reuse);
        losing it degrades continuity but requests still succeed.
    REQUIRED: The provider rejects follow-up requests that omit the
        anchor. Planner cost treats dropping it as breakage.
````

### `RefScope` { #ocai-core-refs-refscope }

```python
class RefScope:
    INTERFACE: Final = 'interface'
    PROVIDER: Final = 'provider'
    MODEL: Final = 'model'
```

````text
Canonical constants for the open `ProviderRef.scope` code.

The scope names the boundary a ref is valid within, and therefore which
conversions must report crossing it (the scoped honesty rule in the
module docstring). Open: unknown scopes pass through verbatim and are
treated as interface-scoped — the narrowest, most honest reading.

Attributes:
    INTERFACE: Valid within the one `(provider, interface)` that minted
        it (response ids, thought signatures) — the default.
    PROVIDER: Valid across the provider's sibling interfaces (OpenAI
        file ids work from `chat_completions`, `responses`, and
        `batch`).
    MODEL: Bound to one resource below the interface (Gemini
        `cachedContents`); `ProviderRef.qualifier` names it.
````

### `ProviderRef` { #ocai-core-refs-providerref }

```python
class ProviderRef:
    provider: str
    interface: str
    kind: str
    id: str
    replay: Replay = Replay.OPTIONAL
    scope: str = RefScope.INTERFACE
    qualifier: str | None = field(default=None, kw_only=True)
```

````text
A name for state that lives on one provider's side.

`scope` declares the validity boundary, and the graph enforces the
scoped honesty rule against it: an interface-scoped ref is `UNSUPPORTED`
crossing any other `(provider, interface)`; a provider-scoped ref
survives same-provider sibling-interface crossings unreported and is
`UNSUPPORTED` across providers; a model-scoped ref is additionally
breakage when the bound resource (`qualifier`) changes.

Attributes:
    provider: The provider that minted the ref (e.g. `"openai"`).
    interface: The interface within the provider (e.g. `"responses"`).
    kind: An open code for what the ref names — canonical constants
        include `"response_id"`, `"file"`, `"thought_signature"`,
        `"audio_id"`.
    id: The provider's opaque identifier, verbatim.
    replay: Whether the provider requires the ref back on follow-ups.
    scope: The open validity-scope code; constants on `RefScope`.
        Defaults to interface-scoped, the narrowest reading.
    qualifier: The bound resource for model-scoped refs (e.g. the model
        name a Gemini `cachedContent` was minted against); None for
        wider scopes.
````

#### `ProviderRef.to_dict` { #ocai-core-refs-providerref-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the ref to a plain JSON-compatible dict, omit-absent.

The default `scope` (`"interface"`) and an unset `qualifier` are
omitted — the exact inverse of `from_dict`'s absent-means-interface
reading, so pre-scope payloads round-trip byte-identically.

Returns:
    A dict with `provider`, `interface`, `kind`, `id`, the `replay`
    string value, and the non-default `scope`/`qualifier` when set.
````

#### `ProviderRef.from_dict` { #ocai-core-refs-providerref-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `ProviderRef` from a serialized dict, totally.

Tolerant per the total-decode rule: an unknown `replay` value falls
back to `Replay.OPTIONAL` rather than raising, and `scope` is an
open code — unknown values are kept verbatim; an absent scope reads
as `"interface"` (the narrowest boundary).

Args:
    data: A mapping with `provider`, `interface`, `kind`, `id`, and
        the optional `replay`/`scope`/`qualifier`.

Returns:
    The decoded `ProviderRef`.
````

## `ocai.core.result`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/result.py)

### `CallResult` { #ocai-core-result-callresult }

```python
class CallResult:
    value: T
    route: Route | None = None
    report: FidelityReport | None = None
    usage: Usage | None = None
    raw: Any | None = None
    host_evidence: HostEvidence | None = field(default=None, kw_only=True)
```

````text
The uniform envelope every capability port returns.

Assembled by the wire-backed facade after decode (route from
`Catalog.resolve`, report merged across the request and response
conversion legs) or built directly by an in-process adapter (which may
leave `route` as None or stamp `route.host = "in-process"`).
Port-tier `CallInterceptor`s see and may replace it wholesale — that is
how fallback and semantic caching compose without touching payloads.

Attributes:
    value: The capability payload — `ChatResponse`, `list[Embedding]`, …
    route: What ocai decided (node, pins, reason, catalog hash), or None
        for adapters that perform no resolution.
    report: THE fidelity account for this call. Payloads stay pure; the
        report has exactly this one home.
    usage: The capability's consumption record — the core-owned
        dimensional `Usage` model, uniform across capabilities.
    raw: The untouched provider response body for power users — never
        contains credentials.
    host_evidence: Optional detached native response and host metadata. Not part
        of the canonical payload and never automatically exported by observers.
````

### `CallContext` { #ocai-core-result-callcontext }

```python
class CallContext:
    tenant: str | None = None
    principal: str | None = None
    classification: str | None = None
    deadline: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict[str, str])
    extensions: dict[str, Any] = field(default_factory=dict[str, Any])
    compartment: str | None = None
    call_id: str | None = None
    parent_id: str | None = None
    correlation_id: str | None = None
```

````text
The per-request governance carrier threaded through every port.

Passed as the optional `ctx` keyword on port methods, seen by every
`CallInterceptor` and policy hook on the way down, and available to
observers on the way back up. It carries *facts about the caller and the
call*, never payload data and never credentials.

Attributes:
    compartment: Trusted isolation scope established by the platform.
    call_id: Optional logical invocation identifier.
    parent_id: Optional parent invocation identifier.
    correlation_id: Optional application correlation identifier.
    tenant: The tenancy the call is made on behalf of.
    principal: The end user or service identity initiating the call.
    classification: A data-classification label for the payload
        (e.g. `"pii"`, `"public"`) that routing policy can gate on.
    deadline: An absolute wall-clock deadline for the whole call,
        including retries. Must be timezone-aware; wire drivers enforce
        the remaining budget and reject late results. Synchronous custom
        transports must cooperate with request timeouts.
    tags: Free-form string labels for tracing/metering dimensions.
    extensions: A namespaced bag for enterprise-specific context fields
        that have no first-class slot (same namespacing convention as IR
        `extensions`).
````

#### `CallContext.to_dict` { #ocai-core-result-callcontext-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the context to a plain JSON-compatible dict.

Returns:
    A dict of the set fields; the `deadline` is ISO-8601 formatted.
````

### `StreamOutcome` { #ocai-core-result-streamoutcome }

```python
class StreamOutcome:
    status: Literal['completed', 'closed', 'cancelled', 'failed', 'incomplete']
    usage: Usage | None = None
    report: FidelityReport | None = None
    error: BaseException | None = None
```

````text
Execution evidence, separate from the successful canonical StreamEnd.

Missing usage means unknown, never zero. An incomplete or failed outcome
may retain usage and conversion findings without claiming completion.
This is a local execution contract, not a new canonical chunk or revision.
````

## `ocai.core.sources`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/sources.py)

### `SourceType` { #ocai-core-sources-sourcetype }

```python
class SourceType(str, Enum):
    UNDEFINED = 'undefined'
    BASE64 = 'base64'
    URL = 'url'
    REF = 'ref'
```

````text
Canonical discriminator tags for the core `Source` variants.

Constants for the tags core ships — the union itself stays open through
`SOURCE_REGISTRY` (unknown tags decode to `SourceUnknown`, and plugins
may register namespaced tags).

Attributes:
    UNDEFINED: No source kind set (the unknown/placeholder tag).
    BASE64: An inline base64-encoded payload (`SourceBase64`).
    URL: A remote URL reference (`SourceUrl`).
    REF: A provider-hosted file handle (`SourceRef`).
````

### `MimeType` { #ocai-core-sources-mimetype }

```python
type MimeType = str
```

### `SourceBase64` { #ocai-core-sources-sourcebase64 }

```python
class SourceBase64(IRObject):
    object: ClassVar[str] = 'source'
    data: str
    mime_type: str | MimeType | None = field(default=None)
    type: Literal[SourceType.BASE64] = field(default=SourceType.BASE64)
```

````text
A media source carrying an inline base64-encoded payload.

Attributes:
    data: The base64-encoded media payload.
    mime_type: The media MIME type, or None if unknown.
    type: The source discriminator, fixed to `SourceType.BASE64`.
````

#### `SourceBase64.from_dict` { #ocai-core-sources-sourcebase64-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `SourceBase64` from a serialized dict.

Args:
    data: A mapping with the base64 `data`, an optional `mime_type`,
        and the common IR envelope fields.

Returns:
    A new `SourceBase64` instance.
````

### `SourceUrl` { #ocai-core-sources-sourceurl }

```python
class SourceUrl(IRObject):
    object: ClassVar[str] = 'source'
    url: str
    mime_type: str | MimeType | None = field(default=None)
    type: Literal[SourceType.URL] = field(default=SourceType.URL)
```

````text
A media source referencing remote content by URL.

Attributes:
    url: The URL of the remote media.
    mime_type: The media MIME type, or None if unknown.
    type: The source discriminator, fixed to `SourceType.URL`.
````

#### `SourceUrl.from_dict` { #ocai-core-sources-sourceurl-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `SourceUrl` from a serialized dict.

Args:
    data: A mapping with the `url`, an optional `mime_type`, and the
        common IR envelope fields.

Returns:
    A new `SourceUrl` instance.
````

### `SourceRef` { #ocai-core-sources-sourceref }

```python
class SourceRef(IRObject):
    object: ClassVar[str] = 'source'
    ref: ProviderRef
    mime_type: str | MimeType | None = field(default=None)
    type: Literal[SourceType.REF] = field(default=SourceType.REF)
```

````text
A media source held on a provider's side, named by a `ProviderRef`.

Used for uploaded-file handles (OpenAI `file_id`, Gemini Files API
names, Anthropic Files). The `ref`'s `scope` bounds where the handle is
valid — converting a request carrying one beyond that scope reports
`UNSUPPORTED` (the scoped honesty rule in `ocai.core.refs`).

Attributes:
    ref: The provider-side handle.
    mime_type: The media MIME type, or None if unknown.
    type: The source discriminator, fixed to `SourceType.REF`.
````

#### `SourceRef.from_dict` { #ocai-core-sources-sourceref-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `SourceRef` from a serialized dict.

Tolerates the pre-freeze `media_type` key (the field's name before
the rename that aligned it with its `SourceBase64`/`SourceUrl`
siblings): the value is accepted into `mime_type` and kept out of
the `extensions` sweep, so old payloads decode losslessly while new
payloads encode only `mime_type`.

Args:
    data: A mapping with the nested `ref`, an optional `mime_type`
        (or legacy `media_type`), and the common IR envelope fields.

Returns:
    A new `SourceRef` instance.
````

### `SourceUnknown` { #ocai-core-sources-sourceunknown }

```python
class SourceUnknown(IRObject):
    object: ClassVar[str] = 'source'
    data: dict[str, Any] = field(default_factory=dict[str, Any])
    type: str = SourceType.UNDEFINED.value
```

````text
Decoder fallback for a source tag this revision does not know.

Preserves the payload verbatim (byte-faithful through `to_dict`) so an
unknown source survives decode/encode untouched and can be upgraded
later via IR self-migration edges. Strictly a *future-canonical-tag*
fallback — total decode's safety net, never constructed deliberately.

Attributes:
    data: The verbatim serialized payload, including its original tag.
    type: The unrecognized discriminator value, preserved verbatim.
````

#### `SourceUnknown.to_dict` { #ocai-core-sources-sourceunknown-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize back to the verbatim payload this instance preserved.

Returns:
    A copy of the original serialized mapping, untouched.
````

#### `SourceUnknown.from_dict` { #ocai-core-sources-sourceunknown-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Preserve an unrecognized source payload verbatim.

Args:
    data: The serialized mapping whose tag no registered source
        matched.

Returns:
    A new `SourceUnknown` carrying the payload untouched.
````

### `Source` { #ocai-core-sources-source }

```python
type Source = SourceBase64 | SourceUrl | SourceRef | SourceUnknown
```

### `SOURCE_REGISTRY` { #ocai-core-sources-source-registry }

```python
SOURCE_REGISTRY: TagRegistry[Any] = TagRegistry(unknown=SourceUnknown)
```

### `cast_source` { #ocai-core-sources-cast-source }

```python
def cast_source(data: dict[str, Any]) -> Source
```

````text
Decode a serialized source into its concrete `Source` variant.

Dispatches on the `type` tag via `SOURCE_REGISTRY`; unknown tags decode
to `SourceUnknown` — this function never raises on unknown input.

Args:
    data: The serialized source mapping, including its `type`
        discriminator.

Returns:
    The decoded `Source` variant.
````

## `ocai.core.traits`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/traits.py)

### `HeaderBodyMapping` { #ocai-core-traits-headerbodymapping }

```python
class HeaderBodyMapping:
    header: str
    field: str
    separator: str | None = None
```

````text
Declare how one feature header becomes a host body field.

Attributes:
    header: Feature header name, compared case-insensitively.
    field: Destination top-level body field.
    separator: Split into a string array on this separator, trimming surrounding
        whitespace. None preserves a scalar verbatim. Empty items are invalid.
````

### `DialectTraits` { #ocai-core-traits-dialecttraits }

```python
class DialectTraits:
    vendor: str
    first_party_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    cloud_body_version: tuple[str, str] | None = None
    first_party_base_url: str | None = None
    version_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    feature_headers: Mapping[str, str] = field(default_factory=dict[str, str])
    host_body_versions: Mapping[str, tuple[str, str] | None] = field(default_factory=dict[str, tuple[str, str] | None])
    host_feature_body_mappings: Mapping[str, tuple[HeaderBodyMapping, ...]] = field(default_factory=dict[str, tuple[HeaderBodyMapping, ...]])
```

````text
Hosting-relevant facts a dialect declares **as data**, read by any host.

This is how the genuine (dialect, host) coupling — e.g. "Anthropic on a
cloud needs `anthropic_version` in the body" — is expressed without a
per-pair class. A host reads these traits generically, so the coupling
costs a few fields, not a new combination of code. Plugins ship one
`DialectTraits` per interface subpackage, registered into their
`CatalogFragment`.

Attributes:
    vendor: The publisher/provider identifier a cloud host uses to address
        the dialect (Vertex `publishers/<vendor>`, Bedrock provider id) and
        the default transport `provider` tag. E.g. `"anthropic"`, `"openai"`.
    first_party_headers: Headers the dialect requires when talked to
        directly (first-party), e.g. Anthropic's `anthropic-version`. A
        cloud host is free to ignore these (it owns its own header policy).
    cloud_body_version: An optional `(field, value)` a cloud host injects
        into the request body in place of a first-party version header
        (e.g. `("anthropic_version", "vertex-2023-10-16")`). `None` for
        dialects that need no such injection.
    first_party_base_url: The dialect's first-party API origin (e.g.
        `"https://api.openai.com"`, no trailing slash), or `None` for a
        dialect with no public first-party endpoint. Hosting data riding
        the fragment (§3.4/§7): the core front door composes a `Direct`
        binding from it without ever importing the plugin; a cloud or
        gateway host ignores it.
    version_headers: Explicit first-party wire-version headers; override the
        legacy header bag case-insensitively.
    feature_headers: Explicit opt-in feature headers, separate from versions.
        Empty by default: declaring a mapping never enables a beta feature.
    host_body_versions: Host key to `(field, value)`; an explicit entry wins
        over `cloud_body_version`. A None entry disables the legacy fallback.
    host_feature_body_mappings: Host key to feature-header relocation rules.
        Only declared feature values are relocated; no credentials belong here.
````

#### `DialectTraits.request_headers` { #ocai-core-traits-dialecttraits-request-headers }

```python
def request_headers(self) -> dict[str, str]
```

````text
Return detached first-party headers, explicit groups over legacy values.

Legacy casing is retained when not overridden. Explicit names use lowercase
so a mixed-case fallback cannot become a second, contradictory header.
````

#### `DialectTraits.body_fields` { #ocai-core-traits-dialecttraits-body-fields }

```python
def body_fields(self, host: str) -> dict[str, str | list[str]]
```

````text
Resolve detached version and declared feature values for one host.

Args:
    host: Explicit host key, such as `vertex` or `bedrock`.

Returns:
    Top-level field values for the host envelope, without modifying input.

Raises:
    ValueError: A split feature value contains an empty item.
````

## `ocai.core.usage`

[Source](https://github.com/ocarinow/ocai/blob/main/python/packages/ocai-core/src/ocai/core/usage.py)

### `UsageModality` { #ocai-core-usage-usagemodality }

```python
class UsageModality:
    TEXT: Final = 'text'
    IMAGE: Final = 'image'
    AUDIO: Final = 'audio'
    VIDEO: Final = 'video'
```

````text
Canonical constants for the open `Consumption.modality` code.

Attributes:
    TEXT: Text content.
    IMAGE: Image content.
    AUDIO: Audio content.
    VIDEO: Video content.
````

### `UsageUnit` { #ocai-core-usage-usageunit }

```python
class UsageUnit:
    TOKENS: Final = 'tokens'
    CHARACTERS: Final = 'characters'
    REQUESTS: Final = 'requests'
    SEARCH_REQUESTS: Final = 'search_requests'
    SAMPLES: Final = 'samples'
    CURRENCY: Final = 'currency'
```

````text
Canonical constants for the open `Consumption.unit` code.

Attributes:
    TOKENS: Counted in tokens (was `"token"` in the pre-2026-07 IR; the
        plural is canonical now).
    CHARACTERS: Counted in characters.
    REQUESTS: Counted in requests.
    SEARCH_REQUESTS: Provider-reported billable search operations, not tokens or results.
    SAMPLES: Counted in samples.
    CURRENCY: Reserved for gateway-reported cost; the value is an
        amount and the consumption's `extensions` carry the currency
        code. First-party cost stays an interceptor concern.
````

### `UsageSource` { #ocai-core-usage-usagesource }

```python
class UsageSource:
    INPUT: Final = 'input'
    OUTPUT: Final = 'output'
    REASONING: Final = 'reasoning'
    CACHED: Final = 'cached'
```

````text
Canonical constants for the open `Consumption.source` code.

The buckets are disjoint by the normalization rule: a token belongs to
exactly one source.

Attributes:
    INPUT: Prompt consumption, excluding cache reads.
    OUTPUT: Completion consumption, excluding itemized reasoning.
    REASONING: Reasoning/thinking consumption, where the provider
        itemizes it.
    CACHED: Cache-read input consumption.
````

### `Consumption` { #ocai-core-usage-consumption }

```python
class Consumption:
    modality: str
    unit: str
    source: str
    value: int | float | str
```

````text
One measured quantity, pinned to the dimensions that give it meaning.

Attributes:
    modality: The open code for what kind of content was consumed;
        constants on `UsageModality`.
    unit: The open code for how the value is counted; constants on
        `UsageUnit`.
    source: The open code for which disjoint bucket of the call this
        belongs to; constants on `UsageSource`.
    value: The consumed amount.
````

#### `Consumption.to_dict` { #ocai-core-usage-consumption-to-dict }

```python
def to_dict(self) -> dict[str, Any]
```

````text
Serialize the consumption to a plain JSON-compatible dict.

Returns:
    A dict with `value`, `modality`, `unit`, and `source`.
````

#### `Consumption.from_dict` { #ocai-core-usage-consumption-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Consumption` from a serialized dict, totally.

The dimensions are open codes, so unknown strings pass through
verbatim — never coerced, never raised on.

Args:
    data: A mapping with `value` and the three dimension codes.

Returns:
    The decoded `Consumption`.
````

### `Usage` { #ocai-core-usage-usage }

```python
class Usage(IRObject):
    object: ClassVar[str] = 'usage'
    consumptions: list[Consumption] = field(default_factory=list[Consumption], kw_only=True)
```

````text
Aggregated consumption for one call — the capability's usage record.

Built by the response codec (or, for streams, folded by the
`StreamAccumulator` with the terminal `StreamEnd.usage` authoritative)
and delivered on `CallResult.usage`. The accessor properties are views
over the disjoint buckets; they never store anything.

Attributes:
    consumptions: The measured consumptions for the call, in report
        order.
````

#### `Usage.input_tokens` { #ocai-core-usage-usage-input-tokens }

```python
@property
def input_tokens(self) -> int
```

````text
Return the non-cached prompt tokens consumed.
````

#### `Usage.output_tokens` { #ocai-core-usage-usage-output-tokens }

```python
@property
def output_tokens(self) -> int
```

````text
Return the completion tokens consumed, excluding reasoning.
````

#### `Usage.reasoning_tokens` { #ocai-core-usage-usage-reasoning-tokens }

```python
@property
def reasoning_tokens(self) -> int
```

````text
Return the itemized reasoning tokens consumed.
````

#### `Usage.cached_input_tokens` { #ocai-core-usage-usage-cached-input-tokens }

```python
@property
def cached_input_tokens(self) -> int
```

````text
Return the cache-read input tokens consumed.
````

#### `Usage.total_tokens` { #ocai-core-usage-usage-total-tokens }

```python
@property
def total_tokens(self) -> int
```

````text
Return every token consumed, across all disjoint buckets.

A plain sum — valid precisely because the normalization rule makes
the buckets disjoint.
````

#### `Usage.from_dict` { #ocai-core-usage-usage-from-dict }

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> Self
```

````text
Build a `Usage` from a serialized dict, totally.

Args:
    data: A mapping with `consumptions` and the common IR envelope
        keys.

Returns:
    The decoded `Usage`.
````
