# Cruise Employee English Assessment Platform

A comprehensive AI-powered English proficiency assessment platform designed specifically for cruise ship employees across Hotel, Marine, and Casino operations.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Project Statistics](#project-statistics)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Assessment Modules](#assessment-modules)
- [API Documentation](#api-documentation)
- [Development Guidelines](#development-guidelines)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Overview

The Cruise Employee English Assessment Platform is a web-based application that provides comprehensive English proficiency testing tailored to the cruise industry. It assesses candidates across six critical language competency areas with division-specific content for Hotel, Marine, and Casino operations.

### Purpose

- Evaluate English proficiency of cruise ship employees
- Ensure consistent language standards across all divisions
- Provide objective, AI-powered assessment scoring
- Generate detailed performance analytics and recommendations
- Support compliance with maritime communication requirements

## Key Features

### Assessment Capabilities

- **6 Comprehensive Modules**: Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking
- **Division-Specific Content**: Customized questions for 16 departments across 3 operational divisions
- **AI-Powered Scoring**: Intelligent speech analysis and automated grading
- **Multi-Format Questions**: Multiple choice, fill-in-the-blank, category matching, speaking responses
- **Safety-Critical Assessment**: Special evaluation of safety-related communication skills

### Technical Features

- **FastAPI Backend**: High-performance async REST API
- **PostgreSQL Database**: Robust data storage with SQLAlchemy ORM
- **Real-time Processing**: Async assessment flow with minimal latency
- **Anti-Cheating Measures**: Session management, IP tracking, time limits
- **Comprehensive Analytics**: Performance tracking, trend analysis, reporting
- **Scalable Architecture**: Docker-ready with horizontal scaling support

### AI/ML Integration

- **Speech Recognition**: AI-powered audio transcription
- **Response Analysis**: Natural language processing for answer evaluation
- **Performance Prediction**: ML-driven candidate performance insights
- **Content Generation**: AI-generated practice scenarios and feedback

## Project Statistics

- **Total Assessment Questions**: 288 (96 per division)
- **Speaking Scenarios**: 160 (comprehensive workplace situations)
- **Question Types**: 5 (Multiple choice, Fill-blank, Category match, Title selection, Speaking)
- **Departments Covered**: 16 (8 Hotel, 3 Marine, 3 Casino, 2 Safety)
- **Assessment Modules**: 6 (Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking)
- **Maximum Score**: 100 points (20 from speaking module)
- **Passing Threshold**: 70% overall + safety questions + 60% speaking minimum

## Technology Stack

### Backend

- **Framework**: FastAPI 0.104.1
- **Language**: Python 3.10+
- **ASGI Server**: Uvicorn with standard extras
- **ORM**: SQLAlchemy 2.0.23 (async)
- **Database Driver**: asyncpg 0.29.0, psycopg2-binary 2.9.9
- **Migrations**: Alembic 1.12.1

### AI & ML

- **AI Services**: OpenAI API 1.3.7, Anthropic Claude 0.7.7
- **Audio Processing**: librosa 0.10.1, soundfile 0.12.1
- **ML Libraries**: scikit-learn 1.3.2, numpy 1.24.3, pandas 2.0.3

### Frontend & Templates

- **Templating**: Jinja2 3.1.2
- **Static Files**: aiofiles 23.2.1
- **Document Generation**: python-docx 1.1.0

### Security & Session Management

- **Authentication**: python-jose[cryptography] 3.3.0
- **Password Hashing**: passlib[bcrypt] 1.7.4
- **Session Storage**: Redis 5.0.1
- **Background Tasks**: Celery 5.3.4

### Development & Testing

- **Testing Framework**: pytest 7.4.3, pytest-asyncio 0.21.1
- **HTTP Client**: httpx 0.25.2
- **Environment**: python-dotenv 1.0.0

### Infrastructure

- **Containerization**: Docker with docker-compose
- **Web Server**: Nginx (reverse proxy)
- **Database**: PostgreSQL 15+
- **Cache/Queue**: Redis 7+

## Project Structure

```
cruise-assessment/
├── src/
│   ├── main/
│   │   └── python/
│   │       ├── api/                    # API routes and endpoints
│   │       │   └── routes/
│   │       │       ├── assessment.py   # Assessment CRUD operations
│   │       │       ├── admin.py        # Admin endpoints
│   │       │       ├── analytics.py    # Analytics and reporting
│   │       │       └── ui.py          # Frontend page routes
│   │       ├── core/                   # Core business logic
│   │       │   ├── config.py          # Application configuration
│   │       │   ├── database.py        # Database connection
│   │       │   └── assessment_engine.py # Assessment flow control
│   │       ├── models/                 # Database models
│   │       │   ├── base.py            # Base model class
│   │       │   └── assessment.py      # Assessment-related models
│   │       ├── services/               # External services
│   │       │   └── ai_service.py      # AI/ML integration
│   │       ├── utils/                  # Utility functions
│   │       │   ├── scoring.py         # Scoring algorithms
│   │       │   └── anti_cheating.py   # Security measures
│   │       ├── middleware/             # HTTP middleware
│   │       │   ├── security.py        # Security headers, CSRF
│   │       │   └── session.py         # Session management
│   │       ├── data/                   # Data management
│   │       │   ├── questions_config.json     # UI question bank
│   │       │   ├── question_bank_sample.json # Sample data
│   │       │   ├── question_bank_loader.py   # DB loader
│   │       │   └── generate_question_bank.py # Question generator
│   │       ├── training/               # ML model training
│   │       ├── evaluation/             # Model evaluation
│   │       ├── inference/              # Inference services
│   │       ├── main.py                # Application entry point
│   │       └── ui_application.py      # UI-specific setup
│   └── test/                          # Test suite
│       ├── unit/                      # Unit tests
│       └── integration/               # Integration tests
├── scripts/                           # Utility scripts
│   ├── create_department_scenarios.py
│   ├── create_operations_document.py
│   ├── create_operations_document_en.py
│   └── update_operations_documents.py
├── static/                            # Static web assets
│   ├── css/                          # Stylesheets
│   ├── js/                           # JavaScript files
│   └── audio/                        # Audio samples
├── templates/                         # Jinja2 templates
│   ├── assessment/                   # Assessment pages
│   ├── admin/                        # Admin pages
│   └── layouts/                      # Layout templates
├── data/                             # Data storage
│   ├── raw/                          # Raw question banks
│   ├── processed/                    # Processed data
│   └── audio/                        # Audio recordings
├── docs/                             # Documentation
├── logs/                             # Application logs
├── models/                           # ML models
├── experiments/                      # ML experiments
├── notebooks/                        # Jupyter notebooks
├── output/                           # Generated outputs
├── docker-compose.yml               # Docker composition
├── Dockerfile                       # Container definition
├── nginx.conf                       # Nginx configuration
├── requirements.txt                 # Python dependencies
├── run_server.py                    # Development server
├── CLAUDE.md                        # Claude Code guidelines
├── ARCHITECTURE.md                  # Architecture documentation
├── API_DOCUMENTATION.md            # API reference
├── DEPLOYMENT.md                   # Deployment guide
└── README.md                        # This file
```

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 15 or higher
- Redis 7 or higher
- Git

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd cruise-assessment
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Database

```bash
# Create PostgreSQL database
createdb english_assessment

# Run migrations
alembic upgrade head
```

### Step 5: Configure Environment

Create a `.env` file in the project root:

```env
# Application
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/english_assessment

# AI Services
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# Redis
REDIS_URL=redis://localhost:6379
```

## Configuration

The application uses a centralized configuration system in `src/main/python/core/config.py`. Key configuration areas:

### Application Settings

- `APP_NAME`: Application name
- `VERSION`: Version number
- `DEBUG`: Debug mode (development only)
- `HOST`: Server host
- `PORT`: Server port

### Security Settings

- `SECRET_KEY`: JWT secret key
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time
- `ALLOWED_ORIGINS`: CORS allowed origins

### Database Settings

- `DATABASE_URL`: PostgreSQL connection string
- Connection pooling and timeout settings

### Assessment Settings

- `PASS_THRESHOLD_TOTAL`: Overall passing score (70%)
- `PASS_THRESHOLD_SAFETY`: Safety questions threshold (80%)
- `PASS_THRESHOLD_SPEAKING`: Speaking minimum score (12/20)

### Session Settings

- `SESSION_TIMEOUT_SECONDS`: Session timeout (4 hours)
- `SESSION_WARNING_SECONDS`: Warning before timeout (5 minutes)

## Running the Application

### Development Server

```bash
python run_server.py
```

The application will be available at:

- **Homepage**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Alternative API Docs**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health

### Production Server

```bash
# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Using Docker
docker-compose up -d
```

### Load Question Bank

Before running assessments, load the question bank:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/assessment/load-questions" \
     -H "Content-Type: application/json" \
     -d '{"admin_key": "admin123"}'
```

## Assessment Modules

### 1. Listening Module (16 points)

- **Questions**: 4 per division
- **Format**: Multiple choice
- **Content**: Audio dialogues from workplace scenarios
- **Skills Tested**: Comprehension, number recognition, time understanding

### 2. Time & Numbers Module (16 points)

- **Questions**: 4 per division
- **Format**: Fill-in-the-blank
- **Content**: Times, dates, room numbers, measurements
- **Skills Tested**: Numerical comprehension, time formats

### 3. Grammar Module (16 points)

- **Questions**: 4 per division
- **Format**: Multiple choice
- **Content**: Service industry grammar, polite expressions
- **Skills Tested**: Grammar accuracy, professional language

### 4. Vocabulary Module (16 points)

- **Questions**: 4 per division
- **Format**: Category matching
- **Content**: Department-specific terminology
- **Skills Tested**: Technical vocabulary, categorization

### 5. Reading Module (16 points)

- **Questions**: 4 per division
- **Format**: Title selection
- **Content**: Notices, schedules, safety protocols
- **Skills Tested**: Reading comprehension, main idea identification

### 6. Speaking Module (20 points)

- **Questions**: 1-2 per division
- **Format**: Audio recording response
- **Content**: Workplace scenarios and customer interactions
- **Skills Tested**: Pronunciation, fluency, appropriateness, clarity

## API Documentation

### Core Endpoints

#### Assessment Flow

```
POST   /api/v1/assessment/register        # Register candidate
POST   /api/v1/assessment/create          # Create assessment session
POST   /api/v1/assessment/{id}/start      # Start assessment
POST   /api/v1/assessment/{id}/answer     # Submit answer
POST   /api/v1/assessment/{id}/speaking   # Submit speaking response
POST   /api/v1/assessment/{id}/complete   # Complete assessment
GET    /api/v1/assessment/{id}/status     # Get assessment status
```

#### Admin Endpoints

```
GET    /api/v1/admin/assessments          # List all assessments
GET    /api/v1/admin/users                # List all users
GET    /api/v1/admin/questions            # Manage questions
POST   /api/v1/admin/export               # Export results
```

#### Analytics Endpoints

```
GET    /api/v1/analytics/overview         # Overall statistics
GET    /api/v1/analytics/division/{div}   # Division performance
GET    /api/v1/analytics/trends           # Performance trends
GET    /api/v1/analytics/candidates       # Candidate analysis
```

For detailed API documentation, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md) or visit `/docs` when the server is running.

## Development Guidelines

### Before Starting Any Task

1. Read `CLAUDE.md` for complete development rules
2. Follow the pre-task compliance checklist
3. Search for existing functionality before creating new files
4. Use proper module structure under `src/main/python/`

### Code Organization

- **NEVER** create files in root directory
- **ALWAYS** extend existing files instead of creating duplicates
- **USE** Task agents for operations >30 seconds
- **COMMIT** after every completed task
- **PUSH** to GitHub after every commit for backup

### Technical Debt Prevention

1. **Search First**: Use Grep/Glob to find existing implementations
2. **Analyze Existing**: Read and understand current patterns
3. **Decision Tree**: Can extend existing? Do it. Must create new? Document why.
4. **Follow Patterns**: Use established project patterns
5. **Validate**: Ensure no duplication or technical debt

## Testing

### Run Unit Tests

```bash
pytest src/test/unit/ -v
```

### Run Integration Tests

```bash
pytest src/test/integration/ -v
```

### Run All Tests

```bash
pytest src/test/ -v --cov=src/main/python
```

### Test Coverage

```bash
pytest --cov=src/main/python --cov-report=html
```

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t cruise-assessment:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Production Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Change `SECRET_KEY` to secure random value
- [ ] Configure production database
- [ ] Set up Redis for sessions
- [ ] Configure CORS allowed origins
- [ ] Enable HTTPS/SSL
- [ ] Set up backup strategy
- [ ] Configure monitoring and logging
- [ ] Review security headers
- [ ] Set up rate limiting

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Contributing

### Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Follow the development guidelines in `CLAUDE.md`
4. Commit your changes (`git commit -m 'Add AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

### Code Standards

- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Write docstrings for all modules, classes, and functions
- Maintain test coverage above 80%
- Document all API endpoints

## License

This project is proprietary software developed for cruise line operations. All rights reserved.

## Support

For technical support or questions:

- Review the documentation in the `docs/` directory
- Check the API documentation at `/docs` endpoint
- Refer to `ARCHITECTURE.md` for technical details
- See `CLAUDE.md` for development guidelines

## Acknowledgments

- Built with FastAPI and modern Python async capabilities
- AI-powered by OpenAI and Anthropic Claude
- Designed for the maritime and cruise industry
- Developed with Claude Code assistance

---

**Version**: 1.0.0
**Last Updated**: 2025-09-30
**Status**: Production Ready
