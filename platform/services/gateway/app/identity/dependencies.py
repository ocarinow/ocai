"""Reusable FastAPI identity dependency; no route becomes protected by implication."""

from fastapi import HTTPException
from starlette.requests import Request

from app.identity.issuer import ExternalIdentity
from app.identity.issuer import IdentityUnavailable
from app.identity.issuer import InvalidToken
from app.identity.issuer import TokenVerifier


async def authenticated_identity(request: Request) -> ExternalIdentity:
    """Require exactly one bearer credential and an explicitly configured verifier."""
    headers = request.headers.getlist("authorization")
    if len(headers) != 1:
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
    scheme, separator, credential = headers[0].partition(" ")
    if scheme.lower() != "bearer" or not separator or not credential or " " in credential:
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"})
    verifier = getattr(request.app.state, "identity_verifier", None)
    if not isinstance(verifier, TokenVerifier):
        raise HTTPException(503)
    try:
        return await verifier.verify(credential)
    except InvalidToken:
        raise HTTPException(401, headers={"WWW-Authenticate": "Bearer"}) from None
    except IdentityUnavailable:
        raise HTTPException(503) from None
