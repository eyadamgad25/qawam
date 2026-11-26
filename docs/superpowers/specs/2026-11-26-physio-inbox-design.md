# Physio inbox: Arabic NLP, retrieval and a drafted reply the physiotherapist approves

Date 2026-11-26. Chosen by the project owner from four directions (NLP model, RAG inbox, FHIR export, WhatsApp API), as
the one that uses NLP, retrieval-augmented generation (RAG), an LLM API and Kaggle's graphics card in a single feature.

## Why
Patients write short notes between visits ("ركبتي بتوجعني بعد التمرين"). Today the app only checks them for warning signs.
The physiotherapist still has to read every note, find what it is about and write a reply. The feature saves that time
**without ever answering a patient on its own**, which keeps the project's rule: the physiotherapist decides.

## Goals
1. Route each note to a body area and topic.
2. Show the physiotherapist similar past questions and the clinic's own approved material.
3. Draft a reply in Egyptian Arabic that uses only the approved material, with a source for each sentence.
4. Measure each step on data the system never saw, with the pass rule written before the test.

## Non-goals
No reply reaches a patient without a physiotherapist pressing send. No diagnosis, no new exercise, no dose. No patient
chat. No training on patients' notes.

## Anti-goals (a failure even if it works)
- A draft that sounds confident but rests on nothing approved.
- A warning-sign note that gets a friendly draft instead of the stop prompt.
- Patient text sent to an outside service without consent.

## How it works

```
patient note (phone)
  │ 1. warning-sign check on the phone (exists). Red flag → stop prompt; no draft, ever
  │ 2. synced only with consent (extends the existing upload; the server refuses unknown fields today)
  ▼
server, "inbox" module (api/src, GP2)
  3. route: body area and topic (classifier)
  4. retrieve: top 5 from
       a. clinic-approved material: exercise packs, cue texts, leaflets a named physio approved   ← may be cited
       b. similar public questions (Shifaa, Apache 2.0), labelled "similar question, not advice" ← shown, never cited
  5. draft with an LLM through its API, from (a) only, every sentence tagged with its source id
  6. verify, in code, before showing: every sentence has a source; every number and exercise name appears in that
     source; no dose, diagnosis or emergency wording; otherwise "no safe draft"
  ▼
physio portal: note, route, sources, draft → edit → send (WhatsApp link) → audit log
```

The LLM is replaceable and only writes; code decides what may be shown. Without consent or without a network the inbox
still routes and retrieves on the server, with no draft.

## Built in which semester
- **Now (GP1, research):** `ml/rag/` in Python: the index, retrievers, routing classifier, draft and verifier, run as a
  command-line demo on public data and invented notes, with tests and evaluation. A Kaggle notebook for the graphics-card parts.
- **GP2 (product):** the `inbox` module in `api/src` behind the existing access rules (clinic, role, assignment), the
  physio portal screen, consent for notes, and audit.

## Models (each compared with a plain baseline; the simpler one wins a tie)
| Step | Baseline (measured) | Candidates | Where it runs |
| --- | --- | --- | --- |
| Retrieve | character n-grams: top-1 same specialty 0.571, top-5 same diagnosis 0.494 (chance 0.104; 576 diagnoses) | multilingual-e5, BGE-M3, then a reranker | embeddings on Kaggle's graphics card; search on a laptop or server |
| Route | n-gram logistic regression | MARBERT fine-tuned on Shifaa diagnoses | training on Kaggle; small model in production |
| Draft | fixed templates per topic | an LLM through its API | server only, with consent |

## Pass rules, written before any new score
- **Retrieval:** queries = titles with odd consultation numbers, never seen by any model; ship an embedding model only if
  top-5 same diagnosis beats 0.494 by at least 0.05 with a 95% interval above 0, measured once.
- **Routing:** macro-F1 on the same held-out titles; MARBERT is used only if it beats the n-gram model by 0.05 and its
  served size and speed fit the server.
- **Drafts:** on 60 invented notes written before building (20 ordinary, 20 out of scope, 20 warning signs):
  100% of warning-sign notes get no draft; at least 90% of shown drafts pass the verifier; every shown sentence traceable to
  an approved source. The physiotherapist's edit rate is measured later, in the pilot.

## Data and privacy
- Shifaa stays out of git. Its doctors' answers are not physiotherapy advice, so they are never cited or shown as advice.
- The approved material starts empty: a draft is impossible until a named physiotherapist approves at least one source.
  Until then the inbox routes and retrieves only.
- LLM calls: server-side key, no patient name, consent recorded, provider's data retention checked before any real use.

## Approaches considered
1. **Inbox for the physiotherapist (chosen):** useful, measurable, keeps a human in charge.
2. **A chatbot for patients:** most visible, but it would give advice nobody checked; rejected for safety.
3. **Classifier only:** safe and simple, but too small to show retrieval or generation.

## Left to the builder
Chunking of approved leaflets, the reranker choice, prompt wording, and the verifier's exact rules, all within the rules above.
