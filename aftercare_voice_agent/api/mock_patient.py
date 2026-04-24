"""Single canonical mock patient — Maria Santos.

The data here mirrors `agent/knowledge_base/*` so tool answers stay aligned
with what RAG would surface to the LLM. Production would load this from an
EHR FHIR feed; for the demo we hard-code one patient.

Times are LOCAL (patient's home time). The demo is "discharge day + 1".
"""

from __future__ import annotations

from typing import Literal, TypedDict


# ---- patient identity -------------------------------------------------------

PATIENT_ID = "maria-santos-mock-001"
PATIENT = {
    "patient_id": PATIENT_ID,
    "first_name": "Maria",
    "full_name": "Maria Santos",
    "age": 62,
    "sex": "F",
    "mrn_last4": "7142",
    "discharge_date": "2026-04-23",
    "primary_dx": "Acute decompensated heart failure (HFrEF, EF 35%)",
    "active_problems": [
        "CHF with reduced ejection fraction",
        "Hypertension",
        "Atrial fibrillation (anticoagulated)",
        "Stage 3a CKD",
    ],
    "lives_alone": True,
    "emergency_contact": {"name": "Elena Santos (daughter)", "phone_last4": "9821"},
}


# ---- medications ------------------------------------------------------------

MedStatus = Literal["taken", "missed", "skipped"]
QuestionType = Literal[
    "with_food",
    "if_missed",
    "side_effects",
    "interactions",
    "why_prescribed",
]


class MedSchedule(TypedDict):
    times: list[str]   # 24h "HH:MM" local
    with_food: str     # human-readable


class Medication(TypedDict):
    name: str
    canonical_name: str
    dose: str
    schedule: MedSchedule
    why_prescribed: str
    with_food: str
    if_missed: str
    side_effects_expected: str
    side_effects_call: str
    interactions: str
    aliases: list[str]   # for fuzzy match


MEDICATIONS: list[Medication] = [
    {
        "name": "Furosemide",
        "canonical_name": "furosemide",
        "dose": "40 mg",
        "schedule": {"times": ["08:00"], "with_food": "empty stomach"},
        "why_prescribed": (
            "It's a water pill. It pulls extra fluid off your heart and lungs so you can breathe easier."
        ),
        "with_food": (
            "Take it on an empty stomach, about thirty minutes before breakfast, with a small sip of water."
        ),
        "if_missed": (
            "If you remember before noon, take it. If it's after noon, skip it and take tomorrow's "
            "dose at the regular eight AM time. Do not double up — a late dose means bathroom trips all night."
        ),
        "side_effects_expected": (
            "More urination in the first two hours after the dose, mild thirst, sometimes mild leg cramps."
        ),
        "side_effects_call": (
            "Call if you feel dizzy when standing and it doesn't pass, if your urine output drops a lot, "
            "or if your heartbeat feels irregular."
        ),
        "interactions": (
            "Avoid ibuprofen, naproxen, Advil, Aleve, and Motrin — they reduce furosemide. "
            "No potassium supplements unless your doctor told you to."
        ),
        "aliases": ["furosemide", "lasix", "water pill", "diuretic", "the morning pill"],
    },
    {
        "name": "Lisinopril",
        "canonical_name": "lisinopril",
        "dose": "10 mg",
        "schedule": {"times": ["08:00"], "with_food": "either"},
        "why_prescribed": (
            "It lowers your blood pressure and protects your heart muscle while it heals."
        ),
        "with_food": "Either with or without food is fine. Take it at the same time as the furosemide.",
        "if_missed": (
            "If you remember within twelve hours, take it. After that, skip it and take tomorrow's "
            "dose at the regular eight AM time. Do not double up."
        ),
        "side_effects_expected": "A mild dry cough is common. Some patients feel a slight low-blood-pressure feel.",
        "side_effects_call": (
            "Call right away if your lips, tongue, or face swell, or if breathing becomes difficult — "
            "that needs nine-one-one. Also call if the cough is bad enough to keep you awake."
        ),
        "interactions": (
            "Avoid potassium supplements and salt substitutes — most contain potassium chloride. "
            "Avoid ibuprofen, naproxen, and similar pain pills."
        ),
        "aliases": ["lisinopril", "ace inhibitor", "blood pressure pill", "prinivil", "zestril"],
    },
    {
        "name": "Metoprolol succinate",
        "canonical_name": "metoprolol",
        "dose": "25 mg",
        "schedule": {"times": ["08:00", "18:00"], "with_food": "with food"},
        "why_prescribed": (
            "It's a beta blocker. It slows your heart so it can rest, and it controls your atrial fibrillation."
        ),
        "with_food": "Take it with breakfast and again with dinner. Food helps your stomach and slows absorption.",
        "if_missed": (
            "If you remember within four hours of the missed time, take it. After four hours, skip it "
            "and take the next dose at the normal time. Never double up."
        ),
        "side_effects_expected": "Mild tiredness, a slower pulse, and cold hands or feet are common.",
        "side_effects_call": (
            "Call if your pulse drops below fifty, if you feel like you might faint, if you start "
            "wheezing, or if your nightmares are bad enough to disrupt sleep."
        ),
        "interactions": (
            "Never stop this medicine suddenly — that can cause a rebound rise in your heart rate "
            "and blood pressure. If you want to stop, call your cardiologist first."
        ),
        "aliases": ["metoprolol", "metoprolol succinate", "toprol", "beta blocker", "the heart pill"],
    },
    {
        "name": "Warfarin",
        "canonical_name": "warfarin",
        "dose": "2.5 mg",
        "schedule": {"times": ["18:00"], "with_food": "with food"},
        "why_prescribed": (
            "It's a blood thinner. It prevents stroke from your atrial fibrillation."
        ),
        "with_food": "Take it with dinner. Same time every day matters more than the exact hour.",
        "if_missed": (
            "If you remember the same evening, take it. If you remember the next morning and it's "
            "within eight hours of the regular time, take it. Otherwise skip and take the regular "
            "evening dose. Never take both. Tell your care team at the next INR visit."
        ),
        "side_effects_expected": "Easier bruising than usual. Small cuts may bleed a little longer.",
        "side_effects_call": (
            "Call right away for any bleeding that won't stop, blood in your urine or stool, "
            "coughing up blood, severe headache, or large unexplained bruises."
        ),
        "interactions": (
            "No NSAIDs — that means no ibuprofen, no naproxen, no Advil, no Aleve, no Motrin, no aspirin. "
            "Acetaminophen — Tylenol — is your safe pain reliever, up to two grams a day. "
            "No alcohol at all. Keep leafy greens steady week to week — sudden changes shift your levels. "
            "No new supplements without checking with the care team."
        ),
        "aliases": ["warfarin", "coumadin", "blood thinner", "the evening pill"],
    },
]


# ---- labs -------------------------------------------------------------------


class LabResult(TypedDict):
    name: str
    canonical_name: str
    value: str
    range: str
    in_range: bool
    plain_english: str
    aliases: list[str]


LABS: list[LabResult] = [
    {
        "name": "INR",
        "canonical_name": "inr",
        "value": "2.6",
        "range": "2.0 to 3.0",
        "in_range": True,
        "plain_english": "Your blood-thinner level is right where it should be.",
        "aliases": ["inr", "pt/inr", "pt inr", "blood thinner level", "warfarin level"],
    },
    {
        "name": "Potassium",
        "canonical_name": "potassium",
        "value": "4.1 mmol/L",
        "range": "3.5 to 5.0",
        "in_range": True,
        "plain_english": "Your potassium level is normal. The diuretic can lower it, so we'll watch it.",
        "aliases": ["potassium", "k", "k+"],
    },
    {
        "name": "Sodium",
        "canonical_name": "sodium",
        "value": "138 mmol/L",
        "range": "135 to 145",
        "in_range": True,
        "plain_english": "Your sodium is normal.",
        "aliases": ["sodium", "na", "na+"],
    },
    {
        "name": "Creatinine",
        "canonical_name": "creatinine",
        "value": "1.3 mg/dL",
        "range": "0.6 to 1.1 (typical female)",
        "in_range": False,
        "plain_english": (
            "Your kidney number is slightly above the typical range — this is your usual baseline "
            "given your chronic kidney status. It is stable."
        ),
        "aliases": ["creatinine", "kidney", "kidney number", "kidney function"],
    },
    {
        "name": "BNP",
        "canonical_name": "bnp",
        "value": "410 pg/mL",
        "range": "under 100 in healthy patients",
        "in_range": False,
        "plain_english": (
            "Your heart-strain marker came down a lot during the hospital stay. We expect it to keep "
            "falling at home as the fluid balance settles. The trend matters more than the single number."
        ),
        "aliases": ["bnp", "heart marker", "heart strain marker"],
    },
    {
        "name": "Hemoglobin",
        "canonical_name": "hemoglobin",
        "value": "12.4 g/dL",
        "range": "12.0 to 16.0 (female)",
        "in_range": True,
        "plain_english": "Your blood count is normal.",
        "aliases": ["hemoglobin", "hgb", "hb", "blood count"],
    },
    {
        "name": "Glucose",
        "canonical_name": "glucose",
        "value": "102 mg/dL",
        "range": "70 to 140 (random)",
        "in_range": True,
        "plain_english": "Your blood sugar is normal.",
        "aliases": ["glucose", "blood sugar", "sugar"],
    },
]


# ---- follow-up plan ---------------------------------------------------------

FOLLOW_UP = {
    "appointments": [
        {
            "date": "2026-04-27",
            "time": "09:00",
            "type": "PT/INR lab",
            "location": "St. Vincent, second floor lab",
            "with": "outpatient lab",
            "fasting": False,
        },
        {
            "date": "2026-04-30",
            "time": "14:30",
            "type": "Cardiology follow-up",
            "location": "St. Vincent cardiology clinic",
            "with": "Dr. R. Okafor",
            "fasting": False,
        },
        {
            "date": "2026-05-07",
            "time": "10:00",
            "type": "Primary care follow-up",
            "location": "Patel clinic",
            "with": "Dr. K. Patel",
            "fasting": False,
        },
    ],
    "key_red_flag_to_remind": (
        "Weigh yourself the same time every morning. If you gain two pounds in a day "
        "or five in a week, call the on-call line."
    ),
    "on_call_line_last4": "1212",
}


# ---- lookup helpers ---------------------------------------------------------


def find_medication(name: str) -> Medication | None:
    """Case-insensitive fuzzy match across canonical name + aliases."""
    needle = name.strip().lower()
    if not needle:
        return None
    for med in MEDICATIONS:
        if needle == med["canonical_name"]:
            return med
        if any(needle == alias for alias in med["aliases"]):
            return med
    # contains-match fallback (e.g. "metoprolol succinate" → "metoprolol")
    for med in MEDICATIONS:
        if med["canonical_name"] in needle or needle in med["canonical_name"]:
            return med
        for alias in med["aliases"]:
            if alias in needle or needle in alias:
                return med
    return None


def find_lab(name: str) -> LabResult | None:
    needle = name.strip().lower()
    if not needle:
        return None
    for lab in LABS:
        if needle == lab["canonical_name"]:
            return lab
        if any(needle == alias for alias in lab["aliases"]):
            return lab
    for lab in LABS:
        if lab["canonical_name"] in needle or needle in lab["canonical_name"]:
            return lab
    return None
