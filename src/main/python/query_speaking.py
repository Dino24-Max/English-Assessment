"""Direct DB query to diagnose speaking 0 score."""
import sqlite3, json, re, os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "assessment.db")

def main():
    print(f"DB path: {DB_PATH}")
    print(f"File exists: {os.path.exists(DB_PATH)}")
    print(f"File size: {os.path.getsize(DB_PATH)} bytes")
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r["name"] for r in cur.fetchall()]
    print(f"Tables found: {tables}")

    if not tables:
        print("\n[ERROR] Database is empty! The server may be using WAL mode or the")
        print("file is locked by the async process. Trying WAL checkpoint...")
        try:
            cur.execute("PRAGMA wal_checkpoint(FULL)")
            result = cur.fetchone()
            print(f"WAL checkpoint result: {dict(result) if result else 'None'}")
        except Exception as e:
            print(f"WAL checkpoint error: {e}")
        conn.close()
        return

    # Count questions
    if "questions" in tables:
        cur.execute("SELECT COUNT(*) as cnt FROM questions")
        print(f"\nTotal questions: {cur.fetchone()['cnt']}")
        cur.execute("SELECT COUNT(*) as cnt FROM questions WHERE question_type='speaking_response'")
        print(f"Speaking questions: {cur.fetchone()['cnt']}")

    # Recent assessments
    if "assessments" in tables:
        print("\n" + "="*70)
        print("RECENT ASSESSMENTS")
        print("="*70)
        cur.execute("""SELECT id, user_id, department, status, total_score, 
                       max_possible_score, speaking_score, created_at
                       FROM assessments ORDER BY id DESC LIMIT 5""")
        for a in cur.fetchall():
            print(f"  #{a['id']} | dept={a['department']} | status={a['status']} | "
                  f"total={a['total_score']}/{a['max_possible_score']} | "
                  f"speaking={a['speaking_score']} | {a['created_at']}")

    # Speaking responses
    if "assessment_responses" in tables:
        print("\n" + "="*70)
        print("SPEAKING RESPONSES (most recent)")
        print("="*70)
        cur.execute("""
            SELECT ar.id, ar.assessment_id, ar.question_id, ar.user_answer, 
                   ar.is_correct, ar.points_earned,
                   q.question_text, q.correct_answer, q.question_metadata, q.points
            FROM assessment_responses ar
            JOIN questions q ON ar.question_id = q.id
            WHERE q.question_type = 'speaking_response'
            ORDER BY ar.id DESC
            LIMIT 10
        """)
        responses = cur.fetchall()
        if not responses:
            print("  No speaking responses found!")
        
        for r in responses:
            meta = json.loads(r["question_metadata"]) if r["question_metadata"] else {}
            print(f"\n{'─'*70}")
            print(f"  Response #{r['id']} | Assessment #{r['assessment_id']} | Q#{r['question_id']}")
            print(f"  Question: {r['question_text'][:100]}")
            print(f"  Points: {r['points_earned']}/{r['points']} | Correct: {r['is_correct']}")
            print(f"  correct_answer field: {r['correct_answer'][:120] if r['correct_answer'] else 'NULL'}")
            print(f"  Metadata speaking_type: {meta.get('speaking_type', 'N/A')}")
            print(f"  Metadata audio_text: {meta.get('audio_text', 'N/A')}")
            print(f"  Metadata expected_keywords: {meta.get('expected_keywords', 'N/A')}")

            user_answer = r["user_answer"] or ""
            print(f"\n  RAW user_answer: {user_answer[:200]}")

            # Parse transcript
            transcript = ""
            duration = 0.0
            if user_answer.startswith("recorded_") and "|" in user_answer:
                head, rest = user_answer.split("|", 1)
                m = re.match(r"recorded_(\d+(?:\.\d+)?)s?", head.strip(), re.I)
                duration = float(m.group(1)) if m else 0.0
                transcript = rest.strip()
            else:
                transcript = user_answer.strip()

            print(f"  Parsed transcript: '{transcript[:150]}'")
            print(f"  Duration: {duration}s")

            # Check invalidity
            t_lower = transcript.strip().lower()
            if not t_lower:
                print(f"  >>> CAUSE: Empty transcript -> 0 score")
                continue
            if t_lower.startswith("[no transcription") or t_lower.startswith("[no speech"):
                print(f"  >>> CAUSE: No speech detected marker -> 0 score")
                continue
            if t_lower == "analysis unavailable":
                print(f"  >>> CAUSE: 'analysis unavailable' -> 0 score")
                continue

            # Meaningful words check
            meaningful_words = re.findall(r'\b[a-zA-Z]{2,}\b', t_lower)
            print(f"  Meaningful words ({len(meaningful_words)}): {meaningful_words[:15]}")
            if len(meaningful_words) < 2:
                print(f"  >>> CAUSE: HARD GUARDRAIL - fewer than 2 meaningful words -> 0 score")
                continue

            # Resolve expected keywords
            expected_kws = meta.get("expected_keywords", [])
            if isinstance(expected_kws, str):
                try:
                    expected_kws = json.loads(expected_kws)
                except Exception:
                    expected_kws = [k.strip() for k in expected_kws.split(",") if k.strip()]
            if not expected_kws and meta.get("audio_text"):
                words = re.findall(r"[A-Za-z]{3,}", meta["audio_text"].lower())
                stopwords = {"the","and","for","are","but","not","you","all","can","had",
                             "her","was","one","our","out","has","have","been","will","your",
                             "from","they","this","that","with","which","their","there",
                             "would","could","should","about","these","those","into","also",
                             "than","when","what","just","like","more","some","very","after","most"}
                seen = set()
                expected_kws = []
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
                except Exception:
                    expected_kws = [k.strip() for k in ca.split(",") if k.strip()]

            print(f"  Expected keywords ({len(expected_kws)}): {expected_kws[:15]}")
            if not expected_kws:
                print(f"  >>> CAUSE: No keywords resolved -> 0 from assessment_engine")
                continue

            # Simulate keyword matching
            matched = []
            missing = []
            for kw in expected_kws:
                kw_lower = kw.lower().strip()
                if kw_lower in t_lower:
                    matched.append(kw)
                else:
                    missing.append(kw)

            match_ratio = len(matched) / len(expected_kws) if expected_kws else 0
            print(f"  Keyword match: {len(matched)}/{len(expected_kws)} = {match_ratio:.1%}")
            print(f"  Matched: {matched[:10]}")
            print(f"  Missing: {missing[:10]}")

            if match_ratio < 0.1:
                print(f"  >>> CAUSE: Extremely low keyword match -> near 0 total score")
            elif match_ratio < 0.3:
                print(f"  >>> CAUSE: Low keyword match ({match_ratio:.1%}) -> very low score")
            else:
                print(f"  >>> Score should be reasonable ({match_ratio:.1%} match)")

    conn.close()
    print("\n" + "="*70)
    print("DIAGNOSIS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
