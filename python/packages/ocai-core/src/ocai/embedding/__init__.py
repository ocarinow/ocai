"""`ocai.embedding` — the embedding capability contract. [PROVISIONAL]

Status (architecture §9): **provisional** — this package does NOT freeze at
v0.2. The port and IR follow the uniform grammar (named request in,
`CallResult`-wrapped named response out, `CallContext` threaded through),
but they stay changeable until they carry `CallResult` in real use. Depend
on the shapes, expect the details to move.

Depends on `ocai.core` only, like every capability contract.
"""

from ocai.embedding.protocol import EmbeddingModel
from ocai.embedding.types import Document
from ocai.embedding.types import Embeddable
from ocai.embedding.types import Embedding
from ocai.embedding.types import EmbeddingRequest
from ocai.embedding.types import EmbeddingResponse
from ocai.embedding.types import Vector

__all__ = [
    "Document",
    "Embeddable",
    "Embedding",
    "EmbeddingModel",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "Vector",
]
