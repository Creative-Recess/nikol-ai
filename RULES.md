# Coaching rules

These are the rules the coach follows for every athlete, plus how to write workouts so intervals.icu and the watch read them correctly.
`scripts/guardrails.py` enforces the ones marked **(enforced)** before anything reaches the calendar.
If this file and the script disagree, fix one of them so they match.

The athlete's own rules (schedule, rides, routes, injuries, gear) are in the "My rules" section of `athlete/profile.md`.
They add to these rules and can tighten them, but never loosen an enforced one.

## Load

1. **(enforced) No single run more than 10% longer than the longest run in the previous 30 days.**
   [Frandsen et al. 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12421110) (5,205 Garmin runners): risk rises sharply above +10%.
2. **(enforced) Weekly run km rises by at most 15% over the last full training week, and at most 30% over two full weeks.**
   [Nielsen et al. 2014](https://www.jospt.org/doi/10.2519/jospt.2014.5164) (novice runners): more distance-related injuries when weekly volume rose by more than 30% over two weeks.
   Weeks marked `down_week` in `plan.json` (down weeks, holidays, the taper) are not ramp-checked, and returning from one is not a jump.
3. **(enforced) Planned run km stays within 10% of the plan's weekly target** (a warning, not a block).
4. **80/20:** at least 80% of running at easy effort.
5. **Spread the runs.**
   Tendons recover and adapt between loading days, so spacing matters more than squeezing in an extra session.
6. **(enforced) A full rest day every full Monday-Sunday week:** no run, ride or swim, and no leg strength (upper body, mobility and walking are fine).
   It goes on the calendar as a `recovery` note carrying the week's recovery plan.
   A logged exception (`"exceptions": {"no_rest_day": "..."}`) is only for unusual weeks such as a cycling tour or a training camp.
7. **(enforced, when the plan coaches cycling) Ride load is measured in hours.**
   Weekly ride hours follow the same 15% and 30% ramp and 10% target tolerance as run km.
   No ride is more than 20% longer than the longest ride in the previous 30 days.
   These limits are conventional coaching practice, not from a study like the running ones: cycling has no impact loading, so the longest ride can grow faster than the long run.
8. **(enforced, when the plan coaches swimming) Swim load is distance.**
   Weekly swim km follows the same ramp and target tolerance, and no swim is more than 20% longer than the longest swim in the previous 30 days (conventional practice, as for rides).
   The shoulders are the swimmer's limiter: a sore shoulder means easier sets and more technique, not more volume.

## Rides

1. **(enforced) No ride the day before a key run session, or before a long run without a logged exception.**
   This covers rides written as notes and ride workouts.
   A ride before an easy long run can be allowed in a week file with `"exceptions": {"ride_before_long_run": "..."}`.
   Key sessions never get an exception.
2. Going over a ride's target gets flagged in the weekly review, because group rides overriding the plan is a common pattern.
3. Cycling load never counts as evidence of running readiness.
   A strong aerobic engine can hide the real limiter (calves, tendons).
4. **When the plan coaches cycling**, rides are workouts pushed to the bike computer with power targets (`% FTP`), or HR targets without a power meter.
   Most riding is endurance (zones 1-2), with at most two or three hard sessions (sweet spot, threshold, intervals) a week, and an easy day or rest before each one.
5. A ride the athlete does their own way (a group ride) stays a note with an NP cap, as cross-training.

## Swims

1. Most swimming is technique and endurance at easy to moderate pace, with one or two threshold (CSS) sessions a week.
2. Paces come from CSS (critical swim speed), set by a 400 m and a 200 m time trial and worked out with `scripts/swim.py`.
3. **Open water safety:** never swim alone in open water.
   Swim with a group or a buddy, or at a patrolled beach between the flags, with a bright cap and a tow float.
   Check the conditions (currents, swell, water temperature, water quality after rain) before going in, and wear a wetsuit in cold water.
   Build up to open water in short swims close to shore, and practise sighting in the pool first.
4. A pool swim's watch workout is built for one pool length: every swim workout states the athlete's pool length.

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
5. **(enforced) Quality work in running (strides, hills, threshold, intervals, race pace, time trials) is allowed unless it flares:** any morning score above 3/10 in the last 7 days, or the 7-day average rising more than 0.5 over the previous 7 days, pauses it.
   No scores logged means assumed fine, so logging daily matters.
   For an injury that riding also aggravates (e.g. a knee), `injury_score.sports` in `athlete/settings.json` (`["Run", "Ride"]`) gates hard rides too.
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

What the coach writes in a workout's `description` in a week file.
Only the lines starting with `-` are parsed as workout steps: the notes above them can say anything.
Everything marked **tested** was pushed to intervals.icu (Sep-Oct 2026) and checked in the parsed workout, with a Garmin watch.
COROS takes the same text, as long as each workout keeps to one target type ([COROS and mixed targets](https://forum.intervals.icu/t/coros-integration-mixed-pace-hr-intervals/127171)).
A Wahoo device only receives runs with HR targets, so pace sessions can't be sent to it ([planned workouts on Wahoo](https://forum.intervals.icu/t/upload-planned-workouts-to-wahoo/65949/25)).
The syntax is intervals.icu's [workout builder syntax](https://forum.intervals.icu/t/workout-builder-syntax-quick-guide/123701).
Why the rules below exist: [pace targets arriving as "No Target"](https://forum.intervals.icu/t/pace-targets-lost-in-garmin-export-for-api-created-running-workouts-steps-arrive-on-watch-as-no-target-parsed-correctly-in-workout-doc/130706) and [mixed pace and HR targets on Garmin](https://forum.intervals.icu/t/syncing-pace-hr-targets-to-garmin/130238).

1. **(enforced) One target type per workout** (Garmin and COROS both need this).
   Easy and long runs use HR only.
   Sessions (threshold, marathon pace, time trials) use pace only, including warm-up and cool-down.
   Rides use power (`% FTP`, power zones or watts), or HR without a power meter.
   Pace targets aren't used for rides, and power targets aren't used for runs.
2. **(enforced) HR targets are percentages or zones.**
   `69-86% LTHR` works (**tested**).
   Absolute bpm (`120-150bpm`, `150bpm HR`) is **silently dropped** (**tested**).
3. **(enforced) Absolute paces need the word `pace`.**
   `5:00/km pace` works, bare `5:00/km` is dropped.
4. **(enforced) `m` means minutes.**
   Use `mtr` for metres (`400mtr`), or `km`.
   On runs, `400m` is almost always a mistake for metres, so it's rejected; on rides, `120m` (2 hours) is fine.
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

**Rides (tested on a Garmin Edge 840 and Forerunner 255S, Oct 2026: every step arrived with its target; the Edge shows a ramp as its power range, and the cadence target):**
```
Warmup
- ramp 10m 50-70% 90rpm

Main Set 3x
- 5m 88-94%
- 3m 55%

Cooldown
- 10m 50-60%
```
A bare `%` is % FTP, and `90rpm` adds a cadence target.
Power zones (`- 15m Z2`), watts (`- 5m 200-220w`) and HR (`- 20m 69-83% LTHR`, `- 10m Z1 HR`) also work.
`power.py` turns % FTP into watts for the notes.

**Pool swims (tested on a Garmin Forerunner 255S, Oct 2026):**
```
Pool length: 50m

Warmup
- Easy 2.20 per 100 200mtr

Main Set 4x
- Hold 1.55-2.05 per 100 100mtr
- Rest 20s

Cooldown
- Easy 2.30 per 100 100mtr
```
1. **(enforced) No targets on swim steps.**
   Pace targets (`1:55/100m Pace`, `80% Pace`) parse in intervals.icu but never reach the watch, so the target pace goes in the step's own text, before the distance.
2. **(enforced) No colons in a step's text:** intervals.icu cuts the text short at a colon, so write `1.55`, not `1:55`.
   `swim.py paces` prints both forms.
3. **(enforced) Every step is a distance (`100mtr`, `1.5km`) or a rest (`- Rest 20s`).**
   Rests arrive on the watch as rests.
4. **(enforced) Every swim workout has a `Pool length: 25m` (or `50m`) line, matching the athlete's pool.**
   Without it intervals.icu assumes 25 m, and the watch won't start a 25 m workout in a pool set to 50 m.

The Garmin Connect app doesn't show the steps of workouts sent from intervals.icu (any sport), only the name and notes.
Check a workout on the watch or bike computer instead.

Syntax adapted from [hhopke/intervals-icu-mcp](https://github.com/hhopke/intervals-icu-mcp) (MIT), which adapts [intervals-icu-workout-parser](https://github.com/MarvinNazari/intervals-icu-workout-parser) by Marvin Nazari (MIT).
