# Two-day recording kit

One question: if three correct reps are recorded on day 1, **how often does the app wrongly correct a correct rep on another
day?** No dataset we have can answer it, because nobody in them has a second correct recording.

**Do not record anyone before MSA ethics approval.** Healthy adult volunteers only. No patients, nobody with pain or a recent injury.

| File | Use |
| --- | --- |
| `consent-form.docx` | Print one per volunteer, English and Arabic. Signed before recording; give them a copy. |
| `session-log.csv` | One line per video, filled in during the session. |
| `test-rule.md` | The pass rule. Do not change it after the first video is recorded. |
| `ml/eval/two_day_eval.py` | Runs the test once on all the videos. |

## Who and how long
- 8 to 10 volunteers (8 is the minimum in the rule), different heights and body shapes, men and women.
- Two sessions per person, **at least 24 hours apart**, about 20 minutes each. Different clothes on day 2 are good, not bad.

## Room and phone
- Phone on a stand at hip height, landscape, 2.5 to 3.5 m away, whole body visible from head to feet the entire time.
- Plain background, light in front of the person, nobody else in the picture.
- 1080p or 720p, 30 frames per second. Same phone both days if you can. **Do not** try to copy the exact camera position on
  day 2: set it up again from these steps, as a patient would.

## Exercises
| Exercise | Name in the file | Person faces | Deliberate fault |
| --- | --- | --- | --- |
| Squat | `squat` | side-on to the phone | go down only about half as far |
| Leg abduction (one leg) | `legabd` | the phone | bend the moving knee |
| Arm raise to the side (one arm) | `armabd` | the phone | bend the elbow |

Use the same leg and arm on both days and write it in the log. Stop at once if anything hurts.

## Each session
1. Check the consent form is signed. Give the volunteer a code (P01, P02, ...). The list linking names to codes stays on paper, apart from the videos.
2. Show the exercise once. Let them try it twice without recording.
3. For each exercise record **two videos of 8 slow reps**, pausing about a second between reps: first correct (`ok`), then with the
   fault (`fault`). Stand still for 2 seconds at the start and the end.
4. Fill in one log line per video. If a rep went wrong in an `ok` video, record the video again and delete the bad one.

That is 6 videos per session, 12 per person.

## File names
`P01_D1_squat_ok.mp4` = person code, day, exercise, `ok` or `fault`. Put them all in `data/raw/two-day/` (ignored by git). Never put
a name in a file name. Nothing is uploaded; delete the videos when the report is accepted, as the consent form says.

## Running the test
After **all** sessions, once:

```
py -3.14 ml\eval\two_day_eval.py
```

It checks the files first and says what is missing. Write the output into `docs/experiments.md` whatever it says.
