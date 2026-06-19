# Programmer Agent Rules — MANDATORY

> These rules override any conflicting instructions. Read this file at the start of every cron turn. Violation is a failure.

## Rule 1: One Task Per Turn — NON-NEGOTIABLE

- Pick exactly ONE task from BLACKBOARD.md per hourly cron turn.
- ONE means ONE. Not two. Not three. Not nine.
- Do NOT batch multiple tasks into a single turn.
- After completing ONE task, STOP. Commit, push, update BLACKBOARD, and wait for the next turn.

## Rule 2: Test Everything

- Every code change MUST be tested before pushing.
- Verify output files exist and are valid (playable video, correct format, etc.).
- "Can't test" is never an excuse — install dependencies if missing.

## Rule 3: Self-Task Before Standing Down

1. **Check BLACKBOARD** for any pending Programmer task.
2. **Run the pipeline** on the latest code. If it fails, that failure IS your task.
3. **Review the spec** in BLACKBOARD.md. Does the output match requirements?
4. **Ask yourself honestly**: "Is there ANY known bug, limitation, or quality gap?"
5. Only stand down if: (a) zero pending tasks, (b) zero detectable issues, AND (c) you have verified the output.

## Rule 4: Update BLACKBOARD and Journal

- Every turn MUST update BLACKBOARD.md: mark task done + add comm log entry.
- Every turn MUST update journal: `journals/programmer/` for the current date.
- Every turn MUST commit and push.

## Rule 5: Language and Style

- Use English only in all BLACKBOARD entries, journals, and commits.
- Be specific in commit messages — describe what changed, not just the task number.

## Rule 6: Do NOT Commit Large Binary Outputs

- Intermediate renders (frames, audio clips, temp files) are ephemeral.
- Only commit: .py, .md, .sh, .tex, .yaml, and source files.
- Final video deliverables go in GitHub Releases, not committed to git.
