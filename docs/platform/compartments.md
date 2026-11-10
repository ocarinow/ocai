# Compartments and domain knowledge

Status: proposed isolation model. Enterprise compartmentalization and reusable
domain knowledge are agreed product requirements; object relationships and
enforcement mechanisms remain to be designed and tested.

## Distinct concepts

| Concept | Purpose | Example |
|---|---|---|
| Tenant | Top-level customer/account isolation boundary | One enterprise customer |
| Workspace | Organize ownership and collaboration | Finance applications and experiments |
| Security compartment | Enforce access and processing boundaries | Restricted financial information |
| Domain package | Reuse expertise and behavior | Procurement terminology, tools, retrieval policy, tests |

A workspace may organize several compartments. A domain package may be used
by several workspaces without sharing their private data. Membership, hierarchy,
and policy inheritance are open decisions; folder location must not implicitly
grant access. Workspace and project naming also needs consolidation.

## End-to-end scope

Compartments govern sources, indexes, uploaded files, artifacts, tools,
credentials, model deployments, histories, memory, caches, runs, traces,
evaluation datasets, audit evidence, budgets, and exports. They apply to human
and workload identities and propagate through background jobs and delegation.

Resolve scope from authenticated context and authorized bindings. A client
header or agent-generated argument cannot choose a more privileged compartment.
Enforce policy at service and storage access boundaries, not only in a UI.
Cache keys and reuse rules must include the effective access context and relevant
asset/policy versions; content similarity is not permission to share an answer.

Proposed isolation options include shared infrastructure with enforced logical
boundaries, dedicated storage/indexes, and dedicated execution environments.
Document the guarantees and threat model of each. Dedicated compute alone does
not prevent leakage through shared logs or administrative tooling.

## Retrieval and lifecycle

Authorize content access before it enters model context or an unauthorized
external reranker. Retrieval services may search within authorized infrastructure,
but must not release forbidden snippets, metadata, or citations. Apply access
rules before unauthorized content can influence an externally visible answer;
filtering citations after generation is too late.

Preserve source identity, version, permissions, freshness, and lineage through
ingestion, chunking, embedding, indexing, retrieval, and generated artifacts.
Source permission changes and deletion require defined propagation behavior
for indexes, cached answers, memory, review queues, and derived datasets.
Already-disclosed content cannot be retracted; define revocation windows and
in-flight behavior honestly. Unknown or stale authorization needs explicit
failure policy.

Data residency covers ingestion workers, vector stores, rerankers, inference,
evaluation, telemetry, and backups. A locally hosted gateway alone cannot
establish the residency of the entire workflow.

## Domain packages

A procurement package could provide terminology and schemas, retrieval rules
that prefer current purchasing policies, supplier lookup tools, approval
workflow templates, and evaluation cases. Deployments bind it to their own
authorized contracts, supplier records, credentials, and model endpoints.

The package declares dependencies, intended uses, permission requirements,
version compatibility, and evaluation evidence. It does not grant its own
requested permissions. Catalog entries for data sources can reference existing
enterprise storage rather than copy all data into the platform.

Sharing expertise and sharing data are separate operations. Even examples and
evaluation cases in a reusable package require review for private information.

## Controlled collaboration

Procurement may expose a narrow capability answering whether a supplier is
approved for a purchase category. Finance can be authorized to invoke it without
reading the underlying contract collection. The capability independently checks
the caller, permitted operation, inputs, and allowed output disclosure.

Cross-compartment grants should identify caller, target, operation, data scope,
expiry, approver, and evidence requirements. Record purpose where useful, but
do not treat a caller-declared purpose as proof of legitimate use. Export or
declassification needs an explicit authorized transformation/release decision.

Delegation must not silently expand the initiating principal's authority.
Service identities can have narrowly approved capabilities; their credentials
must not become a general privilege escalation path for agents.

## Qualification scenarios

Before claiming isolation, test forbidden retrieval, cross-tenant identifier
substitution, cached-answer leakage, background-job scope, reviewer assignment,
tool delegation, exports, administrator payload access, and source revocation.
Exercise both allowed sharing and denied sharing. Implement these checks with
the relevant feature WUs; this design is not itself an isolation certification.
