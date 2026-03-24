# Department Question Pools + CEFR – Implementation Review

**Purpose:** Avoid rebuilding what already exists. This document summarizes what's implemented vs. what remains.

---

## ALREADY IMPLEMENTED – DO NOT REBUILD

### 1. Department Configuration
- **File:** `src/main/python/config/departments.py`
- **Contents:** 30 departments (26 Hotel + 4 Marine), `DEPARTMENTS`, `DEPARTMENT_TO_CONTENT_POOL`, `LEGACY_TO_CANONICAL`, `get_departments_by_operation()`, `get_operation_for_department()`, `normalize_department()`
- **Status:** Complete; single source of truth exists

### 2. Question Model
- **File:** `src/main/python/models/assessment.py`
- **Columns:** `department`, `cefr_level`, `scenario_id`, `scenario_description`
- **Indexes:** `ix_questions_dept_module_cefr`, `ix_questions_dept_cefr`, `ix_questions_department`, etc.
- **Status:** Schema and indexes in place

### 3. Assessment Engine – Department-Based Selection
- **File:** `src/main/python/core/assessment_engine.py`
- **Behavior:** `start_assessment()` fetches `User.department` and passes it to `_generate_question_set(division, department=department)`; filters by `Question.department` when department is set
- **Status:** Implemented

### 4. Auth – Department Flow
- **File:** `src/main/python/api/routes/auth.py`
- **Behavior:** `InvitationCode.department` → `User.department` on registration; existing users updated from invitation
- **Status:** Department flows from invitation to user

### 5. CEFR Specification
- **File:** `src/main/python/data/cefr_spec.py`
- **Contents:** `CEFR_LEVELS`, `MODULE_CEFR_DISTRIBUTION`, `score_percentage_to_cefr()`, grammar/vocabulary hints
- **Status:** Implemented

### 6. Question Bank Generation
- **File:** `src/main/python/data/generate_question_bank.py`
- **Output:** 30 departments × 100 questions = 3,000 questions, CEFR-tagged per module
- **Status:** Implemented

### 7. Question Bank Loader
- **File:** `src/main/python/data/question_bank_loader.py`
- **Behavior:** Loads `department`, `cefr_level` from JSON (`question_bank_full.json`)
- **Status:** Implemented

### 8. Results Page – CEFR Display
- **Files:** `src/main/python/templates/results.html`, `src/main/python/api/routes/ui.py`
- **Behavior:** `score_percentage_to_cefr()` maps percentage to CEFR (A1–C2); results template shows "CEFR Level: {{ cefr_level }}"
- **Status:** Basic CEFR display in place

### 9. Database Migration for `cefr_level`
- **File:** `src/main/python/main.py`
- **Behavior:** Raw SQL `ALTER TABLE questions ADD COLUMN cefr_level` on startup (if missing)
- **Status:** Present (no Alembic; in-code migration)

### 10. Admin Templates – Department Dropdowns
- **Files:** `admin_invitation.html`, `admin_scoreboard.html`
- **Behavior:** Hardcoded `departmentMapping` in JavaScript; values **match** `config/departments.py` exactly (26 Hotel + 4 Marine)
- **Status:** Works today; risk of drift if config changes

---

## RECENTLY COMPLETED

### 1. Assessment Model – `department` Column
- **File:** `src/main/python/models/assessment.py`
- **Change:** Added `department = Column(String(100), nullable=True)` to record which question pool was used
- **Migration:** `main.py` lifespan adds `assessments.department` via `ALTER TABLE` if missing
- **Status:** Done

### 2. `create_assessment` – Pass Department
- **File:** `src/main/python/core/assessment_engine.py`
- **Change:** `create_assessment(user_id, division, department=None)` now accepts and persists `department`
- **Auth:** Both registration paths in `auth.py` pass `department` when calling `create_assessment`
- **start_assessment:** Backfills `assessment.department` from `user.department` for old assessments
- **Status:** Done

### 3. Seed Question Bank
- **Script:** `scripts/load_question_bank.py`
- **Usage:** `python scripts/load_question_bank.py` (run from project root)
- **Behavior:** Clears `questions`, ensures schema (incl. `department`), loads `question_bank_full.json` via `QuestionBankLoader.load_full_question_bank()`
- **Status:** Documented; script already existed, `department` added to schema migration

---

## GAPS – REMAINING WORK (Optional)

### 4. Admin Templates – Use Config (Optional)
- **Current:** Hardcoded `departmentMapping` in JS
- **Idea:** Inject via Jinja from `config.departments.DEPARTMENTS` or serve via `/api/v1/config/departments`
- **Scope:** Reduces duplication; prevents drift

### 5. API `/api/v1/config/departments` (Optional)
- **Current:** Does not exist
- **Idea:** Expose `DEPARTMENTS` for frontend use
- **Scope:** New endpoint; useful if more UIs need department list

### 5. CEFR Enhancement on Results (Optional)
- **Current:** Shows "CEFR Level: B2"
- **Idea:** Add level name (e.g. "Upper-Intermediate") and short description from CEFR table
- **Scope:** Add `CEFR_LEVEL_NAMES` / descriptions in `cefr_spec.py`; pass to template

### 7. Seed Question Bank – Verify Count (Optional)
- **Current:** `scripts/load_question_bank.py` loads `question_bank_full.json`; DB count depends on JSON content
- **Optional:** Add verification step or assert expected count after load

---

## SUMMARY

| Component | Status | Action |
|-----------|--------|--------|
| config/departments.py | Done | None |
| Question schema (department, cefr_level) | Done | None |
| Assessment engine department selection | Done | None |
| Auth department flow | Done | None |
| CEFR spec + score_percentage_to_cefr | Done | None |
| Question bank generation | Done | None |
| Question bank loader | Done | None |
| Results CEFR display (basic) | Done | Optional: enhance with level names |
| Admin departmentMapping | Working | Optional: inject from config |
| Assessment.department | Done | Column + migration in main.py |
| create_assessment(department) | Done | Auth passes department |
| API /config/departments | Missing | Optional |
| Seed script/process | Done | `python scripts/load_question_bank.py` |

---

## RECOMMENDED NEXT STEPS (Completed)

1. ~~**Add `department` to Assessment model** and migration.~~ Done.
2. ~~**Update `create_assessment`** to accept and store `department` from the user.~~ Done.
3. **Ensure auth passes department** when calling `create_assessment` (division comes from invitation; department should too).
4. ~~**Document/script** loading `question_bank_full.json` into the database.~~ Use `python scripts/load_question_bank.py`.
5. (Optional) Inject admin templates’ department list from config or API.
