# Gateway console program

Source: maintainer request on 2026-11-11 to expand the gateway console program,
then rework WU-82–105 around the competitive review, teams/users, and ABAC.
Status: proposed work-unit definitions; no runtime capability is established by
this document. Existing numeric IDs are retained. WU-82a–82i add independently
reviewable prerequisites; numeric order is not dependency order.

This program implements the remaining gateway slices in [the MVP
plan](platform-mvp.md). It consumes the [authenticated console
program](platform-identity.md), [ADRs 0011](../decisions/0011-authenticated-console-contract.md)
and [0013](../decisions/0013-platform-identity.md), and the kernel's public
[governed gateway APIs](gateway-readiness.md). Each WU is one workflow, one
branch and one PR. Runtime work begins after WU-82a's access contract is recorded
and reviewed; the bootstrap's existing owner/viewer semantics remain valid for
its original organization-settings workflow.

## Acceptance workflow

An organization administrator onboards a user, creates Finance and Support teams,
and grants them distinct roles on two projects. Each project has explicit dev/prod
environments and restricted compartments. Membership does not grant access to
another project, and configuration administration does not grant payload access.
An authorized project operator connects a provider, creates deployments with
reviewed processing attributes, registers an application, and publishes a routing
policy. A scoped service-account key invokes only that application's authorized
environment and compartment.

The gateway evaluates scoped permissions and trusted attributes, then applies
routing, fidelity and admission constraints. A fallback cannot bypass the primary
attempt's residency, classification or credential restrictions. Receipts explain
attempts, authorization and policy outcomes using safe reason codes, with pinned
versions and usage provenance. A metadata viewer can inspect authorized receipts
without reading payloads. A conditional content grant permits an audited read
only until its approval expires. Revocation takes effect at the documented
operation boundaries, including queued work and active streams. Readiness stays
unqualified until the relevant real-service isolation and fault tests pass.

## Domain and permission contract

WU-82a records this proposed contract in a new ADR (allocate its number at
implementation; do not overwrite ADR 0011 or 0013). Implementing WUs qualify it.

| Object | Meaning and initial boundary |
|---|---|
| Organization | Customer/account boundary; existing stable identity retained |
| User | Human principal with verified issuer/subject bindings; no email-only account merge |
| Team | Organization-owned group of human members; grants apply to its member set |
| Project | Resource ownership and delegated administration scope; use this public term instead of introducing a second workspace object |
| Environment | Project-owned dev/prod scope with stable ID; an authorization boundary, not a request tag |
| Application | Versioned client contract and workload within a project; environment bindings are explicit |
| Service account | Organization-owned workload principal with accountable owner; may receive explicit application grants |
| Credential | Authentication binding to a principal; intersects current grants and cannot create authority |
| Role binding | Principal or team + fixed role template + organization/project/environment scope |
| Compartment | Organization-owned processing/content restriction, explicitly bound to resources; never implied by project membership |
| Attribute | Typed value with authority, version/observed time and freshness policy; missing is distinct from false/public/zero |

Roles grant named actions; teams and resource relations determine where those
actions apply; mandatory attribute and compartment policies further restrict
access. Applicable grants can combine, but restrictions cannot be bypassed through
another role or an unconditional owner path. Initial templates are organization
Owner, Access administrator, Finance reader; project Administrator, Developer,
Operator, Metadata viewer. Membership alone grants no project access. Content
read/export and inference invocation are separate explicit grants, not implied by
configuration administration. Prevent removal of the last active organization
owner. Templates are versioned permission sets, not a single role column used as
an endpoint switch. A custom-role editor follows in WU-120.

Initial actions include `members.manage`, `teams.manage`, `grants.manage`,
`projects.manage`, `connections.manage`, `deployments.manage`, `policies.publish`,
`applications.invoke`, `keys.issue`, `budgets.manage`, `receipts.read`,
`receipts.export`, `payloads.read`, `requests.replay`, and `migration.run`.
Payload export is not implemented by metadata export and remains deferred.
Grant administrators cannot grant beyond their delegated scope or silently grant
themselves content access. Compartment/content grant administration is a separately
delegated action; its initial administrator is bound by an audited operator step.

ABAC inputs cover principal status, resource classification and compartment,
verified authentication context where qualified, credential scope, reviewed
destination region/retention attributes, server time and approval validity.
PostgreSQL/platform registries and qualified issuer claims supply these facts.
Client tags, end-user IDs, declared purpose, forwarding headers and model-generated
labels are untrusted attribution; they never raise privileges or lower
classification. Destination geography is not established by a display label.

Use OpenFGA for relationships and qualified typed conditions. Platform code
resolves trusted attributes, composes mandatory restrictions, evaluates gateway
eligibility, and enforces results. Do not introduce a second authorization engine
or experimental dynamic-expression execution in this program. Policy templates
have typed parameters, validation, simulation, immutable published versions and
audited rollback. Budget reservations remain transactional admission decisions,
not OpenFGA counters.

## Shared contracts

| Concern | Contract |
|---|---|
| Resource ownership | Every resource has explicit organization and project/environment scope where applicable; compartments are bound in authoritative state. Cross-scope references require an explicit grant; the initial profile rejects them rather than silently sharing. Organization-wide connections are deferred. |
| Resource API | Organization administration uses `/management/v1/organizations/{org}/…`; project resources use `…/projects/{project}/…`, with environment IDs validated against the project. Resource `id`, `version`, `created_at`, `updated_at`; stale writes return 409. Missing and inaccessible IDs share 404. A known readable resource with an unauthorized action returns 403; unavailable required authorization returns sanitized 503. |
| Authorization | One composed decision: active principal/membership AND scoped permission AND credential restriction AND mandatory attribute/compartment policy. WU-82b migrates models and projection; each resource WU registers relations and tests its own permission matrix. No resource waits for WU-101 to become protected. |
| Trusted context | WU-82f supplies typed attributes with provenance, revision/freshness and missing/error states; clients cannot choose a more privileged project, compartment, principal or policy. |
| Policy decision | WU-82g records outcome, safe reason codes, policy/model versions, attribute revision references and enforceable obligations. Missing/stale required attributes and evaluation errors never allow; distinguish deny from unavailable without leaking hidden resources. |
| Enforcement boundaries | Check before admission and before every new outbound attempt, including fallback/replay; revalidate queued work on execution and protected mutations before commit. Streams check at bounded checkpoints (reference maximum 5 seconds) and before starting another attempt; stop release after expiry/revocation is observed, record partial outcome, and never claim recall of delivered content. In-flight provider work/billing may continue. No database lock is held for the generation lifetime. |
| Audit and evidence | Mutations and allowlisted audit commit atomically. Decisions store safe codes and version references, never raw attributes, secrets, prompts or arbitrary provider error bodies. Scope all evidence reads, aggregate queries, exports and background jobs. |
| Configuration snapshots | Pin resource scope, authorization model, attribute/policy revisions, deployment versions, pricing version and catalog/artifact references. Snapshots explain decisions; they do not freeze revocation or bypass current mandatory policy. |
| Data plane | `POST /v1/chat/completions`; WU-82i extends WU-80's organization-read-only keys with explicit application/environment invocation. Keys remain bound to service accounts; caller-reported end users remain attribution. |
| Provenance | Usage/cost distinguish `provider_reported`, `locally_estimated`, `reconciled`, `unknown`. Preserve missing values with reasons. Estimates require recorded methods/bounds; no invented upper bound or zero for unknown. |
| Budgets | WU-92 supports organization, project, application/environment and key; WU-92a adds team and authenticated-principal allocation. All applicable caps apply, including BYOK usage. Unknown final cost keeps a conservative reservation pending reconciliation; strict admission without a qualified upper bound rejects. |
| Tests | Real disposable PostgreSQL/OpenFGA/Keycloak for claimed behavior; provider HTTP/SSE uses recorded pairs only. Platform owns new fixtures under its tests; existing kernel fixtures may be read without edits. No live keys or provider SDK dependencies. |
| Console | Product pages in `platform/apps/console`, shared session/context helpers in `nuxt-platform`, neutral components in `nuxt-ui`. Server authorization is authoritative; hiding UI is not enforcement. Show scope, effective access and safe denial explanations. |
| Gate | Every owning WU adds its acceptance tests to `scripts/check_platform.py`, runs `scripts/check.py` and reports its literal summary with commit/scope. Plan lint checks entry shape; it does not prove permission semantics. |

Architecture subsection numbers beyond §12.5 and Alembic revision IDs are allocated
against the implementation branch's current main. Descriptive subsection/migration
names below are proposed, not reservations that collide with WU-76/77 or another WU.
Kernel source, root `spec/`, provider conversion fixtures and the integration
program remain outside this program's ownership. Record a public-library gap in
[`gaps.md`](gaps.md), with evidence and a dependency, rather than implementing a
private replacement or widening kernel scope.

## Sequencing

```text
Definition:     82 → 82a
Access:         82a → 82b → 82c / 82d → 82e → 82f → 82g → 82h
Control plane:  82h → 83 → 84 ─┐
                82h + 78 → 85 ├→ 86
Credentials:    85 + 80 + 82g + 82h → 82i
Data plane:     82i + 86 → 87 → 88 → 89; 88 → 90 → 91
Admission:      89 + 91 → 92 → 92a
Inspection:     90 + 91 → 93 → 94; 94 + 92a → 100
Operations:     92a → 96; 91 → 95; 93 + 95 → 97; 86 + 91 → 98 → 99
Access proof:   94 + 100 + resource APIs → 101; 76 + 96 + 101 → 102
Qualification:  92a + 94 + 96 + 101 + 102 → 103
Migration:      86 + 91 + 93 + 94 → 104; 104 + 97 + 103 → 105
```

Deps bullets are authoritative; arrows summarize them. There is no dependency on
WU-103 to create an initially paused deployment or inspect a route. Execution uses
the platform's reviewed support manifest backed by existing kernel evidence;
WU-103 adds installation-specific qualification, never infers support from a
catalog entry alone.

## Competitive findings and feature expansion

The November 2026 official-documentation review informs requirements, not claims
of parity. Edition boundaries and experimental features must remain labelled.

| Finding | Program response |
|---|---|
| [LiteLLM teams, keys and access groups](https://docs.litellm.ai/docs/proxy/access_management/overview) | First-class teams and scoped grants; explicit inheritance and credential intersection |
| [Portkey content versus metadata permissions](https://portkey.ai/docs/product/administration/configure-logs-access-permissions-in-workspace) | Separate payload access from configuration and metadata inspection |
| [Langfuse gateway key ownership](https://langfuse.com/docs/gateway/features/api-keys) | Separate service principals, credentials and caller-reported attribution; tags never confer access |
| [Logfire projects and roles](https://pydantic.dev/docs/logfire/manage/organizations-and-projects/) | Projects with delegated administration; fixed templates without a schema dead end for future custom roles |
| [Vercel budget semantics](https://vercel.com/docs/ai-gateway/observability-and-spend/budgets) | Explicit attribution, BYOK coverage, reservation uncertainty and cap behavior rather than an unqualified hard-limit claim |
| [Arize improvement workflows](https://arize.com/docs/ax/quickstarts/quickstart-run-first-experiment) | Receipts are not an evaluation product; datasets, experiments and annotation remain the later evaluation stage |
| [OpenFGA conditions](https://openfga.dev/docs/modeling/conditions) and [model migration](https://openfga.dev/docs/modeling/migrating/migrating-models) | Trusted typed context, conditional grants, migration/backfill/cutover tests |

The companion [competitive feature program](platform-gateway-parity.md) assigns
WU-107–134 to front doors, embeddings/multimodal coverage, balancing, caching,
guardrails/redaction, telemetry/audit, prompts/evaluations, SCIM/custom roles,
federation/personal keys, external secrets, configuration automation, replicated
operation, restoration, retention, model discovery and shadow traffic. Its feature
matrix maps the market comparison to delivery WUs and explicit evidence.

WU-63 remains the independent OTel satellite track. Missing public-library
capabilities block the consuming platform WU and never authorize private platform
conversion code. MCP/agent gateways and additional non-chat capabilities remain
separate product programs, not implied market-parity claims.

## WU-82 — Define the gateway console program

- **Status:** ✅ complete
- **Context:** The gateway console expansion omitted foundational teams, project scopes and
  ABAC despite the platform design requiring them. The maintainer requested a
  rework of WU-82–105 integrating the enterprise feature comparison.
- **Goal:** One coherent gateway program preserves the original workflows while
  defining bounded access/ABAC prerequisites, competitive feature ownership and
  qualification evidence.
- **Scope:** Both gateway plans, WU-82–105, WU-107–134 and lettered prerequisite rows in the
  roadmap, the MVP cross-reference, and docs navigation. About 5 files.
- **Non-goals:** Runtime changes, changing completed identity WUs, public-library
  implementation, or treating proposed access decisions as implemented behavior.
  WU-82a records the detailed successor authorization ADR.
- **Acceptance:**
  - Every numeric and lettered entry follows the WU template —
    `scripts/board_sync.py lint`
  - Roadmap headings, dependency references and the acyclic order agree —
    `docs/plans/README.md`, `docs/plans/platform-gateway.md` and
    `docs/plans/platform-gateway-parity.md`
  - Proposed scope, implemented scope and deferred scope remain distinct and
    links build — `scripts/docs_check.py`
  - Repository verification passes for the planning diff — `scripts/check.py`
- **Done:** The reworked program has matching roadmap entries, no missing or cyclic
  dependencies, explicit access/ABAC and competitive feature ownership, and a
  passing repository gate.
- **Deps:** WU-72 (the identity program this consumes); none else.
- **Architecture:** none (planning only; implementing WUs update §12).
- **Integration:** Planning only. The program connects architecture §12, the
  product design and the delivery sequence to WU-83–105 and WU-107–134; no dependency arrow
  changes.
- **Design sketch:**
  ```text
  program: shared domain / permission / ABAC contracts
  prerequisites: WU-82a..82i; additional budget allocation: WU-92a
  retained delivery workflows: WU-83..105
  competitive feature workflows: WU-107..134
  evidence: owning acceptance suites + cross-resource qualification
  ```
- **Alternatives considered:** Append access after the gateway resources (smaller
  initial plan, but late scope migration); replace numeric IDs (simpler sequence,
  but breaks existing references). Retain IDs and add bounded prerequisites.
- **Freeze:** none.
- **Decision (ownership):** ADRs 0006, 0011 and 0013 preserve the platform/kernel
  boundary and existing bootstrap. New scope/ABAC details are proposals until
  WU-82a records their reviewed contract; this plan makes no runtime claim.
- **Risks:** Entries drift from the mockup as the design iterates; bounded by
  the rule that the plan is the source and the mockup follows. Rollback: revert.
- **Open:** none.
- **Evidence:** `scripts/board_sync.py lint` validates every definition; the
  roadmap and both program files have matching IDs/titles and an acyclic dependency
  graph. `scripts/check.py` verifies the planning diff; the PR carries its clean
  commit gate summary. Runtime features remain pending in their own WUs.
- **Area:** docs
- **Priority:** P0
- **Tier:** program
- **Owner:** unassigned

## WU-82a — Define the scoped RBAC, ReBAC and ABAC contract

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** An authorization ADR and versioned platform contract make the shared domain,
  permission composition, trusted attributes and enforcement boundaries reviewable.
- **Scope:** New ADR, identity/compartment design reconciliation, proposed architecture
  §12.2 text, platform authorization schema and positive/negative decision examples;
  about 8 files. No runtime implementation.
- **Non-goals:** Authorization engine replacement, general policy DSL, custom-role UI,
  SCIM and new identity-provider profiles; deferred identity follow-up.
- **Acceptance:**
  - Typed fixtures distinguish users, teams, projects, environments, principals and credentials; schema validation covers shape and reviewed decision examples record cross-organization denial —
    `platform/services/gateway/tests/test_authorization_contract.py::test_scope_examples`
  - The reviewed decision table covers owner and alternate-grant cases with mandatory restrictions; enforcement is independently tested by WU-82g/82h —
    `platform/services/gateway/tests/test_authorization_contract.py::test_decision_examples`
  - Contract specifies missing/stale attributes, deny/unavailable, policy precedence, revocation boundaries and safe evidence —
    `platform/spec/authorization.schema.json`
- **Done:** The reviewed ADR and schema examples specify one unambiguous composed decision
  for each reference scenario, without claiming the examples are enforcement.
- **Deps:** WU-82; ADRs 0011 and 0013.
- **Architecture:** §12.2 proposed access contract; preserve §12.3–12.5
  implementation claims and record the successor ADR without changing runtime.
- **Integration:**
  - Layer: platform documentation and schema examples;
    no public-library dependency or contract changes.
  - Modules: `docs/decisions/`, `docs/platform/identity.md`, `docs/platform/compartments.md`,
    `platform/spec/authorization.schema.json`, contract fixtures/tests.
  - Flow: maintainer requirements → reviewed contract → fixture validation → dependent WUs.
  - Diagram:
    ```mermaid
    flowchart LR
      Requirements[Identity and gateway requirements] --> Contract[Reviewed scope and ABAC contract]
      Contract --> Fixtures[Schema and decision examples]
      Contract --> Runtime[Implementing WUs]
    ```
- **Design sketch:**
  ```text
  subject: principal_id + optional actor_id; credential: id + restrictions
  resource: organization_id + project_id? + environment_id? + compartment_ids
  decision: allow | deny | unavailable; safe_reason_codes; version_refs
  mandatory restrictions apply after the union of applicable scoped grants
  ```
- **Alternatives considered:** Four global roles are simple but cannot separate projects or content. A fully
  programmable policy engine adds flexibility but exceeds the qualified first profile.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** The shared domain and permission contract above is the proposed design.
  Record its accepted form in this WU; allocate the ADR number against main.
- **Risks:** A broad schema can pretend unsupported behavior; examples identify implemented
  versus future profiles. Rollback is a document/schema revert before consumers land.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for recording the proposed contract. Runtime WUs follow
  its reviewed ADR; this definition does not claim those features are implemented.
- **Evidence:** (filled at completion)
- **Area:** docs
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82b — Migrate pinned authorization models with recoverable projection

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** A populated owner/viewer installation upgrades to a reviewed successor model
  with a recoverable projection and explicit active model/revision tracking.
- **Scope:** Authorization adapter, storage/outbox schema, operator migration command,
  model fixtures and real-service tests; about 16 files.
- **Non-goals:** New member/team UI or policy evaluation; WU-82c–82h. Changing bootstrap
  semantics or automatic startup migrations.
- **Acceptance:**
  - Legacy owner/viewer reads and updates retain their original outcomes after backfill and cutover —
    `platform/services/gateway/tests/test_authorization_migration.py::test_legacy_equivalence`
  - Crash after tuple write, duplicate delivery and cutover restart resume idempotently; unconfirmed models never serve —
    `platform/services/gateway/tests/test_authorization_migration.py::test_resume_and_cutover`
  - Concurrent revoke during migration cannot reappear from backfill or rollback —
    `platform/services/gateway/tests/test_authorization_migration.py::test_revoke_during_migration`
  - Incompatible old workers and failed model qualification produce unavailable rather than allow —
    `platform/services/gateway/tests/test_authorization_migration.py::test_mixed_version_fails_closed`
- **Done:** A real PostgreSQL/OpenFGA upgrade with injected crashes preserves legacy
  outcomes and revocations and only activates the fully confirmed model.
- **Deps:** WU-82a, WU-75.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/authorization/`, `app/storage/`, `app/operator/`, model fixtures and migrations.
  - Flow: operator prepare → backfill plus ordered deltas → verify → atomic active-model cutover.
  - Diagram:
    ```mermaid
    flowchart LR
      Prepare[Reviewed immutable model] --> Backfill[Backfill and ordered deltas]
      Backfill --> Verify[Revision and model verification]
      Verify --> Cutover[Atomic active-model cutover]
    ```
- **Design sketch:**
  ```text
  ModelRevision(id, digest, predecessor, state=prepared|projecting|active|retired)
  ProjectionEvent(organization_id, revision, model_revision, typed_tuple, operation)
  cutover requires verified model + completed backfill + drained ordered deltas
  rollback requires compatibility proof and replay of all intervening revocations
  ```
- **Alternatives considered:** Changing the configured ID alone is easy but loses projection guarantees.
  Unconditional dual-write lacks a recoverable cutover boundary.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** OpenFGA model IDs are immutable; database and projection migrations are
  explicit operator actions, with PostgreSQL authoritative (ADR 0011).
- **Risks:** Backfill or rollback can resurrect grants; serialize revision watermarks and
  test the race. Rollback to an old model is refused if current grants cannot be
  represented safely; recovery can keep access unavailable.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82c — Administer human organization membership

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** An authorized access administrator onboards a verified human
  identity through an explicit enrollment request, suspends or removes membership, and sees the audited lifecycle.
- **Scope:** Authenticated enrollment record, organization membership API/repository, Access members page, client and
  real issuer/authorization tests; about 14 files.
- **Non-goals:** Account creation, passwords and MFA remain with the IdP. Email invitations,
  automatic JIT access and SCIM provisioning is WU-119; invitation delivery remains an identity follow-up.
- **Acceptance:**
  - An unbound user may explicitly enroll using a validated issuer token; enrollment records identity only, and administrator approval alone creates membership; email equality cannot merge accounts —
    `platform/services/gateway/tests/test_memberships.py::test_verified_binding`
  - Only delegated access administrators can modify membership; the last active owner cannot be removed —
    `platform/services/gateway/tests/test_memberships.py::test_delegation_and_last_owner`
  - Suspension and removal revoke access with existing tokens and cannot revive through stale writes —
    `platform/services/gateway/tests/test_memberships.py::test_revocation_race`
  - The members page distinguishes active, suspended and removed membership and displays audit evidence —
    `platform/tests/integration/memberships.test.ts`
- **Done:** The console can onboard a verified user and revoke that membership while
  replayed credentials and concurrent stale updates cannot restore access.
- **Deps:** WU-77, WU-82b.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/access/memberships.py`, storage migration, Access members page and client.
  - Flow: validated user enrollment → administrator approval → binding + membership/audit/outbox transaction.
  - Diagram:
    ```mermaid
    flowchart LR
      User[Verified enrollment] --> Admin[Scoped administrator approval]
      Admin --> Member[Binding and membership transaction]
      Member --> Projector[Audit and projection]
    ```
- **Design sketch:**
  ```text
  Membership(organization_id, principal_id, status, version)
  Enrollment(verified issuer, subject, expires_at, state=pending|accepted|expired)
  Binding(issuer, subject) -> stable principal_id; enrollment grants no access
  POST /management/v1/enrollments (authenticated identity, no organization grant)
  POST .../members {enrollment_id}; PATCH .../members/{id} {status, version}
  ```
- **Alternatives considered:** Email auto-join is convenient but violates issuer/subject identity. Shipping
  SCIM now expands the protocol surface before local lifecycle behavior is proven.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Initial onboarding uses verified bindings and explicit administrator grants.
  Authentication alone creates no organization or project authority (ADR 0011).
- **Risks:** An access administrator could escalate; enforce delegated grant ceilings and
  last-owner protection. Rollback preserves revocation records and disables mutations.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82d — Establish project and environment resource scopes

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** A project owner creates a project with explicit environments and grants
  scoped administration without granting access to other projects.
- **Scope:** Project/environment persistence and API, scope resolver, console switcher,
  client and isolation tests; about 18 files.
- **Non-goals:** Team membership (WU-82e), compartments (WU-82h), cross-organization moves
  and shared cross-project resources (later).
- **Acceptance:**
  - Two projects and their dev/prod environments have distinct stable IDs and constrained parent references —
    `platform/services/gateway/tests/test_projects.py::test_scope_constraints`
  - Lists, direct reads and updates enforce the same scoped grants; switching UI context cannot widen access —
    `platform/services/gateway/tests/test_projects.py::test_scope_isolation`
  - Deactivation prevents new scoped work and rejects stale mutations without deleting audit history —
    `platform/services/gateway/tests/test_projects.py::test_deactivation`
  - The console switches only among accessible projects/environments and clears prior scoped state —
    `platform/tests/integration/projects.test.ts`
- **Done:** Two projects in one organization are independently administered and no
  environment ID substitution or stale console state crosses their boundary.
- **Deps:** WU-77, WU-82b.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/projects/`, `app/authorization/scope.py`, console scope switcher and client.
  - Flow: authorized project create → explicit environments → scoped resolver → filtered UI.
  - Diagram:
    ```mermaid
    flowchart LR
      Org[Organization] --> Project[Project]
      Project --> Env[Environment]
      Grant[Scoped grant] --> Project
      Env --> Query[Authorized resource lookup]
    ```
- **Design sketch:**
  ```text
  Project(id, organization_id, status, version)
  Environment(id, organization_id, project_id, name, status, version)
  ResourceScope(organization_id, project_id, environment_id)
  project roles do not grant organization administration
  ```
- **Alternatives considered:** Teams as resource containers couple people to resource lifecycle. Application
  tags alone cannot constrain reads, writes or background jobs.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Use Project as the collaboration/resource term; Environment is explicit
  scoped state, not a caller-provided label, per WU-82a.
- **Risks:** Moving existing resources implicitly can widen access; this WU creates scopes
  only and forbids implicit transfers. Rollback disables new scope creation.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82e — Grant project permissions through teams

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** An access administrator manages organization-owned teams and binds their
  member sets to fixed permission templates on projects/environments.
- **Scope:** Team membership, scoped role bindings, model projection extension, Access
  teams/grants UI, client and race tests; about 20 files.
- **Non-goals:** Nested teams, SCIM, custom-role editing and content grants (WU-82h).
- **Acceptance:**
  - A user in two teams gets each legitimate scoped grant without leaking into an unrelated project or organization —
    `platform/services/gateway/tests/test_teams.py::test_scoped_grants`
  - Membership removal revokes inherited access at the next check and cannot race a protected mutation commit —
    `platform/services/gateway/tests/test_teams.py::test_removal_race`
  - Grant administrators cannot exceed delegated permissions; organization ownership alone grants no payload access —
    `platform/services/gateway/tests/test_teams.py::test_no_privilege_expansion`
  - The Access UI explains which team and role supply an effective permission without exposing hidden resources —
    `platform/tests/integration/teams.test.ts`
- **Done:** A team grants project access, its removal revokes that access, and every
  effective permission can be traced to an authorized scoped binding.
- **Deps:** WU-82c, WU-82d.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/access/teams.py`, `app/access/grants.py`, authorization projection, console Access.
  - Flow: team mutation → authoritative grant transaction → projection → fresh scoped check.
  - Diagram:
    ```mermaid
    flowchart LR
      User[User] --> Team[Team membership]
      Team --> Binding[Role binding on project or environment]
      Binding --> Check[Effective permission check]
    ```
- **Design sketch:**
  ```text
  Team(id, organization_id, version); TeamMember(team_id, principal_id, active)
  RoleBinding(subject=principal|team_members, role_template_version, scope, version)
  membership + grant + audit + desired_revision commit atomically
  ```
- **Alternatives considered:** Copying grants to each member simplifies checks but leaves stale grants on
  removal; retaining only organization roles cannot delegate project operations.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Fixed role templates expand into named permissions; teams group humans,
  projects own resources, and credentials never become team members (WU-82a).
- **Risks:** Group changes have a broad projection fan-out; until confirmed, affected
  organization access remains unavailable under the initial revision gate. Measure
  this bound; no positive authorization cache. Rollback revokes new bindings first.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82f — Resolve trusted attributes for authorization

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** Every protected operation receives one typed authorization context with
  authoritative scope, attribute provenance and explicit freshness/missing states.
- **Scope:** Attribute registry/resolvers, identity/scope composition, version references,
  tests and contract updates; about 12 files.
- **Non-goals:** Policy editing/evaluation (WU-82g), arbitrary external attribute providers,
  inferred content classification and trusting unqualified MFA/device claims.
- **Acceptance:**
  - Forged headers, tags, purpose and end-user IDs cannot change principal, scope, classification or destination facts —
    `platform/services/gateway/tests/test_authorization_context.py::test_untrusted_attributes`
  - Missing, stale and unavailable required values remain distinct and never default to permissive values —
    `platform/services/gateway/tests/test_authorization_context.py::test_freshness_states`
  - Only allowlisted verified issuer claims can supply attributes, with issuer/profile and expiry provenance —
    `platform/services/gateway/tests/test_authorization_context.py::test_claim_provenance`
  - Context references preserve reproducibility without writing raw sensitive attribute values into audit or logs —
    `platform/services/gateway/tests/test_authorization_context.py::test_safe_evidence`
- **Done:** The same operation produces the same typed context from authoritative
  revisions, and hostile or stale inputs cannot expand any permission.
- **Deps:** WU-82e; WU-74 for the existing issuer profile.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/authorization/context.py`, `attributes.py`, identity adapter and fixtures.
  - Flow: validated credential + server resource lookup → typed attributes → bounded context.
  - Diagram:
    ```mermaid
    flowchart LR
      Issuer[Qualified verified identity] --> Context[Typed trusted context]
      State[Versioned platform attributes] --> Context
      Context --> Freshness[Freshness and authority checks]
    ```
- **Design sketch:**
  ```text
  Attribute(value, authority, revision, observed_at, valid_until, state)
  state = known | missing | stale | unavailable
  AuthorizationContext(subject, actor?, credential, action, resource_scope, attributes)
  input purpose/end_user/tags remain separate untrusted correlation
  ```
- **Alternatives considered:** Passing arbitrary JWT/header dictionaries is flexible but obscures authority.
  Fetching external attributes on every call adds unqualified outage and latency paths.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Only reviewed attribute resolvers may populate authorization inputs; issuer
  authentication does not by itself qualify every claim for authorization (WU-82a).
- **Risks:** Attribute snapshots can outlive revocation; resolve current revisions at
  enforcement boundaries. Rollback disables the consuming policies, never silently
  drops required attributes.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82g — Evaluate versioned attribute policies with explained decisions

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** An authorized administrator publishes typed policy templates and receives
  one composed RBAC/ReBAC/ABAC decision with safe reasons and enforced obligations.
- **Scope:** Policy template registry, validated parameters, immutable versions,
  simulation/publish API and small console form, decision composer and tests;
  about 22 files.
- **Non-goals:** General policy language/editor, experimental OpenFGA Dynamic Conditions,
  budget counters and automatic content redaction; unsupported obligations fail validation.
- **Acceptance:**
  - Time-bound grants and classification/destination templates evaluate with trusted inputs and cannot be bypassed by an owner or alternate grant —
    `platform/services/gateway/tests/test_attribute_policies.py::test_mandatory_conditions`
  - Simulation and enforcement share evaluation; publication is versioned, audited and rejects unknown attributes/obligations —
    `platform/services/gateway/tests/test_attribute_policies.py::test_publish_and_simulate`
  - Required missing attributes deny and infrastructure/evaluation failures return unavailable; neither permits execution —
    `platform/services/gateway/tests/test_attribute_policies.py::test_fail_closed`
  - Policy changes are rechecked before mutations commit; safe explanations identify versions/codes without exposing hidden resources —
    `platform/services/gateway/tests/test_attribute_policies.py::test_revision_and_explanation`
  - The console validates parameters, simulates and publishes a template version —
    `platform/tests/integration/attribute_policies.test.ts`
- **Done:** A published time/classification policy constrains every applicable grant,
  produces attributable decisions, and cannot allow through missing context or failures.
- **Deps:** WU-82f, WU-82b.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/authorization/policies.py`, `decisions.py`, model conditions, policy UI/client.
  - Flow: draft template parameters → simulation → publish → current context + grants → decision → enforce.
  - Diagram:
    ```mermaid
    flowchart LR
      Template[Validated policy template] --> Version[Published immutable policy]
      Version --> Compose[Composed decision]
      Context[Trusted context and scoped grants] --> Compose
      Compose --> Enforce[Enforced obligations]
    ```
- **Design sketch:**
  ```text
  PolicyTemplate(id, parameter_schema, required_attributes, supported_obligations)
  PolicyVersion(id, scope, template_id, parameters, version, state)
  Decision(outcome, safe_codes, model_id, policy_versions, attribute_refs, obligations)
  grant_union AND credential_scope AND every mandatory applicable policy
  proposed obligations: audit_content_read; capture_off; destination_allowlist
  ```
- **Alternatives considered:** Roles for every condition cause role explosion. A second general policy engine
  adds flexibility but creates another consistency/operation boundary before need is proven.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Use reviewed typed OpenFGA conditions for conditional grants and deterministic
  platform composition for mandatory restrictions; one published contract governs both.
  No custom policy execution engine is added (WU-82a).
- **Risks:** A condition on one relation can be bypassed by another path; test the full
  composed decision. Rollback is a new audited policy version and cannot resurrect
  expired grants or override current compulsory restrictions.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82h — Enforce compartment access and processing boundaries

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** Explicit compartment membership/content grants and resource bindings
  constrain project administration, metadata reads and processing independently.
- **Scope:** Compartment records/bindings, grant administration, conditional content-read
  permission, resolver integration, console scope panel and tests; about 18 files.
- **Non-goals:** Actual payload capture/storage (WU-94), RAG/source ACL synchronization,
  cross-compartment declassification and generic shared caches (later stages).
- **Acceptance:**
  - Project administrator and organization owner cannot read a restricted content resource without a separate content grant —
    `platform/services/gateway/tests/test_compartments.py::test_admin_is_not_content_reader`
  - An expiring approved content grant permits only its target scope; expiry, removal and scope substitution deny —
    `platform/services/gateway/tests/test_compartments.py::test_conditional_content_grant`
  - Cross-compartment IDs, lists and queued management operations fail without current permission; grants cannot be self-issued beyond delegation —
    `platform/services/gateway/tests/test_compartments.py::test_scope_and_delegation`
  - Processing attributes constrain eligible destinations; absent region/classification facts deny rather than infer public access —
    `platform/services/gateway/tests/test_compartments.py::test_processing_constraints`
- **Done:** The real-service fixture proves allowed sharing and denied cross-compartment
  access independently of role administration, including expired approval.
- **Deps:** WU-82g, WU-82d, WU-82e.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/access/compartments.py`, resource bindings, authorization resolver, console panel.
  - Flow: explicit grant/binding → projection and attribute policy → constrained resource operation.
  - Diagram:
    ```mermaid
    flowchart LR
      Grant[Separate compartment content grant] --> Check[Current conditional access]
      Resource[Resource compartment binding] --> Check
      Policy[Processing restrictions] --> Check
    ```
- **Design sketch:**
  ```text
  Compartment(id, organization_id, classification, processing_policy_version)
  ResourceBinding(resource_id, compartment_ids, version)
  ContentGrant(subject, compartment_id, action, approved_by, expires_at, version)
  all bound compartments must permit access; no label-only implicit grant
  ```
- **Alternatives considered:** Project membership as content authority is simple but cannot separate operators
  from sensitive evidence. Dedicated infrastructure alone cannot protect shared metadata paths.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Compartments restrict both content and processing; configuration privilege
  grants neither content access nor authority to lower classification (WU-82a).
- **Risks:** A binding change can race work; version/recheck it at each protected boundary.
  Rollback keeps restrictive bindings and disables affected operations until reconciled.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-82i — Authorize application invocation with scoped workload credentials

- **Status:** ⬜ defined
- **Context:** The enterprise gateway review requires scoped RBAC, relationship
  grants and trusted attribute conditions before gateway resources grow. The
  owner/viewer bootstrap from WU-75 does not establish this workflow.
- **Goal:** The existing service-account API-key profile gains explicit application,
  environment and compartment invocation grants without widening management keys.
- **Scope:** WU-80 credential resolver/issuance extension, application invocation bindings,
  Access key form, client and real-service authorization tests; about 14 files.
- **Non-goals:** Personal human API keys (WU-130), workload federation (WU-121),
  enterprise SSO (WU-131); authenticated end-user delegation remains a later profile. Provider execution is WU-87.
- **Acceptance:**
  - An organization-read key remains unable to invoke; a scoped key permits only the bound application/environment/compartments —
    `platform/services/gateway/tests/test_invocation_credentials.py::test_scope_intersection`
  - Suspending the principal, revoking a grant or expiring a key denies despite an otherwise valid credential —
    `platform/services/gateway/tests/test_invocation_credentials.py::test_revocation`
  - Caller-supplied application/environment headers cannot override the authenticated binding —
    `platform/services/gateway/tests/test_invocation_credentials.py::test_scope_substitution`
  - Management keys retain existing behavior and rotation overlap/expiry bounds; issuance never exceeds issuer delegation —
    `platform/services/gateway/tests/test_invocation_credentials.py::test_management_compatibility`
  - The console issues a scoped show-once workload key and displays its effective limits —
    `platform/tests/integration/invocation_credentials.test.ts`
- **Done:** An application key resolves to a bounded invocation context, and neither
  legacy management credentials nor alternate caller headers widen that context.
- **Deps:** WU-80, WU-85, WU-82g, WU-82h. WU-79 remains the separate OAuth workload profile.
- **Architecture:** §12.2–12.5, extended only for this implemented workflow;
  WU-82a records proposed contracts without changing implementation claims.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/credentials/`, `app/applications/grants.py`, Access key UI/client.
  - Flow: credential → active principal → application binding → composed decision → invocation context.
  - Diagram:
    ```mermaid
    flowchart LR
      Key[Scoped workload credential] --> Principal[Active service account]
      Principal --> App[Application and environment grant]
      App --> Decision[Composed invocation decision]
    ```
- **Design sketch:**
  ```text
  InvocationGrant(service_account_id, application_id, environment_id, compartment_ids)
  KeyScope(organization_id, project_id?, application_id?, environment_id?, actions)
  InvocationContext(subject, credential_id, application, environment, compartments)
  effective authority = current grants intersect credential restrictions
  ```
- **Alternatives considered:** Reusing organization-read keys avoids a migration but grants unintended inference
  authority. Treating a key as the principal breaks independent lifecycle/revocation.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** This is the explicit successor to WU-80's read-only profile; application
  identity is distinct from the service account, credential and reported end user.
- **Risks:** An optional application field could become wildcard access; absence means
  management-only, not all applications. Rollback disables invocation keys while
  preserving revocation and original management access.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 1
- **Owner:** unassigned

## WU-83 — Store provider connections with sealed secrets

- **Status:** ⬜ defined
- **Context:** No platform object holds a provider credential. The kernel
  applies `ApiKey` at the driver leaf (rule 13) but the platform has nowhere to
  keep one, no approved-egress list, and no way to prove a connection works
  before a deployment depends on it. Every data-plane WU is blocked on this.
- **Goal:** An authorized project administrator connects a provider account within
  an explicit environment/compartment scope. The secret is sealed at rest, never
  returned by management reads, and applied only at the driver leaf. A bounded
  probe reports status and allowlisted diagnostics; provider bodies are not persisted.
- **Scope:** `app/connections/` (models, repository, service, API), a
  `app/secrets/` sealing module, migration, OpenFGA relations
  `connection#can_read/can_manage`, console Deployments page connections table
  with the create Sheet and Test connection row action, typed client, tests.
  About 20 files.
- **Non-goals:** Deployments (WU-84). Custom or cloud hosts (integration
  program WU-47–58; the first profile is OpenAI and Anthropic direct). Secret
  rotation UI beyond replace-and-audit. External secret managers (the first adapter is WU-122).
- **Acceptance:**
  - Creating a connection stores a sealed secret and an audit event in one
    transaction; the list and detail responses carry only a secret-present indicator —
    `platform/services/gateway/tests/test_connections.py::test_create_seals_secret`
  - No management read, export, error or diagnostic returns the secret —
    `platform/services/gateway/tests/test_connections.py::test_secret_never_leaves`
  - Test connection sends one bounded probe to the approved base URL through
    a recorded pair and stores status, latency and allowlisted diagnostic codes without a body excerpt —
    `platform/services/gateway/tests/test_connections.py::test_probe_safe_diagnostics`
  - A base URL outside the provider allowlist, a redirect, or a metadata
    address is rejected before any I/O —
    `platform/services/gateway/tests/test_connections.py::test_egress_allowlist`
  - A viewer cannot create, a foreign organization cannot read —
    `platform/services/gateway/tests/test_connections.py::test_authorization`
  - The console creates a connection and shows the probe result —
    `platform/tests/integration/connections.test.ts`
  - Project/environment/compartment grants constrain create, read, probe and replace; org ownership alone cannot cross them —
    `platform/services/gateway/tests/test_connections.py::test_scoped_abac`
- **Done:** An authorized project administrator creates both provider connections,
  the probe reports the recorded status and safe diagnostic code, and no secret
  fragment or arbitrary provider body leaves the protected execution path.
- **Deps:** WU-77, WU-82h. Resource model/projection migration is WU-82b,
  not an assumption that WU-75 already supports arbitrary relations.
- **Architecture:** §12 (proposed connections subsection), §7 unchanged.
- **Integration:**
  - Layer: platform service and console; depends on `ocai.core.credentials`
    and `ocai.wire` for the probe; platform → public ocai only.
  - Modules: `app/connections/{models,repository,service,api}.py`,
    `app/secrets/seal.py`, migration for `connections` (revision allocated at implementation), console
    `pages/deployments.vue` (connections section), client operations.
  - Flow: console Sheet → typed client → FastAPI authorize → seal secret →
    transaction (row + audit) → OpenFGA outbox. Probe: service unseals in
    memory → `ocai.wire` request through the provider's catalog host →
    safe probe result row.
  - Diagram:
    ```mermaid
    sequenceDiagram
      participant C as Console
      participant A as FastAPI
      participant S as Sealer
      participant P as PostgreSQL
      participant W as ocai.wire
      C->>A: POST connections {provider, base_url, secret}
      A->>S: seal(secret, key_id)
      A->>P: INSERT connection + audit (one tx)
      C->>A: POST connections/{id}/probe
      A->>S: unseal (memory only)
      A->>W: bounded GET /models (recorded pair)
      A->>P: INSERT probe_result {status, latency_ms, diagnostic_code}
    ```
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Connection:
      id: UUID; scope: ResourceScope; compartment_ids: frozenset[UUID]; version: int
      provider: str                 # "openai" | "anthropic"
      account_label: str            # free text, no secret
      base_url: str                 # must match provider allowlist
      secret_ref: SecretRef         # key_id + ciphertext id, never the value
      secret_present: bool          # no credential substring
      last_probe: ProbeResult | None

  @dataclass(frozen=True, slots=True)
  class ProbeResult:
      at: datetime; status: int | None; latency_ms: int | None
      diagnostic_code: str | None   # allowlisted metadata, never raw provider body
      error: str | None             # transport error class, no secret
  ```
  Endpoints: `GET/POST …/connections`, `GET/PATCH/DELETE …/connections/{id}`,
  `POST …/connections/{id}/probe`.
- **Alternatives considered:** Store secrets in Keycloak or OpenFGA (benefit:
  no sealing code; cost: neither is a secret store). Environment variables per
  connection (benefit: nothing at rest; cost: no runtime creation, no audit).
  Hash the secret (impossible: the driver must apply it; security design).
- **Freeze:** none; provisional platform schema.
- **Decision (sealing):** AES-256-GCM through the runtime's implementation,
  versioned external key, record-bound additional data, as ADR 0011 fixed for
  console tokens; the same key-supply contract, a distinct key id.
- **Decision (egress):** per-provider base URL allowlist in configuration;
  the probe disallows redirects and proxies, as WU-74 fixed for JWKS fetches.
- **Risks:** Probe responses may contain sensitive values; persist only allowlisted
  diagnostics and test malicious recorded responses. Key retirement requires a
  recoverable re-seal procedure. Rollback disables writes while keeping sealed rows
  and audit; it never drops secrets as an incidental down migration.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 2
- **Owner:** unassigned

## WU-84 — Administer deployments on qualified interfaces

- **Status:** ⬜ defined
- **Context:** A policy routes to deployments and a receipt names one, but
  no deployment object exists. The mockup listed batches and embeddings
  deployments, which the qualified surface does not include; the object must
  make the qualified interface list the only choice (delivery design:
  "scope the gateway's supported surface to exercised capabilities").
- **Goal:** An authorized project administrator binds a scoped connection to an
  interface/tag supported by a reviewed platform support manifest backed by kernel
  evidence. Deployments record approved processing attributes and their provenance,
  version and paused state; arbitrary region text does not establish residency.
- **Scope:** `app/deployments/`, migration, OpenFGA relations, the console
  create-deployment Sheet steps 1–3 (connection, model and region, review),
  deployments table, typed client, tests. About 18 files.
- **Non-goals:** Credential step and connect snippet (WU-99). Qualification
  of declared capabilities against traffic (WU-103). Health probes per
  deployment (WU-96 alert source; the probe itself lands with WU-87 health
  gate). Interfaces outside `openai/chat_completions` and
  `anthropic/messages` (integration program).
- **Acceptance:**
  - The interface field accepts only the reviewed platform support manifest backed by
    kernel recorded-pair evidence and matching catalog artifacts; `openai/batches` is rejected with a reason —
    `platform/services/gateway/tests/test_deployments.py::test_interface_must_be_qualified`
  - Create, update and pause each write a new version and an audit event —
    `platform/services/gateway/tests/test_deployments.py::test_versioned_mutations`
  - A deployment cannot reference a connection of another organization, project, environment or
    compartment without an explicit supported grant, or another provider —
    `platform/services/gateway/tests/test_deployments.py::test_connection_scope`
  - Declared capabilities are stored as "declared, not tested" and the
    response says so —
    `platform/services/gateway/tests/test_deployments.py::test_capabilities_declared_flag`
  - The console wizard creates a paused deployment and the table shows it —
    `platform/tests/integration/deployments.test.ts`
  - A guessed region label or stale processing approval cannot satisfy a mandatory residency or classification policy —
    `platform/services/gateway/tests/test_deployments.py::test_processing_attribute_authority`
- **Done:** An owner creates `openai-eu-west` on `openai/chat_completions`
  and `anthropic-us-east` on `anthropic/messages`, both start paused, and an
  attempt to create a batches deployment is refused with the qualified list.
- **Deps:** WU-83.
- **Architecture:** §12 (resource administration extended), §4 catalog lock referenced.
- **Integration:**
  - Layer: platform service and console; reads the kernel `Catalog` and
    `CapabilityProfile` keys against the reviewed platform support manifest.
  - Modules: `app/deployments/{models,repository,service,api}.py`, migration
    for `deployments` (revision allocated at implementation), console wizard components, client.
  - Flow: Sheet → client → authorize → validate interface/tag against support evidence and catalog →
    transaction (row version + audit) → outbox.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Deployment:
      id: UUID; scope: ResourceScope; compartment_ids: frozenset[UUID]; version: int
      name: str                      # lowercase slug, unique per project/environment
      connection_id: UUID
      interface: str                 # NodeId "provider/interface" in qualified set
      interface_tag: str             # dated revision from the catalog
      model: str                     # exact provider model id
      processing: ProcessingAttributes  # reviewed region/retention facts + revision; unknown explicit
      max_concurrent: int
      paused: bool
      declared_capabilities: frozenset[str]   # e.g. {"streaming","tools","response_format.json_schema"}
      qualified_capabilities: frozenset[str]  # empty until WU-103 writes it
  ```
  Endpoints: `GET/POST …/deployments`, `GET/PATCH …/deployments/{id}`,
  `POST …/deployments/{id}/pause`, `…/resume`.
- **Alternatives considered:** Free-text interface with a warning (benefit:
  future providers without a release; cost: the console would advertise
  unqualified surface, the exact failure the mockup showed). Deployment
  without version (benefit: simpler; cost: receipts could not cite the
  revision executed).
- **Freeze:** none.
- **Decision (qualified set):** Catalog presence is a declaration, not execution
  qualification. The platform support manifest pins exercised interface/tag/feature
  evidence and catalog artifacts. WU-103 records installation-specific results;
  declared deployment capabilities never alone authorize a route.
- **Risks:** Catalog and processing-approval revisions can invalidate eligibility;
  retain referenced history, mark unavailable support explicitly and reject new
  execution. Rollback pauses affected deployments rather than erasing evidence.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 2
- **Owner:** unassigned

## WU-85 — Register applications and their contracts

- **Status:** ⬜ defined
- **Context:** The request lifecycle resolves an application context, a
  policy "applies to" an application, and a key belongs to one; the identity
  program stops at service accounts. Without an application object the
  console cannot attribute an execution to `document-assistant` or state
  which interface the client speaks.
- **Goal:** An authorized project administrator registers a versioned application
  contract, accountable owning team, allowed environments and compartment bindings.
  Service-account invocation is an explicit separate grant in WU-82i.
- **Scope:** `app/applications/` persistence/API, environment and compartment
  binding, OpenFGA relations, console Applications page, client and tests; about
  14 files. Credential issuance stays in WU-82i.
- **Non-goals:** Invocation credentials (WU-82i), budgets (WU-92/92a),
  migration analysis (WU-104). Cross-project application transfer is deferred.
- **Acceptance:**
  - A versioned application has an active owning team, project, allowed
    environments and supported client interface/tag —
    `platform/services/gateway/tests/test_applications.py::test_explicit_ownership`
  - Foreign or unauthorized team/environment/compartment bindings fail;
    deactivation blocks new invocation resolution —
    `platform/services/gateway/tests/test_applications.py::test_binding_scope`
  - Contract or binding edits create audited versions and preserve references
    from earlier executions —
    `platform/services/gateway/tests/test_applications.py::test_versioned_contract`
  - The console shows the contract, scope and accountable team without
    implying a key or service account grants access —
    `platform/tests/integration/applications.test.ts`
- **Done:** An application has an attributable, versioned project/environment/
  compartment contract, and invalid cross-scope bindings cannot be created.
- **Deps:** WU-82h, WU-78.
- **Architecture:** §12 (resource administration extended).
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/applications/`, scoped migrations, Applications page/client.
  - Flow: authorized scoped create → validate owner/bindings → versioned row,
    audit and projection → application context consumed by WU-82i.
  - Diagram:
    ```mermaid
    flowchart LR
      Team[Accountable team] --> App[Versioned application]
      Project[Project and environments] --> App
      Compartment[Compartment bindings] --> App
      App --> Grant[WU-82i invocation grant]
    ```
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Application:
      id: UUID; organization_id: UUID; project_id: UUID; version: int
      name: str; owning_team_id: UUID
      client_interface: str; client_tag: str
      environment_ids: frozenset[UUID]; compartment_ids: frozenset[UUID]
      active: bool
  # Service-account bindings and credential restrictions are separate records.
  ```
- **Alternatives considered:** Treat the service account as the application
  (benefit: one object; cost: contract and policy binding would hang off an
  identity object, and one account cannot own two applications). Infer the
  contract from the first request (benefit: no field; cost: violates "no
  inferred authority or contract from caller input").
- **Freeze:** none.
- **Decision (ownership):** Application, accountable team, executing principal
  and credential have independent lifecycles (WU-82a). Owning a team/application
  does not implicitly grant content or invocation permission.
- **Risks:** Changing bindings can leave stale execution authority; WU-82i and
  the data plane recheck current revisions. Rollback keeps historical versions and
  deactivates new bindings, never reconstructs authority from a client tag.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 2
- **Owner:** unassigned

## WU-86 — Version routing policies with explained eligibility

- **Status:** ⬜ defined
- **Context:** The flagship demonstration is an explained route choice. The
  kernel can inspect a prepared execution (WU-27) and enforce loss predicates
  (WU-28), but the platform has no policy object, no draft and publish
  lifecycle, and no dry run. The mockup's Explain panel has no backend.
- **Goal:** An owner edits a draft policy for an application: eligibility
  (providers, regions, required capabilities, health gate), denied loss
  dispositions and denied semantic shifts, fallback order and fallback
  triggers. A dry run against a sample request lists the deployments that
  would be tried in order and each visible excluded deployment with a safe reason; hidden resources are omitted,
  without provider I/O. Publishing creates an immutable version.
- **Scope:** `app/policies/`, migration, OpenFGA relations, console Routing
  policy editor (desktop inline, tablet Sheet, mobile read-only), the Explain
  panel, client, tests. About 24 files.
- **Non-goals:** Execution (WU-87). Health probe implementation (WU-87 adds
  the probe the gate reads). Canary share of a version (WU-105). Cost/latency or weighted selection among eligible candidates (WU-109).
- **Acceptance:**
  - A dry run performs zero wire calls and returns ordered eligible
    candidates plus excluded candidates each with a reason code and sentence —
    `platform/services/gateway/tests/test_policies.py::test_dry_run_explains_without_io`
  - A deployment lacking a required evidenced capability, outside allowed
    regions, paused, or on a non-chat interface is excluded with the matching
    reason —
    `platform/services/gateway/tests/test_policies.py::test_eligibility_reasons`
  - A denied loss disposition on a field the sample request uses excludes the
    deployment by fidelity, using the kernel inspection report —
    `platform/services/gateway/tests/test_policies.py::test_fidelity_exclusion`
  - Publishing freezes the version; editing after publish creates a new draft
    based on it; both write audit —
    `platform/services/gateway/tests/test_policies.py::test_publish_is_immutable`
  - The console editor saves a draft, runs the explain and publishes v8 —
    `platform/tests/integration/policies.test.ts`
  - Missing/stale region or classification facts exclude a deployment; all mandatory scope/ABAC policies apply before fidelity evaluation —
    `platform/services/gateway/tests/test_policies.py::test_abac_eligibility`
  - Explain omits inaccessible candidate identifiers and never returns raw policy attributes or hidden resource counts —
    `platform/services/gateway/tests/test_policies.py::test_explain_no_scope_disclosure`
  - A production policy requiring independent approval cannot be published by its author; approved version and approver are pinned —
    `platform/services/gateway/tests/test_policies.py::test_publish_separation_of_duties`
- **Done:** For the recorded "strict JSON extraction, streaming" sample,
  the dry run of `docassist-prod` v8 lists two candidates in order and five
  exclusions whose reasons match the fixture, with no network call.
- **Deps:** WU-84, WU-85, WU-82g, WU-82h; kernel WU-27 and WU-28 (complete).
- **Architecture:** §12 (proposed routing policy subsection), §3.4 and §5 referenced.
- **Integration:**
  - Layer: platform service and console; uses `ocai.chat.facade` inspection
    and `ocai.core.fidelity` predicates through public APIs only.
  - Modules: `app/policies/{models,rules,explain,api}.py`, migration
    for `policies` (revision allocated at implementation), console editor components, client.
  - Flow: sample request → decode with the client contract codec → for each
    deployment: eligibility rules → kernel inspection (prepared, no I/O) →
    fidelity predicates → candidate or exclusion → ordered result.
  - Diagram:
    ```mermaid
    flowchart LR
      R[Sample request] --> E{Eligibility}
      E -- fails --> X1[Excluded: eligibility reason]
      E -- passes --> I[Kernel inspection, no I/O]
      I --> F{Denied loss or shift?}
      F -- yes --> X2[Excluded: fidelity reason]
      F -- no --> C[Candidate, fallback order]
    ```
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class PolicyVersion:
      policy_id: UUID; version: int; application_id: UUID
      state: Literal["draft", "published", "superseded"]
      scope: ResourceScope
      authorization_policy_versions: tuple[VersionRef, ...]
      eligibility: Eligibility        # approved processing attributes, evidenced capabilities, health
      denied_loss: tuple[LossRule, ...]        # (field_pattern, disposition, condition)
      denied_shifts: tuple[ShiftRule, ...]     # (shift_kind, condition)
      fallback_order: tuple[UUID, ...]         # deployment ids
      fallback_on: frozenset[str]              # {"rate_limited","overloaded","timeout_before_first_token","server_error"}
      published_by: UUID | None; published_at: datetime | None

  @dataclass(frozen=True, slots=True)
  class ExplainResult:
      would_try: tuple[UUID, ...]
      excluded: tuple[Exclusion, ...]          # (deployment_id, kind: "eligibility"|"fidelity", code, sentence)
      snapshot_id: UUID
      authorization_decision_id: UUID; attribute_revision_refs: tuple[VersionRef, ...]
  ```
  Endpoints: `GET/POST …/policies`, `GET/PATCH …/policies/{id}/draft`,
  `POST …/policies/{id}/publish`, `POST …/policies/{id}/explain`.
- **Alternatives considered:** Policy as a YAML file (benefit: diffable;
  cost: no versioned attribution, the product design makes PostgreSQL
  authoritative). Explain by executing against a sandbox (benefit: real
  effects; cost: spend and disclosure; the migration workflow separates
  offline replay from live evaluation).
- **Freeze:** none; provisional platform schema. Kernel `FieldLoss` and
  `SemanticShift` vocabularies are consumed, not changed.
- **Decision (loss versus shift):** rules and the receipt keep the kernel's
  two vocabularies separate (architecture §2.5); the console never merges
  them into one column.
- **Decision (content policy):** refusal and content-filter outcomes are
  never fallback triggers (product design, routing section).
- **Risks:** Explain can drift or disclose hidden deployments. Use the same
  evaluator in execution with current mandatory restrictions and filtered evidence.
  Rollback publishes an audited version; it cannot bypass later security policy.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 2
- **Owner:** unassigned

## WU-87 — Execute governed unary chat on the compatibility endpoint

- **Status:** ⬜ defined
- **Context:** Everything above is control plane. The product promise is a
  request that enters as OpenAI Chat Completions, is routed by policy,
  executed through ocai with credentials at the leaf, and leaves with a
  receipt. The kernel's governed paths are proven on recorded pairs (WU-32);
  the platform has no endpoint.
- **Goal:** An application key sends a unary Chat Completions request; the
  gateway resolves the snapshot, runs the policy explain, executes candidates
  in fallback order through `ocai.chat.facade` with the connection's secret
  applied per attempt, rechecks eligibility on each fallback, and stores a
  receipt linking every attempt, decision and fidelity finding. The response
  carries the execution id.
- **Scope:** `app/dataplane/` (endpoint, execution service, receipt writer),
  `app/receipts/` models and migration, deployment health probe recorder,
  client contract codecs via `ocai.wire`, tests over recorded pairs. About 22
  files.
- **Non-goals:** Streaming (WU-88). Admission limits (WU-89). Usage pricing
  (WU-91). Receipt UI (WU-93). Payload capture (WU-94): this WU stores
  metadata and findings only.
- **Acceptance:**
  - A valid request on the recorded OpenAI pair returns the provider's
    converted response, `ocai-execution-id`, and a receipt with one attempt —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_success_receipt`
  - A recorded 429 on the first candidate falls back to the second; the
    receipt shows both attempts, the allowlisted provider error code and a sanitized message, and the policy
    decision sentence —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_fallback_with_reasons`
  - A request whose conversion would hit a denied disposition is rejected
    before any I/O with an OpenAI-shaped error naming the rule —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_denied_before_io`
  - The route chosen equals the policy explain for the same snapshot —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_route_matches_explain`
  - No response, receipt, log or error contains the connection secret —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_secret_isolation`
  - A key of another application, a paused deployment, and a stale snapshot
    each fail closed with the mapped error —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_fail_closed`
  - Primary outage cannot bypass classification, residency, compartment or credential conditions on a fallback —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_fallback_preserves_abac`
  - Revocation or stale attributes between attempts block the next attempt and preserve a safe rejected/unavailable receipt —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_reauthorize_each_attempt`
  - Obligations are acknowledged by enforcement; unknown or unimplemented obligations cannot allow provider I/O —
    `platform/services/gateway/tests/test_dataplane_unary.py::test_obligation_enforcement`
- **Done:** A permitted recorded fallback preserves the application contract
  and reports its findings; a restricted-EU application excludes a US destination
  even during outage, and a revoked invocation grant prevents the next attempt.
- **Deps:** WU-82i, WU-85, WU-86; kernel WU-29–32 (complete).
- **Architecture:** §12 (proposed execution subsection), §6 and §8 referenced.
- **Integration:**
  - Layer: platform service; platform → `ocai.chat`, `ocai.runtime`,
    `ocai.wire`, plugins through public APIs only.
  - Modules: `app/dataplane/{endpoint,execute,receipt}.py`,
    `app/receipts/{models,repository}.py`, migration for `receipts` (revision allocated at implementation).
  - Flow: key auth → application → snapshot → explain → for each candidate:
    unseal in memory → `ApiKey` → facade `chat()` with policy hooks → on
    retryable failure next candidate → receipt (attempts, decisions,
    `FidelityReport`, usage with provenance) → response encode.
  - Diagram:
    ```mermaid
    sequenceDiagram
      participant App
      participant GW as /v1/chat/completions
      participant Pol as Policy explain
      participant K as ocai facade
      participant P as Provider (recorded)
      App->>GW: POST (application key)
      GW->>Pol: snapshot + request
      Pol-->>GW: would_try [d1, d2], excluded [...]
      GW->>K: chat(request, d1 credential)
      K->>P: attempt 1
      P-->>K: 429 (safe native code)
      GW->>GW: recheck eligibility(d2)
      GW->>K: chat(request, d2 credential)
      P-->>K: 200
      GW->>GW: receipt{attempts, decisions, report, usage}
      GW-->>App: response + ocai-execution-id
    ```
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Receipt:
      execution_id: str             # "exe_" + ULID
      scope: ResourceScope; compartment_ids: frozenset[UUID]
      application_id: UUID; principal_id: UUID; credential_id: UUID | None
      authorization_decision_ids: tuple[UUID, ...]
      snapshot_id: UUID; policy_version: int
      client_contract: str; converter_artifact: str   # ocai version + catalog lock hash
      attempts: tuple[Attempt, ...]
      decisions: tuple[Decision, ...]                # (at, kind, sentence, rule_ref)
      findings: tuple[Finding, ...]                  # from FidelityReport, loss and shift separate
      usage: tuple[UsageDimension, ...]              # (name, attempt, value|None, provenance)
      status: Literal["succeeded","succeeded_after_fallback","failed","rejected"]
      finish: str | None; finish_native: str | None
      evidence_hash: str | None                       # allowlisted metadata only, not payload digest

  @dataclass(frozen=True, slots=True)
  class Attempt:
      index: int; deployment_id: UUID; deployment_version: int
      started_at: datetime; first_token_at: datetime | None; ended_at: datetime
      outcome: str; provider_error_code: str | None  # arbitrary body excluded
  ```
  Endpoint: `POST /v1/chat/completions` (unary only in this WU; `stream:
  true` returns 501 with the `ocai` extension until WU-88).
- **Alternatives considered:** Proxy the request body unchanged to the
  provider (benefit: zero conversion risk; cost: no fidelity report, which is
  the product). One attempt per execution id (benefit: simpler schema; cost:
  the demonstration requires linking attempts).
- **Freeze:** none; the receipt schema is provisional until WU-103.
- **Decision (receipt naming):** An optional digest covers allowlisted evidence
  metadata only and is labelled as a hash; it does not prove authenticity. Payload
  digests are not silently collected when capture is off.
- **Decision (leaf credentials):** settled by ADR 0007 and rule 13; the
  platform unseals in memory for one attempt and never passes the secret
  through a hook.
- **Risks:** A pinned snapshot can conceal a new revocation or policy restriction.
  Revalidate current scope, credential, mandatory policies and processing facts
  before every outbound attempt; never hold database locks over network generation.
  Rollback disables inference while retaining receipts.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 2
- **Owner:** unassigned

## WU-88 — Stream governed chat with explicit partial outcomes

- **Status:** ⬜ defined
- **Context:** A stream failure after delivery needs an explicit partial outcome.
  The kernel owns stream termination and governed middleware; the platform must
  qualify those paths plus bounded access/attribute revalidation during release.
- **Goal:** `stream: true` requests are served as SSE from the canonical
  stream, fallback happens only before the first externally visible semantic output, a failure
  after partial delivery ends the stream with an explicit error event and a
  receipt status of partial, usage is labelled estimated only when a qualified estimator exists, otherwise
  unknown when the provider's final usage never arrives, and cancellation propagates upstream.
- **Scope:** `app/dataplane/stream.py`, receipt status and usage extensions,
  SSE encoding through `ocai.wire` client stream codec (WU-31), tests over
  recorded SSE pairs. About 12 files.
- **Non-goals:** Cross-provider continuation after partial delivery (opt-in
  contract, horizon). Buffering for strict pre-delivery response policy (the
  design says the tradeoff must be explicit; this WU delivers incrementally
  and documents the limit).
- **Acceptance:**
  - A recorded SSE pair streams to the client and the folded receipt usage
    equals the unary receipt's for the paired recording (fold law at the
    platform boundary) —
    `platform/services/gateway/tests/test_dataplane_stream.py::test_fold_parity`
  - A recorded failure before the first chunk falls back to the next
    candidate; one after partial delivery does not, ends with an error event
    carrying canonical code, native code and `retryable`, and the receipt says
    partial with measured delivered bytes/events and separately labelled token estimates —
    `platform/services/gateway/tests/test_dataplane_stream.py::test_partial_is_explicit`
  - When the provider's final usage event never arrives, output tokens are
    stored as locally estimated with an estimator reference when available,
    otherwise unknown; delivered output is never equated to billed usage —
    `platform/services/gateway/tests/test_dataplane_stream.py::test_usage_without_final_event`
  - Client disconnect cancels the upstream request and the receipt records
    cancellation without claiming billing stopped —
    `platform/services/gateway/tests/test_dataplane_stream.py::test_cancellation`
  - An expired approval or observed revocation stops subsequent release at the qualified checkpoint, at most five seconds between checks; authorization outage fails closed with an explicit partial outcome —
    `platform/services/gateway/tests/test_dataplane_stream.py::test_abac_checkpoint`
  - A tool-call or other semantic delta already delivered prevents fallback even when no text token was emitted —
    `platform/services/gateway/tests/test_dataplane_stream.py::test_no_fallback_after_semantic_output`
- **Done:** The first demonstration's streaming half runs on recorded pairs:
  a stream interrupted after recorded partial output ends with an explicit error event and
  a partial receipt, and an outage before the first externally visible output falls back with
  the same explained reasons as the unary path.
- **Deps:** WU-87; kernel WU-24, WU-25, WU-31 (complete).
- **Architecture:** §12 (execution subsection) extended, §3.3 and §9 referenced.
- **Integration:**
  - Layer: platform service; `ocai.chat.facade.stream()` and the client
    stream codec from `ocai.wire`.
  - Modules: `app/dataplane/stream.py`, receipt writer extension.
  - Flow: as WU-87 until the facade call; then chunk → client SSE frame →
    response; `StreamEnd` → usage and report into the receipt; error
    mid-stream → error frame → partial receipt.
- **Design sketch:**
  ```python
  class StreamOutcome(StrEnum):
      COMPLETED = "completed"
      PARTIAL = "partial"            # semantic output delivered before termination
      FAILED_BEFORE_OUTPUT = "failed_before_output"
      CANCELLED = "cancelled"

  # SSE terminal frame on failure, OpenAI-shaped with the ocai extension
  # data: {"error": {"message": "...", "type": "server_error",
  #        "ocai": {"code": "TransientError", "native": "overloaded_error",
  #                 "retryable": true, "delivered_events": 12}}}
  ```
- **Alternatives considered:** Retry transparently after partial delivery
  (benefit: fewer client errors; cost: duplicated or stitched answers the
  design forbids). Buffer the whole stream to apply response policy first
  (benefit: strict guarantee; cost: it is not streaming; offered later as an
  explicit per-application option, not the default).
- **Freeze:** none.
- **Decision (partial default):** settled by the product design's routing
  and streaming section; no retry after the first externally visible semantic output.
- **Decision (error wire shape):** canonical code, native code, retryable,
  as rule 8 requires; carried in the `ocai` extension of the OpenAI error
  frame so existing clients keep parsing.
- **Risks:** Clients that ignore the error frame see a truncated answer;
  bounded by the finish reason `error` in the last chunk and the receipt.
  Rollback: revert; unary path unaffected.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 2
- **Owner:** unassigned

## WU-89 — Admit requests under concurrency and rate reservations

- **Status:** ⬜ defined
- **Context:** Gateway admission needs tested concurrency and rate reservations
  across replicas. The enterprise workflow requires key and parent application/
  environment limits plus deployment caps; current data-plane work has no limits.
- **Goal:** Each application/environment and key carries optional rate limits, each
  deployment its concurrency cap, and admission reserves a slot before
  execution; a refused request returns 429 with the limit that refused it and
  a retry hint, and reservations released on completion, failure or crash
  recovery never leak.
- **Scope:** `app/admission/` (limits, reservations, release), key limit
  fields on the WU-80 key object, deployment cap enforcement, console key
  form rate-limit fields, tests under concurrency. About 14 files.
- **Non-goals:** Budgets (WU-92). Provider rate-limit pacing from measured
  headers (integration program WU-70; consumed later). Global fairness
  across organizations (horizon).
- **Acceptance:**
  - Concurrent requests above a key's max parallel are refused with 429 and
    the reason names the key limit; the others proceed —
    `platform/services/gateway/tests/test_admission.py::test_parallel_cap`
  - Requests per minute and tokens per minute are enforced on a sliding
    window with the window and remaining count in the error —
    `platform/services/gateway/tests/test_admission.py::test_rate_windows`
  - A deployment's concurrency cap excludes it from candidates while full,
    and the receipt records the exclusion as an admission decision —
    `platform/services/gateway/tests/test_admission.py::test_deployment_saturation`
  - A reservation held by a crashed worker expires and is reclaimed; a
    duplicate release is idempotent —
    `platform/services/gateway/tests/test_admission.py::test_reservation_recovery`
  - New key issuance cannot bypass parent application/environment concurrency/rate limits; queued reservations reauthorize before provider I/O —
    `platform/services/gateway/tests/test_admission.py::test_parent_limits_and_queued_revocation`
- **Done:** Under concurrent load on recorded pairs, no key exceeds its
  parallel or per-minute limits, no deployment exceeds its cap, refusals
  name their limit, and reservation counts return to zero after the run.
- **Deps:** WU-88.
- **Architecture:** §12 (execution subsection) extended; §9 observability referenced.
- **Integration:**
  - Layer: platform service; no kernel change (pacing stays in WU-70).
  - Modules: `app/admission/{limits,reservations,api}.py`, key model
    extension, migration for `admission` (revision allocated at implementation).
  - Flow: key auth → admission check (PostgreSQL row-level reservation with
    lease) → explain → execute → release; sweeper reclaims expired leases.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class KeyLimits:
      requests_per_minute: int | None
      tokens_per_minute: int | None     # counted on provider-reported or estimated input+output
      max_parallel: int | None

  @dataclass(frozen=True, slots=True)
  class Reservation:
      id: UUID; scope: Literal["application_environment","key","deployment"]; scope_id: UUID
      execution_id: str; leased_until: datetime
  ```
  429 body: OpenAI error envelope, `ocai: {code: "RateLimitError",
  limit: "key.max_parallel", retry_after_ms: 1200}`.
- **Alternatives considered:** Redis token bucket (benefit: faster; cost: a
  new stateful dependency ADR 0011 declined for sessions; PostgreSQL leases
  suffice at MVP load and are measured in WU-103). In-process counters
  (benefit: trivial; cost: wrong across replicas).
- **Freeze:** none.
- **Decision (storage):** Use transactional PostgreSQL reservation leases in
  this first profile; this is an admission decision, not an implication of ADR
  0011's session choice. Revisit a cache tier only with measured evidence.
- **Risks:** Lease expiry alone cannot prove an upstream call stopped. Use
  fencing, bounded attempt deadlines and reconciliation before releasing ambiguous
  concurrency; tests report the actual overshoot/recovery bound. Rollback disables
  new admission rather than lifting configured limits silently.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 3
- **Owner:** unassigned

## WU-90 — Record the usage ledger with provenance and reconciliation

- **Status:** ⬜ defined
- **Context:** Receipts hold usage per attempt, but there is no ledger to
  sum, no reconciliation when a provider's final usage arrives late, and no
  correction path. The evidence design requires deduplication, reservations,
  reconciliation, provenance and explicit corrections, and the mockup's
  Overview depends on daily totals with an unknown count.
- **Goal:** Every execution writes ledger rows per usage dimension with
  provenance; a reconciliation job ingests provider usage exports or late
  events, writes corrections referencing the original rows, and daily totals
  per organization are queryable with unknown counted separately.
- **Scope:** `app/ledger/` (rows, totals, reconciliation, corrections),
  migration, an operator reconciliation command that reads a recorded export
  fixture, management totals endpoint, tests. About 14 files.
- **Non-goals:** Pricing (WU-91). Budgets (WU-92). Usage breakdown UI
  (WU-95). Live provider usage APIs (a recorded export fixture stands in;
  live ingestion is a later adapter).
- **Acceptance:**
  - An execution writes one row per dimension and attempt with provenance;
    a failed attempt with no usage writes unknown rows with the reason —
    `platform/services/gateway/tests/test_ledger.py::test_rows_with_provenance`
  - Replaying the same execution's write is idempotent —
    `platform/services/gateway/tests/test_ledger.py::test_idempotent_write`
  - Reconciliation from a recorded export writes a correction row linked to
    the original, flips provenance to reconciled, and never edits history —
    `platform/services/gateway/tests/test_ledger.py::test_reconciliation_corrects`
  - Daily totals return known sums and an unknown count, never a zero in
    place of unknown —
    `platform/services/gateway/tests/test_ledger.py::test_totals_keep_unknown`
  - Ledger attribution comes from the admitted server context and survives team renames, membership changes and later application ownership changes —
    `platform/services/gateway/tests/test_ledger.py::test_immutable_attribution`
  - Totals and reconciliation are scoped before aggregation; hidden projects or compartments cannot leak through counts —
    `platform/services/gateway/tests/test_ledger.py::test_authorized_aggregates`
- **Done:** After a recorded day of executions including failures, totals
  per organization match the fixture, the unknown count equals the failed
  attempts without usage, and a reconciliation run adds corrections without
  changing any earlier row.
- **Deps:** WU-88.
- **Architecture:** §12 (proposed evidence/accounting subsection).
- **Integration:**
  - Layer: platform service.
  - Modules: `app/ledger/{models,write,totals,reconcile}.py`, migration
    for `ledger` (revision allocated at implementation), operator command `reconcile-usage`.
  - Flow: receipt commit → ledger rows in the same transaction → totals view;
    reconcile: export fixture → match by execution id and provider request
    id → correction rows.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class LedgerRow:
      id: UUID; scope: ResourceScope; application_id: UUID
      compartment_ids: frozenset[UUID]; principal_id: UUID; credential_id: UUID | None
      allocation_team_id: UUID; attribution_version: int
      execution_id: str; attempt: int; deployment_id: UUID
      dimension: str                 # input_tokens | output_tokens | cache_read | cache_write | reasoning
      value: int | None              # None = unknown
      provenance: Provenance         # provider_reported | locally_estimated | reconciled | unknown
      unknown_reason: str | None
      corrects: UUID | None          # prior row this one supersedes
      occurred_at: datetime
  ```
  Endpoint: `GET …/usage/totals?from&to` → `{known: {...}, unknown_executions: n}`.
- **Alternatives considered:** Derive totals from receipts on read (benefit:
  no second table; cost: corrections and reconciliation would mutate
  receipts). Mutable rows updated on reconciliation (benefit: simpler sums;
  cost: history rewritten, the evidence design forbids it).
- **Freeze:** none.
- **Decision (corrections):** append-only with a `corrects` link, as the
  evidence design states ("corrections reference prior records").
- **Risks:** Double counting when both a late stream usage event and an
  export arrive; bounded by the idempotency key `(execution, attempt,
  dimension, source)`. Rollback: revert; rows remain readable.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 3
- **Owner:** unassigned

## WU-91 — Price usage from a dated pricing table with overrides

- **Status:** ⬜ defined
- **Context:** The mockup's spend card says "list prices of 1 Nov 2026" and
  marks cost as locally estimated; nothing stores a price, its effective
  date, or who overrode it. The integration program's cost satellite (WU-69)
  prices measured usage; the platform needs the table it reads from and the
  provenance of each price.
- **Goal:** An organization has a pricing table: per provider and model,
  per dimension, a price per declared billable unit with an effective date and a
  source (provider list, imported on a date, or override by a principal).
  Cost rows are computed from the ledger using the price effective at
  execution time, carry the pricing version, and show a justified bound when
  available or an explicitly unbounded unknown part.
- **Scope:** `app/pricing/`, migration, cost computation joining the ledger,
  console Settings pricing section with add-override Sheet, client, tests.
  About 14 files.
- **Non-goals:** Fetching provider price pages (WU-65 model facts refresh
  produces reviewable diffs; this WU imports its output). Budgets (WU-92).
  Currency conversion (USD only in release 1).
- **Acceptance:**
  - A price row has an effective date and a source; an override records the
    principal and supersedes without deleting —
    `platform/services/gateway/tests/test_pricing.py::test_override_provenance`
  - Cost uses the price effective at the execution's time, not the current
    one —
    `platform/services/gateway/tests/test_pricing.py::test_effective_date`
  - An execution with unknown input tokens yields a cost range with the
    known part priced and the unknown part listed, never a single number —
    `platform/services/gateway/tests/test_pricing.py::test_unknown_yields_range`
  - A model with no price yields cost unknown with reason `no_price` —
    `platform/services/gateway/tests/test_pricing.py::test_missing_price`
  - The console shows the table and adds an override —
    `platform/tests/integration/pricing.test.ts`
  - Unbounded unknown usage has no invented upper price; price overrides require the scoped pricing permission and immutable audit —
    `platform/services/gateway/tests/test_pricing.py::test_unbounded_and_authorized_override`
- **Done:** The recorded day prices to the fixture total, with the cost of
  each unknown-usage execution reported as a range and the pricing version
  on every cost row.
- **Deps:** WU-90; integration program WU-69 (cost satellite API).
- **Architecture:** §12 (evidence/accounting subsection) extended.
- **Integration:**
  - Layer: platform service and console; consumes the cost satellite's
    pricing function with the platform table as its price source.
  - Modules: `app/pricing/{models,table,cost,api}.py`, migration
    for `pricing` (revision allocated at implementation), console Settings section.
  - Flow: ledger row → price lookup (model, dimension, effective ≤ occurred)
    → cost row (value or range, provenance, pricing_version).
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Price:
      id: UUID; organization_id: UUID
      provider: str; model: str; dimension: str
      usd_per_unit: Decimal; unit_size: Decimal  # tokens or evidenced non-token units
      effective_from: date
      source: Literal["provider_list","import","override"]
      source_ref: str                # list date, import id, or principal id
      supersedes: UUID | None

  @dataclass(frozen=True, slots=True)
  class CostRow:
      execution_id: str; pricing_version: int
      usd_low: Decimal; usd_high: Decimal | None  # None when no evidenced upper bound exists
      provenance: Provenance; unknown_dimensions: tuple[str, ...]
  ```
- **Alternatives considered:** Hardcode a price map in code (benefit: zero
  UI; cost: no effective dates or overrides, and a release per price change).
  Single cost number with a footnote (benefit: simpler UI; cost: "unknown
  consumption stays unknown").
- **Freeze:** none.
- **Decision (range not point):** Unknown consumption stays unknown. A finite
  range requires a recorded bound/estimator; otherwise show the known subtotal
  plus unknown/unbounded dimensions, not a fabricated upper bound. Cost is not a
  provider invoice unless reconciled from such evidence.
- **Risks:** Overrides used to hide real cost; bounded by audit and the
  source shown on every figure. Rollback retains existing cost evidence; any repricing appends a correction with
  its source/version and cannot rewrite historical totals silently.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 3
- **Owner:** unassigned

## WU-92 — Enforce scoped budgets with explicit uncertainty

- **Status:** ⬜ defined
- **Context:** The mockup shows a `budget.cost_unknown` violation and the
  review found budgets at organization, project and key level with block or
  alert modes, soft thresholds and temporary increases in every mature
  gateway. The platform has no budget object and admission does not check
  cost.
- **Goal:** Organization, project, application/environment and key budgets apply
  together to all gateway-metered traffic, including BYOK. Admission reserves a
  qualified upper cost bound; strict block mode rejects if no such bound exists.
  Settlement records known cost and preserves unresolved reservations explicitly.
- **Scope:** Budget API/storage, reservation and reconciliation integration,
  scoped Budget page and client; about 20 files. Team/principal allocation is WU-92a.
- **Non-goals:** Team/principal allocation (WU-92a), alert delivery (WU-96),
  chargeback invoices and billing outside this gateway. Do not claim a hard spend
  ceiling for unbounded or externally billed workloads.
- **Acceptance:**
  - Every applicable organization/project/application-environment/key block cap
    participates; a new key cannot evade a parent cap —
    `platform/services/gateway/tests/test_budgets.py::test_scope_intersection`
  - Strict admission without a qualified upper bound rejects with
    `budget.cost_unknown`; alert-only explicitly records admitted uncertainty —
    `platform/services/gateway/tests/test_budgets.py::test_unknown_admission`
  - Concurrent reservations, duplicate settlement and late reconciliation obey
    the documented bound; unknown final usage retains pending reservation —
    `platform/services/gateway/tests/test_budgets.py::test_reservation_bound`
  - BYOK usage is included; measured spend, estimated reservation and unknown
    exposure are separate, non-additive figures —
    `platform/services/gateway/tests/test_budgets.py::test_byok_and_provenance`
  - Temporary increases expire and audit; thresholds fire once per scope/window —
    `platform/services/gateway/tests/test_budgets.py::test_threshold_and_increase`
  - The console exposes scope, pending uncertainty and permitted budget edits —
    `platform/tests/integration/budgets.test.ts`
- **Done:** Concurrent recorded traffic respects all scoped caps, unknown admission
  follows the declared mode, and unresolved usage remains visibly reserved until
  evidence or an audited adjustment resolves it.
- **Deps:** WU-89, WU-91.
- **Architecture:** §12 (evidence/accounting subsection) extended.
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/budgets/{models,reserve,events,api}.py`, migration
    for `budgets` (revision allocated at implementation), admission hook, console page.
  - Flow: admission → effective budgets (key ∩ application/environment ∩ project ∩ organization)
    → estimate from request size and price → reserve → execute → settle
    with ledger cost → threshold events.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Budget:
      id: UUID; organization_id: UUID; version: int
      scope: Literal["organization","project","application_environment","key"]; scope_id: UUID
      usd_limit: Decimal; window: Literal["daily","weekly","monthly"]
      mode: Literal["block","alert_only"]
      unknown_admission: Literal["reject","allow_with_alert"]  # block requires reject
      soft_threshold_pct: int        # default 85
      temporary_limit: Decimal | None; temporary_until: datetime | None

  class BudgetEvent(StrEnum):
      THRESHOLD_CROSSED = "budget.threshold_crossed"
      BLOCKED = "budget.blocked"
      OVERAGE_ALLOWED = "budget.overage_allowed"
      COST_UNKNOWN = "budget.cost_unknown"
  ```
- **Alternatives considered:** Count unknown cost at list price (benefit:
  conservative; cost: fabricates a number the ledger does not have). Budgets
  only at key level (benefit: one scope; cost: platform teams budget per
  application).
- **Freeze:** none.
- **Decision (unknown is not zero):** Rule 5 requires honest accounting, not
  unlimited admission. Unknown final cost is not fabricated as spend; the reserved
  upper bound remains pending. Strict unbounded requests reject; alert-only
  uncertainty is explicit. Budget enforcement is separate from OpenFGA.
- **Risks:** Unbounded outputs, missing prices and lost usage can invalidate cap
  claims. Require evidenced bounds for block admission and preserve pending
  exposure through crashes. Rollback blocks new traffic for affected budgets
  instead of discarding reservations or reverting to unlimited spend.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 3
- **Owner:** unassigned

## WU-92a — Allocate team and principal budgets from trusted attribution

- **Status:** ⬜ defined
- **Context:** The competitive review and gateway workflow need team and principal
  allocations beyond WU-92's resource caps, without confusing attribution and authority.
- **Goal:** Team and authenticated-principal budgets constrain the same execution as
  its project/application/key caps using immutable server-resolved allocation.
- **Scope:** Budget subject extension, application allocation binding, ledger/admission
  integration and Budget tabs; about 12 files.
- **Non-goals:** Caller-reported end-user budgets, invoices, overlapping multi-team chargeback
  and external billing; later FinOps/identity profiles.
- **Acceptance:**
  - Each execution has one authorized allocation team and one authenticated principal; multiple memberships never double-charge or let the caller choose a cheaper team —
    `platform/services/gateway/tests/test_budget_allocation.py::test_trusted_allocation`
  - Team/principal caps intersect existing caps and cover service-account calls plus human replay without trusting end-user tags —
    `platform/services/gateway/tests/test_budget_allocation.py::test_all_caps`
  - Ownership/allocation changes are audited and prospective; earlier usage remains on its original allocation —
    `platform/services/gateway/tests/test_budget_allocation.py::test_historical_attribution`
  - Usage views explain overlapping scope totals and show only authorized team/principal aggregates —
    `platform/tests/integration/budget_allocation.test.ts`
- **Done:** A recorded multi-team workload reconciles exactly once per execution in
  each applicable budget and cannot bypass caps through forged attribution.
- **Deps:** WU-92, WU-90, WU-82e, WU-82i.
- **Architecture:** §12, evidence/accounting subsection; scope contracts from WU-82a.
- **Integration:**
  - Layer: platform service and console;
    no public-library dependency or contract changes.
  - Modules: `app/budgets/allocation.py`, application bindings, ledger dimensions, Budget UI.
  - Flow: admitted context → immutable allocation → all scope reservations → settlement.
  - Diagram:
    ```mermaid
    flowchart LR
      Input[Authorized input] --> Service[Platform workflow]
      Service --> State[Versioned state and audit]
      State --> Evidence[Projection and qualification evidence]
    ```
- **Design sketch:**
  ```text
  Allocation(application_id, environment_id, team_id, version)
  BudgetSubject = existing scopes | team | authenticated_principal
  execution attribution is pinned at admission; scope totals overlap, not sum
  reported end_user is never the authenticated_principal budget subject
  ```
- **Alternatives considered:** Charging every team membership duplicates spend. Client-supplied cost-center
  tags are useful analytics but cannot select the enforcement account.
- **Freeze:** none; platform-only provisional contracts. No kernel schema,
  conversion edge, fixture census or published package change.
- **Decision (scope):** Team allocation is server-configured and versioned; authenticated-principal
  budgets include workload principals and human operations. Personal API keys
  and authenticated end-user delegation remain deferred.
- **Risks:** Reassignment could move liabilities or leak names; preserve historical
  attribution, authorize allocation changes and scope aggregates. Rollback retains
  caps/pending reservations and refuses new unsupported allocations.
- **Dependency impact:** Gateway consumers depend on this outcome explicitly;
  no completed identity WU is reopened or relabelled as incomplete.
- **Open:** none for definition; implementation follows the accepted WU-82a
  contract and does not introduce additional policy languages or identity profiles.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 3
- **Owner:** unassigned

## WU-93 — Inspect requests and receipts with shared saved filters

- **Status:** ⬜ defined
- **Context:** Operators need scoped request inspection, safe evidence links and
  reusable filters. Receipts exist after WU-87; no list or export workflow yet
  enforces the expanded project/compartment access contract.
- **Goal:** An operator lists executions with filters (time, application,
  principal, status, provenance, fidelity outcome, attempts, route), saves a
  filter under a name with "only me" or explicit project visibility, opens a
  receipt by execution id in a side sheet or full page, and exports the
  filtered list as CSV. Compatibility clients resolve `ocai-execution-id`
  to the same receipt when authorized.
- **Scope:** `app/receipts/` query and filter persistence, receipt read API,
  CSV export, console Requests page and Receipt detail, column picker, saved
  filter chips, client, tests. About 22 files.
- **Non-goals:** Payload evidence (WU-94). Replay (WU-100). Feedback scores
  (evaluation stage). Session grouping (WU-97).
- **Acceptance:**
  - Each filter dimension narrows the list and the count; pagination is
    stable under new writes —
    `platform/services/gateway/tests/test_receipts_api.py::test_filters`
  - A saved filter with project visibility is visible to an authorized project metadata viewer, one
    with only-me is not; both are audited —
    `platform/services/gateway/tests/test_receipts_api.py::test_saved_filter_visibility`
  - A receipt resolves by execution id only within its authorized project/environment and compartments; a
    guessed id of another organization returns the shared 404 —
    `platform/services/gateway/tests/test_receipts_api.py::test_receipt_authorization`
  - CSV export carries provenance columns and the unknown marker, never
    blank or zero for unknown —
    `platform/services/gateway/tests/test_receipts_api.py::test_csv_provenance`
  - The console opens a row in the sheet, saves a filter, and reaches the
    full receipt with attempts, decisions and findings in two columns —
    `platform/tests/integration/requests.test.ts`
  - Counts, pagination, direct links and CSV authorize before selection/aggregation; sharing a filter does not share its underlying records —
    `platform/services/gateway/tests/test_receipts_api.py::test_query_export_isolation`
  - Metadata read and export use separate permissions; evidence redacts sensitive attribute values and inaccessible resource identities —
    `platform/services/gateway/tests/test_receipts_api.py::test_safe_decision_evidence`
- **Done:** The Requests page lists the recorded day, a saved project
  filter "Fallbacks" shows the fallback executions to a viewer, and the
  receipt page for the demonstration execution renders both attempts with
  loss and shift findings in separate columns.
- **Deps:** WU-90, WU-91, WU-82h. Cost joins cannot precede their pricing schema.
- **Architecture:** §12 (evidence/accounting subsection) extended (inspection surface).
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/receipts/{query,filters,export,api}.py`, migration
    for `saved_filters` (revision allocated at implementation), console `pages/requests.vue`,
    `pages/requests/[id].vue`, receipt components.
  - Flow: filter params → authorized scoped query → page; receipt id →
    authorized read → receipt + ledger + cost rows joined.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class SavedFilter:
      id: UUID; scope: ResourceScope; owner_id: UUID
      name: str; visibility: Literal["me","project"]
      params: Mapping[str, str]      # the validated filter query

  # GET …/executions?from&to&application&principal&status&provenance&fidelity&attempts_min&route&cursor
  # GET …/executions/{execution_id}            → Receipt + usage + cost
  # GET …/executions.csv?<same filters>
  ```
- **Alternatives considered:** Store filters in browser storage (benefit:
  no API; cost: not shared, lost per device). Expose receipts by id without
  organization scoping (benefit: simpler links; cost: evidence design says a
  hard-to-guess id is not access control).
- **Freeze:** none.
- **Decision (two columns):** loss and shift render separately (WU-86
  decision, architecture §2.5).
- **Risks:** Large exports; bounded by a row cap with a "narrow the filter"
  message. Rollback: revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P0
- **Tier:** 3
- **Owner:** unassigned

## WU-94 — Govern scoped payload capture and conditional content access

- **Status:** ⬜ defined
- **Context:** Receipts carry metadata, while captured payloads need separate
  content grants, retention and processing policy. The enterprise review requires
  administrators and metadata viewers to remain distinct from content readers.
- **Goal:** An authorized administrator configures capture for an application/
  environment within mandatory organization/compartment restrictions. Capture is
  off by default and narrower scopes/keys may disable it. Encrypted payloads are
  readable only under separate content grants and trusted attribute conditions;
  each successful read is audited before plaintext release.
- **Scope:** `app/capture/` (policy, store, read audit, retention sweep),
  migration, key override field, data-plane hook, console Settings capture
  section and receipt Payload evidence card with locked state, client,
  tests. About 18 files.
- **Non-goals:** Redaction rules (WU-111/112). External
  object storage (sealed PostgreSQL bytea first; an adapter later). Export
  of payloads (needs its own authorization design).
- **Acceptance:**
  - With the default policy, an execution stores no payload and the receipt
    says "not captured: organization policy" —
    `platform/services/gateway/tests/test_capture.py::test_default_off`
  - With capture on for an application and a key override off, that key's
    executions store nothing and say "not captured: key override" —
    `platform/services/gateway/tests/test_capture.py::test_key_override`
  - A read of a captured payload by an allowed principal returns it and
    writes an audit row; a metadata-only viewer of that receipt receives 403 and no audit success row —
    `platform/services/gateway/tests/test_capture.py::test_read_is_audited`
  - The retention sweep deletes payloads past their days and leaves the
    receipt, ledger and audit rows intact —
    `platform/services/gateway/tests/test_capture.py::test_retention_keeps_evidence`
  - Payloads are sealed with the WU-83 sealer and never appear in logs or
    exports —
    `platform/services/gateway/tests/test_capture.py::test_sealed_at_rest`
  - The console shows the policy, the locked card, and the audited unlock —
    `platform/tests/integration/capture.test.ts`
  - Organization owner and project administrator without a content grant cannot read payloads; a valid scoped approval allows and its expiry revokes —
    `platform/services/gateway/tests/test_capture.py::test_conditional_content_access`
  - Scope/policy changes and audit failure between authorization and release prevent plaintext release; inaccessible IDs retain the shared 404 —
    `platform/services/gateway/tests/test_capture.py::test_release_revalidation`
  - Retention jobs and capture-off obligations preserve compartment isolation; mandatory retention restrictions cannot be loosened by a project or key —
    `platform/services/gateway/tests/test_capture.py::test_mandatory_capture_policy`
- **Done:** Captured content is absent by default, conditionally readable only
  through current scoped content grants with committed audit, and deleted by
  authorized retention processing without erasing non-content evidence.
- **Deps:** WU-93, WU-83 (sealer), WU-82g, WU-82h.
- **Architecture:** §12 (evidence/accounting subsection) extended (privacy and access).
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/capture/{policy,store,read,sweep,api}.py`, migration
    for `capture` (revision allocated at implementation), data-plane post-execution hook, console sections.
  - Flow: execution → policy resolve (organization ∩ project/environment ∩ compartment ∩ application ∩ key) →
    seal and store or record reason → receipt link; read → authorize →
    audit → unseal.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class CapturePolicy:
      id: UUID; scope: ResourceScope; version: int
      application_ids: frozenset[UUID]; enabled: bool
      retention_days: int
      # Content-reader grants live in the authorization model, not this policy.

  @dataclass(frozen=True, slots=True)
  class PayloadRef:
      execution_id: str; scope: ResourceScope
      compartment_ids: frozenset[UUID]; sealed_ref: SecretRef
      capture_policy_version: int; expires_at: datetime
  # Read: receipts.read AND payloads.read AND current mandatory conditions.
  # Commit read audit before plaintext release; do not treat role as content access.
  ```
- **Alternatives considered:** Capture on by default with opt-out (benefit:
  debugging from day one; cost: contradicts the security design). Store
  payloads inside the receipt row (benefit: one read; cost: access to a
  summary would grant access to content, which the evidence design
  separates).
- **Freeze:** none.
- **Decision (default off, separated):** settled by the security and
  evidence designs; read access is audited per read.
- **Risks:** Deletion cannot imply enterprise legal-hold support. Reject unsupported
  hold settings and document the qualified retention contract; WU-127 extends
  evidence lifecycle controls. Rollback disables new capture without bypassing
  existing access restrictions or the committed deletion schedule.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 3
- **Owner:** unassigned

## WU-95 — Break down usage by dimension with export

- **Status:** ⬜ defined
- **Context:** The Overview's "Breakdown" link has no target. Every mature
  console groups spend by model, key, team, tag and provider over a time
  range with CSV export; ours has totals only (WU-90).
- **Goal:** A usage page groups the ledger and cost rows by project, environment,
  team, application, deployment, key, principal, tag or provider over a time range with
  presets, renders a stacked time series and a table with provenance per
  cell and an unknown row, and exports the table as CSV.
- **Scope:** `app/ledger/breakdown.py` and API, console Usage page (chart,
  group-by, range, export; mobile table only), client, tests. About 10
  files.
- **Non-goals:** Custom dashboards and widgets (not for MVP). Tags as a
  dimension land with WU-97; the group-by lists them once that WU is in.
- **Acceptance:**
  - Each group-by returns rows whose known sums equal the totals endpoint
    and whose unknown counts match —
    `platform/services/gateway/tests/test_breakdown.py::test_groups_reconcile_with_totals`
  - Time buckets respect the range and the organization's reporting
    timezone setting; empty buckets are present —
    `platform/services/gateway/tests/test_breakdown.py::test_buckets`
  - CSV columns carry provenance and the unknown marker —
    `platform/services/gateway/tests/test_breakdown.py::test_csv`
  - The console renders the chart and table and switches group-by —
    `platform/tests/integration/usage.test.ts`
  - Project/environment/team/principal breakdown uses immutable server attribution and filters authorized records before grouping; hidden groups/counts never appear —
    `platform/services/gateway/tests/test_breakdown.py::test_scope_before_aggregation`
  - Historical team allocation survives current membership changes; scope totals are labelled overlapping and are not summed across dimensions —
    `platform/services/gateway/tests/test_breakdown.py::test_attribution_semantics`
- **Done:** The usage page for the recorded day grouped by application
  shows sums equal to the Overview totals, an unknown row with 212
  executions, and downloads a CSV with provenance columns.
- **Deps:** WU-91, WU-92a (trusted team/principal allocation).
- **Architecture:** §12 (evidence/accounting subsection) extended.
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/ledger/breakdown.py`, console `pages/usage.vue`.
  - Flow: params → scoped aggregate query over ledger and cost rows → series
    and table.
- **Design sketch:**
  ```python
  # GET …/usage/breakdown?group_by=project|environment|team|application|deployment|key|principal|tag|provider
  #     &from&to&bucket=hour|day
  # → {buckets: [...], rows: [{key, label, input_tokens: {value, provenance}, ...,
  #     cost: {low, high, provenance}}], unknown: {executions: n}}
  ```
- **Alternatives considered:** Ship Langfuse-style widgets (benefit:
  flexibility; cost: weeks of UI before the basic breakdown exists).
- **Freeze:** none.
- **Decision (one page, no builder):** a group-by selector over a fixed
  table is the release 1 scope; see Alternatives.
- **Risks:** Slow aggregates on large ledgers; bounded by a daily rollup
  table added when the WU-103 load test shows the need. Rollback: revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 3
- **Owner:** unassigned

## WU-96 — Deliver alert rules to webhook and chat destinations

- **Status:** ⬜ defined
- **Context:** Gateway budget, health, reconciliation and access events need a
  scoped operator notification path. Deliver only safe metadata to approved
  destinations; chat format support does not authorize content export.
- **Goal:** An owner defines alert rules: an event from a fixed catalogue,
  a scope, a destination (generic webhook, Slack-compatible webhook,
  Microsoft Teams webhook, email through a configured SMTP relay), and a
  digest (immediate, hourly, daily). Delivery runs through the outbox with
  retries, a test delivery shows the destination's status and allowlisted diagnostic code, and
  management events (key created, key revoked, policy published) are
  subscribable.
- **Scope:** `app/alerts/` (rules, catalogue, destinations, outbox delivery,
  digest), migration, console Alert rules page, client, tests with a local
  receiver. About 18 files.
- **Non-goals:** Paging integrations (PagerDuty, Opsgenie) beyond generic
  webhook. Alert correlation or silencing (later). Email templates beyond
  plain text.
- **Acceptance:**
  - A rule on `budget.threshold_crossed` delivers one webhook call per
    window with the event payload; the local receiver records it —
    `platform/services/gateway/tests/test_alerts.py::test_budget_rule_delivers`
  - A deployment probe failing for the configured minutes fires
    `deployment.unavailable` once and `deployment.recovered` once —
    `platform/services/gateway/tests/test_alerts.py::test_health_edge_triggered`
  - Hourly digest batches events into one delivery with counts —
    `platform/services/gateway/tests/test_alerts.py::test_digest`
  - A failed delivery retries with backoff and is visible as undelivered
    after the bound; secrets in destination URLs are stored sealed and
    masked —
    `platform/services/gateway/tests/test_alerts.py::test_retry_and_masking`
  - Test delivery returns the receiver's status and allowlisted diagnostic code, never raw body —
    `platform/services/gateway/tests/test_alerts.py::test_test_delivery_safe_diagnostics`
  - The console creates a rule and runs a test delivery —
    `platform/tests/integration/alerts.test.ts`
  - A queued alert rechecks current destination approval and scope before delivery; no payload, secret, hidden-resource identity or raw ABAC attribute is exported —
    `platform/services/gateway/tests/test_alerts.py::test_delivery_scope`
  - An acknowledgement-loss retry uses the same idempotency key and reports at-least-once delivery honestly —
    `platform/services/gateway/tests/test_alerts.py::test_duplicate_delivery`
- **Done:** On the recorded day, the budget threshold, the deployment
  outage, the reconciliation lag and a key creation each reach the local
  webhook receiver with one logical event per rule/digest window and a stable delivery id;
  retries may deliver duplicates.
- **Deps:** WU-92a, WU-87 (probe recorder), WU-82g.
- **Architecture:** §12 (evidence/accounting subsection) extended (monitoring).
- **Integration:**
  - Layer: platform service and console; egress to destinations is
    allowlisted per rule like WU-83.
  - Modules: `app/alerts/{catalogue,rules,deliver,digest,api}.py`,
    migration for `alerts` (revision allocated at implementation), console `pages/settings/alerts.vue`.
  - Flow: event source (budgets, probes, ledger, audit) → event row →
    matching rules → outbox → bounded HTTP delivery → delivery record.
- **Design sketch:**
  ```python
  ALERT_EVENTS: Final = (
      "budget.threshold_crossed", "budget.blocked", "budget.cost_unknown",
      "deployment.unavailable", "deployment.recovered", "region.probe_failing",
      "stream.partial_rate_above", "fidelity.denied_rate_above",
      "ledger.reconciliation_behind",
      "key.created", "key.revoked", "policy.published",
  )

  @dataclass(frozen=True, slots=True)
  class AlertRule:
      id: UUID; resource_scope: ResourceScope; version: int
      event: str; scope: Literal["project","environment","application","deployment"]; scope_id: UUID | None
      threshold: int | None          # for *_rate_above
      destination: Destination       # kind + sealed url/secret + masked display
      digest: Literal["immediate","hourly","daily"]; enabled: bool
  ```
- **Alternatives considered:** Emit everything to the OTel satellite and let
  the customer alert (benefit: no delivery code; cost: the gateway's own
  governance events need an operator path even without an observability
  product; WU-63 remains the export path). Email only (benefit: simplest;
  cost: chat webhooks are what operators asked every vendor for).
- **Freeze:** none.
- **Decision (outbox delivery):** reuse the WU-75 outbox pattern; at-least
  once with consumer-side idempotency key, as the evidence design states.
- **Risks:** Alert storms; bounded by digest mode and the once-per-window
  rule on thresholds. Rollback: revert; rules disabled by default on
  migration.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 3
- **Owner:** unassigned

## WU-97 — Group executions by client session and tags

- **Status:** ⬜ defined
- **Context:** Receipts are per execution. Helicone and Langfuse group
  requests by a client session id and show custom properties as columns;
  LiteLLM attributes spend by tag and end user. Our evidence design names
  session as an identity and the FinOps module needs a chargeback dimension
  beyond application. The data plane ignores client correlation today.
- **Goal:** The data plane accepts bounded `ocai-session-id` and
  `ocai-tags` headers, stores them as execution dimensions without granting
  any authority, the receipt lists related executions of the same session,
  the Requests filters and usage breakdown accept tags, and the OpenAI
  `user` field is stored as `end_user` when present.
- **Scope:** data-plane header parsing with bounds, receipt and ledger
  dimension columns, related-executions query, filter and breakdown
  extensions, console receipt section and tag chips, tests. About 12 files.
- **Non-goals:** Session replay as a conversation view (evaluation stage).
  Hierarchical session paths (later if asked). Per-end-user budgets.
- **Acceptance:**
  - Headers above the bounds (64 chars, 10 tags of 32 chars) are rejected
    with a 400 naming the bound; valid ones are stored —
    `platform/services/gateway/tests/test_sessions.py::test_header_bounds`
  - A session id never changes authorization, application, or policy —
    `platform/services/gateway/tests/test_sessions.py::test_correlation_is_not_authority`
  - Related executions list only the same authorized organization, project, environment, compartments and application —
    `platform/services/gateway/tests/test_sessions.py::test_related_scoped`
  - Each tag breakdown reconciles to its filtered source; multi-tag rows overlap
    and untagged executions form their own row —
    `platform/services/gateway/tests/test_sessions.py::test_tag_breakdown`
  - The receipt shows related executions and tags —
    `platform/tests/integration/sessions.test.ts`
  - A correlation tag named team, classification or end_user changes neither ABAC context nor team/principal budget allocation —
    `platform/services/gateway/tests/test_sessions.py::test_tags_never_authorize_or_allocate`
  - Multi-tag reports label overlapping counts; they do not claim that summed tag rows equal the non-duplicated total —
    `platform/services/gateway/tests/test_sessions.py::test_multi_tag_non_additive`
- **Done:** Two recorded executions sharing a session id appear in each
  other's receipt, a tag filter narrows the Requests list, and the usage
  breakdown identifies overlapping tag groups and preserves the distinct execution total.
- **Deps:** WU-93, WU-95.
- **Architecture:** §12 (execution subsection) and §12 (evidence/accounting subsection) extended.
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/dataplane/correlation.py`, migration for `dimensions` (revision allocated at implementation),
    receipt and ledger column additions, query extensions.
  - Flow: request headers → validate → execution dimensions → receipt and
    ledger rows → filters, related query, breakdown.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class ClientCorrelation:
      session_id: str | None         # ≤ 64 chars, [A-Za-z0-9._-]
      tags: frozenset[str]           # ≤ 10, each ≤ 32 chars, same charset
      end_user: str | None           # unverified caller attribution, ≤ 128 chars
      end_user_source: Literal["client"] = "client"
  # GET …/executions/{id}/related → executions with the same session_id and authorized application/environment/compartment scope
  ```
- **Alternatives considered:** Derive sessions from conversation content
  hashes (benefit: no client change; cost: guesswork and content access).
  Free-form metadata JSON (benefit: flexibility; cost: unbounded cardinality
  in the ledger).
- **Freeze:** none.
- **Decision (correlation is not authorization):** settled by the evidence
  design ("caller-supplied correlation is not authorization").
- **Risks:** Tag cardinality explosion; bounded by the count and length
  limits and a per-organization distinct-tag cap surfaced on the usage page.
  Rollback: revert; columns nullable.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 3
- **Owner:** unassigned

## WU-98 — Publish the routes catalogue for application developers

- **Status:** ⬜ defined
- **Context:** Application developers need to know what they can call:
  LiteLLM ships a model hub for this. Our deployments page is an operator
  surface with secrets adjacent; developers and viewers need a read-only
  catalogue of routes with their interface, capabilities declared versus
  qualified, price and readiness.
- **Goal:** A routes page lists authorized application/environment routes with their
  interfaces, declared and qualified capabilities, unit-labelled pricing and
  effective date, readiness, and a Connect action. Provider/model/processing
  details appear only when separately readable. Discovery grants expose no
  connection or secret data and do not imply invocation permission.
- **Scope:** `app/routes/` read model and API, console Routes page with
  filters, client, tests. About 8 files.
- **Non-goals:** Snippet generation (WU-99 fills the Connect action).
  Public, unauthenticated catalogue (never: it discloses deployments).
- **Acceptance:**
  - The catalogue returns only deployments the caller's scoped grants and mandatory conditions permit reading and
    omits connection ids and secret suffixes —
    `platform/services/gateway/tests/test_routes.py::test_catalogue_projection`
  - Qualified capabilities show empty with "not qualified" until WU-103
    writes them; declared ones are labelled "declared, not
    tested" —
    `platform/services/gateway/tests/test_routes.py::test_capability_labels`
  - Price and effective date come from the pricing table; a route without a
    price shows unknown —
    `platform/services/gateway/tests/test_routes.py::test_price_join`
  - A viewer sees the page; a foreign organization sees nothing —
    `platform/tests/integration/routes.test.ts`
  - Route discovery and invocation are distinct permissions; a visible route does not imply the selected credential may invoke it —
    `platform/services/gateway/tests/test_routes.py::test_discovery_is_not_invocation`
  - Catalogue filtering uses trusted project/environment and processing policies without leaking excluded hidden destinations —
    `platform/services/gateway/tests/test_routes.py::test_scoped_catalogue`
- **Done:** A viewer opens Routes and sees only authorized application/environment routes as a
  route with interface, capabilities labelled declared or qualified, price
  with its date, and readiness, with no connection detail present.
- **Deps:** WU-84, WU-85, WU-86, WU-91.
- **Architecture:** §12 (resource administration subsection) extended (read model).
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/routes/{projection,api}.py`, console `pages/routes.vue`.
  - Flow: authorized deployments → join pricing and qualification → route
    projection.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Route:
      name: str; interface: str; interface_tag: str; model: str; region: str
      declared: frozenset[str]; qualified: frozenset[str]
      price: PriceSummary | None     # usd_per_million per dimension + effective_from
      readiness: Literal["not_qualified","qualified"]; paused: bool
  ```
- **Alternatives considered:** Reuse the deployments page with role-based
  hiding (benefit: one page; cost: operator and developer concerns mixed,
  and secrets one toggle away).
- **Freeze:** none.
- **Decision (projection, no secrets):** a separate read model that never
  joins connections, so the viewer grant cannot widen by accident.
- **Risks:** Drift between catalogue and deployments; bounded by projecting
  on read, no copy. Rollback: revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 3
- **Owner:** unassigned

## WU-99 — Generate connect snippets for a route and key

- **Status:** ⬜ defined
- **Context:** Developers need a connect workflow that names the application,
  environment, supported contract and credential restrictions and produces runnable
  instructions without exposing secrets or inventing unsupported endpoints.
- **Goal:** The Connect panel renders curl, Python stdlib HTTP and TypeScript
  fetch examples for the qualified OpenAI Chat Completions endpoint using the
  application route and a key placeholder, with scope and eligibility explained.
- **Scope:** Read-only snippet renderer/API, reusable Connect panel, client and
  runnable recorded-data-plane tests; about 8 files. Invocation keys are created
  through the existing WU-82i workflow, not implicitly by deployment creation.
- **Non-goals:** Provider SDK dependencies in this repository, Anthropic-native
  inbound endpoint snippets before that endpoint is qualified, new key issuance
  workflows beyond WU-82i, or an independently distributed platform SDK.
- **Acceptance:**
  - Snippets are generated from the route, the base URL setting and the
    application contract; the key is always `<key>` —
    `platform/services/gateway/tests/test_snippets.py::test_placeholder_only`
  - Each snippet, executed against the recorded data plane with a test key,
    produces a successful execution —
    `platform/services/gateway/tests/test_snippets.py::test_snippets_run`
  - The application Connect panel shows the supported contract and scoped
    credential instructions after key issuance —
    `platform/tests/integration/connect.test.ts`
  - Selecting a credential from another application/environment is rejected; visible route metadata never widens invocation authority —
    `platform/services/gateway/tests/test_snippets.py::test_invocation_scope`
- **Done:** For an authorized application/environment, the Connect panel shows
  three copyable examples; each runs with a scoped test key against recorded
  traffic and returns an execution ID without embedding a stored secret.
- **Deps:** WU-98, WU-82i, WU-87.
- **Architecture:** none (console and read-only API).
- **Integration:**
  - Layer: platform service (template rendering) and console.
  - Modules: `app/routes/snippets.py`, console `ConnectPanel.vue`.
  - Flow: route + contract + base URL → templates → strings.
- **Design sketch:**
  ```python
  def render_snippets(route: Route, contract: str, base_url: str) -> Mapping[str, str]:
      """Keys: 'curl', 'python_http', 'typescript_fetch'."""
  ```
- **Alternatives considered:** Templates in the console only (benefit: no
  API; cost: the snippets could not be tested against the data plane).
- **Freeze:** none.
- **Decision (placeholder):** the key value is never embedded, even right
  after issuance (ADR 0011 show-once).
- **Risks:** Snippets drift from the client contract; bounded by the
  run-them test. Rollback: revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 3
- **Owner:** unassigned

## WU-100 — Replay a captured request through the current policy

- **Status:** ⬜ defined
- **Context:** Portkey and Logfire open any log in a playground to rerun
  it. Our policy dry run explains rules without executing, and our capture
  policy decides whether a request body exists. A governed replay turns a
  receipt into a test case while respecting both.
- **Goal:** From a receipt whose request payload is captured and readable
  by the principal, "Replay through current policy" runs the request again
  as a new execution attributed to the replaying principal, linked to the
  origin, with a side-by-side of route, findings, usage and cost. The
  action is disabled with the reason when the payload is not captured or
  the principal may not read it.
- **Scope:** `app/dataplane/replay.py` and API, receipt `replays` link,
  console action and comparison view, tests. About 10 files.
- **Non-goals:** Editing the request before replay (playground; later).
  Replaying tool effects (evidence design: needs explicit authorization and
  separate controls). Shadow traffic (WU-129).
- **Acceptance:**
  - Replay requires a captured request and read permission; otherwise the shared 404 for inaccessible IDs, or 403 for a known
    readable receipt without the required action grant —
    `platform/services/gateway/tests/test_replay.py::test_gated_by_capture_and_permission`
  - The replay is a new execution with `origin_execution_id`, charged to the
    explicit target application/environment budgets and authenticated-principal allocation, admitted like any request —
    `platform/services/gateway/tests/test_replay.py::test_replay_is_new_execution`
  - The comparison lists differing route, findings and usage with
    provenance for both sides —
    `platform/services/gateway/tests/test_replay.py::test_comparison`
  - The console disables the button with a tooltip when not captured —
    `platform/tests/integration/replay.test.ts`
  - Replay separately requires payload read, requests.replay and target invocation permission; the operator never impersonates the original key owner —
    `platform/services/gateway/tests/test_replay.py::test_no_impersonation`
  - Current compartment, destination and approval policies apply; revocation after selection prevents new provider I/O and queued replay reauthorizes —
    `platform/services/gateway/tests/test_replay.py::test_current_abac`
- **Done:** Replaying the demonstration execution under v8 produces a new
  receipt linked to the original, and the comparison shows the route and
  findings differences against the recorded pair.
- **Deps:** WU-94, WU-93, WU-92a, WU-82i.
- **Architecture:** §12 (execution subsection) extended.
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/dataplane/replay.py`, receipt link column, console view.
  - Flow: authorize source read and target invocation (audited) → unseal request → data plane
    execute with `origin_execution_id` → comparison projection.
- **Design sketch:**
  ```python
  # POST …/executions/{id}/replay → {execution_id, origin_execution_id}
  # GET  …/executions/{id}/compare/{other} → {route, findings, usage, cost} per side
  ```
- **Alternatives considered:** Replay offline through inspection only
  (benefit: no spend; cost: that is the dry run, already in WU-86; the value
  here is the real effect).
- **Freeze:** none.
- **Decision (gated by capture):** settled by the evidence design; no
  generic replay button.
- **Risks:** Replay as a cost amplifier; bounded by admission and budgets
  applying unchanged. Rollback: revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 4
- **Owner:** unassigned

## WU-101 — Qualify effective access across gateway resources

- **Status:** ⬜ defined
- **Context:** Each resource WU already enforces the WU-82a scoped permission
  and ABAC contract. A final cross-resource matrix must catch omissions in lists,
  exports, replay, content release and background work before readiness can pass.
- **Goal:** The Access page explains effective permissions from direct/team
  bindings and mandatory conditions, and a real-service matrix proves consistent
  enforcement across every gateway management and invocation surface.
- **Scope:** Cross-resource authorization fixtures and matrix, safe effective-access
  API/projection, Access inspector and client; about 12 files. No new role or team
  model is introduced here.
- **Non-goals:** Initial roles, teams and attribute policy implementation
  (WU-82a–82h), arbitrary custom-role UI and SCIM (identity follow-up).
- **Acceptance:**
  - Every WU-83–100 endpoint has allow/deny/unavailable cases across role,
    team, project, environment, compartment, credential and ABAC context —
    `platform/services/gateway/tests/test_access_matrix.py::test_all_endpoints`
  - Metadata readers and configuration administrators cannot read content
    without a separate current content grant —
    `platform/services/gateway/tests/test_access_matrix.py::test_content_separation`
  - Team removal, approval expiry and attribute-policy revision changes
    constrain lists, exports, queued jobs, mutations and replay at the
    documented enforcement boundaries —
    `platform/services/gateway/tests/test_access_matrix.py::test_revocation_boundaries`
  - Effective-access explanations identify permitted grant/policy provenance
    without leaking hidden resources or raw attributes —
    `platform/services/gateway/tests/test_access_matrix.py::test_safe_explanations`
  - The console displays effective scope and conditional access without
    offering a role-only bypass — `platform/tests/integration/access.test.ts`
- **Done:** Every gateway endpoint is accounted for in the qualified access
  matrix, and effective-access explanations agree with actual enforcement under
  cross-scope, expiry, revocation and dependency-failure tests.
- **Deps:** WU-82h, WU-92a, WU-94, WU-95, WU-96, WU-97, WU-98,
  WU-99, WU-100. Their transitive dependencies cover WU-83–100.
- **Architecture:** §12.5 extended (authorization model).
- **Integration:**
  - Layer: platform API and console; independent real-service qualification.
  - Modules: `app/access/explain.py`, matrix fixtures, Access inspector/client.
  - Flow: authorized subject/resource selection → composed decision explain →
    safe grant/policy references; matrix compares actual endpoint outcomes.
  - Diagram:
    ```mermaid
    flowchart LR
      Grants[Scoped grants] --> Decision[Composed decision]
      Attributes[Trusted attributes] --> Decision
      Decision --> Endpoint[Actual endpoint outcome]
      Decision --> Explain[Safe effective-access explanation]
      Endpoint --> Matrix[Cross-resource matrix]
      Explain --> Matrix
    ```
- **Design sketch:**
  ```text
  case = subject + team bindings + action + resource scope + credential + attributes
  expected = allow | deny | unavailable; outward HTTP follows shared disclosure rules
  surfaces = list / count / direct read / mutation / export / replay / queued work
  mandatory restrictions apply to every role, including organization owner
  content access requires a separate grant and current conditions
  ```
- **Alternatives considered:** Four role-only rows are easy to maintain but
  miss scope, attribute and credential interactions. Deferring access until this WU
  would leave earlier resource implementations under-specified.
- **Freeze:** none; authorization model revision only.
- **Decision (permission composition):** The original four organization-wide roles
  are replaced by WU-82a permission templates and scoped bindings. This WU proves
  their composition; it does not redefine them.
- **Risks:** A matrix may omit new endpoints; compare coverage to the management
  OpenAPI and data-plane route inventory. Rollback disables the inspector, not
  the established authorization enforcement.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 3
- **Owner:** unassigned

## WU-102 — Provide bounded audited emergency recovery access

- **Status:** ⬜ defined
- **Context:** The identity design requires "restricted, audited emergency
  access before production" and LiteLLM documents a break-glass admin for
  SSO outages. ADR 0011 forbids local login as an automatic SSO bypass;
  the platform has no emergency path when the issuer is down and no
  sign-in protection settings page.
- **Goal:** An explicitly authorized host operator obtains a one-use emergency
  sign-in that permits only scoped key revocation and deployment pause during an
  issuer outage. Both Nuxt and FastAPI validate the installation-bound emergency
  grant; ordinary OpenFGA, scope, attribute policy and audit remain required.
- **Scope:** Operator issuance, hashed emergency-grant storage/validation,
  one-use Nuxt redemption and non-refreshable session, backend credential profile,
  audit/alert integration and recovery UI; about 16 files.
- **Non-goals:** General owner access, payload reads/exports, inference, grants
  management, replacement login/SSO, or bypass of unavailable OpenFGA/database/audit.
  Passwords and sign-in protection remain IdP responsibilities.
- **Acceptance:**
  - With the issuer stopped, an authorized operator redeems a one-use
    installation-bound grant and can revoke a scoped key or pause a deployment —
    `platform/services/gateway/tests/test_break_glass.py::test_bounded_recovery`
  - Reuse, another installation, expired/revoked grant or a disallowed action
    fails; ordinary user bearer tokens cannot claim emergency status —
    `platform/services/gateway/tests/test_break_glass.py::test_no_emergency_escalation`
  - Lifetime is at most 60 minutes, redemption at most 5 minutes, no refresh;
    safe incident reference and marker appear in committed audit —
    `platform/services/gateway/tests/test_break_glass.py::test_audit_and_expiry`
  - OpenFGA/database/audit outage prevents action; notification is queued
    durably and later delivered under WU-96 semantics —
    `platform/services/gateway/tests/test_break_glass.py::test_dependency_failure`
  - Real browser redemption and a real protected backend mutation succeed
    while the issuer is stopped — `platform/tests/integration/emergency_access.test.ts`
- **Done:** During issuer outage a named operator performs one scoped recovery
  action through the browser and backend, with finite authority, durable audit and
  an alert, while content access and unrelated administration remain denied.
- **Deps:** WU-76, WU-96, WU-101, WU-82g.
- **Architecture:** §12.2 and §12.4 extended.
- **Integration:**
  - Layer: operator tooling, Nuxt session boundary and FastAPI authorization.
  - Modules: `app/identity/emergency.py`, hashed grant store, Nuxt one-use
    redemption handler/session adapter, recovery UI and audit/alert integration.
  - Flow: host authorization → persisted emergency grant → one-use browser
    redemption → server-held credential → backend validation → normal scoped
    decision → permitted recovery action and audit.
  - Diagram:
    ```mermaid
    sequenceDiagram
      participant O as Host operator
      participant N as Nuxt
      participant G as Gateway
      participant A as Authorization and audit
      O->>G: Explicit local issuance
      O->>N: Redeem one-use credential
      N->>G: Emergency credential, scoped recovery action
      G->>A: Validate current grant, scope and policy
      A-->>G: Decision and durable audit
    ```
- **Design sketch:**
  ```text
  emergency grant: installation, named principal, allowed resource IDs,
    actions={keys.revoke, deployments.pause}, expiry, incident_ref, status
  redemption: one-use hashed secret; remove URL credential before navigation
  session: opaque cookie, server-held emergency credential, no refresh
  backend: explicit emergency profile; no forged IdP token or cookie-only trust
  ```
- **Alternatives considered:** A standing local admin account (benefit:
  familiar; cost: a permanent SSO bypass, forbidden by the identity
  design). Disable the issuer check under a flag (benefit: trivial; cost: a
  silent development fallback ADR 0011 rejects).
- **Freeze:** none.
- **Decision (host command, bounded, audited):** WU-82a qualifies this explicit
  successor recovery profile to ADR 0011; it is never an automatic fallback on
  login failure. A redemption endpoint exists, but cannot issue emergency authority.
- **Risks:** A URL credential may leak and host access is powerful. Use
  one-use redemption, URL cleanup, no logging, finite scope and explicit host
  authorization. Rollback revokes outstanding grants and disables redemption.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P2
- **Tier:** 4
- **Owner:** unassigned

## WU-103 — Run the qualification suite and report inference readiness

- **Status:** ⬜ defined
- **Context:** Readiness is hardcoded false since WU-35, and the mockup
  invented five named checks. The delivery design lists seven qualification
  outcomes; the Overview needs a real suite whose results it renders, and
  the deployments need `qualified_capabilities` written from evidence rather
  than declarations.
- **Goal:** A scoped qualification runner assembles version-bound evidence for
  conversion, receipts, usage, streaming, admission, RBAC/ReBAC/ABAC isolation,
  model migration and recovery. Recorded installation-profile qualification and
  optional live smoke results remain distinct. Relevant changes invalidate prior
  qualification; public readiness exposes only safe aggregate status.
- **Scope:** `app/qualification/` (checks, runner, results), readiness
  endpoint change, console Overview readiness card and setup checklist, a
  Qualification page listing runs, tests. About 16 files.
- **Non-goals:** Live provider calls in CI, unmeasured numeric SLO claims,
  qualification of unsupported future surfaces (RAG, generic caches, payload
  exports), or marking a live endpoint qualified solely from recorded codec tests.
  Any opt-in live smoke run requires current invocation scope, budgets and explicit
  credentials and is labelled separately.
- **Acceptance:**
  - Each check maps to a delivery design outcome and produces pass, fail or
    not run with evidence links —
    `platform/services/gateway/tests/test_qualification.py::test_checks_map_to_outcomes`
  - Readiness remains false while any required check is failed or not run,
    and the response explains which —
    `platform/services/gateway/tests/test_qualification.py::test_readiness_gate`
  - The load check reports measured overhead separate from inference
    latency and never a target —
    `platform/services/gateway/tests/test_qualification.py::test_overhead_measured`
  - Passing conformance records only exercised capabilities with their
    artifact/configuration identity and recorded versus live evidence mode —
    `platform/services/gateway/tests/test_qualification.py::test_qualified_capabilities`
  - The Overview renders the suite and the setup checklist from facts —
    `platform/tests/integration/readiness.test.ts`
  - Real-service team/project/environment/compartment isolation and ABAC adversarial cases run, including owner-without-content-grant, fallback, exports, queued jobs and stream expiry —
    `platform/services/gateway/tests/test_qualification.py::test_access_and_abac_coverage`
  - Model migration failure, stale attributes, issuer/OpenFGA/audit outage and budget uncertainty cannot yield a passed required check —
    `platform/services/gateway/tests/test_qualification.py::test_fault_evidence`
  - Results pin support manifest, artifact, model, policy and configuration revisions; relevant changes invalidate readiness, and recorded evidence is never presented as a live provider test —
    `platform/services/gateway/tests/test_qualification.py::test_evidence_scope_and_invalidation`
  - Public readiness reveals only safe aggregate status; detailed checks and evidence require scoped authorization —
    `platform/services/gateway/tests/test_qualification.py::test_readiness_disclosure`
- **Done:** The recorded installation profile reports every required check and
  evidence reference, remains unqualified on any failed/not-run/stale check, and
  never labels a live provider endpoint tested solely from recorded evidence.
- **Deps:** WU-82b, WU-82h, WU-88, WU-90, WU-92a, WU-94, WU-96,
  WU-101, WU-102. Isolation has implemented prerequisites; not prose-only checks.
- **Architecture:** §12.1 readiness statement replaced; §12 (execution subsection) extended.
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/qualification/{checks/*.py,runner,results,api}.py`,
    migration for `qualification` (revision allocated at implementation), Overview components.
  - Flow: operator command or console action → runner executes checks
    against recorded pairs through the data plane → results rows → readiness
    projection → deployment qualified set.
- **Design sketch:**
  ```python
  class Check(Protocol):
      id: str                         # "conversion_conformance", "receipt_integrity", ...
      required: bool
      def run(self, ctx: QualificationContext) -> CheckResult: ...

  @dataclass(frozen=True, slots=True)
  class CheckResult:
      check_id: str; outcome: Literal["passed","failed","not_run"]
      scope: ResourceScope; revisions: tuple[VersionRef, ...]
      evidence_mode: Literal["recorded","live_smoke"]
      evidence: tuple[str, ...]       # execution ids, fixture names, measured numbers
      measured: Mapping[str, float]   # e.g. {"gateway_overhead_p50_ms": 11.2}
  # GET /readiness → safe aggregate only
  # GET management .../qualification → scoped checks, evidence and blocking reasons
  ```
- **Alternatives considered:** Flip readiness by configuration (benefit:
  immediate; cost: "readiness must not advertise a production-ready gateway"
  without evidence, WU-35). CI-only qualification (benefit: automatic; cost:
  deployments are per installation, the suite must run where they are).
- **Freeze:** none.
- **Decision (evidence-gated readiness):** settled by the delivery design's
  qualification list and WU-35's readiness rule.
- **Risks:** A suite that passes on recordings but not live; bounded by
  labelling the run as recorded or smoke on the card. Rollback: revert;
  readiness returns to not qualified.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-104 — Produce a migration report from a traffic sample

- **Status:** ⬜ defined
- **Context:** The product's second flagship is interface migration with no
  user code change. The product design describes a migration workflow:
  inspect a proposed provider or interface change against an authorized
  traffic sample, offline, and produce a reviewable report. Nothing
  implements it; the mockup's screen 7 is unplanned.
- **Goal:** An owner selects a traffic sample (captured requests within the
  capture policy, or a recorded fixture set) and a proposed change (a draft
  policy version, or a target interface and deployment), and the platform
  replays conversion offline through kernel inspection, producing a report:
  unsupported features with counts, scoped references that would not cross,
  disposition differences per field, estimated cost delta from the pricing
  table, and the list of requests that would be rejected. No provider I/O.
- **Scope:** `app/migration/` (sample selection, offline replay, report),
  migration, console Migrations page with report view and export, tests.
  About 16 files.
- **Non-goals:** Live quality evaluation (WU-118). Shadow traffic with approved
  destinations and data policy (WU-129). Canary (WU-105).
- **Acceptance:**
  - A report over the recorded sample lists per-field dispositions and
    counts matching the fixture, with zero wire calls —
    `platform/services/gateway/tests/test_migration.py::test_offline_report`
  - Requests whose proposed conversion hits a denied rule appear in the
    rejected list with the rule —
    `platform/services/gateway/tests/test_migration.py::test_rejections`
  - Cost delta uses the pricing table with effective dates and reports a
    range when any input is unknown —
    `platform/services/gateway/tests/test_migration.py::test_cost_delta`
  - Sample selection respects the capture policy and the principal's read
    permission; a viewer cannot run a report —
    `platform/services/gateway/tests/test_migration.py::test_sample_authorization`
  - The report pins the converter artifact and the catalog lock hash —
    `platform/services/gateway/tests/test_migration.py::test_artifact_pinned`
  - The console runs a report and exports it —
    `platform/tests/integration/migration.test.ts`
  - Sample selection, execution, report reads and exports reauthorize current scope/content conditions; an offline report does not declassify its source —
    `platform/services/gateway/tests/test_migration.py::test_report_scope_lifecycle`
  - A proposed route blocked by current residency/classification/compartment policy is identified without provider I/O or disclosure of hidden destinations —
    `platform/services/gateway/tests/test_migration.py::test_abac_rejections`
- **Done:** An authorized recorded sample produces reproducible conversion and
  policy findings, safe rejection counts and evidenced cost bounds without network
  I/O; the report retains its source scope and never implies live quality parity.
- **Deps:** WU-86, WU-93, WU-94, WU-91, WU-82g; kernel WU-15 and
  WU-27 (complete). A /responses migration requires its separately qualified
  library evidence; no platform workaround or implied support.
- **Architecture:** §12 (proposed migration subsection), §5 referenced.
- **Integration:**
  - Layer: platform service and console; kernel inspection through public
    APIs.
  - Modules: `app/migration/{sample,replay,report,api}.py`, migration
    for `migration_reports` (revision allocated at implementation), console pages.
  - Flow: sample → for each request: inspection on current and proposed
    route → diff of reports → aggregate → report row with artifact ids.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class MigrationReport:
      id: UUID; scope: ResourceScope; application_id: UUID
      compartment_ids: frozenset[UUID]; authorization_version_refs: tuple[VersionRef, ...]
      sample: SampleRef                # captured window or fixture set, with count
      proposed: Proposed               # policy draft version or (interface, deployment)
      converter_artifact: str; catalog_lock: str; pricing_version: int
      unsupported: tuple[FeatureCount, ...]
      references_blocked: int
      dispositions: tuple[FieldDiff, ...]      # field, today, proposed, count
      rejected: tuple[RejectedRequest, ...]    # execution_id, rule
      cost_today: CostRange; cost_proposed: CostRange
  ```
- **Alternatives considered:** Report from live shadow traffic (benefit:
  real responses; cost: disclosure and spend; the design separates offline
  replay from live evaluation).
- **Freeze:** none.
- **Decision (offline, pinned artifacts):** settled by the product design's
  migration workflow: offline conversion replay, converter artifacts pinned,
  a catalog fingerprint alone not advertised as code identity.
- **Risks:** Large samples; bounded by a sample cap with stratified
  selection by status. Rollback: revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

## WU-105 — Roll out a policy version to a canary share with rollback

- **Status:** ⬜ defined
- **Context:** A migration report that cannot be acted on safely stays a
  document. The product design's migration workflow ends with approved
  canary rollout and rollback; Portkey offers canary testing in production.
  Publishing a policy today switches all traffic at once.
- **Goal:** An owner publishes a policy version to a percentage of an
  application's traffic, chosen deterministically per session id when
  present and per execution otherwise; receipts record which version served
  them; the Migrations page compares canary and baseline on fallback rate,
  partial rate, fidelity denials and cost range; promote or roll back is one
  audited action.
- **Scope:** policy rollout state and selection, data-plane version choice,
  comparison query, console rollout controls, tests. About 12 files.
- **Non-goals:** Automatic promotion on metrics (later, after the
  comparison is trusted). Canary by deployment weight (that is load
  balancing, WU-109).
- **Acceptance:**
  - A 10 percent rollout serves close to that share over the recorded
    sample with deterministic assignment by session id —
    `platform/services/gateway/tests/test_canary.py::test_share_and_determinism`
  - Receipts carry the serving policy version and the comparison splits
    metrics by it —
    `platform/services/gateway/tests/test_canary.py::test_comparison`
  - Rollback returns all traffic to the baseline on the next snapshot and is
    audited; in-flight executions retain their configuration version but obey current
    revocation, mandatory policies and stream checkpoints —
    `platform/services/gateway/tests/test_canary.py::test_rollback`
  - The console starts a rollout, reads the comparison and promotes —
    `platform/tests/integration/canary.test.ts`
  - Neither baseline nor canary can loosen mandatory ABAC/compartment policy; forged or varied session IDs cannot select a less restricted route —
    `platform/services/gateway/tests/test_canary.py::test_security_invariant_across_versions`
  - Promotion and rollback enforce scoped publish permission plus configured independent approval; stale approvals cannot authorize another candidate version —
    `platform/services/gateway/tests/test_canary.py::test_approval_binding`
- **Done:** v8 serves 10 percent of the recorded sample, the comparison
  shows its fallback and partial rates and cost range beside v7, and
  rollback assigns no newly admitted execution to v8 after the change;
  existing executions retain v8 attribution and current security enforcement.
- **Deps:** WU-104, WU-97, WU-86, WU-103. Both candidate profiles
  require current qualification before production rollout.
- **Architecture:** §12 (routing subsection) and §12 (migration subsection) extended.
- **Integration:**
  - Layer: platform service and console.
  - Modules: `app/policies/rollout.py`, snapshot resolution extension,
    comparison query, console controls.
  - Flow: snapshot → rollout state → assignment hash(session or execution)
    → policy version → explain and execute → receipt version → comparison.
- **Design sketch:**
  ```python
  @dataclass(frozen=True, slots=True)
  class Rollout:
      policy_id: UUID; scope: ResourceScope; baseline_version: int; canary_version: int
      qualification_refs: tuple[VersionRef, ...]; approval_ref: UUID | None
      share_pct: int                   # 1..50
      started_by: UUID; started_at: datetime
      state: Literal["running","promoted","rolled_back"]
  # POST …/policies/{id}/rollout {canary_version, share_pct}
  # POST …/policies/{id}/rollout/promote | /rollback
  # GET  …/policies/{id}/rollout/compare → metrics per version
  ```
- **Alternatives considered:** Header-based canary chosen by the client
  (benefit: precise tests; cost: a caller-chosen policy version is caller
  authority). Time-based switch (benefit: simplest; cost: no comparison).
- **Freeze:** none.
- **Decision (server-side assignment):** the client never selects its
  policy version (evidence design: caller-supplied correlation is not
  authorization; session id only seeds the hash).
- **Risks:** Comparison on too few executions reads as signal; bounded by
  showing counts beside every rate and no verdict wording. Rollback: the
  feature's own rollback, plus revert.
- **Open:** none.
- **Evidence:** (filled at completion)
- **Area:** platform
- **Priority:** P1
- **Tier:** 4
- **Owner:** unassigned

