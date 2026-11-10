# Agent execution profiles and environments

Status: proposed runtime architecture. Both ready-to-use agents and advanced
custom agents are agreed product requirements; protocols and hosting are open.

## Four distinct objects

| Object | Defines |
|---|---|
| Agent definition | Purpose, instructions, skills, tools, input/output contracts |
| Execution profile | Loop, stopping rules, retries, callbacks, checkpoints, approval behavior |
| Execution environment | Isolation, runtime dependencies, resource/network limits, credential bindings |
| Deployment | Approved versions and bindings for a compartment and operational configuration |

A run is one execution of a deployment, with its own state and evidence. A
definition can be deployed into several environments without sharing secrets
or histories. An execution profile is distinct from ocai's `CapabilityProfile`.

## Ready-to-use profiles

| Profile | Intended behavior | Qualification focus |
|---|---|---|
| Structured task | Bounded task with validated output | Invalid output, retries, refusal, limits |
| Grounded assistant | Retrieval and source attribution | Authorization, stale sources, insufficient evidence |
| Tool-using agent | Bounded model/tool loop | Tool correlation, permissions, action duplication, budgets |
| Approval workflow | Prepare an action, pause, execute after approval | Exact approved inputs, expiry, identity, post-approval changes |
| Durable workflow | Multiple steps with checkpoints and recovery | Worker failure, resume, cancellation, state compatibility |

Profiles publish their guarantees, unsupported cases, dependencies, and tests.
They provide working loops and integrations so designers primarily connect
approved tools, knowledge, inputs, and outputs. Defaults need evaluation for
the chosen use case; a packaged profile is not automatically suitable for every
domain or risk level.

## Advanced customization

Developers can provide custom loops and execution code through a documented
contract. Authorization, enforced resource limits, cancellation controls, and
required evidence remain at independently controlled execution boundaries.
Untrusted custom code cannot be isolated by an in-process callback protocol.
Decide supported code trust levels and sandbox guarantees before accepting it.

Separate observational callbacks from callbacks that alter decisions or perform
effects. Declare permissions, timeouts, ordering, error behavior, and whether a
callback blocks progress. Required audit delivery cannot be delegated solely to
an optional callback. Customization support must state which standard guarantees
remain enforceable and where customer code assumes responsibility.

## Tools and approvals

Treat tool schemas, retrieved instructions, and model outputs as untrusted
inputs. Validate arguments and authorize each action against authenticated
context. A model suggesting an action is not authorization to execute it.
Credentials are bound to permitted operations and remain outside transcripts.

Approval binds to the specific action, arguments, target, approver, and expiry.
Material changes require renewed approval. Recheck current authorization at
execution, especially after a long pause. Distinguish provider-side approval
exchanges from application authorization; satisfying one does not imply the other.

Classify tools by effects and recovery behavior. Retries of writes need an
idempotency key, a reconciliation procedure, or an explicit decision not to
retry. An ambiguous timeout may mean an action succeeded. Compensation is a
separate business operation, not proof that the original effect never happened.

## Durability and operations

The runtime owns durable state, checkpoints, workers, leases, scheduling,
cancellation, and resume. Bound wall time, step count, concurrency, and spend.
Distinguish queued, running, awaiting approval, cancelling, completed, failed,
and incomplete/unknown outcomes; final state vocabulary is not frozen here.

Checkpoint enough provenance to explain the next step after recovery. Prevent
duplicate workers from performing the same effect where the integration allows
it, and reconcile uncertainty otherwise. Python async execution alone is not a
durable job system. Multi-step execution belongs above ocai's call contracts.

## Environment options

Potential environments include trusted customer workers, isolated containers,
and stronger sandboxed execution for less-trusted code. Each needs declared
network egress, filesystem access, resource ceilings, dependency/artifact
provenance, secret access, and cleanup behavior. These are candidate isolation
tiers, not equivalent security guarantees or selected technologies.

Development can use recorded/replayed integrations or restricted test targets.
Production binds approved versions and credentials. Simulation must identify
which effects are simulated; a passing simulation is not proof of live access
or successful external execution.

## Application experiences

Provide focused, deployable templates and embeddable components: chat with
citations, structured forms, attachments, review/approval inboxes, task progress,
cancellation, artifacts, and feedback. They invoke authorized deployments and
carry run identity through to the user experience.

Streaming progress, reconnection, long-running jobs, and user-visible partial
failure need contracts. Application users see only authorized artifacts and
evidence. User feedback feeds evaluation without automatically becoming a
release approval or permission to reuse private content in a dataset.

A general-purpose frontend builder is optional future scope. The initial
experience layer should make AI and agent capabilities usable without requiring
every customer to build these interaction patterns from scratch.
