# Voice strategy — Aria

## Brief

Aria is a post-discharge voice copilot for vulnerable patients. The voice must feel like a *trusted person* on the phone, not a virtual assistant. Patients are tired, sometimes scared, often alone. Get the voice wrong and the experience becomes either frightening or dismissable.

## Anchor descriptors

- **Warm, low-mid female voice.** Not bright. Not perky. Not clinical-flat.
- **Slower than typical TTS.** Speed 0.92 — about 8% slower than a standard assistant.
- **High stability** — no theatrical swings; this is not a brand voice, it's a care voice.
- **Subtle expressive variation** — enough that "I'm getting a nurse on the line" actually conveys urgency, but never operatic.

## Default settings (mirrors `tools/_config.py`)

| Setting           | Value | Why |
|-------------------|-------|-----|
| stability         | 0.80  | Predictable cadence; no jolts. |
| similarity_boost  | 0.92  | Locks the voice identity tightly — patient should never hear "two Arias". |
| style             | 0.10  | Minimal embellishment; this is a care voice, not a personality voice. |
| speaker_boost     | true  | Browser audio over a patient's home speaker is often poor. |
| speed             | 0.92  | Slower than mb's 0.95. Patients > bank customers on patience needs. |
| TTS model (live)  | `eleven_flash_v2`  | English-primary; API rejects v2.5 here. |
| TTS model (moments) | `eleven_v3`     | Pre-rendered, expressive. Tags drive prosody. |

## Voice ID selection

Default voice ID lives in `tools/_config.py::VOICE_ID_EN` and can be overridden by `ELEVENLABS_VOICE_ID_EN` in `.env`.

For the demo we're using a calm, mature voice. If the production deployment needs a different voice for a different patient cohort (older patients tend to prefer a slower, lower voice; pediatric caregivers prefer a warmer, slightly higher voice), swap via env var rather than re-pushing agent config.

## Audio tag dictionary (used in voice_moments.json)

Tags ElevenLabs v3 understands and we lean on:

- `[warm]` — softens consonants, slows attack
- `[calm]` — flatter pitch contour
- `[soft]` — lower volume, breathier
- `[gentle]` — slower pace, softer dynamics
- `[reassuring]` — slight downward melodic contour, conveys "it's okay"
- `[supportive]` — similar to reassuring with a touch more presence
- `[urgent_calm]` — for the critical-escalation pre-roll. Conveys "this matters" without panic.

## Anti-patterns (do not use)

- `[excited]`, `[enthusiastic]`, `[cheerful]` — wrong register entirely.
- `[whisper]` — sounds creepy at 2 AM in a quiet house.
- Long single-clause utterances without punctuated pauses — the patient loses the thread.

## Six moments — why these six

1. **greeting** — first impression; AI disclosure happens here.
2. **before_critical_escalation** — bridges the dead air while the tool fires, so the patient knows she's been heard before the real handoff confirmation comes back.
3. **handoff_intro** — non-critical escalation confirmation.
4. **dose_logged_taken** — positive reinforcement, brief.
5. **dose_logged_missed** — non-judgmental ack, passes the actual instruction off to the tool return.
6. **wrap_up** — graceful end-of-call.

We deliberately did **not** include "thinking" filler moments. Silence is fine. Filler in this domain reads as patronizing.
