# Debugging Skill
## Trigger
Use this skill when:
- Code throws an error or exception during execution
- Code runs without errors but produces incorrect or unexpected output
- A test fails unexpectedly

## Procedure
1. Reproduce the issue first, run the failing code/test and confirm the exact error message or wrong output.
2. Read the full error traceback/stack trace before making any changes, identify which file and line the error originates from.
3. State a hypothesis about the root cause before editing (For example "the function is receiving None instead of a list").
4. Make the smallest possible change to test that hypothesis.
5. Re-run the same reproduction step to confirm whether the fix worked.
6. If it does not work, revert the change and form a new hypothesis, do not stack multiple unverified fixes on top of each other.
7. Once fixed, add or update a test that would have caught this bug, so it does not silently reappear.

## Verification
- Re-run the original failing command/test, it must now pass.
- Run the full test suite ('pytest'), not just the one test, to confirm nothing else broke.
- Confirm the new/updated test (from procedure step 7) actually fails on the old buggy code and passes on the fixed code, this proves the test is meaningful, not just present.

## Boundaries
- Do not refactor or "clean up" unrelated code while fixing the bug, stay scoped to the actual issue.
- Do not disable, skip, or delete a failing test to make it "pass", the underlying bug must be fixed, not hidden.
- Do not change public function signatures or APIs unless the bug specifically requires it.
- If the root cause is unclear after 2-3 hypotheses, stop and ask for clarification rather than guessing further.