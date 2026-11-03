# Milestone 1 deck: review, fixes and Q&A prep

Reviewed: `Qawam_Milestone1.pdf` (33 slides, 2026-11-03). Every statistic was checked against its source or against this repo's `docs/`.

## 1. Must fix before presenting

| Slide | Problem | Fix |
| --- | --- | --- |
| 1, 30 | Placeholders left: `[Team member 2] · [ID]`, `[Dr. Name]`, `[Fall 2026]` | Fill them in, or remove the brackets |
| 2 | Lang et al. 2022 is cited on the slide but missing from References. The claim "benefit … fades once clinician contact stops" is not what the review says. | Add it to References. Reword: "Digital tools raise home-exercise adherence in the short term; long-term effects are uncertain (Lang et al. 2022)." |
| 4, 6 | "58.2% … technical issues": the survey's own item is **internet connectivity issues** (174/299). The abstract says "technical issues", but the table is more precise. | Write "internet connectivity issues". Cite as [7] with authors (see §3). |
| 5, 12 | Sword/Kaia, Limb, Eilaji and Rxmove are cited only as "public sources"; none is in References. "Limb launched … in 2026" is wrong: MBZUAI wrote about the app in Aug 2024, and 12 Oct 2026 is the Gulf News "last updated" date. | Add references [9]–[12]. Reword: "Limb (Abu Dhabi) gives Arabic spoken feedback (Gulf News, updated 12 Oct 2026)." |
| 8 | Status is out of date: PWA is listed as "Planned" (it is now built, on branch `feat/installable-pwa`), and pain notes as "Rule coded" (there are now 23 cited red-flag phrases with a stop prompt). | PWA: "Done (install + offline)" once merged. Pain notes: "Done (demo, cited list, not physio-reviewed)". |
| 13 | Card 03, "Phone placement, **tested on patients**", overclaims. No phone was used: Kinect skeletons were projected into simulated cameras, with no pose-model noise. | Retitle: "Phone placement, simulated on patient skeletons". |
| 22 | The REHAB24-6 squat AUC 0.79 is computed on **mocap ground truth**, not MediaPipe (`docs/experiments.md` calls it the "upper bound before pose-estimation noise"). REHAB26 pools 3 cameras × 11 orientations of the same reps. Slide 13 claims "squat and lunge", but lunge never appears on slide 22. | Label it "REHAB24-6 (mocap angles)". Add lunge 0.85, or change slide 13 to "squat". Footnote: "rep views are not independent; CIs resample people". |
| 23 | Header says "34 patients", but the squat AUC row uses 31 healthy vs 33 patients and the arm lift uses 32 vs 34. | Header: "KIMORE patients and healthy controls". Keep the "geometry study" footnote. |
| 25 | "Python 3.11": the repo and CI use **3.14**. "Playwright": no Playwright tests are committed (it appears only in `package-lock.json` and `architecture.md`). | Change to Python 3.14. Either commit the fake-camera E2E test or replace Playwright with "Vitest, pytest". |
| 32 | Refs [4], [5], [6], [8] are never cited on a slide by number. Slides cite "Černek 2024" and "PMC11804851" instead. [8] (Learn then Test) has no slide at all. | Use [n] on every slide. Cite [8] on slide 16 ("exact 95% bounds, LTT/fixed-sequence [8]") or drop it. |

## 2. Should improve

- **Slide 21:** "wrong cue" really means "angle error > 10°". Say that in the headline footnote, or examiners will ask what a wrong cue is. The two 95% figures (0.7–7.9% by person vs 7.8% exact) look like a typo. Keep one on the slide and the other in backup.
- **Slide 9:** ">30 fps on a Pixel 2" is the paper's headline figure. As I recall, the paper's table gives about 31 fps for the **Lite** model and about 10 fps for Full (not verified). You use Lite, so say "Lite".
- **Slide 12:** Add a "Price / who pays" or "Works offline" column; HomeRehab AI wins on offline, and that is easy to show.
- **Slide 24:** Expected outcomes are good. Add the false-cue target (≤ 10% per person, upper bound) so it links to O2.
- **Slide 31:** Add "Clinical values not physio-reviewed: demo defaults are literature-derived and labelled on screen" with the decision log as the mitigation.
- **Missing slides:** (a) a **live demo** slide with a QR code to the Pages URL; (b) **Ethics & privacy**: on-device video, PDPL Law 151/2020, MSA ethics before recording people; (c) a backup slide with the evidence-level table (default / dataset-derived / literature / clinician).
- **References to add for methods you name:** DTW (Sakoe & Chiba 1978), Bland–Altman (1986), ICC (Koo & Li 2016), SUS (Brooke 1996), Clopper–Pearson (1934).

## 3. Reference entries to add (verified)

- [7] O. I. Ali, O. M. Salem, S. A. A. Mohamed, S. A. H. Ali, E. A. Embaby, "Physiotherapy Professionals: A Questionnaire for the Evaluation of Telerehabilitation Services in Egypt," *Int. J. Telerehabilitation*, 16(2), e6654, 2025. doi:10.5195/ijt.2024.6654
- [9] S. Lang, C. McLelland, D. MacDonald, D. F. Hamilton, "Do digital interventions increase adherence to home exercise rehabilitation? A systematic review of randomised controlled trials," *Archives of Physiotherapy*, 12, 24, 2022. doi:10.1186/s40945-022-00148-z
- [10] Sword Health, "Sword acquires Kaia Health," press release, 28 Jan 2026. https://swordhealth.com/newsroom/sword-acquires-kaia-health ($285M).
- [11] Gulf News, "Abu Dhabi start-up revolutionizes physiotherapy with AI-powered home recovery solution," updated 12 Oct 2026; MBZUAI, "Going out on a limb," Aug 2024.
- [12] Eilaji (App Store id6478969747); Rxmove (App Store id6789929089), accessed Oct 2026.
- The demo-default sources (Hancock 2018, ACSM 2009, Namdari 2012, Rowe 2000, NHS) are in `rules/literature/demo-defaults.json`. Add them only if you show those values.

## 4. Rename to HomeRehab AI: every place in the deck

Find and replace "Qawam" on slides **1** (title, plus Arabic "قوام"), **12** (comparison table row), **15** ("Qawam study"), **17** ("Qawam API"), **18** ("Qawam web app") and **26** (Gantt row 0, "Qawam — home-physio coach"). Also rename the file, and check speaker notes and the Gantt source file.

The PPTX next to the PDF has only 23 slides, so it is an older version. Edit the 33-slide source the PDF was exported from.

## 5. Questions to expect, with answers

**Statistics and sources**
1. *Where do 2.41B and 1.71B come from?* Cieza et al., The Lancet 2020 (GBD 2019) [6]: 2.41 billion people with conditions that would benefit from rehabilitation; musculoskeletal disorders 1.71 billion, the largest group.
2. *Where does 85.3% come from, and how many people?* Ali et al. 2025 [7]: 299 of 306 Egyptian physiotherapists responded; 255 (85.3%) said telerehab would improve care. It is a self-reported convenience sample of physios, not patients.
3. *Is 59.9 / 58.2 one question?* It is a multi-select barrier item, so the two percentages overlap. 58.2% is "internet connectivity issues".
4. *Adherence claim: what does Lang 2022 show?* 10 RCTs, 1,117 participants; 7 of 10 favour adding a digital tool; the longer trials found no difference; low to moderate quality, no meta-analysis.
5. *Is the competitor table fair?* "Not reported" means no public claim was found, not "doesn't have it". Sources are [10]–[12].

**Method**
6. *What is a "wrong cue"?* A spoken cue on a rep whose MediaPipe angle is more than 10° from ground truth. The 10° is an engineering choice, not a clinical threshold.
7. *Why is 7/166 enough?* It isn't a final claim. It is 5 held-out people. We report the per-person interval (0.7–7.9%) and the worst person (10.8%), and the sealed test people 7 and 9 are untouched until `--final`.
8. *Reps aren't independent, so isn't the exact bound optimistic?* Yes. That is why the per-person interval is reported next to it (`docs/decisions.md`, 2026-11-02).
9. *Is the personal-reference AUC on the pose model or on mocap?* REHAB24-6 uses mocap angles (the upper bound). REHAB26 uses MediaPipe skeletons (0.93 squat). The reference comes from the same session, which is easier than clinic-to-home.
10. *Why DTW and not a learned model?* No per-patient training data; DTW needs one reference rep; it is explainable to a physio; and the learned confidence scores were unstable with 5 people (`experiments.md`).
11. *Where do 0.178 and 0.601 come from?* They are fitted on REHAB24-6 train and validation view labels (shoulder width ÷ torso length). They are research values from non-commercial data, to be re-derived from your own study before any paid use.
12. *Why Lite, not Full?* On these clips Lite had fewer wrong cues (4.2% vs 11.7%) and is faster on phones.
13. *KIMORE: did you test a phone on patients?* No. It is a geometry study: Kinect skeletons projected into simulated phone views, with no detector noise. The real-phone check is the goniometer study.
14. *Why 2D?* Monocular depth is unreliable. Each exercise declares a view in which its angle lies in the image plane, and the gate refuses other views.

**Clinical and safety**
15. *Who approved the thresholds?* Nobody yet. The demo defaults are from published sources (tolerance 14° from Hancock 2018, 8 reps from ACSM 2009, shoulder goals from Namdari 2012), each labelled on screen as not physio-reviewed. Only a named physiotherapist can mark a rule approved, and the code enforces this.
16. *What if the app misses a red flag?* The lexicon is high-recall and a model cannot suppress it. It shows a stop prompt and 123 and never dials. The phrase list is our translation and needs clinical review, and no notification reaches the physio yet.
17. *Is this a medical device?* It is positioned as exercise support under a physio's plan: no diagnosis and no outcome claims. Regulatory classification with the Egyptian Drug Authority is unverified, and that is a GP2 risk.
18. *Data protection?* Video never leaves the device; only metrics are synced, with consent. The PDPL (Law 151/2020) review is in the plan (task 9.4).

**Product and business**
19. *Why would clinics pay, and how much?* Not proven yet. That is why interviews, a price question and letters of intent come before the build (Gantt 5.1–5.3, with a go/no-go on 26 Nov).
20. *What stops Sword or Limb from copying you?* Measured trust (a certified false-cue rate), the clinic-recorded personal reference, Egyptian dialect, WhatsApp delivery, offline use on cheap phones, and our own Egyptian home-recording data.
21. *Why the name change?* Be ready with one sentence on why HomeRehab AI and what the Arabic name is.

**Engineering**
22. *What is actually built vs planned?* Built and tested: the browser coach, 5 packs, view gate, report, API core and the offline PWA. Planned for GP2: server, MongoDB and the physio portal. Have the live link ready.
23. *How is it tested?* 110 JS tests and 128 Python tests run in GitHub Actions CI, the sealed test split is logged, and the fake-camera end-to-end run is in `experiments.md`.
24. *How does it work offline?* The pose model and WASM are bundled, and the service worker caches them after the first visit.
25. *Two people: who did what?* Slide 30. Have a commit history ready if asked.

## 6. Discussion prep: data, models, and what we add over existing work

### The data

**Q: What data do you have, and how did you split it?**
Four public datasets and synthetic test fixtures; no real patient data.

| Dataset | People | What we use it for | Split |
| --- | --- | --- | --- |
| REHAB24-6 [4] | 10 healthy adults, 1,072 physio-labelled reps, 2 RGB cameras + motion capture | Angle error by camera view, the view gate, personal reference | By person: train 6 people (592 reps), validation 2 (238), test 2 (people 7 and 9, 242 reps) sealed; the code refuses to open them without `--final` and logs every access |
| REHAB26-ViewAngles [5] | 5, 3 cameras x 11 orientations, MediaPipe skeletons | Personal vs universal reference at every viewing angle | Leave-one-person-out |
| KIMORE [2] | 78 (34 patients) | Geometry check on patients: Kinect skeletons projected into simulated phones | Gate fitted on REHAB24-6, applied unchanged |
| UCOPhyRehab++ | 27, 1,837 reps scored 1-5 by a physiotherapist | External check of the rep counter and of score agreement | Nothing fitted on it |

**Q: Isn't 10 healthy people too few?**
Yes for a clinical claim, which we do not make. That is why every number is per person with a person-level interval, the worst person is reported (10.8%), results are repeated on three other datasets, and the goniometer study (20 volunteers) is in the plan.

### The models

**Q: What model did you train?**
We did not train a deep model, by choice. Pose comes from Google's pretrained **MediaPipe Pose Landmarker Lite** (BlazePose [1]), unchanged, running in the browser. What we fit is small and explainable:
1. two view thresholds (shoulder width / torso length: side <= 0.178, front >= 0.601), fitted on REHAB24-6 train + validation view labels;
2. a one-rep offset per session, calibrated on the physio-recorded reference rep;
3. the gate's certification: an exact binomial test (Learn-then-Test style [8]) that the wrong-cue rate is <= 10%.
The personal reference is dynamic time warping against one rep: no training at all.

**Q: Why not deep learning?**
(1) 10 people cannot train a model that generalises; (2) deep models collapse under the shift from lab 3D to phone 2D: Khanal & Zhou 2026 report 63.2% -> 1.6% accuracy, and even with uncertainty scores 99.6% of decisions were wrong at 50% coverage; (3) a physio must be able to see why a cue was given; (4) it must run offline on a cheap phone. We did test learned confidence scores: AUROC 0.79-0.80 vs 0.67 for visibility, but with 5 people their thresholds could not be certified, so the shipped gate uses the rule.

**Q: Why Lite and not Full?**
Measured: Lite gave fewer wrong cues on held-out people (4.2% vs 11.7%) and is faster on phones.

**Q: How did you test?**
Split by person, leave-one-person-out, sealed test people, exact 95% bounds and person-resampled intervals, and external datasets with nothing tuned on them. 131 Python and 110 JavaScript tests run in CI.

### How good is the contribution, compared with existing studies?

Say it as: *existing work makes the assessment more accurate; we make the feedback safe to trust, on one phone, and we measure how often it is wrong.*

| Study | What they show | What we add (measured) |
| --- | --- | --- |
| Khanghah et al. 2023 (Kinect, 3D CNN) | 83.8% accuracy, F1 60.6% across people; always answers; needs a depth sensor | Phone camera only; speaks on 26.5% of reps with 4.2% wrong (95% upper 7.8%) and stays silent on the rest |
| Jánošová et al. 2026 (REHAB26) | The right camera angle improves separability by 16.9% (offline) | We turn that into a live rule that enforces the view: wrong cues fall from 14.7% to 4.2% |
| Khanal & Zhou 2026 | Uncertainty scores do not make decisions safe | Same finding for visibility (it certifies nothing), so we bound the wrong-cue rate itself |
| BlazePose 2020 | Per-image keypoint accuracy | Angle error per view: leg abduction 43-48 deg off side-on, 4-9 deg facing; squat side view 3.1 deg after calibration |
| Liao et al. 2020, KIMORE 2019 | One model or template for everyone, offline | Personal reference: AUC 0.79-0.93 vs 0.53-0.69 universal on deliberate errors |
| Live RGB rep counter (Sci. Rep. 2025) | MAE 1.45 reps on KIMORE | MAE 0.56 reps on UCOPhyRehab++ (motion capture, different data: context, not a head-to-head) |
| Limb, Sword/Kaia | Products, no published wrong-cue rate | A published, per-person false-cue number |

In one search we found no study that puts a guaranteed bound on wrong cues for rehab exercise feedback. Say "we found none", not "none exists".

**Admit these before they are asked:**
- The personal reference catches deliberate errors, but on UCOPhyRehab++ no method (ours included) tracks graded quality (4 vs 5): Spearman 0.14-0.22. So the claim is "flags clear mistakes", not "grades like a physio".
- Mostly healthy adults; motion-capture results are upper bounds; no home phone study yet; no physio has approved a value.

### Making the niche sharper (from what the studies show)

1. **Lead with trust, as a number.** Nobody publishes how often their coach is wrong. Show the physio a weekly line: "41 cues spoken, estimated wrong-cue rate <= 8%". That is the edge, and it is measurable.
2. **Start with knee rehabilitation.** The data supports it: on UCOPhyRehab++ the counter is almost perfect on seated and supine knee exercises (error 0-0.2 reps), where one in-plane angle carries the movement. Post-surgery knee patients (knee replacement, ACL) are a clear group with a surgeon and a physio to refer them.
3. **Check the joint, not only the view.** Half the UCOPhyRehab++ exercises move a joint other than the one measured, and the app correctly refused to count them. Make it a setup rule: the reference rep must move the pack's angle by at least 10 deg, or the physio is told to pick another pack.
4. **Physio grades, the app flags.** Because no method grades 4 vs 5, keep review-by-exception: the app flags clear errors and range drops, and the physio judges quality. This is also the safer regulatory position.
5. **Own data is the moat, with a clean licence.** Most public data is non-commercial (REHAB24-6, Fit3D). Use CC BY sets (UCOPhyRehab++, IntelliRehabDS) for anything commercial, and collect Egyptian home recordings under consent; no public dataset covers them.
