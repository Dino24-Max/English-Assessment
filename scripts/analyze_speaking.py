"""
Inspect HOTEL speaking questions and audio_text coverage in question_bank_full.json.
Run from project root: python scripts/analyze_speaking.py
"""
import json
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
bank_path = project_root / "src" / "main" / "python" / "data" / "question_bank_full.json"

with open(bank_path, "r", encoding="utf-8") as f:
    data = json.load(f)

questions = data if isinstance(data, list) else data.get("questions", [])

hotel_speaking = [
    q for q in questions if q.get("module_type") == "speaking" and q.get("department") == "HOTEL"
]
print(f"HOTEL speaking questions: {len(hotel_speaking)}")
for i, q in enumerate(hotel_speaking[:4]):
    meta = q.get("question_metadata", {}) or {}
    qt = q.get("question_text", "")
    at = str(meta.get("audio_text", ""))
    ek = meta.get("expected_keywords", [])
    cl = q.get("cefr_level", "")
    qid = q.get("question_id", "")
    print(f"\nQ{i+1}:")
    print(f"  question_id: {qid}")
    print(f"  cefr_level: {cl}")
    print(f"  question_text: {qt[:100]}")
    print(f"  audio_text: {at[:100]}")
    print(f"  expected_keywords: {ek}")

no_audio = [
    q for q in questions
    if q.get("module_type") == "speaking"
    and not (q.get("question_metadata") or {}).get("audio_text")
]
print(f"\nSpeaking questions without audio_text: {len(no_audio)}")
if no_audio:
    for q in no_audio[:2]:
        print(f"  qid={q.get('question_id')} dept={q.get('department')} meta={q.get('question_metadata')}")

all_audio_texts = set()
for q in questions:
    if q.get("module_type") == "speaking":
        meta = q.get("question_metadata", {}) or {}
        at = meta.get("audio_text", "").strip().lower()
        all_audio_texts.add(at)
print(f"\nTotal unique audio_texts across ALL speaking questions: {len(all_audio_texts)}")
for at in sorted(all_audio_texts):
    print(f"  - {at[:120]}")
