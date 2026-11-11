"""Fixed authenticated endpoints with sanitized and correlated error responses."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from starlette.requests import Request

from app.authorization.openfga import AuthorizationUnavailable
from app.authorization.service import AccessDenied
from app.identity.dependencies import authenticated_identity
from app.identity.issuer import ExternalIdentity
from app.management.service import IdentityView
from app.management.service import Management
from app.management.service import OrganizationPatch
from app.management.service import OrganizationView
from app.management.service import UnboundPrincipal
from app.middleware.errors import ErrorEnvelope
from app.storage.database import StorageError
from app.storage.repository import StaleWrite

router = APIRouter(
    prefix="/management/v1",
    responses={status: {"model": ErrorEnvelope} for status in (401, 403, 404, 409, 422, 503)},
)


def management(request: Request) -> Management:
    """Require explicitly initialized product services; no global registry or lazy migration."""
    service = getattr(request.app.state, "management", None)
    if not isinstance(service, Management):
        raise HTTPException(503)
    return service


async def record_denial(
    request: Request,
    target: UUID | None,
    outcome: Literal["unauthenticated", "denied"],
) -> None:
    """Record only allowlisted security metadata through a separate failed-access transaction."""
    action: Literal["organization.read", "organization.update", "identity.read"] = "identity.read"
    if request.url.path != "/management/v1/me":
        action = "organization.update" if request.method == "PATCH" else "organization.read"
    try:
        async with management(request).database.transaction() as repository:
            await repository.record_denial(
                request_id=UUID(request.state.request_id),
                target_id=target,
                action=action,
                outcome=outcome,
            )
    except StorageError:
        raise HTTPException(503) from None


async def identity(request: Request) -> ExternalIdentity:
    """Authenticate before resource handling; failed authentication has durable bounded evidence."""
    try:
        return await authenticated_identity(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            await record_denial(request, None, "unauthenticated")
        raise


@asynccontextmanager
async def guarded(request: Request, target: UUID | None = None) -> AsyncGenerator[Management]:
    """Map resource failures without exposing existence, provider bodies or database details.

    Yields:
        The configured management service.
    """
    try:
        yield management(request)
    except UnboundPrincipal:
        await record_denial(request, None, "denied")
        raise HTTPException(403) from None
    except AccessDenied:
        await record_denial(request, target, "denied")
        raise HTTPException(404) from None
    except StaleWrite:
        raise HTTPException(409) from None
    except (StorageError, AuthorizationUnavailable):
        raise HTTPException(503) from None


@router.get("/me", operation_id="get_current_identity")
async def me(
    request: Request, caller: Annotated[ExternalIdentity, Depends(identity)]
) -> IdentityView:
    """Return the active platform binding and authorized organization summaries."""
    async with guarded(request) as service:
        return await service.me(caller)


@router.get("/organizations/{organization_id}", operation_id="get_organization")
async def organization(
    organization_id: UUID,
    request: Request,
    caller: Annotated[ExternalIdentity, Depends(identity)],
) -> OrganizationView:
    """Read the current authorized version of one organization."""
    async with guarded(request, organization_id) as service:
        return await service.read(caller, organization_id)


@router.patch("/organizations/{organization_id}", operation_id="update_organization")
async def update_organization(
    organization_id: UUID,
    patch: OrganizationPatch,
    request: Request,
    caller: Annotated[ExternalIdentity, Depends(identity)],
) -> OrganizationView:
    """Rename one organization with optimistic versioning and transactional audit."""
    async with guarded(request, organization_id) as service:
        return await service.update(caller, organization_id, patch, UUID(request.state.request_id))
