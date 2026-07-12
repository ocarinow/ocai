"""`ocai.vectorstore` — the vector store capability contract. [PROVISIONAL]

Status (architecture §9): **provisional** — this package does NOT freeze at
v0.2. The port and IR follow the uniform grammar (`CallResult`-wrapped
named results, keyword-only mutations, one `filters` name, `CallContext`
threaded through), but they stay changeable until they carry `CallResult`
in real use. Depend on the shapes, expect the details to move.

Depends on `ocai.core` only, like every capability contract. Local adapters
(a future `ocai-faiss`) implement the port directly — local and remote are
peers at the port plane.
"""

from ocai.vectorstore.protocol import VectorStore
from ocai.vectorstore.types import QueryFilter
from ocai.vectorstore.types import QueryResult
from ocai.vectorstore.types import Record
from ocai.vectorstore.types import Vector

__all__ = [
    "QueryFilter",
    "QueryResult",
    "Record",
    "Vector",
    "VectorStore",
]
