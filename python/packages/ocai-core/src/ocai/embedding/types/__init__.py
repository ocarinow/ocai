"""[PROVISIONAL] The canonical embedding IR types.

The data shapes the `EmbeddingModel` port speaks: `Document` and the
`Embeddable` sugar union, `Embedding` with its `Vector` alias, and the
named `EmbeddingRequest`/`EmbeddingResponse` pair the reshaped port
exchanges inside `CallResult`.

Provisional per architecture §9: these freeze only after they carry
`CallResult` in real use.
"""

from ocai.embedding.types.document import Document
from ocai.embedding.types.document import Embeddable
from ocai.embedding.types.embedding import Embedding
from ocai.embedding.types.embedding import Vector
from ocai.embedding.types.request import EmbeddingRequest
from ocai.embedding.types.response import EmbeddingResponse

__all__ = [
    "Document",
    "Embeddable",
    "Embedding",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "Vector",
]
