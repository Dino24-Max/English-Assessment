"""
Diagnose Speaking 0-score: inspect DB questions, simulate scoring, trace the full pipeline.
Run from src/main/python/:  python diagnose_speaking.py
"""
import sqlite3, json, re, sys, os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "assessment.db")

def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=" * 80)
    print("1. DATABASE TABLES")
    print("=" * 80)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r["name"] for r in cur.fetchall()]
    print(f"   Tables: {tables}")

    print()
    print("=" * 80)
    print("2. SPEAKING QUESTIONS SAMPLE (first 5)")
    print("=" * 80)
    cur.execute("""
        SELECT id, question_text, correct_answer, question_metadata, points
        FROM questions
        WHERE question_type = 'speaking_response'
        LIMIT 5
    """)
    speaking_qs = cur.fetchall()
    if not speaking_qs:
        print("   [WARNING] No speaking questions found in DB!")
    for q in speaking_qs:
        meta = json.loads(q["question_metadata"]) if q["question_metadata"] else {}
        print(f"\n   Q#{q['id']} | Points: {q['points']}")
        print(f"   Text: {q['question_text'][:120]}")
        print(f"   correct_answer: {q['correct_answer'][:120] if q['correct_answer'] else 'NULL'}")
        print(f"   Metadata keys: {list(meta.keys())}")
        print(f"   speaking_type: {meta.get('speaking_type', 'N/A')}")
        print(f"   audio_text: {meta.get('audio_text', 'N/A')[:100] if meta.get('audio_text') else 'N/A'}")
        print(f"   expected_keywords: {meta.get('expected_keywords', 'N/A')}")
        print(f"   reference_text: {meta.get('reference_text', 'N/A')[:100] if meta.get('reference_text') else 'N/A'}")

    print()
    print("=" * 80)
    print("3. RECENT ASSESSMENTS")
    print("=" * 80)
    cur.execute("SELECT id, user_id, status, total_score, max_score, created_at FROM assessments ORDER BY id DESC LIMIT 5")
    assessments = cur.fetchall()
    if not assessments:
        print("   [INFO] No assessments found yet.")
    for a in assessments:
        print(f"   Assessment #{a['id']} | user={a['user_id']} | status={a['status']} | score={a['total_score']}/{a['max_score']} | {a['created_at']}")

    print()
    print("=" * 80)
    print("4. RECENT SPEAKING RESPONSES (assessment_responses where question is speaking)")
    print("=" * 80)
    cur.execute("""
        SELECT ar.id, ar.assessment_id, ar.question_id, ar.user_answer, ar.is_correct, ar.points_earned,
               q.question_text, q.correct_answer, q.question_metadata
        FROM assessment_responses ar
        JOIN questions q ON ar.question_id = q.id
        WHERE q.question_type = 'speaking_response'
        ORDER BY ar.id DESC
        LIMIT 10
    """)
    responses = cur.fetchall()
    if not responses:
        print("   [INFO] No speaking responses recorded yet.")
        print("   >>> You need to complete an assessment first, then re-run this script.")
    for r in responses:
        meta = json.loads(r["question_metadata"]) if r["question_metadata"] else {}
        print(f"\n   Response #{r['id']} | Assessment #{r['assessment_id']}")
        print(f"   Question: {r['question_text'][:100]}")
        print(f"   User Answer (raw): {r['user_answer'][:200] if r['user_answer'] else 'NULL'}")
        print(f"   is_correct: {r['is_correct']} | points_earned: {r['points_earned']}")
        print(f"   expected_keywords: {meta.get('expected_keywords', 'N/A')}")
        print(f"   audio_text: {meta.get('audio_text', 'N/A')[:100] if meta.get('audio_text') else 'N/A'}")

        user_answer = r["user_answer"] or ""
        transcript = ""
        duration = 0.0
        if user_answer.startswith("recorded_") and "|" in user_answer:
            head, rest = user_answer.split("|", 1)
            m = re.match(r"recorded_(\d+(?:\.\d+)?)s?", head.strip(), re.I)
            duration = float(m.group(1)) if m else 0.0
            transcript = rest.strip()
        else:
            transcript = user_answer.strip()

        print(f"   Parsed transcript: '{transcript[:150]}'")
        print(f"   Parsed duration: {duration}s")

        # Check invalid transcript conditions
        t_lower = transcript.strip().lower()
        if not t_lower:
            print(f"   >>> DIAGNOSIS: Empty transcript -> automatic 0 score")
            continue
        if t_lower.startswith("[no transcription") or t_lower.startswith("[no speech"):
            print(f"   >>> DIAGNOSIS: Whisper returned no-speech marker -> automatic 0 score")
            continue
        if t_lower == "analysis unavailable":
            print(f"   >>> DIAGNOSIS: Transcription failed ('analysis unavailable') -> automatic 0 score")
            continue

        # Check meaningful words guardrail
        meaningful_words = re.findall(r"\b[a-zA-Z]{2,}\b", t_lower)
        print(f"   Meaningful words ({len(meaningful_words)}): {meaningful_words[:20]}")
        if len(meaningful_words) < 2:
            print(f"   >>> DIAGNOSIS: Hard guardrail triggered! < 2 meaningful words -> automatic 0 score")
            continue

        # Resolve expected keywords
        expected_kws = meta.get("expected_keywords", [])
        if isinstance(expected_kws, str):
            try:
                expected_kws = json.loads(expected_kws)
            except:
                expected_kws = [k.strip() for k in expected_kws.split(",") if k.strip()]
        if not expected_kws and meta.get("audio_text"):
            words = re.findall(r"[A-Za-z]{3,}", meta["audio_text"].lower())
            stopwords = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out", "has", "have", "been", "will", "your", "from", "they", "this", "that", "with", "which", "their", "there", "would", "could", "should", "about", "these", "those", "into", "also", "than", "when", "what", "just", "like", "more", "some", "very", "after", "most"}
            expected_kws = []
            seen = set()
            for w in words:
                if w not in stopwords and w not in seen:
                    seen.add(w)
                    expected_kws.append(w)
        if not expected_kws and r["correct_answer"]:
            ca = r["correct_answer"].strip()
            try:
                parsed = json.loads(ca)
                if isinstance(parsed, list):
                    expected_kws = [str(k).strip() for k in parsed if str(k).strip()]
            except:
                expected_kws = [k.strip() for k in ca.split(",") if k.strip()]

        print(f"   Resolved expected_keywords ({len(expected_kws)}): {expected_kws[:15]}")

        if not expected_kws:
            print(f"   >>> DIAGNOSIS: No expected keywords resolved -> returns 0 score from assessment_engine")
            continue

        # Simulate keyword matching
        transcript_words_set = set(re.findall(r'\b\w+\b', t_lower))
        matched = []
        missing = []
        for kw in expected_kws:
            kw_lower = kw.lower().strip()
            if kw_lower in t_lower:
                matched.append(kw)
            elif kw_lower in transcript_words_set:
                matched.append(kw)
            else:
                missing.append(kw)
        
        match_ratio = len(matched) / len(expected_kws) if expected_kws else 0
        print(f"   Keyword match: {len(matched)}/{len(expected_kws)} = {match_ratio:.1%}")
        print(f"   Matched: {matched[:10]}")
        print(f"   Missing: {missing[:10]}")
        
        if match_ratio < 0.1:
            print(f"   >>> DIAGNOSIS: Very low keyword match ({match_ratio:.1%}) -> near 0 total score")
        elif match_ratio < 0.3:
            print(f"   >>> DIAGNOSIS: Low keyword match ({match_ratio:.1%}) -> low score (keyword = 60% weight)")

    conn.close()
    print()
    print("=" * 80)
    print("DONE. If no responses exist, please complete an assessment and re-run.")
    print("=" * 80)


if __name__ == "__main__":
    main()
