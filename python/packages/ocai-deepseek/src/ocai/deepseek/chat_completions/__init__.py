"""Independently qualified unary DeepSeek Chat Completions interface; no serveable component yet."""

from ocai.convert.catalog import CatalogFragment
from ocai.deepseek.chat_completions.descriptor import NODES
from ocai.deepseek.chat_completions.descriptor import ORIGIN
from ocai.deepseek.chat_completions.descriptor import PROFILES
from ocai.deepseek.chat_completions.descriptor import TRAITS
from ocai.deepseek.chat_completions.edges import EDGES

__all__ = ["FRAGMENT"]

FRAGMENT = CatalogFragment(
    origin=ORIGIN, nodes=NODES, profiles=PROFILES, traits=(TRAITS,), edges=EDGES
)
