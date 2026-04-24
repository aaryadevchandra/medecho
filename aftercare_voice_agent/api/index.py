"""Aftercare voice-copilot backend.

Exposes 7 tool endpoints reachable from the browser via @elevenlabs/react
client tools. Default port 8002.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env then .env.local so NEXT_PUBLIC_AGENT_ID, written by setup_agent.py,
# is available to /config.json without a separate process.
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT.parent / ".env")
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / ".env.local", override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.mock_patient import (
    FOLLOW_UP,
    MEDICATIONS,
    PATIENT,
    PATIENT_ID,
    find_lab,
    find_medication,
)
from api.store import store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("aftercare")

app = FastAPI(title="Aftercare voice copilot backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- shared types -----------------------------------------------------------


class ToolReply(BaseModel):
    """Every tool returns the same envelope. `spoken` is what the LLM should
    say verbatim (or near-verbatim) — keeping it a real sentence prevents the
    LLM from improvising clinical advice when the tool seemed to fail."""

    spoken: str = Field(..., description="Natural-language response the agent should speak.")
    data: dict[str, Any] = Field(default_factory=dict)
    not_in_bundle: bool = Field(
        default=False,
        description="True when the question landed outside the patient's discharge bundle.",
    )
    escalate: bool = Field(
        default=False,
        description="True when the agent must call escalate_to_clinician next.",
    )


def _now_iso() -> str:
    # Local time (no tz). All demo timestamps are patient-local; UTC produced
    # cross-day-boundary mismatches against check_adherence's local-time read.
    return datetime.now().isoformat()


# ---- 1. get_medications -----------------------------------------------------


class GetMedicationsRequest(BaseModel):
    patient_id: str | None = Field(default=None, description="Optional override; defaults to demo patient.")


@app.post("/tools/get_medications", response_model=ToolReply)
def get_medications(_: GetMedicationsRequest) -> ToolReply:
    by_time: dict[str, list[str]] = {}
    for med in MEDICATIONS:
        for t in med["schedule"]["times"]:
            by_time.setdefault(t, []).append(f"{med['name']} {med['dose']}")
    morning = by_time.get("08:00", [])
    evening = by_time.get("18:00", [])
    spoken = (
        f"You're on four medications, {PATIENT['first_name']}. "
        f"In the morning at eight: {len(morning)} pills. "
        f"In the evening at six with dinner: {len(evening)} pills. "
        "Want me to walk through them one at a time?"
    )
    return ToolReply(
        spoken=spoken,
        data={
            "patient": {"first_name": PATIENT["first_name"], "patient_id": PATIENT_ID},
            "schedule": [
                {
                    "name": med["name"],
                    "dose": med["dose"],
                    "times": med["schedule"]["times"],
                    "with_food": med["schedule"]["with_food"],
                }
                for med in MEDICATIONS
            ],
        },
    )


# ---- 2. get_medication_detail ----------------------------------------------


QuestionType = Literal["with_food", "if_missed", "side_effects", "interactions", "why_prescribed"]


class GetMedicationDetailRequest(BaseModel):
    medication_name: str = Field(..., description="Drug name as the patient said it (e.g. 'warfarin', 'water pill').")
    question_type: QuestionType


@app.post("/tools/get_medication_detail", response_model=ToolReply)
def get_medication_detail(req: GetMedicationDetailRequest) -> ToolReply:
    med = find_medication(req.medication_name)
    if not med:
        return ToolReply(
            spoken=(
                f"I don't see {req.medication_name} on your discharge list, "
                f"{PATIENT['first_name']}. Let me get a nurse to check on that."
            ),
            data={"requested": req.medication_name},
            not_in_bundle=True,
            escalate=True,
        )

    qt = req.question_type
    if qt == "with_food":
        spoken = med["with_food"]
    elif qt == "if_missed":
        spoken = med["if_missed"]
    elif qt == "side_effects":
        spoken = f"{med['side_effects_expected']} {med['side_effects_call']}"
    elif qt == "interactions":
        spoken = med["interactions"]
    else:  # why_prescribed
        spoken = med["why_prescribed"]

    return ToolReply(
        spoken=spoken,
        data={
            "medication": med["name"],
            "dose": med["dose"],
            "question_type": qt,
        },
    )


# ---- 3. log_dose ------------------------------------------------------------


DoseStatusLiteral = Literal["taken", "missed", "skipped"]


class LogDoseRequest(BaseModel):
    medication_name: str
    status: DoseStatusLiteral
    taken_at: str = Field(
        ...,
        description="ISO-8601 datetime in the patient's local time, or the literal string 'now'.",
    )


@app.post("/tools/log_dose", response_model=ToolReply)
def log_dose(req: LogDoseRequest) -> ToolReply:
    med = find_medication(req.medication_name)
    if not med:
        return ToolReply(
            spoken=(
                f"I don't recognize {req.medication_name} from your list. "
                "Can you tell me which medication you mean? If unsure, I can get a nurse on the line."
            ),
            data={"requested": req.medication_name},
            not_in_bundle=True,
            escalate=True,
        )

    reported_at_iso = _now_iso() if req.taken_at == "now" else req.taken_at
    scheduled = ", ".join(med["schedule"]["times"]) if med["schedule"]["times"] else None

    event = store.log_dose(
        patient_id=PATIENT_ID,
        medication_canonical=med["canonical_name"],
        medication_display=med["name"],
        status=req.status,
        scheduled_time_local=scheduled,
        reported_at_iso=reported_at_iso,
    )

    if req.status == "taken":
        spoken = (
            f"Logged, {med['name']} {_speak_dose(med['dose'])} taken. "
            f"Nice work staying on top of it, {PATIENT['first_name']}."
        )
    elif req.status == "missed":
        spoken = (
            f"Thanks for telling me about the missed {med['name']}. "
            f"Here's what your discharge plan says to do: {med['if_missed']}"
        )
    else:  # skipped
        spoken = (
            f"Logged, {med['name']} skipped. "
            "I've noted it for the care team. "
            "If you skipped because of a side effect, tell me and I'll get a nurse."
        )

    return ToolReply(
        spoken=spoken,
        data={
            "event_id": event.event_id,
            "medication": med["name"],
            "status": req.status,
            "reported_at": reported_at_iso,
        },
    )


# ---- 4. check_adherence -----------------------------------------------------


class CheckAdherenceRequest(BaseModel):
    as_of: str | None = Field(
        default=None,
        description="ISO-8601 'now' for the patient's local time. Defaults to server now (UTC).",
    )


@app.post("/tools/check_adherence", response_model=ToolReply)
def check_adherence(req: CheckAdherenceRequest) -> ToolReply:
    # Use server LOCAL time (not UTC) when as_of isn't supplied. The med
    # schedule is in patient-local "HH:MM" — comparing against UTC produces
    # wildly wrong "next dose" reads. For the demo we assume the server runs
    # in (or close to) the patient's timezone.
    now = datetime.fromisoformat(req.as_of) if req.as_of else datetime.now()
    today_date = now.date().isoformat()

    taken_today: list[str] = []
    for med in MEDICATIONS:
        if store.has_taken_today(PATIENT_ID, med["canonical_name"], today_date):
            taken_today.append(med["name"])

    # Compute "next dose" by walking the schedule forward from `now`.
    upcoming: list[tuple[str, str]] = []  # (HH:MM, "med name dose")
    hhmm_now = now.strftime("%H:%M")
    for med in MEDICATIONS:
        for t in med["schedule"]["times"]:
            if t > hhmm_now:
                upcoming.append((t, f"{med['name']} {_speak_dose(med['dose'])}"))
    upcoming.sort()
    if upcoming:
        next_time, next_med = upcoming[0]
        next_phrase = f"Next is {next_med} at {_speak_time(next_time)}."
    else:
        next_phrase = "Nothing more is due tonight. The next dose is furosemide tomorrow at eight AM."

    if not taken_today:
        spoken = (
            f"I haven't logged any doses for you today, {PATIENT['first_name']}. "
            f"{next_phrase} Let me know when you take it and I'll mark it down."
        )
    else:
        spoken = (
            f"So far today you've taken {len(taken_today)} of your scheduled medications. "
            f"{next_phrase}"
        )

    return ToolReply(
        spoken=spoken,
        data={
            "as_of": now.isoformat(),
            "taken_today": taken_today,
            "next": {"time": upcoming[0][0], "medication": upcoming[0][1]} if upcoming else None,
        },
    )


# ---- 5. explain_lab_result --------------------------------------------------


class ExplainLabRequest(BaseModel):
    test_name: str


@app.post("/tools/explain_lab_result", response_model=ToolReply)
def explain_lab_result(req: ExplainLabRequest) -> ToolReply:
    lab = find_lab(req.test_name)
    if not lab:
        return ToolReply(
            spoken=(
                f"That test isn't in your discharge labs, {PATIENT['first_name']}. "
                "Let me get a nurse to look it up for you."
            ),
            data={"requested": req.test_name},
            not_in_bundle=True,
            escalate=True,
        )

    # Speak only the plain-English read — TTS mangles raw lab values
    # ("4.1 mmol/L" -> "four point one M M O L slash L"). The numeric
    # value + range stay in `data` for the operator/audit view.
    spoken = lab["plain_english"]

    # Safety: out-of-range labs the patient is asking about should escalate,
    # except when the bundle marks the value as a known baseline (e.g. CKD
    # creatinine).
    out_of_range = not lab["in_range"]
    is_baseline = "baseline" in lab["plain_english"].lower()
    should_escalate = out_of_range and not is_baseline

    return ToolReply(
        spoken=spoken,
        data={
            "name": lab["name"],
            "value": lab["value"],
            "range": lab["range"],
            "in_range": lab["in_range"],
        },
        escalate=should_escalate,
    )


# ---- 6. get_followup_plan ---------------------------------------------------


class GetFollowupRequest(BaseModel):
    pass


def _speak_date(iso_date: str) -> str:
    """Render '2026-04-27' → 'Monday, April twenty-seventh' for voice."""
    d = datetime.fromisoformat(iso_date).date()
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December"]
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ordinals = {1: "first", 2: "second", 3: "third", 21: "twenty-first", 22: "twenty-second",
                23: "twenty-third", 31: "thirty-first"}
    if d.day in ordinals:
        day_word = ordinals[d.day]
    else:
        # naive ordinal-as-words fallback for the 4th–30th range we care about
        words = ["fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
                 "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
                 "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth",
                 "twenty-first", "twenty-second", "twenty-third", "twenty-fourth",
                 "twenty-fifth", "twenty-sixth", "twenty-seventh", "twenty-eighth",
                 "twenty-ninth", "thirtieth"]
        day_word = words[d.day - 4] if 4 <= d.day <= 30 else f"{d.day}"
    return f"{weekdays[d.weekday()]}, {months[d.month - 1]} {day_word}"


def _speak_time(hhmm: str) -> str:
    """Render '09:00' → 'nine AM', '14:30' → 'two thirty PM'."""
    h, m = (int(x) for x in hhmm.split(":"))
    suffix = "AM" if h < 12 else "PM"
    h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
    nums = ["zero", "one", "two", "three", "four", "five", "six", "seven",
            "eight", "nine", "ten", "eleven", "twelve"]
    h_word = nums[h12]
    if m == 0:
        return f"{h_word} {suffix}"
    if m < 10:
        return f"{h_word} oh {nums[m]} {suffix}"
    if m == 30:
        return f"{h_word} thirty {suffix}"
    return f"{h_word} {m} {suffix}"


_INT_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
    15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty", 30: "thirty", 40: "forty",
    50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty",
    90: "ninety", 100: "one hundred",
}


def _int_to_words(n: int) -> str:
    if n in _INT_WORDS:
        return _INT_WORDS[n]
    if 21 <= n <= 99:
        tens = (n // 10) * 10
        ones = n % 10
        return f"{_INT_WORDS[tens]}-{_INT_WORDS[ones]}"
    return str(n)


def _number_to_words(token: str) -> str:
    """Render a numeric token (possibly decimal) as words. '2.5' -> 'two point five'."""
    if "." in token:
        whole, frac = token.split(".", 1)
        try:
            whole_n = int(whole)
        except ValueError:
            return token
        whole_w = _int_to_words(whole_n)
        frac_w = " ".join(_INT_WORDS.get(int(d), d) for d in frac if d.isdigit())
        return f"{whole_w} point {frac_w}".strip()
    try:
        return _int_to_words(int(token))
    except ValueError:
        return token


def _speak_dose(dose: str) -> str:
    """Render '40 mg' -> 'forty milligrams', '2.5 mg' -> 'two point five milligrams'."""
    s = dose.strip()
    parts = s.split()
    if len(parts) >= 2:
        num, unit = parts[0], parts[1].lower()
        unit_word = {
            "mg": "milligrams",
            "mcg": "micrograms",
            "g": "grams",
            "ml": "milliliters",
        }.get(unit, parts[1])
        return f"{_number_to_words(num)} {unit_word}"
    return s


@app.post("/tools/get_followup_plan", response_model=ToolReply)
def get_followup_plan(_: GetFollowupRequest) -> ToolReply:
    next_appt = FOLLOW_UP["appointments"][0]
    spoken = (
        f"Your next appointment is {_speak_date(next_appt['date'])} at "
        f"{_speak_time(next_appt['time'])} — {next_appt['type']} at the "
        f"{next_appt['location']}. And remember: {FOLLOW_UP['key_red_flag_to_remind']}"
    )
    return ToolReply(
        spoken=spoken,
        data={"appointments": FOLLOW_UP["appointments"]},
    )


# ---- 7. escalate_to_clinician -----------------------------------------------


UrgencyLiteral = Literal["low", "medium", "high", "critical"]


class EscalateRequest(BaseModel):
    reason: str
    urgency: UrgencyLiteral
    summary: str = Field(..., description="Clinician-ready summary, under 25 words.")
    transcript_snippet: str
    recommended_action: str


@app.post("/tools/escalate_to_clinician", response_model=ToolReply)
def escalate_to_clinician(req: EscalateRequest) -> ToolReply:
    event = store.log_escalation(
        patient_id=PATIENT_ID,
        reason=req.reason,
        urgency=req.urgency,
        summary=req.summary,
        transcript_snippet=req.transcript_snippet,
        recommended_action=req.recommended_action,
        created_at_iso=_now_iso(),
    )

    if req.urgency == "critical":
        spoken = (
            f"{PATIENT['first_name']}, I've alerted the on-call team — they're calling you right now. "
            "If you have chest pain, severe shortness of breath, or signs of stroke, hang up and dial nine-one-one. "
            f"Your case reference is {event.case_ref}."
        )
    elif req.urgency == "high":
        spoken = (
            f"I've passed this to the on-call nurse, {PATIENT['first_name']}. "
            f"They'll call you within fifteen minutes. Your case reference is {event.case_ref}."
        )
    else:
        spoken = (
            f"I've sent this to your care team, {PATIENT['first_name']}. "
            f"They'll get back to you. Your case reference is {event.case_ref}."
        )

    return ToolReply(
        spoken=spoken,
        data={
            "case_ref": event.case_ref,
            "urgency": req.urgency,
            "event_id": event.event_id,
        },
    )


# ---- ops endpoints (not exposed as tools) -----------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "patient_id": PATIENT_ID,
        "loaded_medications": [m["name"] for m in MEDICATIONS],
        "tools": [
            "get_medications",
            "get_medication_detail",
            "log_dose",
            "check_adherence",
            "explain_lab_result",
            "get_followup_plan",
            "escalate_to_clinician",
        ],
    }


@app.get("/ledger")
def ledger() -> dict[str, Any]:
    """Read-only operator view — what the patient has logged this session."""
    return {
        "doses": [e.__dict__ for e in store.doses],
        "escalations": [e.__dict__ for e in store.escalations],
    }


# ---- minimal test page ------------------------------------------------------
# Serves a single static page that wires the ElevenLabs widget to the 7 client
# tools above. One server, one port — no CORS dance for the demo.

_WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@app.get("/config.json")
def web_config() -> JSONResponse:
    """Returns the agent id so the static page can pick it up at runtime
    instead of being baked in. Env: NEXT_PUBLIC_AGENT_ID."""
    return JSONResponse(
        {
            "agent_id": os.environ.get("NEXT_PUBLIC_AGENT_ID", ""),
            "patient_first_name": PATIENT["first_name"],
        }
    )


@app.get("/")
def web_index() -> FileResponse:
    return FileResponse(_WEB_DIR / "index.html")


if _WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")
