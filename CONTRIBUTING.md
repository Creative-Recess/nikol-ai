# Contributing

How Nikol.ai is put together, and how to change it without breaking anyone's coaching.
Agents changing the engine follow this file too.

## How it's put together

- `AGENTS.md` - the coach's instructions, read by the agent every session.
- `RULES.md` - the coaching rules and the workout text format.
  Rules marked **(enforced)** are checked by `scripts/guardrails.py`, so the two must always agree: change one, change the other in the same pull request.
- `scripts/` - standard-library Python 3.9, no dependencies:
  1. `icu.py` - the intervals.icu API: reads, pushes, verifies.
  2. `guardrails.py` - every check a week or plan must pass before it reaches the calendar.
  3. `sports.py` - the sports the coach knows, and how each one's load is measured.
     Adding a sport starts with a row here.
  4. `paces.py`, `power.py`, `swim.py` - running, cycling and swimming maths.
- `template/` - the blank `athlete/` folder a new athlete copies at setup.
- `tests/` - unit tests for all of the above.
- `athlete/` - one athlete's personal data.
  It's git-ignored and never committed: see "Privacy" below.

Everything outside `athlete/` is the engine, and the engine never names or describes a specific athlete.

## Making a change

1. Work on a branch, and open a pull request with one change in it.
   Say what changed, why, and how it was checked.
2. Run the tests, and make sure they pass:
   ```
   python3 -m unittest discover -s tests
   ```
   Add tests for anything new, including a test that fails without your fix.
3. Check the change end to end, as close as possible to how an athlete would hit it: run `guardrails.py check` on a real week file and `guardrails.py plan` on a real plan, before and after the change.
   Anything that changes what the guardrails pass or fail for an existing athlete gets called out in the pull request.
4. If you change `template/`, existing athletes don't get it automatically: `AGENTS.md` ("Getting updates") has the coach compare their `athlete/` folder with `template/` after an update, so describe what's new clearly.
5. Never force-push to `main` or rewrite history that's already on GitHub.

## Workout syntax is only "tested" on a device

intervals.icu can parse a workout correctly and still send something different to a watch (e.g. pace targets for swims parse fine but never reach a Garmin watch).
So workout text in `RULES.md` is only marked **tested** after a real push to intervals.icu, checked step by step on the watch or bike computer.
Say which device and when, and say plainly what wasn't checked.
The Garmin Connect app doesn't show the steps of workouts from intervals.icu, so check on the device itself.

Test workouts go on the calendar with an external id that doesn't start with `nikolai-` (e.g. `nikolaitest-`), so pushing a real week can't delete them by mistake, and are deleted after the check.

## Rules and evidence

A load rule should say where it comes from.
The running limits come from studies (cited in `RULES.md`); where a rule is conventional coaching practice instead, `RULES.md` says so.
Don't present practice as research.

## Privacy

- Never commit `athlete/`, never force-add it (`git add -f`) and never remove it from `.gitignore`.
  Before any commit, check `git check-ignore -q athlete/` succeeds and `git status` shows nothing under `athlete/`.
- Never copy anything from an `athlete/` folder into the engine, including in tests, examples or commit messages.
- The intervals.icu API key comes from `INTERVALS_ICU_API_KEY` or the macOS Keychain, and is never printed, logged or written to a file.

## Writing style

Markdown has one sentence per line (it keeps diffs clean) and no em dashes.

## Useful links

- [intervals.icu API docs](https://intervals.icu/api-docs.html) and [workout builder syntax](https://forum.intervals.icu/t/workout-builder-syntax-quick-guide/123701).
- Prior art: [ClaudeCoach](https://github.com/akselsson/ClaudeCoach), [claude-running-coach](https://github.com/ColinEberhardt/claude-running-coach) and [hhopke/intervals-icu-mcp](https://github.com/hhopke/intervals-icu-mcp).
