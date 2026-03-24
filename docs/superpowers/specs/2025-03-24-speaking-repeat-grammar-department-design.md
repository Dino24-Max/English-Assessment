# Design: Speaking repeat-after-listening + Grammar department alignment

**Date:** 2025-03-24  
**Status:** Approved for implementation planning (user choice **A** locked)

## 1. Problem statement

1. **Grammar:** User selected IT-related department but saw non-IT scenarios (e.g. spa). Likely causes: canonical department string mismatch (`INFO TECHNOLOGY` vs UI label), insufficient/mis-tagged bank rows, or session `department` not matching DB.
2. **Speaking:** Empty or near-empty speech could still yield full module score; current path uses `AIService` + LLM/heuristics, not the strict `SpeakingScorerService` guardrails alone.
3. **Speaking product change:** Replace open-ended “answer the prompt” with **listen to a short dialogue → user repeats what they heard**; **score by how many expected keywords/phrases appear in the transcript** (with silence/invalid-audio rules).

## 2. User decision (brainstorming)

- **Audio scope:** **A — Each of the 3 Speaking questions uses its own independent short dialogue clip** (can still be tailored per department/scenario in the bank).

## 3. Design principles

- **Invalid speech first:** If transcription has fewer than N meaningful words (or duration/RMS below threshold), **force 0 or floor score** before any LLM or leniency logic.
- **Single scoring source of truth:** Keyword-based score for the new mode should be **deterministic** (same transcript → same score); optional LLM only for feedback text, not primary points.
- **Department consistency:** Question selection and bank labels use **`config/departments.py`** canonical names (e.g. `INFO TECHNOLOGY`); UI normalizes via `normalize_department` before engine filters.

## 4. Speaking module — target behavior

| Item | Decision |
|------|----------|
| Flow | Play audio → record → submit → transcribe (Whisper or existing pipeline) → score |
| Points | Split across 3 questions (existing totals preserved, e.g. 7+7+6 = 20) |
| Scoring | Primary: **ratio of matched expected keywords** (synonyms optional, same family as `SpeakingScorerService`); **no keyword match + no valid speech → 0** for that item |
| Metadata | Each question carries `expected_keywords[]`, reference line or `reference_text` for display optional, `audio_file` path |
| LLM | Optional for short feedback only; **must not** override deterministic score |

## 5. Grammar / department — target behavior

- Verify **`department_for_questions`** in session matches **`Question.department`** in DB for IT (`INFO TECHNOLOGY`).
- Audit loader/generator: grammar rows for IT must reflect IT scenarios; fix mis-tagged rows.
- If department-specific count < required per module, **document** whether to show fewer items, block start, or seed department-specific items (product decision — default: prefer blocking or clear message over silent empty set).

## 6. Out of scope (this spec)

- Reusing Listening bank audio for Speaking (option B/C) — **not chosen**.
- Large UI redesign beyond what’s needed for play → record → repeat instructions.

## 7. Testing notes

- IT path: grammar prompts contain IT-relevant wording (spot-check DB or fixture).
- Speaking: submit **silent** or **1-word** audio → **0** or minimal points, not 20.
- Speaking: submit transcript containing **≥ threshold** of expected keywords → partial/full credit per rubric.

## 8. Next step

Invoke **writing-plans** (or project equivalent) to break implementation into: DB/metadata, engine selection, scoring path, `AIService` adjustments, UI copy + audio UX, tests.
