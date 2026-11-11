"""Render deterministic source-based Python and management API documentation.

Parse source rather than importing packages or resolving credentials. Check mode
fails when exports, signatures, package metadata or the OpenAPI contract drift.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs/user/reference"
SOURCE = "https://github.com/ocarinow/ocai/blob/main/"


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return the declared signature without executing defaults or annotations."""
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    params = (
        "[" + ", ".join(ast.unparse(p) for p in node.type_params) + "]" if node.type_params else ""
    )
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}{params}({ast.unparse(node.args)}){returns}"


def documentation(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Render a source declaration and its docstring with literal code examples."""
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        declaration = f"class {node.name}({bases})" if bases else f"class {node.name}"
        fields: list[str] = []
        for member in node.body:
            if isinstance(member, ast.AnnAssign) and isinstance(member.target, ast.Name):
                if not member.target.id.startswith("_"):
                    fields.append(ast.unparse(member))
            elif isinstance(member, ast.Assign):
                if all(
                    isinstance(t, ast.Name) and not t.id.startswith("_") for t in member.targets
                ):
                    value = ast.unparse(member)
                    if len(value) <= 200:
                        fields.append(value)
        if fields:
            declaration += ":\n" + "\n".join(f"    {field}" for field in fields)
    else:
        decorators = [ast.unparse(d) for d in node.decorator_list]
        declaration = "".join(
            f"@{d}\n" for d in decorators if d in {"classmethod", "staticmethod", "property"}
        )
        declaration += signature(node)
    doc = ast.get_docstring(node) or "See the source declaration for this symbol."
    # Literal docstrings do not turn source-relative Markdown links into site links.
    fence = "`" * max(4, max((len(x) + 1 for x in re.findall(r"`+", doc)), default=4))
    return f"```python\n{declaration}\n```\n\n{fence}text\n{doc}\n{fence}\n"


def anchor(module: str, name: str) -> str:
    """Return a stable qualified anchor, including re-export aliases."""
    return (module + "." + name).replace(".", "-").replace("_", "-").lower()


def definition(module: str, name: str, seen: frozenset[str] = frozenset()) -> tuple[str, str]:
    """Follow explicit source re-exports to their actual public declaration."""
    key = module + "." + name
    if key in seen:
        return module, name
    relative = module.replace(".", "/")
    candidates = [
        candidate
        for package in (ROOT / "python/packages").iterdir()
        for candidate in (
            package / "src" / (relative + ".py"),
            package / "src" / relative / "__init__.py",
        )
        if candidate.is_file()
    ]
    if not candidates:
        return module, name
    for node in ast.parse(candidates[0].read_text()).body:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ocai."):
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    return definition(node.module, alias.name, seen | {key})
    return module, name


def render_module(path: Path, module: str) -> str:
    """Document public declarations and explicit re-exports in a source module."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines = [f"## `{module}`\n", f"[Source]({SOURCE}{path.relative_to(ROOT)})\n"]
    exported: set[str] | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
        ):
            value: Any = ast.literal_eval(node.value)
            exported = set(value)
    reexports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module and exported:
            for alias in node.names:
                name = alias.asname or alias.name
                if name in exported:
                    origin, symbol = definition(node.module, alias.name)
                    namespace_parts = origin.split(".")[:2]
                    page = "-".join(namespace_parts) + ".md"
                    link = f"{page}#{anchor(origin, symbol)}"
                    reexports.append(
                        f'| <span id="{anchor(module, name)}"></span>`{name}` '
                        f"| [`{origin}.{symbol}`]({link}) |"
                    )
    if reexports:
        lines += [
            "Public re-exports resolve to the definitions named below.\n",
            "| Export | Definition |\n|---|---|\n" + "\n".join(reexports) + "\n",
        ]
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            lines += [
                f"### `{node.name}` {{ #{anchor(module, node.name)} }}\n",
                documentation(node),
            ]
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                        not method.name.startswith("_") or method.name == "__init__"
                    ):
                        lines += [
                            f"#### `{node.name}.{method.name}` "
                            f"{{ #{anchor(module, node.name + '.' + method.name)} }}\n",
                            documentation(method),
                        ]
        elif isinstance(node, ast.TypeAlias) and not node.name.id.startswith("_"):
            lines += [
                f"### `{node.name.id}` {{ #{anchor(module, node.name.id)} }}\n",
                f"```python\n{ast.unparse(node)}\n```\n",
            ]
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    declaration = ast.unparse(node)
                    if len(declaration) > 300:
                        declaration = f"{target.id}  # See source for the full declaration."
                    lines += [
                        f"### `{target.id}` {{ #{anchor(module, target.id)} }}\n",
                        f"```python\n{declaration}\n```\n",
                    ]
    return "\n".join(lines)


def render() -> dict[Path, str]:
    """Build reference pages from all package sources and the management schema."""
    pages: dict[Path, str] = {}
    groups: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    packages: list[str] = []
    for package in sorted((ROOT / "python/packages").iterdir()):
        metadata = tomllib.loads((package / "pyproject.toml").read_text())["project"]
        name = str(metadata["name"])
        deps = ", ".join(f"`{d}`" for d in metadata.get("dependencies", [])) or "None"
        packages.append(
            f"| `{name}` | `{metadata['version']}` | `{metadata['requires-python']}` | {deps} |"
        )
        for path in sorted((package / "src/ocai").rglob("*.py")):
            parts = path.relative_to(package / "src").with_suffix("").parts
            if any(part.startswith("_") and part != "__init__" for part in parts):
                continue
            module = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
            groups[".".join(parts[:2])].append((path, module))
    links: list[str] = []
    for namespace, modules in sorted(groups.items()):
        file = namespace.replace(".", "-") + ".md"
        links.append(f"- [{namespace}]({file})")
        lead = f"""# `{namespace}` API reference

Generated from the checked-out package sources. Signatures, declared fields,
methods, type aliases and explicit re-exports are checked for drift. Inherited
members follow their named base class; a type's presence does not establish
provider execution support. See [supported features](../provider-feature-matrix.md).

"""
        pages[OUTPUT / file] = lead + "\n".join(
            render_module(path, module) for path, module in modules
        )
    pages[OUTPUT / "README.md"] = (
        """# API reference

These pages describe this repository revision. Installed releases may differ;
check your installed distribution versions before relying on a newer symbol.
Public declarations in non-private modules are included; re-export tables identify
where imported symbols are defined. Internal underscore-prefixed modules are excluded.
Examples and task-oriented explanations live in the [Python guide](../libraries/python/README.md).
Embedding/vector-store contracts and Responses declarations are provisional and do
not imply an executable provider implementation.

## Packages at this revision

| Distribution | Version | Python | Runtime dependencies |
|---|---|---|---|
"""
        + "\n".join(packages)
        + "\n\n## Python namespaces\n\n"
        + "\n".join(links)
        + "\n\n## Platform\n\n- [Management HTTP API](management.md)\n"
        + "- [Management TypeScript client](../platform/client.md)\n"
    )
    schema: dict[str, Any] = json.loads(
        (ROOT / "platform/spec/management.openapi.json").read_text()
    )
    lines = [
        "# Management HTTP API\n",
        """Generated from the checked-in OpenAPI contract. The platform is a foundation
release: these operations do not provide inference or organization administration.
The service disables interactive `/docs`, `/redoc` and `/openapi.json` routes.
""",
        "| Method | Path | Operation | Responses |\n|---|---|---|---|",
    ]
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            responses = ", ".join(operation["responses"])
            lines.append(
                f"| `{method.upper()}` | `{path}` | `{operation['operationId']}` | {responses} |"
            )

    lines += [
        "\n## Response schemas\n",
        "```json\n"
        + json.dumps(schema["components"]["schemas"], indent=2, sort_keys=True)
        + "\n```\n",
        "The [platform guide](../platform/README.md) explains readiness and error handling.\n",
    ]
    pages[OUTPUT / "management.md"] = "\n".join(lines)
    return pages


def main() -> int:
    """Write generated pages, or fail if checked-in pages no longer match source."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    pages = render()
    stale = [
        str(path.relative_to(ROOT))
        for path, body in pages.items()
        if not path.exists() or path.read_text() != body
    ]
    expected = set(pages)
    obsolete = [p for p in OUTPUT.glob("ocai-*.md") if p not in expected]
    if args.check:
        if stale or obsolete:
            print(
                "docs reference: stale: "
                + ", ".join([*stale, *(str(p.relative_to(ROOT)) for p in obsolete)])
            )
            return 1
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for path, body in pages.items():
            path.write_text(body, encoding="utf-8")
        for path in obsolete:
            path.unlink()
    print(f"docs reference: ok ({len(pages)} source-derived pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
