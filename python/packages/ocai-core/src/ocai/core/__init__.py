"""`ocai.core` — the contract layer.

Everything a user, plugin author, or auditor touches is a frozen,
zero-dependency data contract, and it lives here: nothing in this package
performs I/O, imports a third-party module, or knows HTTP exists. It is the
surface a bank audits once and the shapes the future TypeScript/Go ports
mirror from `spec/`.

The vocabulary, by module:

- `identity` — who is speaking: `Capability` → `Shape` → `NodeId` (the graph
  node) → `Origin` (provenance).
- `fidelity` — what conversion cost: `FieldLoss`, `SemanticShift`,
  `EdgeReport`, `FidelityReport`, and `Route` (what ocai decided).
- `result` — what every port returns: `CallResult`, plus the per-request
  governance carrier `CallContext`.
- `usage` — what a call consumed, in any capability: the dimensional
  `Consumption`/`Usage` model (hoisted from chat pre-freeze).
- `finish` — why a run stopped, in any capability: `FinishInfo`,
  `FinishReason`, and the detail union (hoisted from chat pre-freeze).
- `refs` — provider-anchored state: `ProviderRef` and its `Replay` rule.
- `profile` — declared capability facts: `CapabilityProfile` / `Support`.
- `ir` — the IR envelope (`IRObject`: omit-absent encode, tolerant decode)
  and the total-decode `TagRegistry`.
- `canonjson` — the one normative equality predicate: `canonical` /
  `semantic_equal`.
- `errors`, `credentials`, `jsonschema`, `sources`, `primitives` — the
  surviving taxonomy, explicit-only credentials, JSON Schema model, media
  sources, and tagged primitives.

Everything else in the library (capability contracts, the conversion catalog,
drivers, wire) is replaceable machinery *behind* these contracts and depends
downward on this package — never the reverse. `__version__` here is the
library's public-API semver, distinct from the canonical IR revision
(`CANONICAL_REVISION`, dated `ocai@YYYY-MM`) and from any provider interface
tag: three version axes, never conflated.
"""

from __future__ import annotations

from ocai.core.canonjson import canonical
from ocai.core.canonjson import semantic_equal
from ocai.core.credentials import ApiKey
from ocai.core.credentials import Credential
from ocai.core.credentials import CredentialError
from ocai.core.credentials import require_credential
from ocai.core.errors import AuthError
from ocai.core.errors import ContentFilterError
from ocai.core.errors import ContextLengthError
from ocai.core.errors import OcaiError
from ocai.core.errors import RateLimitError
from ocai.core.errors import TransientError
from ocai.core.errors import error_from_response
from ocai.core.fidelity import Disposition
from ocai.core.fidelity import EdgeReport
from ocai.core.fidelity import FidelityReport
from ocai.core.fidelity import FieldLoss
from ocai.core.fidelity import Route
from ocai.core.fidelity import SemanticShift
from ocai.core.fidelity import ShiftKind
from ocai.core.finish import DETAIL_REGISTRY
from ocai.core.finish import DetailOpaque
from ocai.core.finish import DetailType
from ocai.core.finish import ErrorDetail
from ocai.core.finish import FinishDetail
from ocai.core.finish import FinishInfo
from ocai.core.finish import FinishReason
from ocai.core.finish import IncompleteDetail
from ocai.core.finish import RefusalDetail
from ocai.core.finish import SafetyDetail
from ocai.core.finish import SafetyRating
from ocai.core.finish import cast_detail
from ocai.core.identity import CANONICAL_INTERFACE
from ocai.core.identity import CANONICAL_PROVIDER
from ocai.core.identity import CANONICAL_REVISION
from ocai.core.identity import CHAT
from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import EMBEDDING
from ocai.core.identity import VECTORSTORE
from ocai.core.identity import Capability
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import Shape
from ocai.core.identity import Status
from ocai.core.identity import canonical_node
from ocai.core.ir import DataClassProto
from ocai.core.ir import IRObject
from ocai.core.ir import TagRegistry
from ocai.core.jsonschema import MISSING
from ocai.core.jsonschema import JsonSchema
from ocai.core.jsonschema import Schema
from ocai.core.jsonschema import decode_schema
from ocai.core.jsonschema import encode_schema
from ocai.core.primitives import Primitive
from ocai.core.primitives import Value
from ocai.core.primitives import ValueType
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support
from ocai.core.refs import ProviderRef
from ocai.core.refs import Replay
from ocai.core.result import CallContext
from ocai.core.result import CallResult
from ocai.core.sources import SOURCE_REGISTRY
from ocai.core.sources import Source
from ocai.core.sources import SourceBase64
from ocai.core.sources import SourceRef
from ocai.core.sources import SourceType
from ocai.core.sources import SourceUnknown
from ocai.core.sources import SourceUrl
from ocai.core.sources import cast_source
from ocai.core.traits import DialectTraits
from ocai.core.usage import Consumption
from ocai.core.usage import Usage
from ocai.core.usage import UsageModality
from ocai.core.usage import UsageSource
from ocai.core.usage import UsageUnit

# Library public API version (semver). Kept stable across IR/wire changes.
__version__ = "0.1.0"

__all__ = [
    "CANONICAL_INTERFACE",
    "CANONICAL_PROVIDER",
    "CANONICAL_REVISION",
    "CHAT",
    "CHAT_CHUNK",
    "CHAT_REQUEST",
    "CHAT_RESPONSE",
    "DETAIL_REGISTRY",
    "EMBEDDING",
    "MISSING",
    "SOURCE_REGISTRY",
    "VECTORSTORE",
    "ApiKey",
    "AuthError",
    "CallContext",
    "CallResult",
    "Capability",
    "CapabilityProfile",
    "Consumption",
    "ContentFilterError",
    "ContextLengthError",
    "Credential",
    "DialectTraits",
    "CredentialError",
    "DataClassProto",
    "DetailOpaque",
    "DetailType",
    "Disposition",
    "EdgeReport",
    "ErrorDetail",
    "FidelityReport",
    "FieldLoss",
    "FinishDetail",
    "FinishInfo",
    "FinishReason",
    "IRObject",
    "IncompleteDetail",
    "JsonSchema",
    "NodeId",
    "OcaiError",
    "Origin",
    "Primitive",
    "ProviderRef",
    "RateLimitError",
    "RefusalDetail",
    "Replay",
    "Route",
    "SafetyDetail",
    "SafetyRating",
    "Schema",
    "SemanticShift",
    "Shape",
    "ShiftKind",
    "Source",
    "SourceBase64",
    "SourceRef",
    "SourceType",
    "SourceUnknown",
    "SourceUrl",
    "Status",
    "Support",
    "TagRegistry",
    "TransientError",
    "Usage",
    "UsageModality",
    "UsageSource",
    "UsageUnit",
    "Value",
    "ValueType",
    "__version__",
    "canonical",
    "canonical_node",
    "cast_detail",
    "cast_source",
    "decode_schema",
    "encode_schema",
    "error_from_response",
    "require_credential",
    "semantic_equal",
]
