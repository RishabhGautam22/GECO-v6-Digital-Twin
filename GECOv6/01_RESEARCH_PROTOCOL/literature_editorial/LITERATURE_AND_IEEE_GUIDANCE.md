# Literature position and IEEE guidance for GECOv6

Bounded update, checked 7 September 2026. This extends the prior GECOv5 evidence review; it is not a new systematic or exhaustive literature review. References R01-R12 are resolved in `SOURCE_LEDGER.json` and `references.bib`; carried-forward access limits remain explicit.

## The methods story

The question is whether a proposed monitor can distinguish an authorized delivery from the fluid reaching a defined outlet, and whether acting on that evidence improves outcomes under stated failures without unacceptable interruption of delivery. The scientific contribution must be the tested separation of command intent, emission, measurement and mitigation authority. Combining a twin, a Kalman filter and a reference monitor is not enough to establish novelty.

GlucOS already implements a BioKernel reference monitor and layered runtime safeguards for automated insulin delivery [R01]. KnowSafe already studies prediction and mitigation of controller-induced hazards and unintended consequences of mitigation [R02]. Low-flow insulin-pump calibration and Kalman-assisted pump metrology also predate this project [R03,R04]. These are limiting prior works, not merely background citations. No “first independent safety layer,” “first delivery verification,” “first digital-twin insulin security,” or “new because UKF replaces EKF” claim is justified.

**Candidate contribution, conditional on new results:** a reproducible investigation of how separately modeled delivery evidence and independently exercised stop authority change security outcomes, tested against a simpler monitor under the same authority, across more than one physiological model family, with a defined and uncertainty-aware physical measurement handoff. A negative or mixed result remains a legitimate methods result. Until independent physical records exist, the demonstrated scope is simulation; the rig is proposed hardware.

| Literature/technical boundary | Consequence for a defensible GECO paper |
|---|---|
| Reference monitoring already exists [R01] | Compare command enforcement with downstream delivery evidence; avoid novelty by renaming |
| Predictive hazard mitigation already exists [R02] | Measure unwanted stops, underdelivery and recovery as well as avoided excess |
| Discrete-dose calibration and sensor fusion already exist [R03,R04] | State the distinct adversarial/causal experiment and characterize the metrology rather than claiming mass sensing itself is novel |
| Hovorka is an established compartment model [R05] | Attribute equations/parameters precisely; a derived implementation is not the original validated system |
| Unscented filtering and adaptive insulin estimation are established [R06,R07] | Compare UKF/EKF under matched inputs, tuning and test partitions; do not predict which will win |
| UVA/Padova refinements have their own lineage [R08] | Name the precise model edition; approval/validation of one simulator does not transfer to a derivative or cybersecurity claim |

## Physiological model and estimator wording

Hovorka et al. (2004) developed nonlinear model-predictive control for fasting conditions; the original equations and parameter tables are an appropriate primary source for the new independent plant [R05]. The supplied original PDF was visually checked at printed page 909 (PDF page 5): Table 2 prints sensitivity means 51.2×10^-4 and 8.2×10^-4 min^-1 per mU L^-1 for transport/disposal, and 520×10^-4 per mU L^-1 for endogenous glucose production. These exponents are visible in the page image, not an OCR inference. Footnotes label the values as means for Bayesian estimation and define the sensitivity ratios k_b/k_a. `Hovorka2004_page909.png` is the inspection image. Any synthetic variation, clamping, unit conversion or equilibrium initialization belongs to GECO's implementation and must be documented separately.

Julier and Uhlmann's *Proceedings of the IEEE* paper is the foundational UKF citation [R06]; bibliographic identity was checked against publisher-deposited Crossref metadata. IEEE full text required a browser challenge and the institutional PDF fetch failed, so this pass does not claim a full reading. Hajizadeh et al. provide a directly accessible journal example using Hovorka dynamics and a UKF for personalized plasma-insulin estimation with clinical data [R07]. That supports relevance, not GECO accuracy or a universal UKF advantage. The 2016 EKF/UKF/particle-filter CGM-drift comparison (DOI 10.1109/EMBC.2016.7591484) is a conference paper, not a journal paper; its abstract is useful but is not a replacement for matched GECO comparisons.

A useful estimator comparison freezes observation data, command availability, forecast horizon, initial states, units, training/validation/test boundaries, noise tuning and missing-data behavior. Evaluate prediction error and uncertainty calibration on untouched data, then evaluate downstream monitoring outcomes separately. A filter cannot identify a coherent compromised history from identical available observations without additional assumptions or independent information. Higher forecast accuracy alone does not prove safer delivery.

## Physical measurement boundary

In software, latent emitted mass can drive the virtual physiological plant independently of the balance-report channel. A physical rig cannot read that latent variable. A validated estimate of delivered fluid, its time alignment and its uncertainty must be established before using it as virtual-patient input. A balance indication, camera image or positive-only difference of noisy readings is not automatically ground truth. Positive-only accumulation can introduce a zero-flow bias; the reference reconstruction must be tested explicitly. JCGM 100 supplies the uncertainty framework [R09]; it does not certify a particular bench. The proposed reference method, correction model and validation remain **IIT Patna measurement pending**.

## Current IEEE preparation guidance

IEEE's current author policy requires disclosure of generated content, identifying the AI system, affected sections and how it was used; editing/grammar-only assistance is treated differently [R10]. GECO assistance includes research synthesis, code, drafting and media, so an editing-only disclosure would be incomplete. Do not reuse the sample protocol's claim that all conceptual content/classification is exclusively the authors' own without verifying it. Bibliographic entries should be checked rather than freely rewritten by an editing pass.

IEEE authorship requires substantive intellectual contribution, drafting or intellectual revision, and approval of the final article [R11]. Author names, affiliations, ORCIDs, funding, conflicts and final approval remain team-supplied fields; the sample survey's author block is not evidence for this article. Use the official template selector and the intended publication's instructions once a venue is chosen [R12]. An IEEE-looking manuscript is a draft format, not an acceptance or certification claim.

Suggested working disclosure (team to confirm before submission): “OpenAI Codex assisted with literature organization, source checking, implementation drafting, figure and media preparation, and manuscript drafting and revision. The specific tool-assisted outputs and verification procedures are documented in the supplementary provenance record. [Team to specify the actual human review, corrections and final approval.] Synthetic narration is identified in the accompanying video.” Add actual model/version information only when exposed in the run record; do not invent it. This is a draft disclosure, not a statement that human verification has already occurred.
