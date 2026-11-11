# Documentation program

Source: maintainer request to audit documentation against current main and separate
user usage/API/platform documentation from development, design and roadmap material.

## WU-135 — Publish current user documentation with a verified audience boundary

- **Status:** ⬜ defined
- **Context:** The public site publishes internal plans, research and proposed
  platform designs alongside usage guides. Existing guides omit shipped packages
  and repeat obsolete feature and installation claims.
- **Goal:** Users can install and use the qualified library surfaces, inspect package
  API references and understand the platform's actual available operations through
  a site whose content agrees with current source and tested contracts.
- **Scope:** Documentation inventory/audit, `docs/user/`, contributor/design/research
  organization and mechanical link migration, repository/package README corrections,
  Zensical navigation, reference generation and documentation verification. Roughly
  35 substantive files plus mechanical moves and generated reference pages.
- **Non-goals:** Runtime behavior, provider qualification, new platform features,
  rewriting historical decisions as current design, or changing concurrent library
  implementation. Research dates and historical plans retain their original meaning.
- **Acceptance:**
  - Only user content is rendered; internal content is absent from output/search —
    `scripts/tests/test_docs_contract.py::test_user_publication_boundary`
  - Every documented public export and management operation matches source and the
    checked-in API contract — `scripts/docs_reference.py --check`
  - Credential-free guide examples execute against recorded/local fixtures —
    `scripts/tests/test_docs_contract.py::test_documented_examples`
  - Links, navigation and generated references are current — `scripts/docs_check.py`
  - The inventory classifies every documentation source and records code evidence
    for current-status corrections — `docs/audits/documentation.md`
- **Done:** The user site builds with verified references/examples, contains no
  internal planning/research pages, and the audit accounts for documentation sources
  and their current, historical or proposed status.
- **Deps:** WU-82 (retain gateway definitions while reorganizing publication), WU-106
  (current shared CI scope policy).
- **Architecture:** Documentation map/status only; no runtime layer contract changes.
- **Integration:** Repository docs and source/schema readers feed the generated
  reference and Zensical build. Public-library source and platform behavior are read
  only; documentation tooling imports no platform application into the kernel.
- **Design sketch:**
  ```text
  docs/user/         -> published Zensical site
  docs/development/  -> contributor workflows
  docs/design/       -> proposed platform product design
  docs/research/     -> dated provider/capability investigations
  docs/plans/        -> WU source of truth (repository only)
  docs/decisions/    -> historical and accepted ADRs (repository only)
  docs/architecture.md -> structural contract (repository only)
  source exports + management.openapi.json -> checked API reference
  ```
- **Alternatives considered:** Remove internal pages from navigation only (small
  diff, still publishes and indexes them); use a dedicated user docs root (explicit
  publication boundary, requires mechanical link migration). Choose the latter.
- **Freeze:** none; documentation and validation only.
- **Decision (audience):** The maintainer explicitly requires the Zensical site to
  serve library and platform users. Preserve contributor/architecture/roadmap
  material in the repository, separately indexed and classified.
- **Risks:** Moved URLs and mistaken support claims. Preserve meaningful user URLs
  where possible, validate local links, label unimplemented surfaces, and generate
  reference signatures from source. Rollback is reverting the documentation PR.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** docs
- **Priority:** P0
- **Tier:** program
- **Owner:** Codex
