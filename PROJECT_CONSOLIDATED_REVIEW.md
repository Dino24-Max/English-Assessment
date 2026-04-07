# Cruise Employee English Assessment Platform - Consolidated Project Review

> **Generated**: 2026-04-07
> **Source**: 36 markdown files consolidated into a single review document
> **Purpose**: Full project state review before implementation phase

---

## 1. Project Overview

**Product**: Web-based AI-powered English proficiency testing for Carnival cruise ship employees across Hotel and Marine divisions.

**Assessment Structure**: 6 modules, 21 questions total, 100 points max

| Module | Questions | Points | Type |
|--------|-----------|--------|------|
| Listening | Q1-Q3 (3) | 16 | Multiple choice |
| Time & Numbers | Q4-Q6 (3) | 16 | Fill-in-the-blank |
| Grammar | Q7-Q10 (4) | 16 | Multiple choice gap-fill |
| Vocabulary | Q11-Q14 (4) | 16 | Category matching / drag-and-drop |
| Reading | Q15-Q18 (4) | 16 | Title selection |
| Speaking | Q19-Q21 (3) | 20 | AI-analyzed responses |

**Technology Stack**:
- Backend: Python 3.10+, FastAPI, SQLAlchemy (async), Uvicorn
- Database: SQLite (dev) / PostgreSQL (prod), Redis (cache)
- Frontend: Jinja2 templates, HTML/CSS/JS, Web Speech API
- AI: OpenAI API (future), Browser-based speech recognition (current)

**Division Categories** (2 divisions, 29 departments):

- **Hotel Division** (25 departments):
  AUDIO/VISUAL MEDIA, AUX SERV, BEVERAGE GUEST SERV, CASINO, CULINARY ARTS, ENT - TECHNICAL, ENTERTAINMENT, F&B MGMT, FLEET FINANCE, GUEST SERVICES, GUEST TECHNOLOGY, HOTEL, HOUSEKEEPING, HUMAN RESOURCES, INFO TECHNOLOGY, INFOTAINMENT, LAUNDRY, MUSICIANS, ONBOARD MEDIA, PHOTO, PRODUCTION STAFF, PROVISIONS, REST. SERVICE, SHORE EXCURS, YOUTH PROGRAMS

- **Marine Division** (4 departments):
  DECK, ENGINE, MEDICAL, SECURITY SERVICES

---

## 2. Architecture Summary

(Source: `ARCHITECTURE.md`)

```
Client (Browser) 
  -> API Gateway (Uvicorn) 
    -> FastAPI Application
      -> Routes: auth, ui, assessment, admin, analytics
      -> Core: assessment_engine, anti_cheating, scoring
      -> Services: ai_service, speech_analyzer
      -> Models: SQLAlchemy ORM (User, Assessment, Question, InvitationCode)
      -> Data: question_bank_loader, questions_config.json
    -> Database: SQLite/PostgreSQL (async)
    -> Redis Cache (optional)
    -> External: OpenAI, Anthropic (future)
```

Key architectural features:
- Async request handling via FastAPI + SQLAlchemy async
- Session-based authentication with cookie middleware
- Anti-cheating system (tab-switch detection, IP tracking, copy-paste monitoring)
- Department-based question selection from question bank
- CEFR level calculation and display

---

## 3. Question Bank Design

(Source: `question_bank_design.md`)

**Target**: 2,900 total questions across 29 departments (100 questions per department)

| Division | Departments | Questions/Dept | Speaking/Dept | Total |
|----------|------------|----------------|---------------|-------|
| Hotel | 25 | 100 | 10 | 2,500 |
| Marine | 4 | 100 | 10 | 400 |

**Current State**: 1,600 questions implemented (16 departments x 100 questions), loaded from `question_bank_full.json` with 300 speaking questions. Remaining 13 departments need question generation.

**Question JSON Schema** (per question):
- `question_id`, `module`, `question_type`, `question_text`
- `options` (for MC), `correct_answer`, `points`
- `audio_text`, `expected_keywords` (for speaking)
- `department`, `difficulty`, `cefr_level`

---

## 4. Correct Answers Reference

(Source: `ANSWERS_21_QUESTIONS.md`, `TEST_ANSWERS_COMPLETE.md`)

All 21 questions have documented correct answers:
- Q1-Q3 (Listening): 7 PM, 8254, Deck 12
- Q4-Q6 (Time & Numbers): 7:00, 8, 9173
- Q7-Q10 (Grammar): May, has, direct, on
- Q11-Q14 (Vocabulary): Drag-and-drop matching (cabin/galley/bridge/muster)
- Q15-Q18 (Reading): Specific title selections for 4 passages
- Q19-Q21 (Speaking): Scenario-based responses scored by keyword matching

**Scoring per module**: Listening 16, Time&Numbers 16, Grammar 16, Vocabulary 16, Reading 16, Speaking 20 = **100 total**

---

## 5. Implementation Status

### 5.1 Completed Features

(Source: `CHANGELOG.md`, `IMPLEMENTATION_SUMMARY.md`, `IMPLEMENTATION_REVIEW.md`)

**Core Platform** (v1.0.0):
- FastAPI application with async support
- User registration/login with department selection
- 6-module assessment flow (21 questions)
- Real-time progress tracking
- Results page with module breakdown
- Carnival brand theme (100% complete across 14 HTML templates)

**Question Bank System**:
- 1,600 questions loaded from JSON (16 of 29 departments)
- Question bank loader with deduplication
- Auto-load on startup if DB empty
- Department-based question selection

**Admin System**:
- Admin login with checkbox enforcement
- Invitation code generation and management
- Question bank management endpoints
- Admin UI at `/admin/invitations`

**Scoring System**:
- Config-based scoring (`score_answer_from_config` in `ui.py`)
- Direct scoring from `questions_config.json` without DB dependency
- Speaking scoring via keyword matching (Web Speech API transcription)
- Score aggregation from session data on assessment completion

**Speaking & TTS**:
- Intelligent keyword-based scoring for speaking questions
- Pre-generated MP3 audio files with browser TTS fallback
- Real-time transcription display during recording

**Anti-Cheating**:
- Tab-switch detection and logging
- IP tracking and rate limiting
- Copy-paste monitoring
- Session validation

**Security & Performance (P0 Fixes)**:
- Logging system refactored from `print()` to Python `logging`
- Error handling improved (no sensitive info leaks)
- CORS configuration hardened
- Session security configuration
- Database session management via FastAPI `Depends`
- Hardcoded passwords/keys removed, config constants used
- Database connection pooling, indexes, N+1 query resolution

### 5.2 Department + CEFR Plan Status

(Source: `docs/department_cefr_plan_checklist.md`, `IMPLEMENTATION_REVIEW.md`)

Most items from the CEFR plan are already implemented:
- Department config exists
- Question/Assessment models have `department` and `cefr_level` fields
- Assessment engine has department-based selection
- Auth flow captures department
- CEFR spec and basic scoring exist
- Question bank generator and loader support departments
- In-app `ALTER TABLE` migrations replace Alembic

**Not yet implemented**:
- Full 2,900-question generation (29 depts x 100 questions; 13 departments still need questions)
- Advanced CEFR calculation formula in results display

---

## 6. Known Bugs and Critical Issues

### 6.1 The 21-Question / Speaking Bug (CRITICAL)

(Source: user testing + code analysis)

**Symptom**: Only 2 speaking questions appear instead of 3; assessment ends early with fewer than 21 questions.

**Root Causes**:
1. `_question_content_key` in `assessment_engine.py` only considers `question_text` for speaking dedup, ignoring `audio_text` and `expected_keywords`. Since all 300 speaking questions in `question_bank_full.json` share identical `question_text`, they deduplicate to 1 unique question.
2. Sample speaking questions (lines 1011-1015) also have identical `question_text`.
3. `min(count, len(available_questions))` allows fewer questions than targeted.
4. UI redirects to results when `next_question > len(question_order)`, ending early.
5. Hardcoded "21" in multiple places (ui.py, assessment.py, templates) is inconsistent with dynamic assessment length.

### 6.2 Security Vulnerabilities (HIGH PRIORITY)

(Source: `CODE_REVIEW_REPORT.md`, `PRODUCTION_CODE_REVIEW.md`)

**Critical/High issues still pending**:
- Admin endpoints have NO authentication
- CSRF protection incomplete
- XSS potential in template rendering
- Sensitive data stored in localStorage
- Email enumeration possible on login
- Input validation gaps
- Authorization bypass risks
- Race conditions in assessment submission
- No rate limiting on sensitive endpoints

**Fixed**:
- Scoring engine / text matching / vocabulary scoring
- Missing database indexes / constraints / FK cascades
- Logging and error handling (P0)
- Hardcoded passwords/keys (P0)
- Database session management (P0)

### 6.3 Scoring Threshold Inconsistency

Speaking scoring uses different thresholds:
- `ui.py`: 50% and 70% thresholds
- `assessment_engine.py`: 60% threshold

These need to be unified.

---

## 7. Testing Status

(Source: `TESTING.md`, `TEST_SUITE_SUMMARY.md`)

**Phase 0 Test Suite**:
- 45+ test cases across 5 unit test files and 2 integration test files
- ~60% coverage (target was 50%+)
- Anti-cheating tests: 25+ cases (~95% coverage of anti_cheating.py)
- UI integration tests: 20+ cases
- Critical path coverage: 100%

**Known test limitations**:
- Browser-based audio recording not testable
- Full end-to-end session flow not covered
- AI service mocks needed for OpenAI integration tests

---

## 8. API Documentation

(Source: `API_DOCUMENTATION.md`)

**Base URL**: `http://127.0.0.1:8000`

**Key Endpoints**:
- `POST /api/v1/register` - User registration
- `POST /api/v1/login` - Authentication
- `POST /api/v1/assessment` - Create assessment
- `GET /api/v1/assessment` - Assessment status
- `POST /api/v1/assessment/submit` - Submit answer
- `POST /api/v1/assessment/complete` - Complete assessment
- `GET /api/v1/admin/*` - Admin operations (questions, invitations)
- `GET /api/v1/analytics/*` - Analytics endpoints

---

## 9. Deployment & Setup

(Source: `DEPLOYMENT.md`, `SETUP_GUIDE.md`, `docs/SETUP_RUNBOOK.md`)

**Quick Dev Setup**:
```bash
cd "Claude Demo"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run_server.py  # starts on http://127.0.0.1:8000
```

**Environment Variables** (critical for production):
- `SECRET_KEY` - Required in production
- `DATABASE_URL` - SQLite (dev) or PostgreSQL (prod)
- `ADMIN_API_KEY` - Admin authentication
- `DEBUG` - true/false
- `CORS_ORIGINS` - Allowed origins

**Production Deployment Options**:
- Systemd + Nginx (recommended)
- Docker + docker-compose
- Both with PostgreSQL, Redis, and proper SSL

---

## 10. Carnival Brand Theme

(Source: `CARNIVAL_BRAND_THEME_PROGRESS.md`, `CARNIVAL_THEME_COMPLETION_REPORT.md`)

**Status**: 100% complete across all 14 HTML templates.

Brand colors: Navy (#003366), Gold (#D4AF37), White, Light backgrounds.
All pages use consistent Carnival styling, logos, gradients, and typography.

---

## 11. Pending Work Summary (Prioritized)

### P0 - Must Fix Before Any Testing

1. **Fix speaking question deduplication** - Update `_question_content_key` to include `audio_text` + `expected_keywords`
2. **Distinct sample speaking questions** - Give each of the 3 sample speaking questions unique `question_text`
3. **Replace all hardcoded "21"** - Use `TOTAL_QUESTIONS` constant derived from module config
4. **Add question count guard** - Warning/assertion when generated questions < expected total
5. **Unify scoring thresholds** - Align speaking scoring between ui.py and assessment_engine.py

### P1 - Security (High Priority)

6. **Admin authentication** - Add proper auth to all admin endpoints
7. **CSRF protection** - Complete CSRF token implementation
8. **Input validation** - Add comprehensive validation on all user inputs
9. **Rate limiting** - Implement on login, registration, and admin endpoints

### P2 - Feature Completion

10. **Full 3,000 question bank** - Generate remaining questions for all 30 departments
11. **Advanced CEFR display** - Show CEFR level prominently in results with breakdown
12. **Drag-and-drop vocabulary** - Implement actual drag-and-drop UI (currently may be radio buttons)

### P3 - Quality & Polish

13. **Increase test coverage** - Add end-to-end tests, AI mock tests
14. **Unit test for 21-question guarantee** - Verify `create_assessment` always produces 21 questions
15. **Production code review fixes** - Address remaining items from code review reports

---

## 12. File Index

| Category | Files |
|----------|-------|
| Project Overview | `README.md`, `CCL_English_Assessment_Project_Report.md` |
| Architecture | `ARCHITECTURE.md` |
| Requirements | `question_bank_design.md`, `ANSWERS_21_QUESTIONS.md` |
| Design Specs | `docs/superpowers/specs/2025-03-24-speaking-repeat-grammar-department-design.md` |
| Implementation | `CHANGELOG.md`, `IMPLEMENTATION_SUMMARY.md`, `IMPLEMENTATION_REVIEW.md` |
| CEFR Plan | `docs/department_cefr_plan_checklist.md` |
| Fix Reports | `P0_FIXES_SUMMARY.md`, `SCORING_FIX_SUMMARY.md`, `SPEAKING_TTS_IMPROVEMENTS.md`, `PHASE_0_COMPLETION.md`, `ADMIN_LOGIN_FIX_SUMMARY.md`, `PERFORMANCE_TEST_REPORT.md` |
| Theme | `CARNIVAL_BRAND_THEME_PROGRESS.md`, `CARNIVAL_THEME_COMPLETION_REPORT.md` |
| Code Review | `CODE_REVIEW_REPORT.md`, `PRODUCTION_CODE_REVIEW.md` |
| Testing | `TESTING.md`, `TEST_SUITE_SUMMARY.md`, `TEST_ANSWERS_COMPLETE.md`, `TESTING_INSTRUCTIONS.md` |
| API & Deployment | `API_DOCUMENTATION.md`, `DEPLOYMENT.md` |
| Setup Guides | `SETUP_GUIDE.md`, `docs/SETUP_RUNBOOK.md`, `QUICK_TEST_GUIDE.md`, `AUDIO_GENERATION_GUIDE.md` |
| Reference | `TEST_LINKS.md`, `ADMIN_LOGIN_SETUP.md` |
| Tooling | `SERENA_MCP_SETUP.md`, `GIT_UPLOAD_SUMMARY.md`, `CLAUDE.md` |

---

*End of consolidated review. 36 source files summarized.*
