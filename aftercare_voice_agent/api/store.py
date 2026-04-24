"""In-memory dose log + escalation ledger for the demo session.

Lives for the lifetime of the uvicorn process. Restart wipes state — that's
intentional for a demo. Production would persist to a real adherence store
that the care team can read.
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

logger = logging.getLogger("aftercare.store")


DoseStatus = Literal["taken", "missed", "skipped"]
EscalationUrgency = Literal["low", "medium", "high", "critical"]


@dataclass
class DoseEvent:
    event_id: str
    patient_id: str
    medication_canonical: str
    medication_display: str
    status: DoseStatus
    scheduled_time_local: str | None  # "HH:MM" the dose was scheduled for, if known
    reported_at_iso: str               # when the patient told us
    note: str | None = None


@dataclass
class EscalationEvent:
    event_id: str
    patient_id: str
    reason: str
    urgency: EscalationUrgency
    summary: str
    transcript_snippet: str
    recommended_action: str
    case_ref: str
    created_at_iso: str


@dataclass
class Store:
    doses: list[DoseEvent] = field(default_factory=list)
    escalations: list[EscalationEvent] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ---- doses --------------------------------------------------------------

    def log_dose(
        self,
        *,
        patient_id: str,
        medication_canonical: str,
        medication_display: str,
        status: DoseStatus,
        scheduled_time_local: str | None,
        reported_at_iso: str,
        note: str | None = None,
    ) -> DoseEvent:
        event = DoseEvent(
            event_id=f"dose_{uuid.uuid4().hex[:10]}",
            patient_id=patient_id,
            medication_canonical=medication_canonical,
            medication_display=medication_display,
            status=status,
            scheduled_time_local=scheduled_time_local,
            reported_at_iso=reported_at_iso,
            note=note,
        )
        with self._lock:
            self.doses.append(event)
        logger.info(
            "dose-log patient=%s med=%s status=%s sched=%s reported_at=%s",
            patient_id,
            medication_canonical,
            status,
            scheduled_time_local,
            reported_at_iso,
        )
        return event

    def doses_today(self, patient_id: str, today_local_date: str) -> list[DoseEvent]:
        with self._lock:
            return [
                e
                for e in self.doses
                if e.patient_id == patient_id
                and e.reported_at_iso.startswith(today_local_date)
            ]

    def has_taken_today(
        self, patient_id: str, medication_canonical: str, today_local_date: str
    ) -> bool:
        for e in self.doses_today(patient_id, today_local_date):
            if e.medication_canonical == medication_canonical and e.status == "taken":
                return True
        return False

    # ---- escalations --------------------------------------------------------

    def log_escalation(
        self,
        *,
        patient_id: str,
        reason: str,
        urgency: EscalationUrgency,
        summary: str,
        transcript_snippet: str,
        recommended_action: str,
        created_at_iso: str,
    ) -> EscalationEvent:
        # Case ref pattern AC-YY-MM-NNN (Aftercare). Mirrors the mb AMCB pattern.
        with self._lock:
            seq = len(self.escalations) + 1
            year = created_at_iso[2:4]
            month = created_at_iso[5:7]
            case_ref = f"AC-{year}-{month}-{seq:03d}"
            event = EscalationEvent(
                event_id=f"esc_{uuid.uuid4().hex[:10]}",
                patient_id=patient_id,
                reason=reason,
                urgency=urgency,
                summary=summary,
                transcript_snippet=transcript_snippet,
                recommended_action=recommended_action,
                case_ref=case_ref,
                created_at_iso=created_at_iso,
            )
            self.escalations.append(event)
        logger.warning(
            "escalation patient=%s urgency=%s case=%s reason=%s",
            patient_id,
            urgency,
            case_ref,
            reason,
        )
        return event


store = Store()
