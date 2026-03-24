"""Quick script to verify listening questions in DB and ID range."""
import sqlite3
import json

conn = sqlite3.connect("data/assessment.db")
c = conn.cursor()
# ID range
c.execute("SELECT MIN(id), MAX(id), COUNT(*) FROM questions")
mn, mx, cnt = c.fetchone()
print(f"Questions: count={cnt}, id range={mn}-{mx}\n")

c.execute(
    "SELECT id, question_text, question_metadata FROM questions WHERE module_type='listening' LIMIT 3"
)
for row in c.fetchall():
    qid, qtext, meta = row
    meta = json.loads(meta or "{}")
    audio = meta.get("audio_text") or meta.get("audio") or ""
    print(f"ID={qid}")
    print(f"  Q: {(qtext or '')[:100]}")
    print(f"  Audio: {(audio or '')[:180]}...")
    print()

# Sample assessments and their question_order - check first question content
c.execute("SELECT id, question_order FROM assessments ORDER BY id DESC LIMIT 2")
for row in c.fetchall():
    aid, qo_str = row
    qo = json.loads(qo_str or "[]")
    first_id = qo[0] if qo else None
    if first_id:
        c.execute(
            "SELECT module_type, question_text, question_metadata FROM questions WHERE id=?",
            (first_id,),
        )
        r = c.fetchone()
        if r:
            mod, qt, meta = r
            meta = json.loads(meta or "{}")
            audio = (meta.get("audio_text") or meta.get("audio") or "")[:120]
            print(f"Assessment {aid} Q1 (id={first_id}): module={mod}")
            print(f"  question_text: {(qt or '')[:80]}")
            print(f"  audio_text: {audio}...")
        else:
            print(f"Assessment {aid} Q1: question_id {first_id} NOT FOUND in DB")
    print()
conn.close()
