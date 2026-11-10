---
name: maintainer-handoff
description: What to do when work hits something only the maintainer can decide or do (a contract shape, a freeze question, a repo setting, a merge, a credential) — file a decision-needed issue with a recommendation, keep working on what does not depend on it, and say so in the report. Use whenever you are about to ask the maintainer a question or wait on them.
---

# Maintainer handoff

Agents do not block in chat. A question for the maintainer becomes a draft
card in the **Blocked on maintainer** column of the project (never an
issue), with a recommendation, and the agent continues with everything that
does not depend on the answer.

## When this applies

- A frozen-candidate surface would change (rule 2) and no ADR settles it.
- A gate, a ruleset, a repository setting, a secret, or a merge is needed.
- Two reasonable readings of a WU lead to materially different work.
- An action is outward-facing (posting, publishing, deleting) and not
  already authorized by the WU.

Not for: things you can verify in the code or the docs; routine judgment
calls a careful colleague would make.

## Procedure

1. Write the question so it can be answered with a word: the question,
   the options with what each costs and makes easier, one recommendation,
   what it blocks.
2. File it:

   ```bash
   task board:decision -- "Decision: <one line>" <file>
   ```

   The task runs the privacy guard on the body, then adds the card directly
   in Blocked on maintainer.
3. If the decision outlives the PR, note that the answer becomes an ADR in
   `docs/decisions/` (numbered after rebasing onto `main`).
4. Continue with the parts of the WU that do not depend on the answer. If
   nothing can proceed, say so in the decision card's body ("blocks WU-NN")
   and the maintainer parks the WU card in Blocked on maintainer.
5. In your report, list every handoff by issue number. Never state or
   imply the maintainer approved something unless they wrote it in the
   repo, the PR, or the issue.

## When the answer arrives

Record the decision where it belongs (ADR, WU Decision bullet, or the
PR), then move the decision card to Done — the one card an agent may move,
since nothing else derives it — noting in its body where it was recorded.
