# Red Flags — Maria Santos

> **MOCK DATA.** Used only for grounding the demo agent.

This file lists symptoms that change the conversation immediately. The agent uses this list to decide between **answer**, **escalate (high)**, and **escalate (critical / 911)**. There is no "wait and see" tier.

---

## CRITICAL — call `escalate_to_clinician(urgency: critical)` in the same turn

The agent must call the escalation tool before finishing its sentence. The tool's return value is the entire spoken response.

- Chest pain, chest pressure, chest tightness, jaw pain, arm pain
- Sudden shortness of breath, or shortness of breath worse than at discharge
- Coughing up pink frothy sputum (pulmonary edema)
- Fainting or passing out
- Slurred speech, drooping face, weakness on one side, sudden confusion (stroke signs)
- Heavy bleeding that won't stop after 10 minutes of pressure
- Vomiting blood, coughing up blood, blood in urine (visibly red), black tarry stool
- Severe headache that came on suddenly ("worst headache of my life")
- Suspected medication overdose (took double dose, took someone else's pills, can't remember if she dosed twice)
- Severe allergic reaction: swelling of face, lips, tongue; trouble breathing or swallowing; whole-body rash
- Suicidal statements or self-harm intent
- Heart rate sustained above 130 or below 40 at rest

If the patient is describing one of these in real time, the agent should also remind her to call **911** in addition to the escalation. The on-call nurse line is not a substitute for emergency services.

---

## HIGH — call `escalate_to_clinician(urgency: high)` in the same turn

These warrant a clinician callback within 15 minutes.

- Weight gain of **2 lb or more in one day** (CHF decompensation early sign)
- Swelling in legs/ankles **worse** than at discharge
- Shortness of breath **with exertion** that is new or worse than at discharge (but not severe at rest)
- Heart rate sustained between 110 and 130, or 40 to 50, at rest
- Dizziness when standing that lasts more than a minute, more than once today
- Easy bruising in many spots, small bleeds that take longer than usual to stop (warfarin watch)
- Fever above 100.4 °F (38 °C)
- Vomiting more than twice in 6 hours, or unable to keep medications down
- Diarrhea more than 3 times in 6 hours
- Sudden weight gain over a few days **with** new shortness of breath
- New rash that is spreading
- Headache that is unusual for her, even if not "the worst ever"
- Any fall, even if she feels fine

---

## MEDIUM — call `escalate_to_clinician(urgency: medium)` when the conversation hits a dead end

Use medium urgency when the question is reasonable but the bundle does not answer it. The patient is not in danger but should not be left without an answer.

- Question about a medication, lab, or test not in her bundle
- Question about an OTC drug, supplement, herb, or alcohol not covered in the bundle's interaction list
- Question about a family member's care
- Confusion about the discharge plan that the agent cannot resolve from the bundle alone
- Patient explicitly asks for a human

---

## What is **NOT** a red flag (agent answers from bundle, no escalation needed)

The agent should not over-escalate. These are normal expected experiences post-discharge for Maria's situation, and are answered from the bundle:

- More urination in the first 2 hours after furosemide (expected)
- Mild thirst on the diuretic
- Mild dry cough on lisinopril (about 1 in 10 patients; only escalate if disrupting sleep)
- Slight tiredness on metoprolol (expected)
- Cold hands and feet on metoprolol (expected)
- Easier-than-usual bruising on warfarin (expected; only escalate if many spots or bleeds that won't stop)
- Mild dizziness on standing the very first time after a dose (expected; escalate if it persists or recurs)
- Vivid dreams on metoprolol (expected; escalate if disrupting sleep significantly)

---

## Agent decision shortcut

Single rule the agent can apply:

> **"If she is describing a symptom and I am not 100% certain it is on the 'NOT a red flag' list above, escalate. The cost of one extra escalation is minutes of a nurse's time. The cost of missing a true red flag is a readmission or a death."**
