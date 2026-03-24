# Department Question Pools + CEFR — Plan compliance checklist

**Source plan:** `.cursor/plans/department_question_pools_cefr_85e67dc5.plan.md`  
**Purpose:** Line-by-line mapping to the plan’s “Files to Modify” and numbered sections. Use this when reviewing or extending the feature.

---

## Plan §1 — Department list (single source of truth)

| Requirement | Status | Where |
|---------------|--------|--------|
| `config/departments.py` with 30 departments | Done | `src/main/python/config/departments.py` — `DEPARTMENTS`, `DEPARTMENT_MAPPING`, helpers |
| API e.g. `/api/v1/config/departments` | Optional / not done | Not implemented; UIs use Python imports or hardcoded JS |
| Admin templates synced from backend | Partial | `admin_invitation.html` / `admin_scoreboard.html` still duplicate JS `departmentMapping`; values should match `DEPARTMENTS` |

---

## Plan §2 — Database schema

| Requirement | Status | Where |
|---------------|--------|--------|
| `Question.cefr_level` | Done | `models/assessment.py` — `String(2)` (fits A1–C2); indexes `ix_questions_dept_cefr`, `ix_questions_dept_module_cefr` |
| `Assessment.department` | Done | `models/assessment.py` |
| Alembic migration | Alternative | Plan asked for Alembic; project uses startup `ALTER TABLE` in `main.py` (see `IMPLEMENTATION_REVIEW.md`) |

---

## Plan §3 — CEFR level definitions & scoring bands

| Requirement | Status | Where |
|---------------|--------|--------|
| A1–C2 names / descriptions | Done | `data/cefr_spec.py` (generation); `utils/cefr.py` (results bands 0–16 … 85–100, names, descriptions) |

---

## Plan §4 — Pool structure (100 questions / department)

| Module | Plan count | Implementation |
|--------|------------|----------------|
| Listening | 20 | `generate_question_bank.py` + `cefr_spec` per-module targets |
| Time & Numbers | 20 | Same |
| Grammar | 20 | Same |
| Vocabulary | 20 | Same |
| Reading | 10 | Same |
| Speaking | 10 | Same |
| **Total** | **100** | **3,000** = 30 × 100 |

---

## Plan §5 — `generate_question_bank.py`

| Requirement | Status | Where |
|---------------|--------|--------|
| 30 departments from config | Done | Imports `DEPARTMENTS` / `DEPARTMENT_COUNT` |
| 100 questions/dept, CEFR spread | Done | `MODULE_CEFR_DISTRIBUTION` in `data/cefr_spec.py` |
| Output for loader | Done | `question_bank_full.json` workflow |

---

## Plan §6 — `assessment_engine.py`

| Requirement | Status | Where |
|---------------|--------|--------|
| `create_assessment(..., department=...)` | Done | Persists on `Assessment` |
| `_generate_question_set` department-first, division fallback | Done | Filters by `Question.department`; per-module counts 3+3+4+4+4+3 = 21 |
| Random sample per module | Done | Department pool grouped by module |

---

## Plan §7 — Auth, UI, transaction, assessment routes

| File | Requirement | Status | Where |
|------|-------------|--------|--------|
| `auth.py` | Pass `department` from invitation; session | Done | `api/routes/auth.py` |
| `ui.py` | `start_assessment` uses session/user department | Done | `api/routes/ui.py` |
| `assessment.py` | Create payload accepts `department` | Done | `api/routes/assessment.py` |
| `transaction.py` | Pass `department` when available | Done | `create_user_and_assessment` resolves from invitation / `user_data`, calls `create_assessment(..., department=..., auto_commit=False)` |

---

## Plan §8 — CEFR results

| Requirement | Status | Where |
|---------------|--------|--------|
| Calculator | Done | `utils/cefr.py` — `get_cefr_display`, `score_percentage_to_cefr` |
| Results template | Done | `templates/results.html` — level, name, description |

---

## Plan §9 — Backward compatibility

| Requirement | Status | Where |
|---------------|--------|--------|
| `NULL` department → division selection | Done | `assessment_engine._generate_question_set` |
| No questions for department → error / message | Done | Engine raises; UI shows admin message |

---

## “Files to Modify” table (plan) — snapshot

| Plan file | Role |
|-----------|------|
| `config/departments.py` | Canonical 30 departments |
| `models/assessment.py` | `cefr_level`, `department` on question/assessment |
| `alembic/` | Replaced by in-app migration in this repo |
| `data/generate_question_bank.py` | 3k questions |
| `core/assessment_engine.py` | Department selection |
| `api/routes/auth.py` | Invitation → user + assessment + session |
| `api/routes/ui.py` | Start assessment department resolution |
| `api/routes/assessment.py` | Optional `department` on create |
| `core/transaction.py` | Atomic user+assessment with `department` |
| `utils/scoring.py` or `utils/cefr.py` | CEFR mapping → `utils/cefr.py` |
| `templates/results.html` | CEFR display |
| `question_bank_loader.py` | Loads `department`, `cefr_level` from JSON |

---

## Optional follow-ups (not blocking)

1. Add `GET /api/v1/config/departments` returning `DEPARTMENTS` JSON.
2. Replace hardcoded admin JS with Jinja-injected list from `config.departments`.
3. Replace startup `ALTER TABLE` with Alembic if you standardize on migrations.
4. Remove temporary debug logging (`debug-ccd1fc.log` / agent regions) from `auth.py`, `ui.py`, `assessment_engine.py` when stable.

---

*Generated for traceability against the Department Question Pools CEFR plan.*
