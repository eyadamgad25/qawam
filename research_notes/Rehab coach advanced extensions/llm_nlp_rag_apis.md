# LLMs, NLP, RAG, speech and health APIs in physiotherapy / MSK rehabilitation (2023-2026): measured benefit and safety

Scope note: roughly 22 searches/fetches. Most findings come from search-result excerpts. Two papers were fetched in full (Fu et al. 2026; the CVPRW 2026 VLM action-quality paper). Where a number comes only from a snippet or a vendor/law-firm page, the bullet says so. Project context: Arabic-first (Egyptian dialect) offline PWA. Pose estimation and an on-device char n-gram red-flag check already exist. Own results: fine-tuned Arabic BERT did not beat char n-grams; Qwen2.5-7B zero-shot labeller kappa 0.52.

## 1. LLMs/RAG for exercise prescription, HEP generation, patient education, SOAP/progress notes

### Takeaway
LLM output for MSK exercise programs and patient education is rated "moderate-to-good" for information quality. Safety, contraindications and clinical correctness are mostly not measured, and readability is usually above patient level. The strongest measured benefit is in documentation drafting: hallucination around 1.5% per sentence in a large annotated study, and modest time savings in RCTs. Even there, time savings are smaller than marketing claims. For this project, the defensible uses are clinician-reviewed drafts, plus RAG restricted to physio-approved content. Autonomous prescription is not supported by the evidence.

### Cited Findings
**Exercise program generation**
- Fu et al., Healthcare (Basel) 2026;14(15):2389. GPT-3.5-turbo, GPT-4-turbo, GPT-4o and Claude-3-haiku generated programs for low back, neck and shoulder pain and hip/knee OA, across 3 scenarios (FAQ, post-diagnosis inquiry, 50 case analyses), giving 1,476 responses from 369 questions — [PMC13465567](https://pmc.ncbi.nlm.nih.gov/articles/PMC13465567/)
  - DISCERN scores: the abstract reports 55.60 ± 8.40 (range 26-68), but that figure is one doctor's ratings. The averaged human score on 123 programs was 50.48 ± 8.15. Agreement among the 5 experts was moderate (ICC 0.68), and human vs GPT-4o-as-rater ICC was 0.62 — [PMC13465567](https://pmc.ncbi.nlm.nih.gov/articles/PMC13465567/)
  - Safety and contraindications were **not quantified**, because DISCERN does not measure them. The authors' "without significant errors" is a qualitative impression. The study was English only, and most scoring was done by GPT-4o — [PMC13465567](https://pmc.ncbi.nlm.nih.gov/articles/PMC13465567/)
  - Prompting effect: no-prompt answers scored 2.38 DISCERN points above chain-of-thought and 2.06 above "identity" prompts. Readability was mean FKGL 7.30 and SMOG 10.11, above recommended patient reading levels — [PMC13465567](https://pmc.ncbi.nlm.nih.gov/articles/PMC13465567/)
- Clinician-directed approach (arXiv 2511.18274): therapists prescribed, and the LLM generated the intervention software. Instructions were delivered correctly in 397/398 cases, but hallucinated monitoring logic appeared in 2.5% (10/398) of instructions. The LLM was transcribing clinician prescriptions, not designing them — [arXiv 2511.18274](https://arxiv.org/html/2511.18274)
- MSK rehab knowledge tests: primary therapists averaged 76.9% accuracy, and the best LLM reached 85.8% (snippet). This measures knowledge, not program safety — [PMC12929487](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12929487/)
- A scoping review of LLMs in exercise and health coaching found evaluation methods heterogeneous and unstandardised — [PMC12520646](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12520646/)

**Patient education**
- Low back pain: answers to 25 questions were rated by a pain specialist, a pain fellow and an EM resident. Question phrasing significantly changed accuracy — [PMC12444463](https://pmc.ncbi.nlm.nih.gov/articles/PMC12444463/)
- LBP answers often exceeded the ≤6th-grade readability target for patient materials. Accuracy against guidelines was highest for treatment and self-management and lowest for risk factors (snippet) — [Frontiers Digital Health 2025](https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1618510/xml)
- ChatGPT-4.0 significantly outperformed 3.5 on LBP education. Both underperformed on psychosocial concerns such as anxiety and family support — [World Neurosurgery 2025](https://www.sciencedirect.com/science/article/pii/S1878875025001111)
- Accuracy and readability trade off for rotator-cuff education across chatbots (title-level evidence only) — [PMC12609729](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12609729/)

**RAG**
- JMIR AI 2025: a German orthopaedic/trauma patient-education RAG chatbot built on guidelines and patient leaflets. 30 human raters scored 12 answers. RAGAS on 100 synthetic queries gave faithfulness ~0.85 and contextual precision ~0.89. The authors say RAG reduces fabricated answers but "cannot eliminate them entirely" — [PMC12551339](https://pmc.ncbi.nlm.nih.gov/articles/PMC12551339/)
- ClinicBot (arXiv 2026) proposes guideline-typed retrieval ranked by clinical authority, with validation and verifiable citations. Results were not confirmed (abstract only) — [arXiv 2605.00846](https://arxiv.org/html/2605.00846)
- No physiotherapy-specific RAG study with hallucination metrics was found — search result summary of [PMC12551339](https://pmc.ncbi.nlm.nih.gov/articles/PMC12551339/) and related.

**SOAP / progress notes and ambient scribes**
- A clinical safety and hallucination framework: 12,999 clinician-annotated sentences across 18 configurations showed 1.47% hallucination and 3.45% omission rates, and iterative pipeline changes reduced both — [medRxiv 2024.09.12.24313556](https://www.medrxiv.org/content/10.1101/2024.09.12.24313556.full.pdf)
- TN-Eval (ACL Industry 2025), on SOAP-format therapy notes: therapist-written notes often lacked completeness, while LLM notes contained hallucinations. Therapists still preferred the LLM notes in a blind test. LLM-as-judge struggled to detect hallucinations — [ACL Anthology 2025.acl-industry.14](https://aclanthology.org/2025.acl-industry.14.pdf)
- A 2026 SOAP benchmark reports that reasoning modes "do not reliably improve and can substantially harm" SOAP note generation (snippet) — [arXiv 2605.24902](https://arxiv.org/html/2605.24902v2)
- Lukac et al. 2025 RCT: 238 physicians in 14 specialties were randomised to Microsoft DAX, Nabla or usual care (Nov 2024 - Jan 2025). Only Nabla reduced time-in-note, and either scribe gave modest burnout and task-load improvements. The trial was not pre-registered and was short — [PMC12265753](https://pmc.ncbi.nlm.nih.gov/articles/PMC12265753/)
- "Ambient AI Scribes in Clinical Practice": 16.0 fewer documentation minutes (95% CI 13.7-18.3). The search snippet suggests a difference-in-differences design, so check whether it was truly randomised — [PMC12768499](https://pmc.ncbi.nlm.nih.gov/articles/PMC12768499/)
- Secondary sources cite "40-60% reduction" in documentation time, which does not match the modest RCT effects. Treat it as marketing-grade — search summary for [PMC12265753](https://pmc.ncbi.nlm.nih.gov/articles/PMC12265753/)

### Inferences
- The best-evidenced LLM feature for the physio portal is a **draft SOAP/progress note** built from structured session data the app already has (reps, ROM from pose, pain scores, adherence, PROMs). The physio edits and signs it. Grounding the draft in structured data rather than free conversation should reduce hallucination, and claim-level grounding checks such as "each sentence cites a data field" are a known mitigation. Measure edit distance and time-to-sign against a manual baseline.
- Use LLMs to **draft or translate patient-education text** (Egyptian Arabic, readability target ≤ grade 6) that a physio approves once and that is then served statically and offline. This avoids runtime hallucination entirely and gets around the readability weakness documented above.
- RAG is useful when the corpus is the clinic's own approved exercise library and leaflets, with refusal when retrieval finds nothing. Faithfulness of ~0.85 means about 1 in 7 answers carries some unsupported content, which is not acceptable for unsupervised patient-facing clinical advice.
- Do not generate HEPs autonomously. At most, the LLM proposes from a physio-curated exercise library, and the physio approves.

### Gaps
- No study found that measured physio time saved by LLM HEP generation or SOAP drafting specifically in physiotherapy.
- No Arabic-language evaluation of LLM-generated exercise programs or physio notes was found.
- No contraindication or safety error rate for LLM-generated MSK programs was found.

## 2. Conversational / voice coaching: TTS/ASR quality for Egyptian Arabic, offline browser options

### Takeaway
Zero-shot Egyptian Arabic ASR is weak (Whisper-large-v3 about 48-50% WER). Fine-tuned Whisper models self-report about 18-23% WER, and cloud GPT-4o-transcribe reaches about 31%. Free-form patient speech recognition is therefore unreliable, but short-command recognition or pre-generated TTS cues are feasible. Egyptian TTS exists in Azure (2 neural voices). For offline use, cues should be pre-rendered audio files, and Whisper can run in-browser via transformers.js/WebGPU with tiny or base models.

### Cited Findings
- Almieyar multi-dialect benchmark (arXiv, 2026): Whisper-large-v3 scored ~48.9% WER on the Egyptian subset (another table gives 47.5%; the subset is only 0.7 h). GPT-4o-transcribe scored 30.6% and Voxtral 35.8% — [arXiv 2609.35564](https://arxiv.org/html/2609.35564v1)
- Egyptian ASR evaluation on 60 MGB-3 clips: Whisper-large-v3 had ~50.1% raw / ~36.3% normalised WER, Whisper-small 65.3% raw, and Jais-ASR the lowest at 38.76% raw (GitHub repo, not peer-reviewed) — [GitHub Saher-AI-ML](https://github.com/Saher-AI-ML/Egyptian-Arabic-ASR-Evaluation-and-Long-Form-Transcription)
- Fine-tuned Whisper-medium on ~72 h of Egyptian speech reports 18.03% validation WER (self-reported model card) — [HF MAdel121/whisper-medium-egy](https://huggingface.co/MAdel121/whisper-medium-egy). Fine-tuned Whisper-small reports ~22.7% test WER — [HF MAdel121/whisper-small-egyptian-arabic](https://huggingface.co/MAdel121/whisper-small-egyptian-arabic)
- On code-switched Egyptian-English (ArzEn-LLM), Whisper-medium reached 31.1 WER and Whisper-small 32.6 — [arXiv 2406.18120](https://arxiv.org/html/2406.18120v2.pdf)
- Other Arabic dialect ASR resources: Casablanca multidialect dataset [arXiv 2410.04527](https://arxiv.org/pdf/2410.04527); NADI 2025 ASR subtask [arXiv 2511.10090](https://arxiv.org/pdf/2511.10090); VoxArabica dialect-aware ASR [arXiv 2310.11069](https://arxiv.org/pdf/2310.11069)
- Azure officially lists 2 Egyptian Arabic neural voices, ar-EG-SalmaNeural (F) and ar-EG-ShakirNeural (M). A third-party page claims "55" ar-EG voices, which contradicts Microsoft's docs and is unreliable — [Microsoft Learn language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support); contradicted by [speechgen.io](https://speechgen.io/en/tts-arabic-egypt/)
- Transformers.js runs Whisper in-browser via the ASR pipeline with `device: "webgpu"` and falls back to WASM — [HF transformers.js WebGPU guide](https://huggingface.co/docs/transformers.js/en/guides/webgpu); demo: [xenova/whisper-web](https://github.com/xenova/whisper-web)
- Practical limits: use only tiny or base models for real-time use (whisper-base is ~200 MB). Input must be 16 kHz mono Float32, and the pipeline does not check the sample rate. Streaming needs a VAD gate such as Silero. The Web Speech API needs internet in some browser implementations (tutorial-level sources) — [LogRocket](https://blog.logrocket.com/how-to-build-a-real-time-voice-ai-agent-in-the-browser); [DEV tutorial](https://dev.to/proflead/real-time-audio-to-text-in-your-browser-whisper-webgpu-tutorial-j6d); [AssemblyAI blog](https://www.assemblyai.com/blog/offline-speech-recognition-whisper-browser-node-js)
- A posture-feedback prototype using Gemini 2.5 Flash for spoken feedback hit API rate limits that halted feedback, and the team switched to a local model — [ICDVRAT, AAU journals](https://journals.aau.dk/index.php/ICDVRAT/article/download/11716/9100)

### Inferences
- Real-time voice coaching ("lower your hip", "3 reps left") should use a fixed library of Egyptian Arabic phrases, pre-synthesised once (Azure Salma/Shakir or recorded by a native speaker) and cached in the PWA. That gives zero latency, works offline and cannot hallucinate. Pose rules choose which clip plays.
- ASR fits only a small closed vocabulary ("stop", "pain", "next", or a pain score 0-10). Whisper-tiny/base, which is weaker than large-v3, will do worse than the ~50% WER figure on dialect free speech. If voice pain reports are wanted, transcribe and then run the existing char n-gram red-flag check, and measure it on own recorded data before relying on it.
- Cloud LLM voice loops add latency and rate-limit risk, and break offline use. The Gemini rate-limit case shows this.

### Gaps
- No peer-reviewed study was found on the effect of real-time voice feedback on home-exercise outcomes or form error rates.
- No measured numbers were found for MMS, SeamlessM4T, Google Cloud Egyptian Arabic or Azure ASR on Egyptian Arabic in these searches. These models were not covered by the results.
- No quality scores (MOS) were found for Egyptian Arabic TTS voices.
- Web Speech API offline Arabic support per browser was not verified.

## 3. Multimodal LLMs judging exercise form from video or pose

### Takeaway
Current frontier VLMs (Gemini 3.1 Pro, Qwen3-VL-235B, InternVL3.5) judge movement quality only marginally above chance. Pose overlays do not fix this consistently. Pose-based rule or ML checks, which the project already has, remain the right tool, and LLMs at most turn structured pose metrics into wording.

### Cited Findings
- "Can Vision Language Models Judge Action Quality?" (CVPRW 2026) tested Gemini 3.1 Pro Preview, Qwen3-VL-235B (Instruct and Thinking) and InternVL3.5-241B on LLM-FMS, EgoExo-Fitness, Fitness-AQA, FineFS and MTL-AQA — [arXiv 2604.08294](https://arxiv.org/html/2604.08294v1); [CVF open access](https://openaccess.thecvf.com/content/CVPR2026W/SAUAFG/papers/Monte_e_Freitas_Can_Vision_Language_Models_Judge_Action_Quality_An_Empirical_Evaluation_CVPRW_2026_paper.pdf)
  - Balanced accuracy, with chance at about 0.50: best on Functional Movement Screen was 0.603 (Gemini; chance 0.431), best on EgoExo-Fitness 0.573 (Qwen3-VL), and Gemini 0.560 on Fitness-AQA squat/overhead press
  - Score regression: best Spearman ρ was about 0.26-0.28, and Gemini reached 0.058 on MTL-AQA
  - Skeleton overlays helped only sometimes. Skeleton-only renders pushed correlation to about zero or negative
  - The models tend to predict "correct execution" regardless of the visual evidence, and their outputs shift with superficial wording of the guidelines
- FormCoach (2025) evaluates VLMs, including Gemini 2.0, comparing user and reference videos on accuracy, actionability and hallucination. Scores were not retrieved — [arXiv 2508.07501](https://arxiv.org/html/2508.07501v2)
- Text-LLM prompting (zero-shot, few-shot, CoT) on pose features for rehab exercise quality and feedback, evaluated on UI-PRMD and REHAB24-6. Numbers were not retrieved — [arXiv 2505.18412](https://arxiv.org/pdf/2505.18412)
- GPT-4o grading video-recorded CPR showed error patterns complementary to human raters. The authors frame it as a "second reader", not a replacement — [PMC13301782](https://pmc.ncbi.nlm.nih.gov/articles/PMC13301782/)
- RehabGen (KAIST): an expert-in-the-loop VLM for contextualised rehab exercises — [KAIST pure](https://pure.kaist.ac.kr/en/publications/rehabgen-generative-expert-in-the-loop-vision-language-model-for-/)
- Single-phone markerless 3D pose showed good accuracy against mocap for squats and deadlifts — [Heliyon 2024](https://www.cell.com/heliyon/fulltext/S2405-8440(24)03627-2)

### Inferences
- Do not use a VLM as the form judge. The project's own pose-angle checks are more transparent, run offline and can be validated per exercise.
- A plausible, low-risk LLM use is turning pose-check outputs (structured: "knee valgus 12° on reps 3-5") into a weekly Egyptian Arabic summary for the patient, or a portal summary for the physio. Uploading video to a cloud VLM also creates biometric-data exposure under Egypt's PDPL (see section 8).

### Gaps
- No study was found on GPT-4o, Claude or Qwen-VL judging physiotherapy exercise videos of patients against clinician ratings.

## 4. Arabic medical NLP models and benchmarks 2024-2026

### Takeaway
On independent Arabic medical benchmarks, general frontier models (Gemini 1.5/2.5 Pro, GPT-4) beat dedicated Arabic medical LLMs (BiMediX2) and the Arabic-centric Jais. Benchmarks are mostly MSA exam or QA style. There is no Egyptian-dialect triage or red-flag benchmark. This fits the project's own finding that a small char n-gram model matched fine-tuned Arabic BERT on short dialect titles.

### Cited Findings
- BiMediX2 (Dec 2024) is a bilingual EN/AR medical LMM with BiMed-MBench (386 expert-verified queries). The authors claim it beats prior methods by >9% (EN) and >20% (AR), with an Arabic score of 50.47 vs 44.61 for the English-only variant (self-reported) — [arXiv 2412.07769](https://arxiv.org/html/2412.07769)
- MedArabiQ (PMLR 298, MLHC 2025) has 7 Arabic medical tasks (~700 samples: MCQ, fill-in, patient-doctor QA) and evaluated GPT-4, Gemini 1.5 Pro, DeepSeek-V3, Jais and others zero-shot with LLM-as-judge. Gemini 1.5 Pro was best overall, and Jais was best on BERTScore for dialogue but weak on exams. Model counts differ between versions (5 vs 8) — [PMLR v298](https://proceedings.mlr.press/v298/daoud25a.html); [arXiv 2505.03427](https://arxiv.org/html/2505.03427v2)
- In an ArabicNLP 2025 shared-task system paper, general models significantly outperformed specialised medical LLMs not optimised for Arabic. BiMediX2 "lagged general models". The best was Gemini 2.5 Pro at 78% dev and 74% blind test — [ACL Anthology 2025.arabicnlp-sharedtasks.20](https://aclanthology.org/2025.arabicnlp-sharedtasks.20.pdf)
- AraHealthQA 2025 was the first Arabic health QA shared task at ArabicNLP/EMNLP 2025. Track 1 is MentalQA and Track 2 is MedArabiQ (500 QA pairs, multiple specialties). Leaderboard numbers were not retrieved — [arXiv 2508.20047](https://arxiv.org/html/2508.20047v3)
- An Arabic healthcare reasoning benchmark (2025) also exists — [arXiv 2508.15797](https://arxiv.org/html/2508.15797)

### Inferences
- For the red-flag check, keep the char n-gram model (offline, auditable). Use a frontier LLM only offline at development time, as a second labeller whose labels are adjudicated by a physio. The project's kappa of 0.52 for Qwen2.5-7B is consistent with smaller and specialised models lagging. A larger model (e.g., Gemini 2.5 Pro class) may label better but must pass the same gate against blind physio labels.
- Arabic medical LLM leaderboards (MSA exam QA) do not transfer to Egyptian-dialect symptom text. Any model choice needs project-specific blind evaluation.

### Gaps
- No Egyptian-dialect medical triage or red-flag dataset or shared task was found.
- Apollo and Meditron Arabic performance was not covered by these results.
- AraBERT variant comparisons for symptom detection in 2024-2026 were not found in these searches.

## 5. Interoperability: HL7 FHIR for rehab, SMART on FHIR, Egypt UHI digitalisation

### Takeaway
The HL7 Physical Activity IG (STU1, FHIR R4) already models exercise prescription with CarePlan, Observation, Goal, QuestionnaireResponse and ServiceRequest, including a rehab-referral scenario. That makes it a ready template for exporting the app's plans, sessions and PROMs. Egypt's UHI is digitising facilities with unified EMRs, but no public FHIR API for third-party apps was found.

### Cited Findings
- The HL7 Physical Activity IG (US realm, STU1 v1.0.0 on FHIR R4; build v1.0.1) uses CarePlan for "planned approaches to help the patient become more physically active" and Observation profiles for days/week, minutes/day and minutes/week. It also uses QuestionnaireResponse, with an example of a patient reporting discomfort during shoulder exercises — [HL7 PA IG](https://hl7.org/fhir/us/physical-activity/); [Artifacts](https://hl7.org/fhir/us/physical-activity/STU1/artifacts.html)
- IG Scenario 1 covers exercise prescription, and another scenario covers post-rehab referral to a trainer with updated care plans, goals and surveys. Questionnaires use SDC profiles — [Scenario 1](https://build.fhir.org/ig/HL7/physical-activity/branches/master/ExampleScenario-Scen1ExercisePrescriptionScenario.html); [Scenarios](https://build.fhir.org/ig/HL7/physical-activity/branches/master/scenarios.html)
- India's ABDM IG defines its own PhysicalActivity Observation profile, an example of a national IG deriving from base resources — [NRCES ABDM](https://nrces.in/ndhm/fhir/r4/StructureDefinition-ObservationPhysicalActivity.html)
- Egypt Healthcare Authority: its HIS is deployed in 265 primary care units and 166 hospital departments across 6 governorates, with a Minya pilot of 14 facilities for UHIS phase 2 and unified EMRs planned for phase-2 governorates — [Ahram Online](https://english.ahram.org.eg/News/573309.aspx)
- UHIS phase 1 covered 6 governorates (Aswan fully launched July 2025). Phase 2 adds Matrouh, Damietta, Kafr El-Sheikh and North Sinai. The National Digital Health Strategy 2025-2029 targets EMRs for all citizens — [Ahram Online](https://english.ahram.org.eg/News/576202.aspx); [Egyptian Gazette](https://egyptian-gazette.com/egypt/egypts-healthcare-journey-towards-universal-access-global-collaboration/)
- IQVIA says it supported the nationwide CMP EMR implementation with EHA (corporate blog) — [IQVIA 2026](https://www.iqvia.com/locations/middle-east-and-africa/blogs/2026/07/public-private-partnerships). Opportunity for private providers: [IFC 2025](https://www.ifc.org/en/insights-reports/2025/the-uhc-opportunity-for-private-healthcare-providers-in-egypt)
- WHO UHC monitoring notes that Egypt piloted standard medical records and EMR systems — [WHO extranet](https://extranet.who.int/uhcpartnershiplivemonitoring/activity/egypt-standard-medical-records-and-electronic-medical-records-systems-are-piloted)

### Inferences
- A low-cost, high-value step is to store the portal's data in FHIR-shaped JSON: CarePlan (HEP), Observation (reps, ROM, NPRS), QuestionnaireResponse (KOOS/ODI), and Communication or Flag for red-flag alerts. Offer FHIR export now and SMART on FHIR launch later, if a partner EHR exposes one. No integration exists to build against today.
- The 6.7M EMR / 85% figures for Egypt come from a LinkedIn post and should not be cited.

### Gaps
- No public FHIR API or interoperability spec was found for Egypt's UHI or EHA systems.
- SMART on FHIR adoption in Egypt was not found.
- An HL7 rehab-specific IG beyond Physical Activity was not checked.

## 6. Messaging APIs (WhatsApp/SMS) for adherence reminders

### Takeaway
The best RCT evidence (ADHERE, knee OA, n=110, 24 weeks) shows behaviour-change SMS **increases self-reported home-exercise adherence but not clinical outcomes**. No WhatsApp-specific home-exercise RCT was found.

### Cited Findings
- ADHERE RCT: 110 people with knee OA and obesity (56 SMS vs 54 no SMS) did a physio-prescribed HEP 3×/week for 24 weeks. Behaviour-change SMS increased self-reported adherence but did not improve clinical outcomes — [JMIR mHealth 2020, PMC7551110](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7551110/); protocol [BMC MSK 2019](https://bmcmusculoskeletdisord.biomedcentral.com/articles/10.1186/s12891-019-2801-z)
- The SMS content was designed with the Behaviour Change Wheel — [JMIR mHealth 2019 e14619](https://mhealth.jmir.org/2019/10/e14619/)
- Before ADHERE, SMS for knee-OA home exercise had only 3 pilot or feasibility studies — summary of [PMC6745064](https://pmc.ncbi.nlm.nih.gov/articles/PMC6745064/)
- A post-MI pilot RCT (n=50) used 4 daily texts on medication and exercise — [PMC5561384](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5561384/)

### Inferences
- Reminders are worth building because they are cheap and adherence is a valid process metric. Do not claim outcome benefit. Measure objective adherence (sessions completed in-app, which is better than self-report) with an A/B or stepped rollout.
- In Egypt, WhatsApp is the likely channel. The WhatsApp Business Platform needs pre-approved message templates and opt-in, and costs money per conversation (not verified here). A free offline-first alternative is PWA Web Push plus local notifications.
- LLM-personalised reminder text has no evidence of benefit over fixed behaviour-change templates. Fixed, physio-approved Egyptian Arabic templates are enough.

### Gaps
- No WhatsApp-specific RCT for physio home-exercise adherence was found.
- WhatsApp Business API pricing and template rules for Egypt in 2026 were not verified.
- No Egypt or MENA reminder-adherence study was found.

## 7. Patient-reported outcome measures with validated Arabic versions

### Takeaway
Arabic ODI versions are validated (Tunisian base, adapted for Saudi Arabia and the UAE, ICC 0.99 intra-observer). Several other MSK instruments have Arabic validations (Modified LBP Disability Questionnaire, Functional Rating Index, FIHOA). This search did not confirm adult Arabic KOOS, Arabic PSFS or Egyptian-specific versions. Each needs a targeted check before the app ships them.

### Cited Findings
- Arabic ODI (Tunisian version) was validated in Saudi Arabia, with validity r ≈ 0.7 and intra-observer ICC 0.99 — [ResearchGate](https://www.researchgate.net/publication/264546333_Validation_of_an_Arabic_version_of_the_Oswestry_index_in_Saudi_Arabia)
- UAE adaptation of the Tunisian Arabic ODI: reliability and construct validity in 108 LBP patients — [Stellenbosch scholar](https://scholar.sun.ac.za/handle/10019.1/2402)
- Arabic Modified Low Back Pain Disability Questionnaire: cross-cultural adaptation and psychometrics — [ResearchGate](https://www.researchgate.net/publication/340516687_Cross-cultural_adaptation_and_psychometric_testing_of_the_Arabic_version_of_the_Modified_Low_Back_Pain_Disability_Questionnaire)
- Arabic Functional Rating Index (neck/back), with PSFS used as a comparator — [PMC9246610](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9246610/)
- Arabic FIHOA (hand OA) — [PMC7305589](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7305589/)
- Moroccan-dialect KOOS-Child (paediatric, not adult KOOS) — [PMC10758221](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10758221/)

### Inferences
- Ship ODI (Arabic) and NPRS (0-10, numeric, near language-independent) first. KOOS/PSFS should wait until their Arabic validation papers and licences are confirmed. KOOS licensing is through koos.nu and is free for non-commercial use (not verified here).
- Collect PROMs as FHIR QuestionnaireResponse. Score them deterministically in code; never use an LLM to score.
- Linguistic validation applies to MSA or the regional version. Rewording into Egyptian dialect, including by an LLM, invalidates the psychometrics.

### Gaps
- Adult Arabic KOOS and Arabic PSFS validation studies were not found in this search, though they may exist. A targeted search is needed.
- NPRS Arabic validation was not checked.
- No Egyptian-specific validation was found for any of these instruments.

## 8. Safety / regulatory: WHO LMM guidance, FDA, EU AI Act, Egypt PDPL 151/2020

### Takeaway
WHO (Jan 2024) gives more than 40 recommendations and warns specifically about automation bias. FDA's Jan 2026 CDS and general-wellness revisions loosen some lines but keep patient-facing CDS under device policy. Under the EU AI Act, AI in MDR Class IIa+ devices is high-risk, with obligations postponed to Aug 2028. Egypt's PDPL treats health and biometric data as sensitive, with executive regulations from Nov 2025 and compliance due around 31 Oct / 1 Nov 2026, so now in force. Cross-border transfer limits matter for cloud LLM and ASR calls.

### Cited Findings
- WHO "Ethics and governance of AI for health: Guidance on large multi-modal models" (Jan 2024): 40+ recommendations for governments, developers and providers, and 5 application areas including clinical care and patient-guided use. It warns of automation bias, urges a regulator to approve LMMs for health use, and calls for independent post-release audits disaggregated by user characteristics — [WHO IRIS](https://iris.who.int/server/api/core/bitstreams/e9e62c65-6045-481e-bd04-20e206bc5039/content); [Baker McKenzie summary](https://healthcarelifesciences.bakermckenzie.com/2024/01/30/healthcare-and-ai-who-releases-ai-guidance-for-large-multi-modal-models/)
- FDA draft guidance "AI-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations" (7 Jan 2025) covers the total product lifecycle, transparency and bias. It does not address generative AI specifically. Finalisation status was not confirmed — [Federal Register](https://www.federalregister.gov/documents/2025/01/07/2024-31543/artificial-intelligence-enabled-device-software-functions-lifecycle-management-and-marketing); [DLA Piper](https://www.dlapiper.com/en/insights/publications/2025/01/fda-issues-artificial-intelligence-enabled-device-software-functions-guidance)
- FDA Jan 6 2026 revised final CDS and General Wellness guidances, issued without public comment:
  - Enforcement discretion now covers CDS giving a single recommendation to an HCP when that is the only clinically appropriate option
  - Most of the "time-critical = device" language was removed
  - Wellness scope expanded
  - Patient-facing CDS still falls under the Device Software Functions / Mobile Medical Apps policy
  - No LLM-specific provisions
  — [DLA Piper 2026](https://www.dlapiper.com/en/insights/publications/2026/01/fda-updates-its-clinical-decision-support-and-general-wellness-guidances-key-points); [King & Spalding](https://www.kslaw.com/insights/articles/fda-updates-general-wellness-and-clinical-decision-support-guidance-documents); [Ropes & Gray](https://www.ropesgray.com/en/insights/alerts/2026/01/fda-adapts-with-the-times-on-digital-health-updated-guidances-on-general-wellness-products)
- EU AI Act: an AI medical device is high-risk when it is itself, or a safety component of, a device that needs notified-body assessment, which in practice means MDR Class IIa/IIb/III. Obligations layer on top of the MDR. The Digital Omnibus postpones medical-device high-risk obligations to Aug 2028 (secondary sources) — [regulatoryai.eu](https://www.regulatoryai.eu/ai-medical-devices/); [RAPS](https://www.raps.org/resource/eu-commission-drafts-guidelines-on-classifying-high-risk-systems-under-the-ai-act.html)
- Egypt PDPL 151/2020:
  - "Sensitive personal data" includes physical and mental health, genetic, biometric and financial data, and all children's data (per one guide) — [Law text (ACC)](https://www.acc.com/sites/default/files/program-materials/upload/Data%20Protection%20Law%20-%20Egypt%20-%20EN%20-%20MBH.PDF)
  - Executive Regulations are Ministerial Decree 816/2025, dated 1 Nov 2025 and published 25 Dec 2025 — [Shalakany](https://shalakany.com/wp-content/uploads/2025/12/New-Executive-Regulations-for-Egypts-Personal-Data-Protection-Law-.pdf); [Shehata & Partners](https://shehatalaw.com/wp-content/uploads/2026/01/Shehata-Partners-Publications-Data-Protection-Executive-Regulations-English.pdf)
  - Cross-border transfer is prohibited unless the destination's protection is not lower than Egypt's and the PDPC has licensed it — [recordinglaw.com](https://www.recordinglaw.com/world-laws/world-data-privacy-laws/egypt-data-privacy-laws/)
  - Sources disagree on the compliance deadline: 31 Oct 2026 per [e-cens](https://e-cens.com/blog/egypt-data-protection-law-compliance-guide/) vs 1 Nov 2026 per another summary. Either way the deadline has now passed (today is 26 Nov 2026)
  - One source says Egypt lacks GDPR-style vital-interest and public-health exemptions, which makes health processing narrower — summary of [nhimg.org](https://nhimg.org/egypt-personal-data-protection-law-guide) (secondary, conflicting with another guide's Article 15 reading)

### Inferences
- The offline/on-device design (pose, red-flag n-gram, cached TTS) is a regulatory asset. No health or biometric data leaves Egypt for these features. Any cloud LLM or ASR call carrying patient text or voice is a cross-border transfer of sensitive data and needs a PDPC licence and explicit consent, or should be avoided. Physio-side drafting with de-identified structured data reduces this exposure.
- Keeping a physio as the decision-maker addresses WHO's automation-bias concern and puts the product closer to the "HCP-facing CDS" side under the FDA framing. The red-flag check is patient-facing and triage-like, which is closer to device territory in the US and EU. Wording such as "contact your physio / seek urgent care" and a physio review queue are the mitigations.
- Log every LLM draft and the physio's edits. This supports WHO-style auditing and gives the measurement data (edit rate, time saved).

### Gaps
- No official Egyptian guidance on AI or LLMs in healthcare, or on SaMD registration with the Egyptian Drug Authority, was found in these searches.
- Whether the Jan 2025 FDA AI-enabled device draft has been finalised was not checked.
- The official Gazette text of the Egypt Executive Regulations was not read. All PDPL points come from law-firm summaries.
