#!/usr/bin/env python3
"""
Interactive English Assessment Demo
Allows users to actually take the assessment
"""

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import json
import random

app = FastAPI(title="English Assessment - Interactive Demo")

# Sample questions from our question bank
SAMPLE_QUESTIONS = {
    "hotel_listening": [
        {
            "id": 1,
            "question": "Guest says: 'I'd like to book a table for four at 7 PM.' What time is the reservation?",
            "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
            "correct": "7 PM",
            "audio_text": "I'd like to book a table for four at seven PM tonight."
        },
        {
            "id": 2,
            "question": "Guest complaint: 'The air conditioning is too cold in room 8254.' What is the room number?",
            "options": ["8245", "8254", "8524", "2548"],
            "correct": "8254",
            "audio_text": "The air conditioning is way too cold in room eight-two-five-four."
        }
    ],
    "hotel_grammar": [
        {
            "id": 3,
            "question": "___ I help you with your luggage?",
            "options": ["May", "Do", "Will", "Am"],
            "correct": "May"
        },
        {
            "id": 4,
            "question": "Your room ___ been cleaned and is ready.",
            "options": ["have", "has", "had", "having"],
            "correct": "has"
        }
    ],
    "hotel_time_numbers": [
        {
            "id": 5,
            "question": "Breakfast is served from ___ to 10:30 AM.",
            "answer": "7:00",
            "hint": "Format: H:MM"
        },
        {
            "id": 6,
            "question": "Your cabin number is ___.",
            "answer": "8254",
            "hint": "4-digit number"
        }
    ]
}

# Store user responses (in memory for demo)
user_responses = {}
current_question = 0

@app.get("/", response_class=HTMLResponse)
def start_assessment():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🚢 English Assessment - Take the Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .header { text-align: center; background: #1e3a8a; color: white; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
            .division-card { background: #e8f4fd; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 5px solid #1e3a8a; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin: 10px; }
            .btn:hover { background: #1e40af; }
            .info { background: #f0f9ff; padding: 15px; border-radius: 6px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚢 Cruise Employee English Assessment</h1>
                <p>Interactive Assessment Demo</p>
            </div>

            <div class="info">
                <h3>📋 Assessment Overview</h3>
                <ul>
                    <li><strong>Duration:</strong> This demo has 6 sample questions</li>
                    <li><strong>Modules:</strong> Listening, Grammar, Time & Numbers</li>
                    <li><strong>Division:</strong> Hotel Operations</li>
                    <li><strong>Scoring:</strong> Immediate feedback after each question</li>
                </ul>
            </div>

            <div class="division-card">
                <h2>🏨 Hotel Operations Assessment</h2>
                <p>You'll be tested on scenarios common in cruise ship hotel operations:</p>
                <ul>
                    <li>Guest check-in conversations</li>
                    <li>Room service requests</li>
                    <li>Service grammar and vocabulary</li>
                    <li>Time and number comprehension</li>
                </ul>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" onclick="startAssessment()">🚀 Start Assessment</button>
                <button class="btn" onclick="viewSampleQuestions()" style="background: #059669;">📝 View Sample Questions</button>
            </div>
        </div>

        <script>
            function startAssessment() {
                window.location.href = '/assessment/start';
            }
            function viewSampleQuestions() {
                window.location.href = '/sample-questions';
            }
        </script>
    </body>
    </html>
    """)

@app.get("/assessment/start", response_class=HTMLResponse)
def start_test():
    global current_question
    current_question = 0

    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Assessment Started</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
            .progress { background: #e5e7eb; height: 20px; border-radius: 10px; margin: 20px 0; }
            .progress-bar { background: #10b981; height: 100%; border-radius: 10px; width: 0%; transition: width 0.3s; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Assessment Started!</h1>
            <div class="progress">
                <div class="progress-bar" id="progress" style="width: 0%;"></div>
            </div>
            <p><strong>Progress:</strong> 0 of 6 questions completed</p>

            <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>📋 Instructions:</h3>
                <ul>
                    <li>Answer each question to the best of your ability</li>
                    <li>You'll get immediate feedback</li>
                    <li>Click "Next Question" to continue</li>
                    <li>Your score will be calculated at the end</li>
                </ul>
            </div>

            <button class="btn" onclick="nextQuestion()">➡️ Start First Question</button>
        </div>

        <script>
            function nextQuestion() {
                window.location.href = '/question/1';
            }
        </script>
    </body>
    </html>
    """)

@app.get("/question/{question_id}", response_class=HTMLResponse)
def get_question(question_id: int):
    # Get question based on ID
    if question_id <= 2:
        questions = SAMPLE_QUESTIONS["hotel_listening"]
        question = questions[question_id - 1]
        question_type = "multiple_choice"
    elif question_id <= 4:
        questions = SAMPLE_QUESTIONS["hotel_grammar"]
        question = questions[question_id - 3]
        question_type = "multiple_choice"
    else:
        questions = SAMPLE_QUESTIONS["hotel_time_numbers"]
        question = questions[question_id - 5]
        question_type = "fill_blank"

    progress = (question_id - 1) * 16.67  # 6 questions = 100%

    if question_type == "multiple_choice":
        options_html = ""
        for i, option in enumerate(question["options"]):
            letter = chr(65 + i)  # A, B, C, D
            options_html += f'''
            <label style="display: block; padding: 15px; margin: 10px 0; background: #f8fafc; border-radius: 6px; cursor: pointer; border: 2px solid transparent;"
                   onclick="selectOption('{option}', this)">
                <input type="radio" name="answer" value="{option}" style="margin-right: 10px;">
                <strong>{letter})</strong> {option}
            </label>
            '''
    else:
        options_html = f'''
        <input type="text" name="answer" placeholder="Enter your answer"
               style="width: 100%; padding: 15px; border: 2px solid #e5e7eb; border-radius: 6px; font-size: 16px;"
               id="answer_input">
        <p style="color: #6b7280; font-style: italic;">Hint: {question.get("hint", "")}</p>
        '''

    # Add audio text for listening questions
    audio_section = ""
    if "audio_text" in question:
        audio_section = f'''
        <div style="background: #fef3c7; padding: 15px; border-radius: 6px; margin: 20px 0; border-left: 5px solid #f59e0b;">
            <h4>🎧 Audio Content:</h4>
            <p><em>"{question['audio_text']}"</em></p>
            <p style="font-size: 14px; color: #92400e;">In a real test, you would hear this audio and could replay it twice.</p>
        </div>
        '''

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {question_id}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }}
            .btn:disabled {{ background: #9ca3af; cursor: not-allowed; }}
            .progress {{ background: #e5e7eb; height: 20px; border-radius: 10px; margin: 20px 0; }}
            .progress-bar {{ background: #10b981; height: 100%; border-radius: 10px; width: {progress}%; transition: width 0.3s; }}
            .selected {{ border-color: #1e3a8a !important; background-color: #dbeafe !important; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>Question {question_id} of 6</h2>
                <span style="background: #e8f4fd; padding: 8px 16px; border-radius: 20px; font-weight: bold;">Hotel Operations</span>
            </div>

            <div class="progress">
                <div class="progress-bar"></div>
            </div>

            {audio_section}

            <div style="background: #f8fafc; padding: 25px; border-radius: 8px; margin: 20px 0;">
                <h3>{question["question"]}</h3>

                <form id="questionForm">
                    {options_html}
                </form>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" id="submitBtn" onclick="submitAnswer({question_id})" disabled>
                    ✅ Submit Answer
                </button>
            </div>
        </div>

        <script>
            let selectedAnswer = '';

            function selectOption(answer, element) {{
                // Remove previous selection
                document.querySelectorAll('label').forEach(label => {{
                    label.classList.remove('selected');
                }});

                // Add selection to clicked option
                element.classList.add('selected');
                selectedAnswer = answer;

                // Enable submit button
                document.getElementById('submitBtn').disabled = false;
            }}

            // For fill-in-the-blank questions
            document.addEventListener('input', function(e) {{
                if (e.target.name === 'answer') {{
                    selectedAnswer = e.target.value;
                    document.getElementById('submitBtn').disabled = selectedAnswer.trim() === '';
                }}
            }});

            function submitAnswer(questionId) {{
                if (!selectedAnswer.trim()) {{
                    alert('Please select or enter an answer');
                    return;
                }}

                // Submit via form
                fetch(`/submit/${{questionId}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                    body: `answer=${{encodeURIComponent(selectedAnswer)}}`
                }})
                .then(response => response.json())
                .then(data => {{
                    // Redirect to results page
                    window.location.href = `/result/${{questionId}}?correct=${{data.correct}}&answer=${{encodeURIComponent(selectedAnswer)}}`;
                }});
            }}
        </script>
    </body>
    </html>
    """)

@app.post("/submit/{question_id}")
async def submit_answer(question_id: int, answer: str = Form(...)):
    # Get correct answer
    if question_id <= 2:
        questions = SAMPLE_QUESTIONS["hotel_listening"]
        question = questions[question_id - 1]
        correct_answer = question["correct"]
    elif question_id <= 4:
        questions = SAMPLE_QUESTIONS["hotel_grammar"]
        question = questions[question_id - 3]
        correct_answer = question["correct"]
    else:
        questions = SAMPLE_QUESTIONS["hotel_time_numbers"]
        question = questions[question_id - 5]
        correct_answer = question["answer"]

    # Check if correct (flexible matching for time/numbers)
    is_correct = (
        answer.strip().lower() == correct_answer.lower() or
        answer.strip() == correct_answer or
        (question_id > 4 and answer.strip() in correct_answer)
    )

    # Store response
    user_responses[question_id] = {
        "answer": answer,
        "correct": is_correct,
        "correct_answer": correct_answer
    }

    return {"correct": is_correct, "correct_answer": correct_answer}

@app.get("/result/{question_id}", response_class=HTMLResponse)
def show_result(question_id: int, correct: bool, answer: str):
    response_data = user_responses.get(question_id, {})

    result_color = "#10b981" if correct else "#ef4444"
    result_icon = "✅" if correct else "❌"
    result_text = "Correct!" if correct else "Incorrect"

    next_question = question_id + 1
    next_button = f'''
        <button class="btn" onclick="nextQuestion({next_question})">➡️ Next Question</button>
    ''' if next_question <= 6 else '''
        <button class="btn" onclick="showFinalResults()" style="background: #10b981;">🎉 View Final Results</button>
    '''

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {question_id} Result</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }}
            .result {{ background: {result_color}; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; }}
            .feedback {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="result">
                <h2>{result_icon} {result_text}</h2>
                <p style="font-size: 18px; margin: 0;">Question {question_id} of 6</p>
            </div>

            <div class="feedback">
                <h3>📝 Your Answer:</h3>
                <p style="font-size: 18px;"><strong>"{answer}"</strong></p>

                <h3>✅ Correct Answer:</h3>
                <p style="font-size: 18px; color: #10b981;"><strong>"{response_data.get('correct_answer', '')}"</strong></p>

                {"<p style='color: #10b981;'>Great job! You understood the scenario correctly.</p>" if correct else "<p style='color: #ef4444;'>Keep practicing! Review similar scenarios to improve.</p>"}
            </div>

            <div style="text-align: center;">
                {next_button}
            </div>
        </div>

        <script>
            function nextQuestion(questionId) {{
                window.location.href = `/question/${{questionId}}`;
            }}

            function showFinalResults() {{
                window.location.href = '/final-results';
            }}
        </script>
    </body>
    </html>
    """)

@app.get("/final-results", response_class=HTMLResponse)
def final_results():
    total_questions = len(user_responses)
    correct_answers = sum(1 for resp in user_responses.values() if resp["correct"])
    score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    passed = score_percentage >= 70
    grade = "PASS" if passed else "FAIL"
    grade_color = "#10b981" if passed else "#ef4444"

    questions_html = ""
    for q_id, resp in user_responses.items():
        icon = "✅" if resp["correct"] else "❌"
        questions_html += f'''
        <div style="padding: 10px; margin: 5px 0; background: {'#f0fdf4' if resp['correct'] else '#fef2f2'}; border-radius: 6px;">
            <strong>Question {q_id}:</strong> {icon} {resp['answer']}
            {f"(Correct: {resp['correct_answer']})" if not resp['correct'] else ""}
        </div>
        '''

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Assessment Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; margin: 10px; }}
            .score {{ background: {grade_color}; color: white; padding: 30px; border-radius: 12px; text-align: center; margin: 30px 0; }}
            .details {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align: center;">🎉 Assessment Complete!</h1>

            <div class="score">
                <h2>Final Score: {correct_answers}/{total_questions} ({score_percentage:.1f}%)</h2>
                <h3>Grade: {grade}</h3>
                <p>{"Congratulations! You passed the assessment." if passed else "Please review and try again."}</p>
            </div>

            <div class="details">
                <h3>📊 Detailed Results:</h3>
                {questions_html}
            </div>

            <div class="details">
                <h3>💡 Assessment Summary:</h3>
                <ul>
                    <li><strong>Division:</strong> Hotel Operations</li>
                    <li><strong>Modules Tested:</strong> Listening, Grammar, Time & Numbers</li>
                    <li><strong>Pass Threshold:</strong> 70% (4.2/6 questions)</li>
                    <li><strong>Your Performance:</strong> {score_percentage:.1f}%</li>
                </ul>
            </div>

            <div style="text-align: center;">
                <button class="btn" onclick="restartAssessment()">🔄 Take Assessment Again</button>
                <button class="btn" onclick="goHome()" style="background: #059669;">🏠 Back to Home</button>
            </div>
        </div>

        <script>
            function restartAssessment() {{
                window.location.href = '/assessment/start';
            }}
            function goHome() {{
                window.location.href = '/';
            }}
        </script>
    </body>
    </html>
    """)

@app.get("/sample-questions", response_class=HTMLResponse)
def sample_questions():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sample Questions</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .module { background: #f8fafc; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 5px solid #1e3a8a; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📝 Sample Questions Preview</h1>

            <div class="module">
                <h3>🎧 Listening Module</h3>
                <p><strong>Audio:</strong> "I'd like to book a table for four at seven PM tonight."</p>
                <p><strong>Question:</strong> What time is the reservation?</p>
                <p><strong>Options:</strong> A) 6 PM  B) 7 PM  C) 8 PM  D) 4 PM</p>
                <p style="color: #10b981;"><strong>Answer:</strong> B) 7 PM</p>
            </div>

            <div class="module">
                <h3>📝 Grammar Module</h3>
                <p><strong>Question:</strong> ___ I help you with your luggage?</p>
                <p><strong>Options:</strong> A) May  B) Do  C) Will  D) Am</p>
                <p style="color: #10b981;"><strong>Answer:</strong> A) May</p>
            </div>

            <div class="module">
                <h3>⏰ Time & Numbers Module</h3>
                <p><strong>Question:</strong> Breakfast is served from ___ to 10:30 AM.</p>
                <p><strong>Type:</strong> Fill in the blank</p>
                <p style="color: #10b981;"><strong>Answer:</strong> 7:00</p>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" onclick="takeAssessment()">🚀 Take the Full Assessment</button>
                <button class="btn" onclick="goHome()" style="background: #6b7280;">🏠 Back to Home</button>
            </div>
        </div>

        <script>
            function takeAssessment() { window.location.href = '/assessment/start'; }
            function goHome() { window.location.href = '/'; }
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("🚢 Starting Interactive English Assessment...")
    print("📊 Take the test at: http://127.0.0.1:8001")
    print("🎯 Sample questions available")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8001)