# Architecture Documentation

## System Architecture Overview

The Cruise Employee English Assessment Platform is built on a modern, scalable architecture using FastAPI, PostgreSQL, and AI services. The system follows clean architecture principles with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Web Browser  │  │ Admin Portal │  │ API Clients  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (Nginx)                          │
│              ┌────────────────────────────────┐                 │
│              │  Rate Limiting                 │                 │
│              │  SSL Termination               │                 │
│              │  Load Balancing                │                 │
│              └────────────────────────────────┘                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            FastAPI Application (Uvicorn)                  │  │
│  │                                                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │   Routes   │  │   Core     │  │  Services  │         │  │
│  │  │            │  │  Business  │  │            │         │  │
│  │  │ - UI       │  │  Logic     │  │ - AI       │         │  │
│  │  │ - API      │  │            │  │ - Audio    │         │  │
│  │  │ - Admin    │  │ - Engine   │  │ - Email    │         │  │
│  │  │ - Analytics│  │ - Scoring  │  │            │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  │                                                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │  │
│  │  │ Middleware │  │   Models   │  │   Utils    │         │  │
│  │  │            │  │            │  │            │         │  │
│  │  │ - Security │  │ - User     │  │ - Scoring  │         │  │
│  │  │ - Session  │  │ - Question │  │ - Cheating │         │  │
│  │  │ - CORS     │  │ - Response │  │            │         │  │
│  │  └────────────┘  └────────────┘  └────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────┬─────────────────────┬───────────────────────────┘
                │                     │
                ▼                     ▼
┌───────────────────────┐   ┌─────────────────────────┐
│   Data Layer          │   │   External Services     │
│                       │   │                         │
│  ┌─────────────────┐ │   │  ┌──────────────────┐   │
│  │   PostgreSQL    │ │   │  │   OpenAI API     │   │
│  │   Database      │ │   │  │   (Speech Eval)  │   │
│  │                 │ │   │  └──────────────────┘   │
│  │ - Users         │ │   │                         │
│  │ - Assessments   │ │   │  ┌──────────────────┐   │
│  │ - Questions     │ │   │  │  Anthropic API   │   │
│  │ - Responses     │ │   │  │  (Claude)        │   │
│  └─────────────────┘ │   │  └──────────────────┘   │
│                       │   │                         │
│  ┌─────────────────┐ │   │  ┌──────────────────┐   │
│  │     Redis       │ │   │  │   Email Service  │   │
│  │   (Sessions)    │ │   │  │   (SMTP)         │   │
│  │   (Cache)       │ │   │  └──────────────────┘   │
│  │   (Queue)       │ │   │                         │
│  └─────────────────┘ │   └─────────────────────────┘
└───────────────────────┘
```

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, high-performance Python web framework
- **Uvicorn**: ASGI server with WebSocket support
- **Python 3.10+**: Primary programming language

### Database
- **PostgreSQL 15+**: Primary relational database
- **SQLAlchemy 2.0**: Async ORM for database interactions
- **Alembic**: Database migrations
- **asyncpg**: Async PostgreSQL driver

### Caching & Sessions
- **Redis 7+**: Session storage, caching, task queue
- **Redis-py**: Python Redis client

### AI & ML
- **OpenAI API**: Speech analysis and content generation
- **Anthropic Claude**: Advanced language processing
- **librosa**: Audio processing and feature extraction
- **scikit-learn**: ML algorithms and evaluation

### Security
- **python-jose**: JWT token handling
- **passlib**: Password hashing (bcrypt)
- **CORS middleware**: Cross-origin request handling

## Component Architecture

### 1. API Layer (`src/main/python/api/`)

#### Routes Module (`api/routes/`)
Handles all HTTP endpoints organized by functionality:

**assessment.py** - Core assessment operations
```python
POST   /api/v1/assessment/register       # Register candidate
POST   /api/v1/assessment/create         # Create session
POST   /api/v1/assessment/{id}/start     # Start assessment
POST   /api/v1/assessment/{id}/answer    # Submit answer
POST   /api/v1/assessment/{id}/complete  # Complete assessment
GET    /api/v1/assessment/{id}/status    # Get status
```

**admin.py** - Administrative functions
```python
GET    /api/v1/admin/assessments         # List all assessments
GET    /api/v1/admin/users               # Manage users
POST   /api/v1/admin/export              # Export results
GET    /api/v1/admin/analytics           # System analytics
```

**analytics.py** - Performance analytics
```python
GET    /api/v1/analytics/overview        # Overall statistics
GET    /api/v1/analytics/division/{div}  # Division performance
GET    /api/v1/analytics/trends          # Performance trends
```

**ui.py** - Frontend page rendering
```python
GET    /                                 # Homepage
GET    /register                         # Registration page
GET    /question/{num}                   # Question pages
GET    /results                          # Results page
```

### 2. Core Layer (`src/main/python/core/`)

#### Assessment Engine (`core/assessment_engine.py`)
Central business logic coordinator:

```python
class AssessmentEngine:
    async def create_assessment(user_id, division) -> Assessment
    async def start_assessment(assessment_id) -> Dict
    async def submit_response(assessment_id, question_id, answer) -> Dict
    async def complete_assessment(assessment_id) -> Dict
    async def _generate_question_set(division) -> Dict
    async def _score_response(question, answer) -> Tuple[bool, float]
```

**Responsibilities:**
- Assessment lifecycle management
- Question selection and randomization
- Response validation and scoring
- Progress tracking
- Final score calculation

#### Configuration (`core/config.py`)
Centralized application settings using Pydantic:

```python
class Settings(BaseSettings):
    # Application
    APP_NAME: str
    VERSION: str
    DEBUG: bool

    # Database
    DATABASE_URL: str

    # AI Services
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str

    # Assessment
    PASS_THRESHOLD_TOTAL: int = 70
    PASS_THRESHOLD_SAFETY: float = 0.8
    PASS_THRESHOLD_SPEAKING: int = 12

    # Security
    SECRET_KEY: str
    SESSION_TIMEOUT_SECONDS: int = 14400
```

#### Database (`core/database.py`)
Async database connection management:

```python
# Async engine
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)

# Session factory
async_session_maker = async_sessionmaker(engine, class_=AsyncSession)

# Dependency injection
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
```

### 3. Models Layer (`src/main/python/models/`)

#### Database Models (`models/assessment.py`)

**User Model**
```python
class User(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str (unique)
    nationality: str
    division: DivisionType
    department: str
    is_active: bool
```

**Assessment Model**
```python
class Assessment(BaseModel):
    id: int
    user_id: int (FK)
    session_id: str (unique)
    division: DivisionType
    status: AssessmentStatus
    started_at: datetime
    completed_at: datetime
    total_score: float
    module_scores: Dict[str, float]
    passed: bool
    feedback: JSON
```

**Question Model**
```python
class Question(BaseModel):
    id: int
    module_type: ModuleType
    division: DivisionType
    question_type: QuestionType
    question_text: Text
    options: JSON
    correct_answer: Text
    points: int
    is_safety_related: bool
```

**AssessmentResponse Model**
```python
class AssessmentResponse(BaseModel):
    id: int
    assessment_id: int (FK)
    question_id: int (FK)
    user_answer: Text
    is_correct: bool
    points_earned: float
    time_spent_seconds: int
    audio_file_path: str (for speaking)
    speech_analysis: JSON
```

### 4. Services Layer (`src/main/python/services/`)

#### AI Service (`services/ai_service.py`)
Integration with AI APIs:

```python
class AIService:
    async def analyze_speech_response(audio_file, expected, context) -> Dict:
        """
        Analyzes speaking response using AI
        Returns: {
            'transcript': str,
            'pronunciation_score': float,
            'fluency_score': float,
            'appropriateness_score': float,
            'clarity_score': float,
            'total_points': float,
            'feedback': str
        }
        """

    async def generate_feedback(assessment_results) -> str:
        """Generate personalized feedback"""

    async def generate_audio_dialogue(scenario) -> bytes:
        """Generate audio for listening module"""
```

### 5. Middleware Layer (`src/main/python/middleware/`)

#### Security Middleware (`middleware/security.py`)
```python
class SecurityMiddleware:
    - CSRF protection
    - Security headers (HSTS, CSP, X-Frame-Options)
    - Input validation
    - Request size limits
    - Rate limiting
```

#### Session Middleware (`middleware/session.py`)
```python
class SessionMiddleware:
    - Session creation and validation
    - Session timeout management
    - Session rotation
    - Anti-session-hijacking measures
```

### 6. Utils Layer (`src/main/python/utils/`)

#### Scoring Engine (`utils/scoring.py`)
```python
class ScoringEngine:
    async def calculate_final_scores(responses) -> Dict:
        """
        Calculates comprehensive scores:
        - Module scores
        - Total score
        - Safety question pass rate
        - Speaking performance
        - Pass/fail determination
        """

    def calculate_module_score(responses, module) -> float
    def check_safety_threshold(responses) -> bool
```

#### Anti-Cheating Service (`utils/anti_cheating.py`)
```python
class AntiCheatingService:
    async def record_session_start(assessment_id, request)
    async def detect_suspicious_activity(assessment_id) -> bool
    async def validate_session(session_id) -> bool

    Measures:
    - IP address tracking
    - User agent validation
    - Time limit enforcement
    - Question randomization
    - Session hijacking prevention
```

## Data Flow

### Assessment Creation Flow
```
1. User Registration
   └─> POST /api/v1/assessment/register
       └─> Create User record
           └─> Return user_id

2. Assessment Creation
   └─> POST /api/v1/assessment/create
       └─> AssessmentEngine.create_assessment()
           └─> Generate session_id
           └─> Create Assessment record
           └─> Set expiration time
           └─> Return assessment_id + session_id

3. Assessment Start
   └─> POST /api/v1/assessment/{id}/start
       └─> AssessmentEngine.start_assessment()
           └─> Update status to IN_PROGRESS
           └─> Generate question set (randomized)
           └─> Return questions for all modules
```

### Response Submission Flow
```
1. Answer Submission
   └─> POST /api/v1/assessment/{id}/answer
       └─> AssessmentEngine.submit_response()
           └─> Validate assessment status
           └─> Check for duplicate submission
           └─> Score response
           │   └─> Multiple choice: exact match
           │   └─> Fill blank: flexible matching
           │   └─> Speaking: AI analysis
           └─> Create AssessmentResponse record
           └─> Return result + feedback

2. Speaking Response
   └─> POST /api/v1/assessment/{id}/speaking
       └─> Save audio file
       └─> AIService.analyze_speech_response()
           └─> Transcribe audio
           └─> Evaluate pronunciation
           └─> Evaluate fluency
           └─> Evaluate appropriateness
           └─> Calculate points (0-20)
       └─> Create AssessmentResponse record
       └─> Return analysis + points
```

### Assessment Completion Flow
```
1. Complete Assessment
   └─> POST /api/v1/assessment/{id}/complete
       └─> AssessmentEngine.complete_assessment()
           └─> Get all responses
           └─> ScoringEngine.calculate_final_scores()
               └─> Calculate module scores
               └─> Calculate total score
               └─> Check safety threshold (80%)
               └─> Check speaking threshold (12/20)
               └─> Determine pass/fail
           └─> Update Assessment record
               └─> Set status = COMPLETED
               └─> Set completed_at timestamp
               └─> Store all scores
               └─> Store pass/fail result
           └─> Generate feedback
           └─> Return comprehensive results
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────────┐
│       users         │
├─────────────────────┤
│ id (PK)            │
│ first_name         │
│ last_name          │
│ email (UNIQUE)     │
│ nationality        │
│ division           │
│ department         │
│ is_active          │
│ created_at         │
│ updated_at         │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────────────┐
│      assessments            │
├─────────────────────────────┤
│ id (PK)                    │
│ user_id (FK)               │
│ session_id (UNIQUE)        │
│ division                   │
│ status                     │
│ started_at                 │
│ completed_at               │
│ expires_at                 │
│ total_score                │
│ listening_score            │
│ time_numbers_score         │
│ grammar_score              │
│ vocabulary_score           │
│ reading_score              │
│ speaking_score             │
│ passed                     │
│ safety_questions_passed    │
│ speaking_threshold_passed  │
│ ip_address                 │
│ user_agent                 │
│ feedback (JSON)            │
│ analytics_data (JSON)      │
│ created_at                 │
│ updated_at                 │
└──────────┬──────────────────┘
           │
           │ 1:N
           │
┌──────────▼────────────────────┐
│   assessment_responses        │
├───────────────────────────────┤
│ id (PK)                      │
│ assessment_id (FK)           │
│ question_id (FK)             │
│ user_answer                  │
│ is_correct                   │
│ points_earned                │
│ points_possible              │
│ time_spent_seconds           │
│ answered_at                  │
│ audio_file_path              │
│ speech_analysis (JSON)       │
│ created_at                   │
│ updated_at                   │
└──────────────────────────────┘
           │
           │ N:1
           │
┌──────────▼──────────┐
│     questions       │
├─────────────────────┤
│ id (PK)            │
│ module_type        │
│ division           │
│ question_type      │
│ question_text      │
│ options (JSON)     │
│ correct_answer     │
│ audio_file_path    │
│ difficulty_level   │
│ is_safety_related  │
│ points             │
│ metadata (JSON)    │
│ created_at         │
│ updated_at         │
└────────────────────┘
```

## Security Architecture

### Authentication & Authorization
- Session-based authentication using Redis
- Secure session cookies with HttpOnly and SameSite flags
- CSRF token validation
- Role-based access control (RBAC) for admin functions

### Data Protection
- Password hashing using bcrypt
- Sensitive data encryption at rest
- TLS/SSL for data in transit
- SQL injection prevention via parameterized queries

### Anti-Cheating Measures
- Session IP address binding
- User agent validation
- Time limit enforcement
- Question randomization
- Tab/window switching detection (frontend)
- Multiple submission prevention

### Rate Limiting
- Global rate limit: 100 requests/minute
- Authentication rate limit: 5 attempts/5 minutes
- Per-endpoint specific limits

## Scalability

### Horizontal Scaling
- Stateless application design
- Session storage in Redis (shared state)
- Database connection pooling
- Load balancing via Nginx

### Vertical Scaling
- Async I/O for concurrent request handling
- Database query optimization
- Redis caching for frequently accessed data
- Background task processing via Celery

### Performance Optimization
- Database indexes on frequently queried fields
- Lazy loading of relationships
- Response compression
- Static file caching
- CDN for audio files

## Monitoring & Logging

### Application Logs
- Request/response logging
- Error tracking and stack traces
- Performance metrics
- Security events

### Metrics Collection
- Response times
- Request counts
- Error rates
- Database query performance
- Cache hit rates

### Health Checks
- `/health` endpoint for liveness probe
- Database connectivity check
- Redis connectivity check
- External service availability

## Deployment Architecture

### Docker Containers
```yaml
services:
  web:
    image: cruise-assessment:latest
    ports: ["8000:8000"]
    environment: [DATABASE_URL, REDIS_URL, etc.]

  db:
    image: postgres:15
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7
    volumes: ["redis_data:/data"]

  nginx:
    image: nginx:latest
    ports: ["80:80", "443:443"]
    volumes: ["./nginx.conf:/etc/nginx/nginx.conf"]
```

### Production Infrastructure
- Load Balancer: Nginx/HAProxy
- Application Servers: Multiple Uvicorn workers
- Database: PostgreSQL with replication
- Cache: Redis cluster
- Storage: S3/MinIO for audio files
- Monitoring: Prometheus + Grafana

## Future Enhancements

1. **Microservices Architecture**
   - Separate assessment engine service
   - Dedicated AI/ML service
   - Analytics service

2. **Real-time Features**
   - WebSocket for live progress updates
   - Real-time proctoring
   - Live admin dashboard

3. **Advanced ML**
   - Custom speech recognition models
   - Adaptive difficulty
   - Predictive analytics

4. **Mobile Support**
   - Native mobile apps
   - Offline assessment capability
   - Mobile-optimized audio recording

---

**Document Version**: 1.0
**Last Updated**: 2025-09-30
**Author**: Development Team
