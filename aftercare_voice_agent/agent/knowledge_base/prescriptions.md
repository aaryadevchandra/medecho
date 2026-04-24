# Prescriptions — Maria Santos

> **MOCK DATA.** Used only for grounding the demo agent. Not real medical guidance.

This file is the **single source of truth** for medication answers. If a question can be answered from here, the agent answers from here. If not, the agent escalates.

---

## 1. Furosemide 40 mg — oral tablet

- **Why prescribed:** Diuretic ("water pill"). Removes excess fluid that builds up in heart failure.
- **Schedule:** Once daily, **8:00 AM**, on an empty stomach (30 minutes before breakfast).
- **With food?** No — empty stomach for best absorption. Take with a small sip of water.
- **If a dose is missed:**
  - If remembered **before noon**: take it as soon as you remember.
  - If remembered **after noon**: skip it. Do **not** double up. Resume the normal 8 AM dose tomorrow. Why: a late-day diuretic disturbs sleep with overnight bathroom trips.
- **Common side effects to expect:** more urination (especially in the first 2 hours after the dose), mild thirst, occasional leg cramps.
- **Side effects to call about:** dizziness when standing that doesn't pass, muscle weakness, very dry mouth with little urination, irregular heartbeat.
- **Interactions / things to avoid:**
  - Avoid NSAIDs (ibuprofen, naproxen, Advil, Aleve, Motrin) — they reduce furosemide effectiveness.
  - Avoid potassium supplements unless prescribed.
  - Avoid licorice root.

---

## 2. Lisinopril 10 mg — oral tablet

- **Why prescribed:** ACE inhibitor. Lowers blood pressure and protects the heart muscle in heart failure.
- **Schedule:** Once daily, **8:00 AM**, with or without food. Take it at the same time as the furosemide for convenience.
- **With food?** Either is fine.
- **If a dose is missed:**
  - If remembered **within 12 hours**: take it as soon as you remember.
  - If remembered **after 12 hours**: skip it. Resume the normal 8 AM dose tomorrow. Do **not** double up.
- **Common side effects to expect:** mild dry cough (about 1 in 10 patients), slightly low blood pressure feel.
- **Side effects to call about:** swelling of the lips, tongue, or face (rare but serious — call 911), persistent cough that disrupts sleep, very low blood pressure (lightheaded all day).
- **Interactions / things to avoid:**
  - Avoid potassium supplements and salt substitutes (most contain potassium chloride).
  - Avoid NSAIDs.
  - Avoid grapefruit juice (mild interaction; safe in small amounts but ask).

---

## 3. Metoprolol succinate 25 mg (extended release) — oral tablet

- **Why prescribed:** Beta blocker. Slows the heart, helps the heart muscle recover, controls atrial fibrillation rate.
- **Schedule:** Twice daily, **8:00 AM and 6:00 PM**, **with food**.
- **With food?** Yes — take with breakfast and dinner to reduce stomach upset and slow absorption.
- **If a dose is missed:**
  - If remembered **within 4 hours** of the missed time: take it.
  - If remembered **after 4 hours**: skip it. Take the next dose at the normal time. Do **not** double up.
- **Common side effects to expect:** mild fatigue, slower pulse, cold hands or feet.
- **Side effects to call about:** pulse below 50, dizziness or fainting, wheezing, swelling of legs that is new, very vivid nightmares.
- **CRITICAL — never stop suddenly:** stopping metoprolol abruptly can cause a rebound rise in heart rate and blood pressure and increases the risk of a heart event. If she wants to stop or reduce, she must call her cardiologist first. The agent must escalate any "I want to stop my metoprolol" turn.
- **Interactions / things to avoid:**
  - Avoid NSAIDs (same reason as above).
  - Use caution with calcium channel blockers (not currently on the list, but flag if mentioned).

---

## 4. Warfarin 2.5 mg — oral tablet

- **Why prescribed:** Anticoagulant ("blood thinner"). Prevents stroke from atrial fibrillation.
- **Schedule:** Once daily, **6:00 PM**, with dinner. **Same time every day** — consistency matters more than the exact time.
- **With food?** Yes — take with dinner. Helps remember.
- **If a dose is missed:**
  - If remembered **the same evening or before bedtime**: take it.
  - If remembered **the next morning**: do **not** take both doses. Take the missed dose only if it is still within 8 hours; otherwise skip and take the regular evening dose. Tell the care team at the next INR visit.
- **Common side effects to expect:** easier bruising than usual, slightly longer bleeding from small cuts.
- **Side effects to call about IMMEDIATELY:** bleeding that won't stop, blood in urine or stool (red or black), coughing up blood, severe headache, large unexplained bruises, blood in vomit, heavy menstrual bleeding (not applicable here but listed for completeness).
- **Interactions / things to avoid — STRICT:**
  - **No NSAIDs.** No ibuprofen, no naproxen, no Advil, no Aleve, no Motrin, no aspirin (unless specifically prescribed by Dr. Okafor — it is not currently prescribed). Acetaminophen (Tylenol) is the safe pain reliever, **maximum 2 grams per day** while on warfarin.
  - **No alcohol.** Not even a glass of wine. Alcohol changes warfarin levels unpredictably.
  - **Vitamin K-rich foods (kale, spinach, collards, broccoli, brussels sprouts):** keep intake **consistent week to week**. Sudden large changes (going on a kale smoothie streak, or stopping leafy greens entirely) shift INR. Small, steady portions are fine.
  - **No new supplements without checking** — especially fish oil, vitamin E, ginkgo, garlic supplements, St. John's Wort.
  - **Antibiotics**: many antibiotics raise INR. If a new antibiotic is started by another provider, the care team must be told.
- **Lab schedule:** PT/INR on **2026-04-27 at 9:00 AM**. Target INR range **2.0 – 3.0**.

---

## Summary timing card (for `get_medications` tool)

| Time   | Medication              | Dose   | With food? |
|--------|-------------------------|--------|------------|
| 8:00 AM | Furosemide              | 40 mg  | Empty stomach |
| 8:00 AM | Lisinopril              | 10 mg  | Either |
| 8:00 AM | Metoprolol (AM dose)    | 25 mg  | With breakfast |
| 6:00 PM | Metoprolol (PM dose)    | 25 mg  | With dinner |
| 6:00 PM | Warfarin                | 2.5 mg | With dinner |

## Things explicitly NOT prescribed (do not "fill in" if patient asks)

- No daily aspirin
- No statin (none currently on list — patient was statin-intolerant in the past; do not assume one)
- No insulin or diabetes medication
- No opioid pain medication
- No sleep medication

If the patient mentions any of these or asks "can I take", the agent must escalate.
