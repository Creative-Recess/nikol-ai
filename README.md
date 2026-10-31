# Nikol.ai

An AI training coach for endurance athletes, built on intervals.icu.
It coaches running, cycling and swimming, and plans around other sports and strength as cross-training.
It runs inside any AI coding agent that can read files and run commands, such as Claude Code, Codex or Cursor.

## How it works

1. Your watch (and bike computer) syncs activities, HRV, sleep and resting HR to intervals.icu.
2. The coach reads that data through the intervals.icu API and writes planned workouts back to your intervals.icu calendar.
3. intervals.icu forwards the next ~7 days of workouts to your watch, and rides to your bike computer.
4. Every push goes through `scripts/guardrails.py` first (long-run spikes, weekly ramp, rest days, an optional injury score, workout syntax) and is verified afterwards.

## Devices

nikol.ai only talks to intervals.icu, so it works with any watch that syncs to intervals.icu and can receive planned workouts from it.

| Device | Status | Notes |
|---|---|---|
| Garmin | Supported, tested | The most complete data: activities, HRV, sleep, resting HR, and planned workouts with pace or HR targets. Ride workouts with power or HR targets tested on an Edge 840 and a Forerunner 255S, and pool swim workouts on the Forerunner (pace targets don't reach the watch for swims, so the pace is written into each step). The Garmin Connect app doesn't show the steps of these workouts, but the devices do. An Edge may keep showing its own Daily Suggested Workout next to them if that can't be turned off |
| COROS | Supported, not yet tested end to end | Activities, basic wellness, and planned workouts with pace or HR targets. COROS can't take pace and HR targets in the same workout, which the guardrails already prevent. Check the first pushed workout on the watch |
| Wahoo | Partial | Fine as a bike computer for ride data (ride workouts not yet tested). Running workouts only upload with HR targets, so pace sessions won't reach a Wahoo device |
| Polar | Not supported | Sends activities but can't receive planned workouts |

If your watch's HRV or sleep data is thin, an Oura ring or WHOOP band syncs wellness data to intervals.icu directly.
Connect your watch to intervals.icu directly, not through Strava: activities imported via Strava are blocked from the intervals.icu API.
More on which devices work: [watch compatibility with intervals.icu](https://stas.run/en/guides/intervals-icu-watch-compatibility).

## What you need

1. A supported watch (see above).
2. A free [intervals.icu](https://intervals.icu) account connected to your watch (Settings → Connections, with **Upload planned workouts** ticked), and a Run threshold pace set in its sport settings (an FTP in the Ride settings if you ride, and a threshold pace in the Swim settings if you swim).
3. An intervals.icu API key (Settings → Developer).
4. An AI coding agent that can read files and run shell commands, and Python 3.9+ (standard library only).
   It runs on macOS, Linux and Windows.

## Setup

Open your agent in this folder and say "set me up".
It reads `AGENTS.md` (the coach's instructions) and walks you through everything, one step at a time:

1. Creating an intervals.icu account and connecting your watch.
2. Setting your heart rate and pace thresholds, or working them out if you don't know them.
3. Saving your intervals.icu API key on your computer (you run that command yourself, so the key never goes into the chat).
4. Building your profile from your intervals.icu history and a short conversation.
5. Setting up your race (or a training block if you don't have one yet) and a plan that's checked against the safety rules.
6. Writing your first week and sending it to your watch.

## Using it

Ask things like:

- "What's today?"
- "Weekly review"
- "Write and push next week"
- "I ran the 5 km time trial in 24:30"
- "I did a 20-minute FTP test at 250 W"
- "I swam a 400 m in 7:00 and a 200 m in 3:20"

The coach's instructions are in `AGENTS.md`, and the coaching rules in `RULES.md`.

## Why it's built this way

1. **intervals.icu as the hub.**
   It's free, has official integrations with the main watch makers, and an open API with a personal key, so one integration covers every supported device.
   The watch makers' own APIs are business-only or closed.
2. **Plain files and scripts, no third-party tools.**
   Markdown instructions plus standard-library Python work in any agent, with no supply chain, and the API key stays on your computer.
3. **Maths in code, not in the model.**
   The most common failures reported with AI coaches are wrong dates, pace arithmetic errors and ramping load too fast (see [Düking et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC10915606), experts rating ChatGPT training plans), so scripts do all of it (`paces.py` for running, `power.py` for cycling, `swim.py` for swimming).
4. **A fixed plan, adjusted within bounds.**
   The week-by-week skeleton is set up front.
   Weekly reviews can only move, shorten or swap sessions within the rules, and anything bigger is a logged decision.
5. **Guardrails before anything is written.**
   Every week is checked against the rules in `RULES.md` before it reaches the calendar, and verified afterwards.
6. **State in files and the calendar, never in chat memory.**
   Every session starts from a fresh read of intervals.icu and the repo, so long conversations can't drift.

## Getting updates

Ask your agent to "get the latest version".
It pulls the changes and checks whether your setup needs anything new.
Your `athlete/` folder is never touched by an update.

## Privacy

Everything about you lives in `athlete/`, which holds personal health data and is ignored by git, so it isn't committed.
Your training data also lives in intervals.icu, and is sent to the AI provider behind your agent while it coaches you.
Your intervals.icu API key stays on your computer, in the Keychain or an environment variable, and is never written to a file in this repo.

## Contributing

Want to improve the coach? See [CONTRIBUTING.md](CONTRIBUTING.md) for how the project is put together, how to run the tests and how changes are checked.

## Licence

MIT. See [LICENSE](LICENSE).
