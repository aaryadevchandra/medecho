# Lab Results — Maria Santos (discharge labs, 2026-04-23)

> **MOCK DATA.** Used only for grounding the demo agent.

The agent reads from this list when the patient asks about a lab. Each entry includes the value, the reference range from this hospital, and a one-line plain-English explanation. The agent does **not** interpret beyond what is here.

---

## INR (PT/INR — warfarin monitoring)

- **Value at discharge:** 2.6
- **Target range for Maria:** 2.0 – 3.0 (set by cardiology for atrial fibrillation on warfarin)
- **Plain-English read:** "Your blood-thinner level is right where it should be."
- **Status:** in range
- **Next check:** 2026-04-27 at 9:00 AM
- **If a future value is ABOVE 3.0:** escalate. Above-range INR means higher bleeding risk; the dose may need to be lowered by the care team.
- **If a future value is BELOW 2.0:** escalate. Below-range INR means stroke-protection is reduced.

## Potassium

- **Value at discharge:** 4.1 mmol/L
- **Reference range:** 3.5 – 5.0 mmol/L
- **Plain-English read:** "Your potassium level is normal. Diuretics can lower it, so we'll watch it."
- **Status:** in range
- **Why it matters here:** furosemide can lower potassium; lisinopril can raise it. The combined effect tends to balance for most patients but is monitored.

## Sodium

- **Value at discharge:** 138 mmol/L
- **Reference range:** 135 – 145 mmol/L
- **Plain-English read:** "Your sodium is normal."
- **Status:** in range

## Creatinine

- **Value at discharge:** 1.3 mg/dL
- **Reference range (female):** 0.6 – 1.1 mg/dL
- **Plain-English read:** "Your kidney number is slightly above the typical range — this is your usual baseline given your chronic kidney status. It is stable."
- **Status:** at known baseline (not new)
- **eGFR:** 48 mL/min/1.73m² — consistent with stage 3a CKD, stable

## BNP (heart-failure marker)

- **Value at discharge:** 410 pg/mL
- **Reference (rule-out heart failure):** under 100 pg/mL in healthy patients
- **Plain-English read:** "Your heart-strain marker came down a lot during the hospital stay. We expect it to keep falling at home as the fluid balance settles."
- **Status:** elevated but improved (admission value was 2,180)
- **Trend matters more than the single number** — the cardiologist will repeat this at the 2026-04-30 visit.

## Hemoglobin

- **Value at discharge:** 12.4 g/dL
- **Reference range (female):** 12.0 – 16.0 g/dL
- **Plain-English read:** "Your blood count is normal."
- **Status:** in range

## Glucose (random)

- **Value at discharge:** 102 mg/dL
- **Reference range:** 70 – 140 mg/dL (random)
- **Plain-English read:** "Your blood sugar is normal."
- **Status:** in range

---

## What the agent does when a patient asks about a lab not on this list

If the patient asks about a test that is not in this file (e.g., "what was my A1c?", "what about my liver?"), the tool returns `not_in_bundle: true` and the agent says:

> *"That test isn't in your discharge labs. Let me get a nurse to look it up for you."*

Then escalates with `urgency: medium`.
