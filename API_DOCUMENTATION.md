# API Documentation

Complete API reference for the Cruise Employee English Assessment Platform.

## Base URL

```
Development: http://127.0.0.1:8000
Production: https://assessment.example.com
```

## Authentication

Most endpoints require session-based authentication. Authentication cookies are automatically managed by the browser.

## Response Format

All API responses follow this structure:

```json
{
  "status": "success|error",
  "data": {},
  "message": "Optional message",
  "errors": []
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400  | Bad Request - Invalid input |
| 401  | Unauthorized - Authentication required |
| 403  | Forbidden - Insufficient permissions |
| 404  | Not Found - Resource doesn't exist |
| 422  | Validation Error - Invalid data format |
| 429  | Too Many Requests - Rate limit exceeded |
| 500  | Internal Server Error |

---

## Assessment Endpoints

### Register Candidate

Register a new candidate for assessment.

**Endpoint:** `POST /api/v1/assessment/register`

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "nationality": "USA",
  "division": "hotel",
  "department": "Front Desk / Guest Services"
}
```

**Response:** `201 Created`
```json
{
  "user_id": 123,
  "message": "Candidate registered successfully",
  "next_step": "create_assessment"
}
```

**Validation Rules:**
- `first_name`: Required, max 100 characters
- `last_name`: Required, max 100 characters
- `email`: Required, valid email format, unique
- `nationality`: Required, max 100 characters
- `division`: Required, one of: hotel, marine, casino
- `department`: Required, must match division's valid departments

---

### Create Assessment

Create a new assessment session for a registered candidate.

**Endpoint:** `POST /api/v1/assessment/create`

**Request Parameters:**
```json
{
  "user_id": 123,
  "division": "hotel"
}
```

**Response:** `201 Created`
```json
{
  "assessment_id": 456,
  "session_id": "assess_123_1696089600",
  "division": "hotel",
  "expires_at": "2025-09-30T14:00:00Z",
  "status": "created",
  "next_step": "start_assessment"
}
```

**Business Rules:**
- User must exist
- User cannot have multiple incomplete assessments
- Session expires after 2 hours
- Division must match user's division

---

### Start Assessment

Start an assessment and retrieve questions.

**Endpoint:** `POST /api/v1/assessment/{assessment_id}/start`

**Response:** `200 OK`
```json
{
  "status": "started",
  "assessment_data": {
    "assessment_id": 456,
    "session_id": "assess_123_1696089600",
    "status": "in_progress",
    "expires_at": "2025-09-30T14:00:00Z",
    "total_questions": 21,
    "questions": {
      "listening": [
        {
          "id": 1,
          "question_text": "Guest says: 'I'd like to book a table for four at 7 PM.' What time is the reservation?",
          "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
          "question_type": "multiple_choice",
          "points": 4,
          "audio_file": "/static/audio/listening_1.mp3",
          "is_safety_related": false
        }
      ],
      "time_numbers": [...],
      "grammar": [...],
      "vocabulary": [...],
      "reading": [...],
      "speaking": [...]
    }
  },
  "instructions": {
    "listening": "Listen carefully to each dialogue...",
    "time_numbers": "Fill in the missing time or number...",
    "grammar": "Choose the correct answer...",
    "vocabulary": "Match words to their correct categories...",
    "reading": "Read the text and choose the best title...",
    "speaking": "Speak your response clearly..."
  }
}
```

**Business Rules:**
- Assessment must be in `NOT_STARTED` status
- Questions are randomized for each session
- 4 questions per module (except speaking: 1-2)

---

### Submit Answer

Submit an answer for a question.

**Endpoint:** `POST /api/v1/assessment/{assessment_id}/answer`

**Request Body:**
```json
{
  "question_id": 1,
  "user_answer": "7 PM",
  "time_spent": 15
}
```

**Response:** `200 OK`
```json
{
  "status": "answer_recorded",
  "result": {
    "is_correct": true,
    "points_earned": 4,
    "points_possible": 4,
    "feedback": "Correct! Well done."
  }
}
```

**Business Rules:**
- Assessment must be `IN_PROGRESS`
- Question can only be answered once
- Time spent is optional but recommended

---

### Submit Speaking Response

Submit audio recording for speaking module.

**Endpoint:** `POST /api/v1/assessment/{assessment_id}/speaking`

**Request:** `multipart/form-data`
```
question_id: 10
audio_file: [audio file binary]
```

**Response:** `200 OK`
```json
{
  "status": "speaking_response_processed",
  "transcript": "I apologize for the inconvenience. I'll send someone to adjust...",
  "points_earned": 18,
  "feedback": {
    "pronunciation_score": 9,
    "fluency_score": 8,
    "appropriateness_score": 10,
    "clarity_score": 9,
    "overall": "Excellent response with clear communication"
  }
}
```

**Requirements:**
- File format: WAV, MP3, or M4A
- Max file size: 50MB
- Max duration: 20 seconds
- Audio quality: 16kHz or higher

**AI Analysis Criteria:**
- Pronunciation (0-5 points)
- Fluency (0-5 points)
- Appropriateness (0-5 points)
- Clarity (0-5 points)
- Total: 20 points maximum

---

### Complete Assessment

Complete assessment and calculate final results.

**Endpoint:** `POST /api/v1/assessment/{assessment_id}/complete`

**Response:** `200 OK`
```json
{
  "status": "completed",
  "results": {
    "assessment_id": 456,
    "total_score": 85,
    "passed": true,
    "scores": {
      "listening": 16,
      "time_numbers": 16,
      "grammar": 12,
      "vocabulary": 12,
      "reading": 12,
      "speaking": 17,
      "total_score": 85,
      "safety_pass_rate": 0.9
    },
    "feedback": {
      "overall_result": "PASS",
      "total_score": 85,
      "breakdown": {...},
      "recommendations": []
    },
    "completed_at": "2025-09-30T12:30:00Z"
  },
  "certificate": {
    "issued": true,
    "score": 85,
    "grade": "PASS",
    "valid_until": "2026-12-31"
  }
}
```

**Pass/Fail Criteria:**
- Total score >= 70/100 (70%)
- Safety questions >= 80% correct
- Speaking score >= 12/20 (60%)
- All three conditions must be met

---

### Get Assessment Status

Get current assessment status and progress.

**Endpoint:** `GET /api/v1/assessment/{assessment_id}/status`

**Response:** `200 OK`
```json
{
  "assessment_id": 456,
  "status": "in_progress",
  "started_at": "2025-09-30T10:00:00Z",
  "completed_at": null,
  "expires_at": "2025-09-30T14:00:00Z",
  "total_score": 0,
  "progress": {
    "questions_answered": 8,
    "total_questions": 21
  }
}
```

---

### Load Question Bank (Admin Only)

Load questions into the database.

**Endpoint:** `POST /api/v1/assessment/load-questions`

**Request Body:**
```json
{
  "admin_key": "admin123"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Question bank loaded successfully",
  "divisions": ["hotel", "marine", "casino"],
  "modules": ["listening", "time_numbers", "grammar", "vocabulary", "reading", "speaking"]
}
```

---

## Admin Endpoints

### List All Assessments

**Endpoint:** `GET /api/v1/admin/assessments`

**Query Parameters:**
- `status`: Filter by status (not_started, in_progress, completed, expired)
- `division`: Filter by division
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)
- `page`: Page number (default: 1)
- `limit`: Results per page (default: 50)

**Response:** `200 OK`
```json
{
  "total": 150,
  "page": 1,
  "pages": 3,
  "assessments": [
    {
      "id": 456,
      "user": {
        "id": 123,
        "name": "John Doe",
        "email": "john.doe@example.com"
      },
      "division": "hotel",
      "status": "completed",
      "total_score": 85,
      "passed": true,
      "started_at": "2025-09-30T10:00:00Z",
      "completed_at": "2025-09-30T12:30:00Z"
    }
  ]
}
```

---

### List All Users

**Endpoint:** `GET /api/v1/admin/users`

**Response:** `200 OK`
```json
{
  "total": 200,
  "users": [
    {
      "id": 123,
      "name": "John Doe",
      "email": "john.doe@example.com",
      "division": "hotel",
      "department": "Front Desk",
      "assessments_count": 1,
      "latest_score": 85,
      "is_active": true
    }
  ]
}
```

---

### Export Results

Export assessment results in various formats.

**Endpoint:** `POST /api/v1/admin/export`

**Request Body:**
```json
{
  "format": "excel",
  "filters": {
    "division": "hotel",
    "date_from": "2025-09-01",
    "date_to": "2025-09-30"
  }
}
```

**Response:** `200 OK`
- Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- File download

**Supported Formats:**
- `excel`: XLSX file
- `csv`: CSV file
- `pdf`: PDF report
- `json`: JSON data

---

## Analytics Endpoints

### Overview Statistics

**Endpoint:** `GET /api/v1/analytics/overview`

**Response:** `200 OK`
```json
{
  "total_assessments": 500,
  "completed_assessments": 450,
  "pass_rate": 0.75,
  "average_score": 78.5,
  "by_division": {
    "hotel": {
      "total": 300,
      "pass_rate": 0.78,
      "average_score": 79.2
    },
    "marine": {
      "total": 150,
      "pass_rate": 0.72,
      "average_score": 77.5
    },
    "casino": {
      "total": 50,
      "pass_rate": 0.70,
      "average_score": 76.8
    }
  },
  "by_module": {
    "listening": {"average": 13.2, "pass_rate": 0.82},
    "time_numbers": {"average": 12.8, "pass_rate": 0.80},
    "grammar": {"average": 11.5, "pass_rate": 0.72},
    "vocabulary": {"average": 12.0, "pass_rate": 0.75},
    "reading": {"average": 11.8, "pass_rate": 0.74},
    "speaking": {"average": 15.2, "pass_rate": 0.76}
  }
}
```

---

### Division Performance

**Endpoint:** `GET /api/v1/analytics/division/{division}`

**Response:** `200 OK`
```json
{
  "division": "hotel",
  "total_assessments": 300,
  "pass_rate": 0.78,
  "average_score": 79.2,
  "by_department": {
    "Front Desk": {
      "total": 80,
      "pass_rate": 0.82,
      "average_score": 81.5
    },
    "Housekeeping": {
      "total": 70,
      "pass_rate": 0.75,
      "average_score": 77.8
    }
  },
  "module_performance": {
    "listening": 13.5,
    "time_numbers": 13.2,
    "grammar": 11.8,
    "vocabulary": 12.5,
    "reading": 12.2,
    "speaking": 16.0
  }
}
```

---

### Performance Trends

**Endpoint:** `GET /api/v1/analytics/trends`

**Query Parameters:**
- `period`: day, week, month (default: month)
- `date_from`: Start date
- `date_to`: End date

**Response:** `200 OK`
```json
{
  "period": "month",
  "data": [
    {
      "date": "2025-09",
      "total_assessments": 150,
      "pass_rate": 0.75,
      "average_score": 78.5
    }
  ]
}
```

---

## UI Routes

These routes return HTML pages (not JSON):

- `GET /` - Homepage
- `GET /register` - Registration form
- `GET /instructions` - Assessment instructions
- `GET /question/{question_num}` - Question page (1-21)
- `POST /submit` - Submit answer and redirect
- `GET /results` - Results page

---

## WebSocket Endpoints

### Real-time Progress Updates (Future)

**Endpoint:** `WS /ws/assessment/{assessment_id}`

**Messages:**
```json
{
  "type": "progress_update",
  "data": {
    "questions_answered": 10,
    "current_score": 40
  }
}
```

---

## Rate Limits

| Endpoint Category | Limit |
|------------------|-------|
| Assessment endpoints | 100 requests/minute |
| Authentication | 5 requests/5 minutes |
| Admin endpoints | 200 requests/minute |
| Analytics endpoints | 50 requests/minute |

---

## Data Models

### Division Types
- `hotel` - Hotel Operations
- `marine` - Marine Operations
- `casino` - Casino Operations

### Module Types
- `listening` - Listening Module (16 points)
- `time_numbers` - Time & Numbers Module (16 points)
- `grammar` - Grammar Module (16 points)
- `vocabulary` - Vocabulary Module (16 points)
- `reading` - Reading Module (16 points)
- `speaking` - Speaking Module (20 points)

### Assessment Status
- `not_started` - Assessment created but not started
- `in_progress` - Assessment in progress
- `completed` - Assessment completed
- `expired` - Assessment expired (2 hour timeout)

### Question Types
- `multiple_choice` - Multiple choice questions
- `fill_blank` - Fill in the blank
- `category_match` - Category matching
- `title_selection` - Select best title
- `speaking_response` - Spoken response

---

## Code Examples

### Python (httpx)

```python
import httpx

async def create_and_start_assessment():
    async with httpx.AsyncClient() as client:
        # Register candidate
        register_response = await client.post(
            "http://127.0.0.1:8000/api/v1/assessment/register",
            json={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "nationality": "USA",
                "division": "hotel",
                "department": "Front Desk"
            }
        )
        user_id = register_response.json()["user_id"]

        # Create assessment
        create_response = await client.post(
            "http://127.0.0.1:8000/api/v1/assessment/create",
            json={"user_id": user_id, "division": "hotel"}
        )
        assessment_id = create_response.json()["assessment_id"]

        # Start assessment
        start_response = await client.post(
            f"http://127.0.0.1:8000/api/v1/assessment/{assessment_id}/start"
        )
        questions = start_response.json()["assessment_data"]["questions"]

        return assessment_id, questions
```

### JavaScript (fetch)

```javascript
async function submitAnswer(assessmentId, questionId, answer) {
  const response = await fetch(
    `http://127.0.0.1:8000/api/v1/assessment/${assessmentId}/answer`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question_id: questionId,
        user_answer: answer,
        time_spent: 15
      }),
      credentials: 'include'
    }
  );

  const result = await response.json();
  return result;
}
```

### cURL

```bash
# Register candidate
curl -X POST "http://127.0.0.1:8000/api/v1/assessment/register" \
     -H "Content-Type: application/json" \
     -d '{
       "first_name": "John",
       "last_name": "Doe",
       "email": "john@example.com",
       "nationality": "USA",
       "division": "hotel",
       "department": "Front Desk"
     }'

# Create assessment
curl -X POST "http://127.0.0.1:8000/api/v1/assessment/create" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 123,
       "division": "hotel"
     }'
```

---

## Testing

Interactive API documentation available at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

---

**API Version**: 1.0
**Last Updated**: 2025-09-30
**Contact**: Development Team
