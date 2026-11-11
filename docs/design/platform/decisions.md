# Platform direction and open decisions

> **Proposed design, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Recorded 2026-11-10 from the platform product discussion. This is a product
direction register, not a replacement for [engineering ADRs](../../decisions/README.md).

## Agreed direction

| ID | Direction | Scope |
|---|---|---|
| D-01 | The AI Gateway is the first platform product around ocai | Product priority after necessary kernel qualification |
| D-02 | The gateway establishes the foundation for observability, logs, and auditability | Shared contracts reusable by later producers |
| D-03 | Observability/monitoring/evaluation, an AI catalog, and an agent builder follow | Portfolio direction, not dated delivery commitments |
| D-04 | Enterprise compartmentalization is a central requirement | Data, execution, assets, evidence, and controlled sharing |
| D-05 | Domain knowledge and retrieval are valuable platform capabilities | Reusable expertise with deployment-specific private data |
| D-06 | Human evaluation serves use-case owners and domain experts | Multiple roles, answer analysis, review, and acceptance |
| D-07 | Prompt and skill studios complement agent authoring | Versioned authoring and testing experiences |
| D-08 | Support both custom agents and ready-to-use execution profiles | Configure tools/inputs/outputs or customize execution behavior |
| D-09 | Execution environments are a platform concern | Hosting and isolation details remain open |
| D-10 | Application frontends and self-hosted model management are longer-term options | Candidate scope, not required first-release features |
| D-11 | Customer-hosted deployment comes first; managed hosting follows later | Preserve architectural suitability for a managed service without requiring both at launch |
| D-12 | The first target is a platform team standardizing model access, governance, and costs | Pair the gateway pilot with one concrete application to exercise compartments, observability, and human evaluation |
| D-13 | Deployable products live under top-level `platform/`; language directories remain for independently distributed libraries | Accepted layout in [ADR 0006](../../decisions/0006-platform-product-layout.md); gateway at `platform/services/gateway/` |
| D-14 | The first release includes the console and management API | Database-backed configuration; files serve bootstrap/import/export |
| D-15 | Organizations, teams, users, scoped API keys, and resource-specific permissions are foundational | Anticipate federation and attribute conditions; detailed model remains to qualify |
| D-16 | Use Nuxt/Vue, shadcn-vue/Tailwind, FastAPI, PostgreSQL, and OpenFGA | Product stack; no new dependencies in the kernel |
| D-17 | Reuse UI and platform shell through shallow Nuxt layers | Shared frontend composition; product features remain modular in one console initially |
| D-18 | Bundle Keycloak as the reference identity provider; retain qualified customer OIDC integration | Local accounts and brokered SAML; separate provider deployment; [ADR 0013](../../decisions/0013-platform-identity.md) |
| D-19 | Nuxt server owns browser sessions; FastAPI enforces API authentication and resource authorization | Server-held tokens, opaque cookies, modular backend integration; [identity design](identity.md) |
| D-20 | Non-human identities are first-class platform principals | Service accounts, OAuth client credentials and scoped API keys; human delegation is separately qualified |

The existing kernel/satellite boundary remains authoritative. These technology
choices do not freeze schemas or establish that features are built. See
[the stack design](stack.md) for boundaries and remaining integration choices.

## Proposed design choices

| Proposal | Rationale | Validation needed |
|---|---|---|
| Separate gateway data and control responsibilities | Preserve later independent deployment without requiring it for the MVP | Offline policy expiry, revocation, dependency-failure tests |
| Start a minimal asset registry before the catalog product | Reproducible version references from the first receipt | Initial asset contracts and ownership |
| Build runtime before promising visual agent execution | Builder and code use the same behavior | One profile end to end, custom-code boundary |
| Distinguish workspace, compartment, and domain package | Collaboration and expertise need not imply data access | Customer organization and sharing examples |
| Distinguish definition, profile, environment, deployment, and run | Separate behavior, execution policy, hosting, and history | Schema examples and lifecycle transitions |
| Separate telemetry, audit, accounting, and evaluations | Different durability, access, and correctness needs | Failure semantics and retention requirements |
| Integrate external telemetry and serving systems | Independent adoption and narrower initial scope | First integration requirements |

## Resolved product questions

The maintainer confirmed both recommendations in the follow-up discussion.

| ID | Question | Resolution | Remaining detail |
|---|---|---|---|
| Q-01 | Customer-hosted first, managed first, or both for launch? | Customer-hosted first; managed hosting later (D-11) | Hosting topology, supported infrastructure, and operating responsibilities |
| Q-02 | Who is the first design partner and what workflow proves value? | Target a platform team standardizing model access, paired with one concrete application (D-12) | Named partner and exact application/domain; a domain knowledge assistant is the proposed example |

## Open decision register

No default below is an approved selection. Questions can remain open while
independent documentation or kernel work continues.

| ID | Question | Needed before | Current position |
|---|---|---|---|
| Q-03 | Which compatibility endpoints and features form the first supported surface? | Gateway interface WU | Narrow qualified slice proposed; exact choice open |
| Q-04 | How do tenant, workspace/project, compartment, and delegated grants relate? | Identity and authorization schema | Organizations, teams, users, and resource grants required; compartment hierarchy/inheritance open |
| Q-05 | What are the default fidelity policies and late response violation behavior? | Gateway execution contract | Reject forbidden request loss; buffering/partial-result choices open |
| Q-06 | Which operations require durable evidence before effect, and how do outages behave? | Audit and admission design | Per-operation explicit behavior proposed |
| Q-07 | What payload capture, retention, deletion, export, and residency defaults apply? | Evidence storage and customer security review | Metadata/content separation proposed |
| Q-08 | Which code trust levels and execution isolation tiers are supported? | Custom agent execution | In-process hooks alone are insufficient for untrusted code |
| Q-09 | Which packaged agent profile and tool integrations ship first? | Runtime pilot | Select from actual workflow needs |
| Q-10 | What human-review roles, rubrics, adjudication, and approval duties are required? | Evaluation pilot | Use-case owner and expert reviewer experiences required |
| Q-11 | Which knowledge sources and permission systems are integrated first? | Retrieval pilot | Source-aware authorization and revocation required |
| Q-12 | What artifact identity, provenance, and promotion guarantees are supported? | Registry/release design | Immutable published versions proposed |
| Q-13 | What service objectives and spending guarantees can the deployment sustain? | Production release | Measure and qualify; no invented SLA or absolute budget claim |
| Q-14 | What package namespaces and commercial model serve the satellites? | Packaging and distribution | Repository layout settled by ADR 0006; exact package namespaces, naming, and licensing remain open |
| Q-15 | Should model operations or application experiences move earlier? | Portfolio planning after pilot feedback | Conditional on customer needs |
| Q-16 | Which versions, client libraries, session store and provider profiles are qualified? | First authenticated workflow | Keycloak reference and Nuxt session ownership settled; implementation choices and compatibility evidence pending |
| Q-17 | What are the session/token lifetimes, revocation bounds and queued/in-flight behavior? | Protected resource release | Explicit policy and outage tests required; logout alone does not revoke all issued tokens |
| Q-18 | How are provider realms, platform organizations and external identity migrations mapped? | Identity schema and federation administration | Stable platform IDs and explicit issuer/subject bindings; no email-only linking or implicit realm/organization equivalence |

## Recording resolutions

Update this register when the maintainer answers a product question. For an
engineering decision, capture alternatives, consequences, and evidence in an ADR,
then link the implementing WU and tests. A suggested answer or unanswered question
must not become an accepted decision merely because implementation has started.

The first two product questions are resolved above. Remaining implementation
details stay open; the selected customer profile does not identify a committed
design partner or fix the application's domain.
