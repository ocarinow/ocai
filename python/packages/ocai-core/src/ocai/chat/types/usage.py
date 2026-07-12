"""Re-export shim for the dimensional usage vocabulary.

The vocabulary is core-owned since the capability stress-test: `Usage` and
`Consumption` generalize across capabilities (chat tokens, image seconds,
vector read-units), so they live in `ocai.core.usage`. Import from
`ocai.core` going forward; this module only keeps the historical
`ocai.chat.types.usage` import path working.
"""

from ocai.core.usage import Consumption
from ocai.core.usage import Usage
from ocai.core.usage import UsageModality
from ocai.core.usage import UsageSource
from ocai.core.usage import UsageUnit

__all__ = [
    "Consumption",
    "Usage",
    "UsageModality",
    "UsageSource",
    "UsageUnit",
]
