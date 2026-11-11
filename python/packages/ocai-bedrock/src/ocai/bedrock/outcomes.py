"""Bedrock-native outcome mapping behind provider-neutral host contracts."""

from __future__ import annotations

from typing import Any

from ocai.convert import DeclaredDisposition
from ocai.convert.host_effects import HostEffectContract
from ocai.core import AuthError
from ocai.core import ContentFilterError
from ocai.core import Disposition
from ocai.core import FieldLoss
from ocai.core import OcaiError
from ocai.core import RateLimitError
from ocai.core import SemanticShift
from ocai.core import TransientError
from ocai.core.ir import is_json_array
from ocai.core.ir import is_json_object
from ocai.wire.http import HttpResponse
from ocai.wire.outcomes import HostAdaptation
from ocai.wire.outcomes import HostErrorMapper
from ocai.wire.outcomes import HostResponseAdapter


def _native_error(error: OcaiError, options: dict[str, Any]) -> OcaiError | None:
    headers = {key.lower(): value for key, value in (error.response_headers or {}).items()}
    raw = error.raw or {}
    native = headers.get("x-amzn-errortype") or raw.get("__type") or raw.get("code")
    if not isinstance(native, str) or not native:
        return None
    name = native.split(":", 1)[0].rsplit("#", 1)[-1]
    error_type: type[OcaiError] | None = None
    if name in {"ThrottlingException", "ModelNotReadyException", "ServiceQuotaExceededException"}:
        error_type = RateLimitError
    elif name in {
        "ServiceUnavailableException",
        "InternalServerException",
        "InternalFailure",
        "ModelTimeoutException",
        "ModelStreamErrorException",
        "ModelErrorException",
    }:
        error_type = TransientError
    elif name in {
        "AccessDeniedException",
        "ExpiredTokenException",
        "UnrecognizedClientException",
        "NotAuthorized",
        "IncompleteSignature",
        "InvalidSignatureException",
    }:
        error_type = AuthError
    if error_type is None:
        error.code = native
        return error
    return error_type("Bedrock request failed", code=native)


def error_mapping() -> HostErrorMapper:
    """Build a detached native-code classifier; no status-only provider guessing."""
    return HostErrorMapper("bedrock.invoke-errors@1", _native_error)


def _assessment_actions(assessment: object) -> set[str]:
    actions: set[str] = set()
    if not is_json_object(assessment):
        return actions
    lanes = {
        "topicPolicy": ("topics",),
        "contentPolicy": ("filters",),
        "wordPolicy": ("customWords", "managedWordLists"),
        "sensitiveInformationPolicy": ("piiEntities", "regexes"),
    }
    for policy, names in lanes.items():
        record = assessment.get(policy)
        if not is_json_object(record):
            continue
        for name in names:
            values = record.get(name)
            if is_json_array(values):
                actions.update(
                    value["action"]
                    for value in values
                    if is_json_object(value) and isinstance(value.get("action"), str)
                )
    return actions


def _actions(trace: object) -> tuple[set[str], set[str]]:
    """Read documented assessment lanes only; modelOutput is never classified."""
    if not is_json_object(trace) or not is_json_object(guardrail := trace.get("guardrail")):
        return set(), set()
    input_actions: set[str] = set()
    input_root = guardrail.get("input")
    if is_json_object(input_root):
        for assessment in input_root.values():
            input_actions.update(_assessment_actions(assessment))
    output_actions: set[str] = set()
    outputs = guardrail.get("outputs")
    for root in outputs if is_json_array(outputs) else []:
        if is_json_object(root):
            for assessment in root.values():
                output_actions.update(_assessment_actions(assessment))
    return input_actions, output_actions


def _response(
    response: HttpResponse, payload: dict[str, Any], options: dict[str, Any]
) -> HostAdaptation:
    metadata: dict[str, Any] = {"body": {}, "headers": {}}
    losses: list[FieldLoss] = []
    for key in tuple(payload):
        if key.startswith("amazon-bedrock-"):
            metadata["body"][key] = payload.pop(key)
            losses.append(
                FieldLoss(
                    f"body[{key}]", Disposition.RENAMED, note="Preserved in host evidence metadata"
                )
            )
    for key, value in response.headers.items():
        if key.lower() in {
            "x-amzn-bedrock-service-tier",
            "x-amzn-bedrock-performanceconfig-latency",
        }:
            metadata["headers"][key.lower()] = value
            losses.append(
                FieldLoss(
                    f"headers[{key.lower()}]",
                    Disposition.RENAMED,
                    note="Preserved in host evidence metadata",
                )
            )
    action = metadata["body"].get("amazon-bedrock-guardrailAction")
    trace = metadata["body"].get("amazon-bedrock-trace")
    shifts: list[SemanticShift] = []
    error: OcaiError | None = None
    if action == "INTERVENED":
        input_actions, output_actions = _actions(trace)
        if "BLOCKED" in input_actions | output_actions:
            shifts.append(
                SemanticShift(
                    "bedrock.guardrail_blocked",
                    "response",
                    "An explicit guardrail assessment blocked the invocation",
                )
            )
            error = ContentFilterError(
                "Bedrock guardrail blocked the invocation", code="guardrail_intervened"
            )
        elif "ANONYMIZED" in output_actions:
            shifts.append(
                SemanticShift(
                    "bedrock.masked_output",
                    "response",
                    "An explicit guardrail assessment anonymized output",
                )
            )
        else:
            shifts.append(
                SemanticShift(
                    "bedrock.guardrail_intervened",
                    "response",
                    "Intervention is known; its exact effect is unqualified",
                )
            )
    elif action is not None and action != "NONE":
        shifts.append(
            SemanticShift(
                "bedrock.guardrail_intervened",
                "response",
                "Unknown guardrail action preserved without interpreting it",
            )
        )
    return HostAdaptation(payload, metadata, tuple(losses), tuple(shifts), error)


def response_mapping() -> HostResponseAdapter:
    """Declare unary host metadata and effects without changing Anthropic edges."""
    contract = HostEffectContract(
        census={
            "body[]": DeclaredDisposition(
                Disposition.RENAMED,
                "Only amazon-bedrock-* body members move into HostEvidence.metadata",
            ),
            "headers[]": DeclaredDisposition(
                Disposition.RENAMED,
                "Selected service-tier/performance headers copy into HostEvidence.metadata",
            ),
        },
        semantic_shifts=tuple(
            SemanticShift(kind, "response")
            for kind in (
                "bedrock.guardrail_blocked",
                "bedrock.masked_output",
                "bedrock.guardrail_intervened",
            )
        ),
    )
    return HostResponseAdapter("bedrock", "bedrock.invoke-response@1", _response, contract)
