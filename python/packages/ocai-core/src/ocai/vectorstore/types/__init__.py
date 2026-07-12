"""[PROVISIONAL] The canonical vector store types.

The data shapes the `VectorStore` port speaks: `Record` (the storage
unit), `QueryResult` (one similarity match), the local `Vector` alias, and
`QueryFilter` (the metadata-filter shape, always named `filters` at call
sites).

Provisional per architecture §9: these freeze only after they carry
`CallResult` in real use.
"""

from ocai.vectorstore.types.filter import QueryFilter
from ocai.vectorstore.types.record import QueryResult
from ocai.vectorstore.types.record import Record
from ocai.vectorstore.types.record import Vector

__all__ = [
    "QueryFilter",
    "QueryResult",
    "Record",
    "Vector",
]
