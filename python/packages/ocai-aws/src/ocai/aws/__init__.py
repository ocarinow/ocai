"""Explicit AWS credentials, independent of hosting and capability codecs."""

from ocai.aws.credentials import SigV4Credential

__all__ = ["SigV4Credential"]
