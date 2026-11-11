"""Normalize measured DeepSeek buckets without inventing missing detail."""

from copy import deepcopy
from typing import Any

from ocai.core.fidelity import Disposition
from ocai.core.fidelity import FieldLoss
from ocai.core.ir import is_json_object
from ocai.core.usage import Consumption
from ocai.core.usage import Usage


def decode_usage(raw: Any, losses: list[FieldLoss]) -> Usage | None:
    """Keep aggregate counters when a disjoint breakdown cannot be established."""
    if raw is None:
        return None
    values: list[Consumption] = []
    uncertain = not is_json_object(raw)
    data = raw if is_json_object(raw) else {}

    def count(value: Any) -> int | None:
        nonlocal uncertain
        if value is None:
            return None
        if type(value) is int and value >= 0:
            return value
        uncertain = True
        return None

    def add(source: str, value: int | None) -> None:
        if value is not None:
            values.append(Consumption(modality="text", unit="tokens", source=source, value=value))

    prompt = count(data.get("prompt_tokens"))
    completion = count(data.get("completion_tokens"))
    hit = count(data.get("prompt_cache_hit_tokens"))
    miss = count(data.get("prompt_cache_miss_tokens"))
    prompt_details = data.get("prompt_tokens_details")
    completion_details = data.get("completion_tokens_details")
    cached = count(prompt_details.get("cached_tokens")) if is_json_object(prompt_details) else None
    reasoning = (
        count(completion_details.get("reasoning_tokens"))
        if is_json_object(completion_details)
        else None
    )
    input_conflict = hit is not None and cached is not None and hit != cached
    hit = hit if hit is not None else cached
    if prompt is not None and hit is not None and miss is not None and hit + miss != prompt:
        input_conflict = True
    if prompt is not None and (
        (hit is not None and hit > prompt) or (miss is not None and miss > prompt)
    ):
        input_conflict = True
    if input_conflict:
        uncertain = True
        add("deepseek.prompt_total", prompt)
    else:
        if miss is None and prompt is not None and hit is not None:
            miss = prompt - hit
        if hit is None and prompt is not None and miss is not None:
            hit = prompt - miss
        if hit is None and miss is None:
            add("deepseek.prompt_total", prompt)
        else:
            add("input", miss)
    if completion is not None and reasoning is not None:
        if reasoning <= completion:
            add("output", completion - reasoning)
        else:
            uncertain = True
            add("deepseek.completion_total", completion)
            reasoning = None
    elif completion is not None:
        add("deepseek.completion_total", completion)
    if not input_conflict:
        add("cached", hit)
    add("reasoning", reasoning)
    known = {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
        "prompt_tokens_details",
        "completion_tokens_details",
    }
    uncertain |= bool(set(data) - known)
    for detail, key in (
        (prompt_details, "cached_tokens"),
        (completion_details, "reasoning_tokens"),
    ):
        if detail is not None:
            uncertain |= not is_json_object(detail) or bool(set(detail) - {key})
    total = count(data.get("total_tokens"))
    if total is not None and (prompt is None or completion is None):
        uncertain = True
    if total is not None and prompt is not None and completion is not None:
        uncertain |= total != prompt + completion
    if uncertain:
        losses.append(
            FieldLoss(
                "usage",
                Disposition.EXTENSIONS,
                note="unknown or inconsistent usage retained without invented buckets",
            )
        )
    return Usage(
        consumptions=values,
        extensions={"deepseek.usage_unmapped": deepcopy(raw)} if uncertain else {},
    )
