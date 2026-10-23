# [Event name and year]

**Race:** [Event], [day and date], [start time].
**Goal:** [time] ([pace]/km average).
Anything [fallback] is a good result.
**Plan:** [N] weeks, [start date] to race day, week by week in `plan.json`.

## 1. The event

### Course

[Start and finish, distance, elevation gain, notable hills and where they fall, surface, aid stations.]

### Conditions

[Typical weather at race time, humidity, wind.]

### Key dates in the build

| Date | What |
|---|---|
| [YYYY-MM-DD] | Week 1 |
| [YYYY-MM-DD] | [Checkpoint race or time trial] |
| [YYYY-MM-DD] | Race |

### Entry and logistics

[Entry status, deadlines, travel and accommodation, how to get to the start.]

## 2. The goal

### Where you started

[Recent weekly km and long runs (from `icu.py weeks --days 84`), recent races, current niggles, starting VDOT.]

### What the goal takes

[Goal time, the VDOT it needs (`paces.py goal H:MM:SS`), and the gap from today's VDOT. Adjust for a hilly or hot course.]

### Checkpoints

| Checkpoint | Date | Event | On track if | VDOT |
|---|---|---|---|---|
| [5 km] | [YYYY-MM-DD] | [Solo time trial] | [time] | [VDOT] |

Each checkpoint updates `athlete/settings.json` and the intervals.icu threshold pace, with an entry in `athlete/decision-log.md`.

## 3. The plan

The week-by-week plan is in `plan.json`: weekly km, long run, key session and rides for every week.
Each week's detailed sessions are in `weeks/` once they're written, about two weeks ahead.
The rules are in `RULES.md` and the "My rules" section of `athlete/profile.md`, and every week is checked against them before it's pushed.
This section is the reasoning and the parts that don't fit in `plan.json`.

### Phases

| Phase | Weeks | Focus |
|---|---|---|
| Base | [1-N] | [Easy volume, strides, strength] |
| Build | [N-N] | [Threshold, longer long runs] |
| Specific | [N-N] | [Race-pace work] |
| Taper | [last 2-3 weeks] | [Volume down, keep some intensity] |

### Weekly templates

One template per phase: which days have runs, rides, strength and the rest day.

#### Base

| Day | Session |
|---|---|
| Mon | Rest + recovery |
| Tue | [Easy + Strength C] |
| Wed | [Strength A] |
| Thu | [Easy + strides] |
| Fri | [Rest or easy ride] |
| Sat | [Ride or easy run] |
| Sun | [Long run] |

### Training paces

[From `paces.py paces VDOT`: easy, race pace, threshold, interval, now and at the target VDOT. Easy and long runs go by heart rate, sessions by pace.]

### Supporting work

[Strength sessions, fuelling in training, shoes, recovery specific to this build.]

### What could change this plan

[Injury flags, illness, travel, missed weeks, and what happens in each case.]

## 4. Race day guide

### Race plan

[Target pace from the last checkpoint, and the fallback if it's going wrong.]

### Pacing the course

[Section by section: where to hold back, where to let the pace drop on climbs, where to push.]

### Race week and race morning

1. [Carb loading: 8-10 g/kg a day for the 36-48 hours before.]
2. [Breakfast about 3 hours before the start.]
3. [Race fuelling: what, how much and when, as practised in training.]
4. [Race shoes and kit, all tested in a long run.]
5. [Getting to the start, bag drop.]

### After the race

[A week of walking and easy spins, and two weeks before any hard running.]
