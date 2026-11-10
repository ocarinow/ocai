# Platform products and users

Status: proposed portfolio supporting the direction in [the overview](README.md).

## Users and responsibilities

Roles are scoped responsibilities, not exclusive account types. A person may
review one application's answers while administering another compartment.

| User | Responsibility | Primary experience |
|---|---|---|
| Use-case owner | Define business success and accept releases | Examples, rubrics, answer analysis, acceptance criteria |
| Domain expert or reviewer | Assess correctness and evidence | Review queues, annotations, comparisons, adjudication |
| Application designer | Compose approved capabilities | Prompt/skill studios and guided agent configuration |
| Agent developer | Customize execution and integrations | SDK, code, custom loops, tests, traces |
| Platform administrator | Operate boundaries and deployments | Identity, compartments, quotas, environments, policies |
| Auditor | Inspect authorized evidence | Read-only histories, provenance, decisions, approvals |
| Application end user | Perform a business task | Forms, chat, results, artifacts, approval interactions |

Administrative access does not automatically imply access to sensitive payloads.
Reviewer assignment, asset discovery, execution, and release approval are
separately authorized activities.

## Product responsibilities

| Product | Owns | Depends on |
|---|---|---|
| AI Gateway | Model access, conversion policy, routing, quotas, receipts | Qualified ocai paths; identity, evidence, minimal registry |
| Observability and Monitoring | Traces, diagnostics, health, alerts, operational analysis | Shared evidence and instrumentation |
| Evaluation | Datasets, experiments, automated assessments, human review, regression analysis | Versioned assets, authorized evidence, evaluator provenance |
| AI Catalog | Discovery, ownership, versions, dependencies, approval and lifecycle | Typed asset contracts and access policy |
| Agent Runtime and Operations | Runs, tools, state, approvals, recovery, workers, deployment | Profiles, environments, authorization, evidence |
| Agent Builder and Studios | Authoring, composition, testing, publishing | Catalog, evaluation, common execution contracts |
| Application Experiences | End-user interfaces to deployed capabilities | Deployment authorization, identity, artifacts, feedback |
| Model Operations | Self-hosted endpoints, rollout, capacity, health, utilization | Serving-system adapters, gateway registration, operational evidence |

These boundaries need not become separate commercial SKUs or microservices.
Observability, monitoring, and evaluation may share a product experience while
retaining distinct semantics and storage requirements.

## Competitive direction

The gateway aims to make provider and interface changes enforceable and
explainable through conversion contracts, eligibility checks, execution
receipts, and migration analysis. Basic proxying, quotas, dashboards, and
provider counts are insufficient differentiation on their own.

The observability and evaluation offering aims to connect changes in quality
and operations to asset, policy, model, retrieval, and converter versions.
It should help investigate causes and run controlled experiments, without
treating correlated changes as causal proof.

LiteLLM and Langfuse are comparison targets from the product discussion, not
evidence that particular capabilities are absent from their products. Before
publishing feature comparisons, recheck their current documentation:

- [LiteLLM Gateway](https://docs.litellm.ai/docs/simple_proxy)
- [LiteLLM Enterprise](https://docs.litellm.ai/docs/enterprise)
- [Langfuse data model](https://langfuse.com/docs/observability/data-model)

The differentiation is a product hypothesis to validate with design partners.
Do not claim superior latency, security, fidelity coverage, or operational
reliability without a defined comparison and evidence.

## Additional modules

| Module | Scope | Introduction point |
|---|---|---|
| Policy, Identity and Governance | Authorization, compartments, retention, approvals, emergency controls | Gateway foundation |
| Tool and Connector Execution | Enterprise integrations, scoped credentials, isolation, action authorization | Before production agents |
| Human Review and Approval | Review assignment, adjudication, operational approvals, escalation | Evaluation and runtime |
| Knowledge and Retrieval | Ingestion, indexes, access-aware retrieval, freshness, source lineage | First knowledge use case |
| AI Release Management | Evaluation gates, dependency impact, promotion, canaries, rollback | Across catalog and deployments |
| FinOps and Capacity | Reconciliation, chargeback, forecasting, allocations, utilization | Gateway ledger, then model operations |

Self-hosted model management should initially integrate existing serving
systems. Model artifacts, serving deployments, and routable endpoints are
different objects. Training infrastructure, a new inference engine, and a
general-purpose compute scheduler are not assumed requirements.

Domain packages can combine reusable expertise, retrieval configuration,
tools, tests, and templates. Private data and credentials are bound per
deployment; see [compartments](compartments.md).

## Initial customer and pilot

The first target is a platform team standardizing model access, governance,
and costs. The launch deployment model is customer-hosted, with managed hosting
later. Pair the gateway with one concrete application; a domain knowledge
assistant is the proposed example for exercising compartments, observability,
and human evaluation. The named design partner and precise domain remain open.

The pilot and subsequent workflows can develop as follows:

1. A platform team standardizes model access and proves policy-respecting
   failover with an inspectable execution receipt.
2. A use-case owner evaluates a document assistant using domain rubrics and
   restricted sources, then approves a measured release.
3. A designer configures a procurement agent from a tested profile, connects
   approved tools, and requires approval before an external write.

The first release should qualify the selected pilot workflow rather than claim
the entire portfolio. The procurement workflow is a later illustration, not a
confirmed first customer requirement.
