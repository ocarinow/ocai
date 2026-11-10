"""A separately packaged, conversion-only community plugin.

Importing builds FRAGMENT without mutating any shared catalog. Applications
compose it explicitly or discover the installed ocai.fragments entry point.
There is no live chat component or streaming adapter.
"""

from ocai.contrib.echo.codec import EchoChatCodec
from ocai.contrib.echo.fragment import ECHO_CHAT_REQUEST
from ocai.contrib.echo.fragment import ECHO_CHAT_RESPONSE
from ocai.contrib.echo.fragment import ECHO_ORIGIN
from ocai.contrib.echo.fragment import FRAGMENT

__all__ = [
    "ECHO_CHAT_REQUEST",
    "ECHO_CHAT_RESPONSE",
    "ECHO_ORIGIN",
    "FRAGMENT",
    "EchoChatCodec",
]
