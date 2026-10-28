# Requirements (traceability stub)

MoSCoW from the build brief. Implementation status starts at Task 0.

| ID | Priority | Statement | Status |
| --- | --- | --- | --- |
| F-ACC | M | Accounts, roles, consent | not started |
| F-ISO | S | Multi-clinic isolation | not started |
| F-LIB | M | Versioned Arabic exercise library + plan builder | not started |
| F-WIZ | M | Camera setup wizard | not started |
| F-POSE | M | On-device pose, angles, rep count, rule form checks with rule IDs | partial: local MediaPipe Lite overlay and test-only arm-raise counter connected to pose landmarks; mapping/thresholds are explicitly unverified; no form checks or coaching |
| F-CA | M | `cannot_assess` state | partial: configurable Python/browser landmark-visibility helpers and rule-evaluator abstention with reason codes; no pose/UI integration |
| F-RTA | M | Record-then-analyze summary | partial: local video inference shows an unsaved end-of-clip count/duration and optional difference from a manually entered reference; no session persistence, validated metrics, or form assessment |
| F-RT | S | Real-time cues | not started |
| F-SYM | S | Own-baseline / symmetry | not started |
| F-PAIN | M | Pain/difficulty check-ins + red-flag pathway | partial: configurable Arabic text normalization and lexicon/model OR escalation primitive; interactive UI only exposes a harmless test phrase, not a reviewed lexicon or actual check-in |
| F-NLP | S | Pain-diary NLP | not started |
| F-REC | S | Recall engine | not started |
| F-PHY | S | Physio portal, review-by-exception, rule sign-off, audit | not started |
| F-PRG | S | Progression recommender | not started |
| F-ENG | S/C | Engagement layer | not started |
| F-PDF | S | Progress PDF + consent-based sharing | not started |
| F-DEL | M | Export/delete | not started |
| F-CLF | S | Learned form classifier vs rules | not started |

Non-functional: safety, explainability (cue → rule ID + version), privacy, RBAC, Arabic RTL, offline queue — see `docs/AI_BRIEF.md`.
