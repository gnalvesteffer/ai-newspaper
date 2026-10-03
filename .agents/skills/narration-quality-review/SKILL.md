---
name: daily-signal-narration-quality-review
description: Evaluate paper narration for natural spoken delivery, factual fidelity, section alignment, and browser playback usability.
---

# Narration quality review

Use when changing generated speech scripts, voice selection, transcript display, reading navigation, or spoken playback. Read [reader-e2e-review](../reader-e2e-review/SKILL.md) for simulated voice tests and their limitations.

- Compare narration with the paper: preserve names, numbers, uncertainty, and important caveats; avoid adding unsupported claims. Prefer a concise news-reader script over verbatim card metadata while keeping the full article meaning.
- Check section and sentence mapping from spoken words back to visible paper content. Advance through multiple paragraphs and chunks; validate word offsets around punctuation, inline markup, Unicode, and long passages.
- Verify a prepared script is used without waiting for another model request. Preserve a fallback for older editions without a script, and report preparation failures plainly.
- Exercise play, pause, resume, restart, stop, speed and voice changes, section navigation, unavailable voices, and stale callbacks. Check that user scrolling can disable follow and that the control can re-enable it.
- Review the transcript drawer on desktop and short phone viewports: current sentence/word should be clear, scrolling behavior should be controllable, and the drawer should not cover most of the paper.
- Test simulated utterances for state, mapping, and cleanup. Only claim voice quality, pronunciation, or timing after listening on an actual supported browser/device; record browser and voice used.
