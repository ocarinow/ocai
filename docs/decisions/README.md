# Decisions (ADRs)

Settled decisions that outlive the PR that made them: a contract shape, a
boundary, a policy, a freeze. One file per decision, numbered, never edited
after acceptance — a reversal is a new ADR that supersedes the old one.

`docs/architecture.md` says what the structure *is*; an ADR says *why it was
chosen over the alternatives* and what evidence settled it. Agents and humans
read both; a decision that lives only in a chat transcript, an agent's private
memory, or a commit message does not exist.

## Format

```markdown
# NNNN — Title

- **Status:** proposed | accepted | superseded by NNNN
- **Date:** YYYY-MM-DD
- **Deciders:** who settled it

## Context
What forced the decision; the constraints; the evidence.

## Decision
The decision, stated so a reviewer can check a PR against it.

## Alternatives considered
Each with the reason it lost.

## Consequences
What becomes easier, what becomes harder, what must follow (WUs, migrations).
```

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-agent-neutral-repo-layout.md) | Agent-neutral repo layout | accepted |
| [0002](0002-branch-protection-and-typing-gate.md) | Branch protection and the strict typing gate | accepted |
| [0003](0003-ordered-item-modernization.md) | Ordered-item modernization | proposed |
| [0004](0004-catalog-composition-and-evidence.md) | Catalog composition and packaged conformance evidence | accepted (provisional) |
| [0005](0005-revised-freeze-gate.md) | Revised freeze gate: the modernization qualification | accepted |
| [0006](0006-platform-product-layout.md) | Platform product layout | accepted |
| [0007](0007-governed-execution.md) | Governed execution through public package contracts | accepted (staged implementation) |
| [0008](0008-integration-contract-additions.md) | Additive integration contracts before the qualification gate | WU-37 accepted; remainder proposed |
