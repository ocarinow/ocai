# Catalog studios and human evaluation

> **Proposed design, not a usage guide.** Original research/design dates are retained.
> Implementation status comes from [the roadmap](../../plans/README.md) and
> [qualified user documentation](../../user/index.md).

Status: proposed shared asset and authoring lifecycle. Human evaluation,
different user responsibilities, prompt studios, and skill studios are part
of the agreed product direction.

## Typed asset catalog

Provide common identity, owner, version, compartment, provenance, dependency,
approval, and lifecycle metadata while preserving separate contracts for:

- Prompt templates: variables, examples, input assumptions, output requirements.
- Skills: instructions, resources, tool requirements, intended use, test cases.
- Tools: operation schemas, effect classification, authentication and permissions.
- MCP servers: protocol capabilities and connection requirements, distinct from
  the tools exposed by a particular server instance.
- Agent definitions, execution profiles, and environments: separate objects
  described in [execution](execution.md).
- Model artifacts and deployments: artifact identity differs from a serving
  endpoint or mutable provider alias.
- Data sources, knowledge packages, and datasets: access, freshness, lineage,
  and evaluation purpose.
- Evaluators, rubrics, and policies: versioned criteria and enforcement behavior.

The asset catalog is not `ocai.convert.Catalog`. Model/asset versions also do
not replace ocai's interface tag, canonical IR revision, or package API version.

Start with the minimal registry needed to pin deployments, policies, and
evidence. Add discovery, ownership workflows, dependency impact, deprecation,
and approval views as the catalog product develops. Registry infrastructure
may be shared; an arbitrary untyped blob is insufficient as every asset contract.

## Studios

| Studio | Authoring experience | Validation |
|---|---|---|
| Prompt Studio | Templates, variables, examples, output constraints | Example runs, model comparisons, regression datasets |
| Skill Studio | Instructions, resources, tool dependencies | Scenario tests, permission review, dependency validation |
| Agent Studio | Skills, tools, knowledge, profiles, inputs and outputs | Simulations, authorized test runs, traces, human evaluation |

Nontechnical users should begin with guided business templates, such as document
review or procurement approval. Expose meaningful options like "require approval
before sending" rather than callback internals. Show required access, expected
cost bounds, possible external effects, and unresolved validation before publish.

Code-authored and visually authored assets should use the same versioned
contracts. Round-trip editing limits must be explicit: custom code need not be
editable as visual blocks, but must remain inspectable and testable through
the same deployment and evidence lifecycle.

## Human evaluation

The use-case owner defines success through examples, a versioned rubric, and
acceptance criteria. Reviewers assess authorized execution evidence:

1. Select a population or sample of runs and record the selection method.
   Distinguish random samples from incidents or handpicked difficult cases.
2. Assign cases to authorized domain reviewers. Assignment does not itself grant
   access to underlying content; provide a permitted redacted view if necessary.
3. Show the answer, authorized source evidence, relevant execution steps, and
   rubric. Permit dimension scores, passage annotations, correction proposals,
   and explicit abstention when evidence is insufficient.
4. Support blinded comparisons and multiple reviewers where useful. Record
   disagreement and adjudication without overwriting original assessments.
5. Let the use-case owner inspect trends and failure categories and make a
   separate release decision against the acceptance criteria.
6. Promote approved cases into versioned regression datasets with provenance,
   access and retention checks, and controls against test-data contamination.

End-user feedback, expert judgments, model-based evaluations, and release
approvals remain distinguishable. An assessment records evaluator identity,
rubric version, target version/run, time, evidence, and amendments. Automated
evaluators also record model/tool configuration and uncertainty where available.

An operational approval authorizes a particular proposed action. It is not the
same as an evaluation label or a general approval of the agent definition.

## Release lifecycle

Draft → test → review → publish → deploy → observe → revise.

Published versions should be immutable; corrections create new versions.
Deployments reference approved versions and dependency bindings. A user editing
a prompt must not silently change a production agent. Mutable convenience aliases
resolve to recorded versions during execution where possible; unavailable
upstream version identity remains explicitly unknown.

Promotion records the approver, required evaluation results, policy, dependency
versions, and target compartment/environment. Support canaries and rollback,
including compatibility checks for persisted state. Rolling back code does not
undo external actions already performed by an agent.

Use-case owners and platform administrators can have separate approval duties.
Which releases require separation of duties is configurable policy, not a
universal assumption about every customer.
