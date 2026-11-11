"""Qualified DeepSeek unary execution through the standard chat front door."""

from ocai.convert.catalog import CatalogFragment
from ocai.convert.catalog import Component
from ocai.core.identity import CHAT
from ocai.deepseek.chat_completions.codec import DeepSeekCodec
from ocai.deepseek.chat_completions.descriptor import INTERFACE
from ocai.deepseek.chat_completions.descriptor import NODES
from ocai.deepseek.chat_completions.descriptor import ORIGIN
from ocai.deepseek.chat_completions.descriptor import PROFILES
from ocai.deepseek.chat_completions.descriptor import PROVIDER
from ocai.deepseek.chat_completions.descriptor import TRAITS
from ocai.deepseek.chat_completions.edges import EDGES

__all__ = ["FRAGMENT"]

FRAGMENT = CatalogFragment(
    origin=ORIGIN,
    nodes=NODES,
    profiles=PROFILES,
    traits=(TRAITS,),
    edges=EDGES,
    components=(
        Component(provider=PROVIDER, interface=INTERFACE, capability=CHAT, factory=DeepSeekCodec),
    ),
)
