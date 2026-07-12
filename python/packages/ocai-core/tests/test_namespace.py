"""The single most important invariant: the PEP 420 namespace stays open.

The subpackages (shipped by THREE separate distributions) must all import, and
there must be NO `__init__.py` at the `ocai` namespace root in any
distribution — a root `__init__.py` would collapse the namespace and make the
sibling distributions' subpackages vanish.
"""

from __future__ import annotations

from pathlib import Path

# Every namespace subpackage the core distribution ships (architecture §1).
CORE_SUBPACKAGES = ("core", "chat", "embedding", "vectorstore", "convert", "runtime", "wire")


def test_core_subpackage_imports() -> None:
    from ocai.core import CallResult  # noqa: F401


def test_plugin_subpackages_import() -> None:
    import ocai.anthropic  # noqa: F401
    import ocai.openai  # noqa: F401


def test_ocai_is_a_namespace_package() -> None:
    import ocai

    # A PEP 420 namespace package has no single __init__.py, so __file__ is None
    # (or absent) and __path__ spans multiple directories.
    assert getattr(ocai, "__file__", None) is None, (
        "ocai must be a namespace package; a root __init__.py collapses it"
    )


def test_namespace_spans_all_distributions() -> None:
    import ocai

    # Each distribution contributes its own src/ocai directory to the namespace.
    paths = list(ocai.__path__)
    assert len(paths) >= 3, f"expected >=3 namespace paths, got {paths}"


def test_no_root_init_on_disk(core_src: Path, openai_src: Path, anthropic_src: Path) -> None:
    for src in (core_src, openai_src, anthropic_src):
        assert not (src / "__init__.py").exists(), (
            f"forbidden namespace-root __init__.py present at {src / '__init__.py'}"
        )

    # ...while the real subpackages DO carry __init__.py (and ship py.typed).
    for sub in CORE_SUBPACKAGES:
        assert (core_src / sub / "__init__.py").exists(), f"missing {sub}/__init__.py"
        assert (core_src / sub / "py.typed").exists(), f"missing {sub}/py.typed"
    assert (openai_src / "openai" / "__init__.py").exists()
    assert (openai_src / "openai" / "py.typed").exists()
    assert (anthropic_src / "anthropic" / "__init__.py").exists()
    assert (anthropic_src / "anthropic" / "py.typed").exists()
