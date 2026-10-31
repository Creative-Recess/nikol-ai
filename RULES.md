# Coaching rules

These are the rules the coach follows for every athlete, plus how to write workouts so intervals.icu and the watch read them correctly.
`scripts/guardrails.py` enforces the ones marked **(enforced)** before anything reaches the calendar.
If this file and the script disagree, fix one of them so they match.

The athlete's own rules (schedule, rides, routes, injuries, gear) are in the "My rules" section of `athlete/profile.md`.
They add to these rules and can tighten them, but never loosen an enforced one.

## Load

1. **(enforced) No single run more than 10% longer than the longest run in the previous 30 days.**
   Frandsen et al. 2025 (5,205 Garmin runners): risk rises sharply above +10%.
2. **(enforced) Weekly run km rises by at most 15% over the last full training week, and at most 30% over two full weeks.**
   Weeks marked `down_week` in `plan.json` (down weeks, holidays, the taper) are not ramp-checked, and returning from one is not a jump.
3. **(enforced) Planned run km stays within 10% of the plan's weekly target** (a warning, not a block).
4. **80/20:** at least 80% of running at easy effort.
5. **Spread the runs.**
   Tendons recover and adapt between loading days, so spacing matters more than squeezing in an extra session.
6. **(enforced) A full rest day every full Monday-Sunday week:** no run, ride or swim, and no leg strength (upper body, mobility and walking are fine).
   It goes on the calendar as a `recovery` note carrying the week's recovery plan.
   A logged exception (`"exceptions": {"no_rest_day": "..."}`) is only for unusual weeks such as a cycling tour or a training camp.

## Rides

1. **(enforced) No ride the day before a key session, or before a long run without a logged exception.**
   A ride before an easy long run can be allowed in a week file with `"exceptions": {"ride_before_long_run": "..."}`.
   Key sessions never get an exception.
2. Going over a ride's target gets flagged in the weekly review, because group rides overriding the plan is a common pattern.
3. Cycling load never counts as evidence of running readiness.
   A strong aerobic engine can hide the real limiter (calves, tendons).

## Availability and schedule

1. **(enforced)** Nothing is scheduled on dates listed in `plan.json` under `unavailable`.
2. **(enforced)** On office days (`schedule.office_days` in `plan.json`), morning training has to fit before work.
   WFH days (`schedule.wfh_days`) and public holidays (`holidays`) are flexible.
3. **(enforced)** No strength after a morning ride: strength on a ride day is marked `"time": "evening"`.
   Upper body never on a leg strength day.
   Week files mark strength with `"strength": "A"` (full legs), `"B"` (short calves and plyo) or `"C"` (upper body).
4. Evening runs are easy or recovery runs, never sessions.
   Mark them `"time": "evening"` in the week file.

## Injury score (optional)

For an athlete with a niggle to watch (an Achilles, a calf, a knee), `injury_score.name` in `athlete/settings.json` names the body part.
Leave it empty to not track one.

1. The athlete rates it 0-10 every morning, logged as `name: N` in intervals.icu wellness comments (`icu.py score N`).
   For a tendon: first steps out of bed, then 10 single-leg heel raises.
2. Up to 3/10 during a run is OK.
3. By the next morning it must be back to the usual score.
   If not, the next run is shortened or swapped for cross-training.
4. If the weekly trend rises, progression pauses.
5. **(enforced) Quality work (strides, hills, threshold, intervals, race pace, time trials) is allowed unless it flares:** any morning score above 3/10 in the last 7 days, or the 7-day average rising more than 0.5 over the previous 7 days, pauses it.
   No scores logged means assumed fine, so logging daily matters.
   Based on Silbernagel's pain-monitoring model.

## Other pain

Any pain above 3/10, or anything that changes gait, ends that run and triggers a plan review.

## Recovery

1. If the athlete has a sauna, use it after training 4-5 times a week, building from 10-15 to 20-30 minutes (Scoon et al. 2007).
2. Ice (or an ice bath) after runs and rides is fine (it doesn't blunt endurance adaptations), but never within about 6 hours after leg strength (A or B), since it blunts strength gains (Malta et al. 2021).
   Upper-body Strength C doesn't rule out ice.
3. Sleep 8+ hours.
4. Protein 1.6-2 g/kg a day, carbs matched to the day's training.
5. Foam roll the calf muscle, never the Achilles tendon.
6. Strength and recovery go on the calendar as notes, since only run, ride and swim workouts reach the watch.
7. The first run after a big block (a long ride plus a run, or the long run plus a long ride) is a recovery run at 69-78% LTHR, walking the climbs if needed to stay under the cap.

## Data and interpretation

1. HRV changes the plan only when the 7-day average is clearly below baseline, never from one night.
2. HRV and fitness numbers from unusual weeks (a cycling tour, travel, illness) are treated as noise.
3. Device readiness scores (e.g. Garmin's Training Readiness) don't sync to intervals.icu, so they aren't used.
4. Naps count toward sleep.
   Most watches don't record them, so they're logged as `nap: N min` in wellness comments and added to the night's sleep in reviews.
5. The athlete's own report beats the device when they disagree (e.g. a bad night the watch scored as good).
   Use HRV, resting HR, sleep and the injury score.

## Behaviour

1. Always use explicit dates with weekdays, and compute them in code.
2. Never do pace or load arithmetic by hand.
   Use `scripts/paces.py` and `scripts/guardrails.py`.
3. The weekly review can move sessions, shorten or lengthen within the rules, or swap a session type.
   Anything bigger (goal, phases, peak volume) needs the athlete's decision, recorded in the decision log.
4. Say plainly when something is off: missed sessions, rides over target, the injury trend.
   Don't flatter and don't quietly reschedule.

## Workout text

What the coach writes in a run's `description` in a week file.
Only the lines starting with `-` are parsed as workout steps: the notes above them can say anything.
Everything marked **tested** was pushed to intervals.icu (Sep-Oct 2026) and checked in the parsed workout, with a Garmin watch.
COROS takes the same text, as long as each workout keeps to one target type.
A Wahoo device only receives runs with HR targets, so pace sessions can't be sent to it.

1. **(enforced) One target type per workout** (Garmin and COROS both need this).
   Easy and long runs use HR only.
   Sessions (threshold, marathon pace, time trials) use pace only, including warm-up and cool-down.
2. **(enforced) HR targets are percentages or zones.**
   `69-86% LTHR` works (**tested**).
   Absolute bpm (`120-150bpm`, `150bpm HR`) is **silently dropped** (**tested**).
3. **(enforced) Absolute paces need the word `pace`.**
   `5:00/km pace` works, bare `5:00/km` is dropped.
4. **(enforced) `m` means minutes.**
   Use `mtr` for metres (`400mtr`), or `km`.
5. **(enforced) Every step has a target.**
6. **Strides go in the notes, not as steps**, e.g. "Finish with 6x20 s strides, press lap for each".
   They'd mix target types, and HR can't track a 20-second effort anyway.
7. **Leave a blank line before and after repeat blocks.**

HR targets, for example with a threshold HR of 170 (`% = bpm / LTHR x 100`):

| Target | bpm |
|---|---|
| `69-86% LTHR` | 117-146 (easy and long runs) |
| `69-78% LTHR` | 117-133 (recovery) |
| `Z2 HR` | Zone 2 as set in intervals.icu |

**Easy or long run (tested):**
```
- 10km 69-86% LTHR
```
Decimal kilometres work too (`- 9.5km 69-86% LTHR`, **tested**).

**Threshold session (tested):**
```
Warmup
- 2km 5:45-6:30/km pace

Main Set 4x
- 5m 5:00/km pace
- 90s 6:00-7:00/km pace

Cooldown
- 1km 5:45-6:30/km pace
```

**Relative to threshold pace (tested):** `- 5m 98-102% pace` (100% = the Run threshold pace in intervals.icu).

**Long run with marathon-pace blocks:**
```
Warmup
- 5km 5:45-6:20/km pace

Main Set 3x
- 5km 5:15/km pace
- 1km 5:45-6:20/km pace

Cooldown
- 10km 5:45-6:20/km pace
```

Syntax adapted from [hhopke/intervals-icu-mcp](https://github.com/hhopke/intervals-icu-mcp) (MIT), which adapts [intervals-icu-workout-parser](https://github.com/MarvinNazari/intervals-icu-workout-parser) by Marvin Nazari (MIT).
