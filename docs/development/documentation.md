# Maintaining documentation

Publish user instructions only from `docs/user/`. The Zensical `docs_dir` boundary
excludes contributor material, plans, ADRs, product proposals and vendor research
from output and search. Put these in their separate folders listed in the
[documentation map](../README.md). This uses Zensical's documented
[documentation-root setting](https://zensical.org/docs/setup/basics/).

Update a usage guide when behavior changes, and name the owning tests in the
support/audit evidence. A registered type, catalog entry or provider marketing page
does not prove execution support. Distinguish repository-main behavior from installed
release versions and external live service availability.

## Reference and examples

`scripts/docs_reference.py` parses Python source using the stdlib AST, without
importing packages or credentials, and reads package metadata plus
`platform/spec/management.openapi.json`. It writes the user API reference with
public declarations, methods, fields, type aliases and re-export tables. Inherited
members belong to their documented base. Private underscore modules are excluded.

After a source/schema change:

```bash
uv run python scripts/docs_reference.py
uv run python scripts/docs_check.py
```

The check fails if generated pages differ. Do not hand-edit those pages. The docs
suite is selected when package source, platform contracts or reference tooling
changes. A maintained guide example uses `<!-- test: offline -->` or
`<!-- test: recorded -->` immediately before its Python fence; the documentation
contract suite executes it without live keys using existing recorded HTTP/SSE.
Do not mark incomplete fragments as runnable examples.

`docs_contract.py` verifies public navigation, owned Markdown local-link targets,
and that user links cannot escape the publication root. Repository material is
linked explicitly to GitHub when useful. Source docstrings are rendered literally
so code examples and source-relative links do not become broken site links.

## Move and review policy

Rewrite local links from their original location when moving documents; update
repository-qualified prose and Taskfile descriptions too. Preserve useful existing
user URLs. Internal site URLs are intentionally retired; their materials stay in
the repository instead of remaining search-indexed public-site pages. The docs
build is clean, so stale output does not survive publication.

The audit in `docs/audits/documentation.md` records source categories, corrected
claims and the evidence used. Archived plans and research keep their dates and
historical intent. Review publication output for plans/design/research leakage and
run the full gate before declaring a documentation change complete.
