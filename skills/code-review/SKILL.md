# Code Review Skill

## Trigger
Use this skill when:
- Reviewing a pull request before approving or requesting changes.
- Asked to review code someone else has written.
- Asked to self-review code before opening a pull request.

## Procedure
1. Read the PR description first: Understand what problem it is solving before reading the code.
2. Check correctness: Does the code do what it claims? Are edge cases (empty input, None values, unexpected types) handled?
3. Check quality: Is the solution code understandable? is the solution more complicated than it needs to be (KISS)?
4. Check maintainability: Will someone else understand this later? Are tests and documentation updated if needed?
5. Check scope: Does the PR only touch what it claims to touch, or does it include unrelated changes?
6. Write feedback that is specific, constructive, and actionable: Point to the exact line/issue, explain why it matters, and suggest a possible fix rather than just criticizing. 

## Verification
- Confirm every changed file in the PR diff was actually read, not skimmed.
- Confirm at least Correctness, Quality, and Maintainability were each explicitly checked (not just "looks fine").
- If tests exist for the changed code, confirm they were run and pass before approving.
- Confirm the review decision (Approve/"Request change"/Comment) matches the severity of what was found, do not approve if a correctness issue was flagged.

## Boundaries
- Do not approve a PR without reading the actual code changes, even if the description sounds reasonable.
- Do not rewrite the author's code yourself in review comments. Suggest changes, let the author implement them.
- Do not focus only on style/formatting while missing correctness or security issues.
- If the PR is too large to review properly in one sitting, say so and ask for it to be split into smaller PRs.