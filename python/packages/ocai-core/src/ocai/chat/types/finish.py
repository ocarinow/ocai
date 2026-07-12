"""Re-export shim for the finish vocabulary.

The vocabulary is core-owned since the capability stress-test: `FinishInfo`
and its detail union describe why *any* capability's run stopped (a chat
turn, an image generation, an async job's terminal state), so they live in
`ocai.core.finish`. Import from `ocai.core` going forward; this module only
keeps the historical `ocai.chat.types.finish` import path working.
"""

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

__all__ = [
    "DETAIL_REGISTRY",
    "DetailOpaque",
    "DetailType",
    "ErrorDetail",
    "FinishDetail",
    "FinishInfo",
    "FinishReason",
    "IncompleteDetail",
    "RefusalDetail",
    "SafetyDetail",
    "SafetyRating",
    "cast_detail",
]
