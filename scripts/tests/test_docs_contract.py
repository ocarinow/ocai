"""Documentation examples and audience/API contracts must agree with executable code."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import docs_contract
import docs_reference
import httpx
import pytest
import respx
from ci_scope import affected

ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "docs/user"


def test_user_publication_boundary() -> None:
    assert docs_contract.check() == []
    assert not any((USER / name).exists() for name in ("plans", "research", "design", "decisions"))


def test_reference_matches_source_and_schema() -> None:
    pages = docs_reference.render()
    assert len(pages) >= 14
    for path, body in pages.items():
        assert path.read_text() == body, path
    assert "get_system_status" in pages[docs_reference.OUTPUT / "management.md"]
    assert "intercept_stream" in pages[docs_reference.OUTPUT / "ocai-runtime.md"]
    assert "SigV4Credential" in pages[docs_reference.OUTPUT / "ocai-aws.md"]


@pytest.mark.parametrize(
    "path",
    [
        "python/packages/ocai-core/src/ocai/core/result.py",
        "platform/spec/management.openapi.json",
        "scripts/docs_reference.py",
    ],
)
def test_api_changes_select_documentation_validation(path: str) -> None:
    assert affected("docs", frozenset({path}))


def test_signature_generation_does_not_execute_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(docs_reference, "ROOT", tmp_path)
    source = tmp_path / "sample.py"
    source.write_text(
        'raise RuntimeError("must not execute")\n\n'
        "def sample(value: int, *, limit: int = 3) -> str:\n"
        '    """Explain the public call."""\n    return str(value)\n'
    )
    rendered = docs_reference.render_module(source, "ocai.sample")
    assert "sample(value: int, *, limit: int=3) -> str" in rendered
    assert "Explain the public call." in rendered


def test_documented_examples(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-documentation-key")
    fixture_root = ROOT / "python/packages/ocai-core/tests/http"
    unary: dict[str, Any] = json.loads(
        (fixture_root / "openai_chat_completion_stream_paired.json").read_text()
    )
    stream: dict[str, Any] = json.loads(
        (fixture_root / "openai_chat_completion_stream.json").read_text()
    )
    requests: list[dict[str, Any]] = []

    def reply(request: httpx.Request) -> httpx.Response:
        body: dict[str, Any] = json.loads(request.content)
        requests.append(body)
        pair = stream if body.get("stream") else unary
        assert body["messages"] == pair["request"]["json"]["messages"]
        assert body["model"] == pair["request"]["json"]["model"]
        response = pair["response"]
        if body.get("stream"):
            return httpx.Response(
                response["status"],
                headers=response["headers"],
                content="\n\n".join(response["sse"]) + "\n\n",
            )
        return httpx.Response(response["status"], json=response["json"])

    examples = 0
    with respx.mock(assert_all_called=False, assert_all_mocked=True) as router:
        router.post("https://api.openai.com/v1/chat/completions").mock(side_effect=reply)
        for path in sorted(USER.rglob("*.md")):
            for source in re.findall(
                r"<!-- test: (?:offline|recorded) -->\s*```python\n(.*?)\n```",
                path.read_text(),
                re.S,
            ):
                namespace: dict[str, Any] = {"__name__": "documentation_example"}
                exec(  # noqa: S102 — repository-owned examples; HTTP is recorded.
                    compile(source, str(path.relative_to(ROOT)), "exec", dont_inherit=True),
                    namespace,
                )  # noqa: S102 — execute repository-owned examples under recorded HTTP.
                examples += 1
    assert examples == 7
    assert len(requests) == 4


def test_documentation_boundary_rejects_internal_site_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(docs_contract, "ROOT", tmp_path)
    monkeypatch.setattr(docs_contract, "USER", tmp_path / "docs/user")
    monkeypatch.setattr(docs_contract, "documentation_files", lambda: list[Path]())
    (tmp_path / "zensical.toml").write_text('[project]\ndocs_dir = "docs"\nnav = []\n')
    assert "Zensical must publish only docs/user" in docs_contract.check()


def test_platform_availability_matches_documented_profile() -> None:
    schema = json.loads((ROOT / "platform/spec/management.openapi.json").read_text())
    assert set(schema["paths"]) == {"/health/live", "/health/ready", "/management/v1/status"}, (
        "Update platform user workflows and availability when the HTTP surface expands."
    )


def test_management_client_documentation_names_actual_package() -> None:
    package = json.loads((ROOT / "platform/packages/management-client/package.json").read_text())
    guide = (USER / "platform/client.md").read_text()
    assert f"from '{package['name']}'" in guide
    assert package["private"] is True
    source = (ROOT / "platform/packages/management-client/index.ts").read_text()
    assert "async getStatus(signal?: AbortSignal)" in source
    assert "getStatus(signal?: AbortSignal)" in guide
