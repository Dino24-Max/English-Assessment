#!/usr/bin/env python3
"""
Simple Interactive Assessment - Take the English Test
"""

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Take English Assessment")

# Sample questions
QUESTIONS = {
    1: {
        "type": "listening",
        "question": "Guest says: 'I'd like to book a table for four at 7 PM.' What time is the reservation?",
        "audio": "I'd like to book a table for four at seven PM tonight.",
        "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
        "correct": "7 PM"
    },
    2: {
        "type": "grammar",
        "question": "___ I help you with your luggage?",
        "options": ["May", "Do", "Will", "Am"],
        "correct": "May"
    },
    3: {
        "type": "time_numbers",
        "question": "Breakfast is served from ___ to 10:30 AM.",
        "correct": "7:00",
        "hint": "Enter time in H:MM format"
    }
}

user_score = {"correct": 0, "total": 0, "answers": {}}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>English Assessment - Take the Test</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .card { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { background: #1e3a8a; color: white; text-align: center; padding: 30px; border-radius: 8px; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px; }
            .btn:hover { background: #1e40af; }
            .info { background: #e8f4fd; padding: 20px; border-radius: 5px; border-left: 5px solid #1e3a8a; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Cruise Employee English Assessment</h1>
            <p>Interactive Assessment Demo - Hotel Operations</p>
        </div>

        <div class="card info">
            <h3>Assessment Information</h3>
            <ul>
                <li><strong>Questions:</strong> 3 sample questions</li>
                <li><strong>Modules:</strong> Listening, Grammar, Time & Numbers</li>
                <li><strong>Division:</strong> Hotel Operations (cruise ship hospitality)</li>
                <li><strong>Scoring:</strong> Immediate feedback after each question</li>
                <li><strong>Pass Grade:</strong> 70% (2 out of 3 correct)</li>
            </ul>
        </div>

        <div class="card">
            <h3>What You'll Be Tested On:</h3>
            <ul>
                <li><strong>Listening:</strong> Understanding guest requests and conversations</li>
                <li><strong>Grammar:</strong> Polite service language and proper sentence structure</li>
                <li><strong>Time & Numbers:</strong> Comprehending schedules, times, and room numbers</li>
            </ul>
        </div>

        <div style="text-align: center;">
            <a href="/question/1"><button class="btn">START ASSESSMENT</button></a>
            <a href="/preview"><button class="btn" style="background: #059669;">PREVIEW QUESTIONS</button></a>
        </div>
    </body>
    </html>
    """)

@app.get("/question/{q_num}", response_class=HTMLResponse)
def show_question(q_num: int):
    if q_num not in QUESTIONS:
        return HTMLResponse("<h1>Question not found</h1>")

    q = QUESTIONS[q_num]
    progress = ((q_num - 1) / 3) * 100

    if q["type"] in ["listening", "grammar"]:
        # Multiple choice
        options_html = ""
        for i, option in enumerate(q["options"]):
            letter = chr(65 + i)  # A, B, C, D
            options_html += f'''
            <label style="display: block; padding: 15px; margin: 10px 0; background: #f8f9fa; border-radius: 5px; cursor: pointer;" onclick="selectAnswer('{option}')">
                <input type="radio" name="answer" value="{option}" style="margin-right: 10px;">
                <strong>{letter})</strong> {option}
            </label>
            '''
        form_input = options_html
    else:
        # Fill in the blank
        form_input = f'''
        <input type="text" name="answer" id="textAnswer" placeholder="Enter your answer"
               style="width: 300px; padding: 15px; border: 2px solid #ddd; border-radius: 5px; font-size: 16px;"
               onchange="selectAnswer(this.value)">
        <p style="color: #666; font-style: italic;">Hint: {q.get("hint", "")}</p>
        '''

    # Audio section for listening questions
    audio_html = ""
    if q["type"] == "listening":
        audio_html = f'''
        <div style="background: #fff3cd; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 5px solid #ffc107;">
            <h4>Audio Content (Listen carefully):</h4>
            <p style="font-style: italic; font-size: 18px;">"{q["audio"]}"</p>
            <p style="font-size: 14px; color: #6c757d;">In a real test, this would be audio you could replay twice.</p>
        </div>
        '''

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {q_num} - English Assessment</title>
        <style>
            body {{ font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
            .btn:disabled {{ background: #6c757d; cursor: not-allowed; }}
            .progress {{ background: #e9ecef; height: 15px; border-radius: 10px; margin: 20px 0; }}
            .progress-bar {{ background: #28a745; height: 100%; border-radius: 10px; width: {progress}%; }}
            .selected {{ background-color: #d1ecf1 !important; border: 2px solid #1e3a8a !important; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <h2>Question {q_num} of 3</h2>
                <span style="background: #e8f4fd; padding: 5px 15px; border-radius: 15px; color: #1e3a8a; font-weight: bold;">
                    {q["type"].replace("_", " ").title()}
                </span>
            </div>

            <div class="progress">
                <div class="progress-bar"></div>
            </div>

            {audio_html}

            <div style="background: #f8f9fa; padding: 25px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #1e3a8a;">{q["question"]}</h3>

                <form id="answerForm" action="/submit/{q_num}" method="post">
                    {form_input}
                </form>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" id="submitBtn" onclick="submitAnswer()" disabled>Submit Answer</button>
            </div>
        </div>

        <script>
            let selectedAnswer = '';

            function selectAnswer(answer) {{
                selectedAnswer = answer;
                document.getElementById('submitBtn').disabled = false;

                // Visual feedback for radio buttons
                document.querySelectorAll('label').forEach(label => {{
                    label.classList.remove('selected');
                }});
                event.target.closest('label')?.classList.add('selected');
            }}

            function submitAnswer() {{
                if (!selectedAnswer) {{
                    alert('Please select an answer');
                    return;
                }}

                const form = document.getElementById('answerForm');
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'answer';
                input.value = selectedAnswer;
                form.appendChild(input);
                form.submit();
            }}
        </script>
    </body>
    </html>
    ''')

@app.post("/submit/{q_num}", response_class=HTMLResponse)
def submit_answer(q_num: int, answer: str = Form(...)):
    if q_num not in QUESTIONS:
        return HTMLResponse("<h1>Invalid question</h1>")

    q = QUESTIONS[q_num]
    is_correct = answer.strip().lower() == q["correct"].lower()

    # Update score
    user_score["total"] += 1
    user_score["answers"][q_num] = {"answer": answer, "correct": is_correct}
    if is_correct:
        user_score["correct"] += 1

    # Show result
    result_color = "#28a745" if is_correct else "#dc3545"
    result_icon = "✓" if is_correct else "✗"
    result_text = "Correct!" if is_correct else "Incorrect"

    next_q = q_num + 1
    if next_q <= 3:
        next_button = f'<a href="/question/{next_q}"><button class="btn">Next Question</button></a>'
    else:
        next_button = '<a href="/results"><button class="btn" style="background: #28a745;">View Final Results</button></a>'

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {q_num} Result</title>
        <style>
            body {{ font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; }}
            .result {{ background: {result_color}; color: white; padding: 25px; border-radius: 8px; text-align: center; margin: 20px 0; }}
            .feedback {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="result">
                <h2>{result_icon} {result_text}</h2>
                <p>Question {q_num} of 3 completed</p>
            </div>

            <div class="feedback">
                <h3>Your Answer:</h3>
                <p style="font-size: 18px; font-weight: bold;">"{answer}"</p>

                <h3>Correct Answer:</h3>
                <p style="font-size: 18px; color: {result_color}; font-weight: bold;">"{q["correct"]}"</p>

                <h3>Explanation:</h3>
                <p>{"Great! You understood the context correctly." if is_correct else "This is a common hospitality scenario. Practice similar conversations to improve."}</p>
            </div>

            <div style="text-align: center;">
                {next_button}
            </div>
        </div>
    </body>
    </html>
    ''')

@app.get("/results", response_class=HTMLResponse)
def show_results():
    percentage = (user_score["correct"] / user_score["total"]) * 100 if user_score["total"] > 0 else 0
    passed = percentage >= 70
    grade = "PASS" if passed else "FAIL"
    grade_color = "#28a745" if passed else "#dc3545"

    # Individual question results
    questions_html = ""
    for q_num in range(1, 4):
        if q_num in user_score["answers"]:
            ans_data = user_score["answers"][q_num]
            icon = "✓" if ans_data["correct"] else "✗"
            color = "#28a745" if ans_data["correct"] else "#dc3545"
            questions_html += f'''
            <div style="padding: 15px; margin: 10px 0; background: white; border-left: 5px solid {color}; border-radius: 5px;">
                <strong>Question {q_num}:</strong> {icon} {ans_data["answer"]}
                {f"(Correct answer: {QUESTIONS[q_num]['correct']})" if not ans_data["correct"] else ""}
            </div>
            '''

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Assessment Results</title>
        <style>
            body {{ font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0; }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; margin: 10px; }}
            .score {{ background: {grade_color}; color: white; padding: 40px; border-radius: 10px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="text-align: center; color: #1e3a8a;">Assessment Complete!</h1>

            <div class="score">
                <h2>Final Score: {user_score["correct"]}/{user_score["total"]} ({percentage:.0f}%)</h2>
                <h3>Result: {grade}</h3>
                <p>{"Congratulations! You passed the Hotel Operations assessment." if passed else "You need 70% to pass. Please review and try again."}</p>
            </div>
        </div>

        <div class="card">
            <h3>Question-by-Question Results:</h3>
            {questions_html}
        </div>

        <div class="card">
            <h3>Assessment Summary:</h3>
            <ul>
                <li><strong>Division:</strong> Hotel Operations (Cruise Ship Hospitality)</li>
                <li><strong>Modules Tested:</strong> Listening, Grammar, Time & Numbers</li>
                <li><strong>Total Questions:</strong> 3 (Demo version)</li>
                <li><strong>Pass Threshold:</strong> 70% (2 correct answers)</li>
                <li><strong>Your Score:</strong> {percentage:.0f}%</li>
                <li><strong>Result:</strong> {grade}</li>
            </ul>
        </div>

        <div style="text-align: center;">
            <a href="/"><button class="btn">Take Assessment Again</button></a>
            <a href="/preview"><button class="btn" style="background: #6c757d;">Review Questions</button></a>
        </div>
    </body>
    </html>
    ''')

@app.get("/preview", response_class=HTMLResponse)
def preview_questions():
    return HTMLResponse('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question Preview</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { background: white; padding: 25px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; }
            .module { border-left: 5px solid #1e3a8a; background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 15px 0; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Sample Questions Preview</h1>
            <p>Here's what you'll encounter in the assessment:</p>
        </div>

        <div class="module">
            <h3>Question 1: Listening Module</h3>
            <p><strong>Audio:</strong> "I'd like to book a table for four at seven PM tonight."</p>
            <p><strong>Question:</strong> What time is the reservation?</p>
            <p><strong>Options:</strong> A) 6 PM  B) 7 PM  C) 8 PM  D) 4 PM</p>
            <p style="color: #28a745;"><strong>Answer:</strong> B) 7 PM</p>
        </div>

        <div class="module">
            <h3>Question 2: Grammar Module</h3>
            <p><strong>Question:</strong> ___ I help you with your luggage?</p>
            <p><strong>Options:</strong> A) May  B) Do  C) Will  D) Am</p>
            <p style="color: #28a745;"><strong>Answer:</strong> A) May (polite service language)</p>
        </div>

        <div class="module">
            <h3>Question 3: Time & Numbers Module</h3>
            <p><strong>Question:</strong> Breakfast is served from ___ to 10:30 AM.</p>
            <p><strong>Type:</strong> Fill in the blank</p>
            <p style="color: #28a745;"><strong>Answer:</strong> 7:00</p>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="/"><button class="btn">Take the Assessment</button></a>
        </div>
    </body>
    </html>
    ''')

if __name__ == "__main__":
    print("Starting Interactive English Assessment...")
    print("Take the test at: http://127.0.0.1:8002")
    uvicorn.run(app, host="127.0.0.1", port=8002)