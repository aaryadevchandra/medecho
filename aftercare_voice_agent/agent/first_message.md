# First message (English, AI-disclosure compliant)

## Primary

> Hi Maria, this is Aria — your AI recovery copilot from the hospital. I have your discharge plan in front of me. How are you feeling tonight?

## Pre-rendered Greeting Version (with audio tags for expressiveness)

This is the `greeting` entry in `agent/voice_moments.json`, rendered by `python -m tools.render_first_message`. Audio tags control prosody and do not appear in the spoken output.

```
[warm][calm] Hi Maria, this is Aria — [soft] your AI recovery copilot from the hospital. [reassuring] I have your discharge plan in front of me. [gentle] How are you feeling tonight?
```

## Notes

- The greeting names the patient. In a real deployment we'd template the name in at session start; for the prototype it is hard-coded for Maria Santos.
- "AI recovery copilot" satisfies AI-disclosure on the first turn. We avoid the word "nurse" intentionally — Aria is not a nurse, and patients should never be confused on that point.
- Open with a check-in question, not a menu. The first thing the patient hears should make her feel met, not interrogated.
- If the patient speaks before the greeting completes, the agent should switch to live mode and respond to what she said, not finish the canned greeting.
