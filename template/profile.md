# Athlete profile: [First name]

**Last updated:** [YYYY-MM-DD]

The coach reads this file every session.
Current thresholds, paces, VDOT and FTP live only in `settings.json`, and zones live in intervals.icu, so don't copy them here.
This file is for everything else: who you are, where the numbers came from, and your own rules.

## 1. About you

- **Name:** [First name]
- **Age:** [XX]
- **Weight:** [XX] kg (used for protein and fuelling targets)
- **Running background:** [How long you've been running, typical weekly km over the last 6 months, longest recent run]
- **Other sport:** [Cycling, swimming, gym - anything that adds load]
- **Is this your first marathon (or first race at this distance)?** [Yes/No]

## 2. Benchmarks and baselines

- **Recent races or time trials:** [Distance, time, date, course (flat or hilly), average HR]
- **Where the thresholds came from:** [Lab test, race, watch estimate, intervals.icu eFTP]
- **Resting HR and overnight HRV baseline:** [e.g. 48 bpm, 55 ms]

## 3. Injury history and limiters

- **Current niggles:** [Anything sore right now, which side, how bad out of 10]
- **Past injuries:** [What, when, what fixed it]
- **What tends to break first:** [e.g. calves, Achilles, knees, back]
- **Anything the coach should never prescribe:** [e.g. downhill repeats, track sessions]

## 4. Life and schedule

- **Work pattern:** [Office days, WFH days, what time training has to finish by]
- **Days you can't train:** [Regular commitments]
- **Morning or evening:** [When you prefer to run]
- **Travel coming up:** [Trips, holidays, blocks with no running]

## 5. Where you train

- **Home routes:** [Flat or hilly, roads or trails]
- **Flat loop for time trials:** [Where]
- **Track access:** [Yes/No, which nights]
- **Gym or strength equipment:** [Gym, dumbbells, bodyweight only]

## 6. Gear

- **Watch:** [Garmin or COROS model. A Wahoo watch only takes HR-target runs]
- **Bike computer:** [Garmin, Wahoo or none]
- **Wellness device:** [Oura, WHOOP or none, if the watch's HRV and sleep data is thin]
- **Daily trainers:** [Shoe]
- **Race shoes:** [Shoe]
- **Recovery:** [Sauna, ice bath, foam roller, anything you have access to]

## 7. How you want to be coached

- **What motivates you:** [e.g. hitting numbers, enjoying the run, a finish time]
- **What to watch out for:** [e.g. "I go too hard on easy days", "I skip strength"]

## 8. My rules

These add to `RULES.md` for this athlete.
They can tighten the general rules but never loosen an enforced one.
Write each rule as one line the coach can act on, and note the date and reason for anything that's a personal call.
Delete the examples below once you've written your own.

### Runs

1. [Example: 4 runs a week: Tuesday, Thursday, Saturday and the Sunday long run.]
2. [Example: Monday is the full rest day.]

### Rides and other sport

1. [Example: Saturday group ride, NP at or below 200 W, and never the day before a key session.]

### Schedule

1. [Example: Office days are Mon, Wed and Thu, and training finishes by 8am.
   These days and times also go in the event's `plan.json` under `schedule` (`office_days`, `office_start`, `office_done_by`), so the guardrails can check them.]

### Injuries

1. [Example: Left calf. Set `injury_score` in `settings.json` to `"name": "calf"`, `"side": "left"`, and score it every morning.]

### Routes

1. [Example: Time trials on the flat river loop.]

### Recovery and strength

1. [Example: Strength A on Wednesday evening, Strength B after the Saturday run.]
