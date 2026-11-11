"""DeepSeek identity and hosting facts, distinct from conversion qualification."""

from datetime import date

from ocai.core.identity import CHAT_CHUNK
from ocai.core.identity import CHAT_REQUEST
from ocai.core.identity import CHAT_RESPONSE
from ocai.core.identity import NodeId
from ocai.core.identity import Origin
from ocai.core.identity import Status
from ocai.core.profile import CapabilityProfile
from ocai.core.profile import Support
from ocai.core.traits import DialectTraits

PROVIDER = "deepseek"
INTERFACE = "chat_completions"
# Observation snapshot, not a vendor API version or model release.
TAG = "2026-11"
RELEASED = date(2026, 11, 11)
BASE_URL = "https://api.deepseek.com"
PATH = "/chat/completions"
MODEL_IDS = ("deepseek-flash", "deepseek-v4-pro")
ORIGIN = Origin(distribution="ocai-deepseek", version="0.1.0")

CHAT_COMPLETIONS_REQUEST = NodeId(PROVIDER, INTERFACE, TAG, CHAT_REQUEST, RELEASED, Status.STABLE)
CHAT_COMPLETIONS_RESPONSE = NodeId(PROVIDER, INTERFACE, TAG, CHAT_RESPONSE, RELEASED, Status.STABLE)
CHAT_COMPLETIONS_CHUNK = NodeId(PROVIDER, INTERFACE, TAG, CHAT_CHUNK, RELEASED, Status.STABLE)
NODES = (CHAT_COMPLETIONS_REQUEST, CHAT_COMPLETIONS_RESPONSE, CHAT_COMPLETIONS_CHUNK)
TRAITS = DialectTraits(vendor=PROVIDER, first_party_base_url=BASE_URL)
# Only independently qualified features are declared; media remains unknown.
PROFILES = tuple(
    CapabilityProfile(
        provider=PROVIDER,
        interface=INTERFACE,
        model_pattern=model,
        features={
            "chat.config.output.json_schema": Support.ABSENT,
            "chat.config.output.json": Support.NATIVE,
            "chat.parts.reasoning.replay": Support.NATIVE,
        },
    )
    for model in MODEL_IDS
)
