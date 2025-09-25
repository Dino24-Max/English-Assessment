#!/usr/bin/env python3
"""
English Assessment with Real Audio Generation
Includes text-to-speech for listening questions
"""

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import hashlib
from pathlib import Path

# Create audio directory
audio_dir = Path("generated_audio")
audio_dir.mkdir(exist_ok=True)

app = FastAPI(title="English Assessment with Audio")

# Mount static files for audio
app.mount("/audio", StaticFiles(directory="generated_audio"), name="audio")

# Questions with audio
QUESTIONS = {
    1: {
        "type": "listening",
        "question": "Guest says: 'I'd like to book a table for four at 7 PM.' What time is the reservation?",
        "audio_text": "Hello, I'd like to book a table for four people at seven PM tonight, please.",
        "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
        "correct": "7 PM"
    },
    2: {
        "type": "listening",
        "question": "Guest complaint: 'The air conditioning is too cold in room 8254.' What is the room number?",
        "audio_text": "Excuse me, the air conditioning is way too cold in room eight-two-five-four. Could you please send someone to fix it?",
        "options": ["8245", "8254", "8524", "2548"],
        "correct": "8254"
    },
    3: {
        "type": "grammar",
        "question": "___ I help you with your luggage?",
        "options": ["May", "Do", "Will", "Am"],
        "correct": "May"
    }
}

user_score = {"correct": 0, "total": 0, "answers": {}}

def generate_audio_filename(text):
    """Generate consistent filename for audio text"""
    return hashlib.md5(text.encode()).hexdigest() + ".wav"

def create_audio_with_browser_tts(text, filename):
    """Create a simple HTML file that will generate audio using browser TTS"""
    audio_path = audio_dir / filename

    # Create a simple audio file placeholder (we'll use browser TTS instead)
    if not audio_path.exists():
        # Create empty placeholder file
        audio_path.touch()

    return str(audio_path)

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>English Assessment with Audio</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .card { background: white; padding: 30px; border-radius: 8px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .header { background: #1e3a8a; color: white; text-align: center; padding: 30px; border-radius: 8px; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px; text-decoration: none; display: inline-block; }
            .btn:hover { background: #1e40af; }
            .info { background: #e8f4fd; padding: 20px; border-radius: 5px; border-left: 5px solid #1e3a8a; }
            .audio-feature { background: #f0f9ff; padding: 20px; border-radius: 8px; border: 2px solid #3b82f6; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎧 English Assessment with Audio</h1>
            <p>Cruise Employee Assessment - Hotel Operations</p>
            <p style="font-size: 18px; margin-top: 15px;">✨ Now with Real Audio Playback! ✨</p>
        </div>

        <div class="audio-feature">
            <h3>🔊 NEW: Audio Listening Module</h3>
            <ul>
                <li>✅ <strong>Real Audio Playback</strong> - Hear actual conversations</li>
                <li>✅ <strong>Replay Feature</strong> - Listen up to 2 times per question</li>
                <li>✅ <strong>Clear Voice</strong> - Professional text-to-speech</li>
                <li>✅ <strong>Realistic Scenarios</strong> - Actual guest interactions</li>
            </ul>
        </div>

        <div class="card info">
            <h3>📋 Assessment Information</h3>
            <ul>
                <li><strong>Questions:</strong> 3 questions (2 Listening + 1 Grammar)</li>
                <li><strong>Audio Questions:</strong> Listen carefully and answer</li>
                <li><strong>Division:</strong> Hotel Operations (cruise hospitality)</li>
                <li><strong>Scoring:</strong> Real-time feedback after each question</li>
                <li><strong>Pass Grade:</strong> 70% (2 out of 3 correct)</li>
            </ul>
        </div>

        <div class="card">
            <h3>🎧 What You'll Hear:</h3>
            <ul>
                <li><strong>Question 1:</strong> Guest making dinner reservation</li>
                <li><strong>Question 2:</strong> Room temperature complaint with specific room number</li>
                <li><strong>Question 3:</strong> Grammar question (no audio)</li>
            </ul>
        </div>

        <div style="text-align: center;">
            <a href="/question/1" class="btn">🚀 START AUDIO ASSESSMENT</a>
            <a href="/audio-test" class="btn" style="background: #059669;">🔊 TEST AUDIO FIRST</a>
        </div>
    </body>
    </html>
    """)

@app.get("/audio-test", response_class=HTMLResponse)
def audio_test():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px; }
            .audio-player { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; border: 2px solid #28a745; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🔊 Audio System Test</h1>
            <p>Test your audio before starting the assessment:</p>

            <div class="audio-player">
                <h3>Sample Audio:</h3>
                <p><strong>Text:</strong> "Welcome to the cruise ship English assessment. Please listen carefully."</p>

                <button onclick="playTestAudio()" class="btn" style="background: #28a745;">▶️ Play Test Audio</button>
                <button onclick="stopTestAudio()" class="btn" style="background: #dc3545;">⏹️ Stop Audio</button>

                <div id="audioStatus" style="margin-top: 15px; font-weight: bold;"></div>
            </div>

            <div style="background: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4>Audio Requirements:</h4>
                <ul>
                    <li>✅ Make sure your speakers or headphones are working</li>
                    <li>✅ Adjust volume to comfortable level</li>
                    <li>✅ You'll be able to replay audio twice in the real test</li>
                    <li>✅ Each audio clip is about 10-15 seconds long</li>
                </ul>
            </div>

            <div style="text-align: center;">
                <a href="/question/1"><button class="btn">✅ Audio Works - Start Assessment</button></a>
                <a href="/"><button class="btn" style="background: #6c757d;">🏠 Back to Home</button></a>
            </div>
        </div>

        <script>
            let testAudio;

            function playTestAudio() {
                // Stop any existing audio
                stopTestAudio();

                // Create speech synthesis
                const utterance = new SpeechSynthesisUtterance("Welcome to the cruise ship English assessment. Please listen carefully to each question.");
                utterance.rate = 0.9;
                utterance.pitch = 1.0;
                utterance.volume = 0.8;

                utterance.onstart = function() {
                    document.getElementById('audioStatus').innerHTML = '🔊 Playing audio...';
                    document.getElementById('audioStatus').style.color = '#28a745';
                };

                utterance.onend = function() {
                    document.getElementById('audioStatus').innerHTML = '✅ Audio finished playing';
                    document.getElementById('audioStatus').style.color = '#17a2b8';
                };

                utterance.onerror = function(event) {
                    document.getElementById('audioStatus').innerHTML = '❌ Audio error: ' + event.error;
                    document.getElementById('audioStatus').style.color = '#dc3545';
                };

                speechSynthesis.speak(utterance);
                testAudio = utterance;
            }

            function stopTestAudio() {
                if (testAudio) {
                    speechSynthesis.cancel();
                    document.getElementById('audioStatus').innerHTML = '⏹️ Audio stopped';
                    document.getElementById('audioStatus').style.color = '#6c757d';
                }
            }
        </script>
    </body>
    </html>
    """)

@app.get("/question/{q_num}", response_class=HTMLResponse)
def show_question(q_num: int):
    if q_num not in QUESTIONS:
        raise HTTPException(status_code=404, detail="Question not found")

    q = QUESTIONS[q_num]
    progress = ((q_num - 1) / 3) * 100

    # Generate audio controls for listening questions
    audio_section = ""
    audio_script = ""

    if q["type"] == "listening":
        audio_section = f'''
        <div style="background: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 5px solid #ffc107;">
            <h4>🎧 Listen to the Audio:</h4>
            <div style="text-align: center; margin: 20px 0;">
                <button onclick="playAudio()" class="btn" style="background: #28a745; margin: 5px;">▶️ Play Audio</button>
                <button onclick="stopAudio()" class="btn" style="background: #dc3545; margin: 5px;">⏹️ Stop</button>
                <div id="replayCount" style="margin-top: 10px; font-weight: bold; color: #6c757d;">Replays remaining: <span id="replaysLeft">2</span></div>
                <div id="audioStatus" style="margin-top: 10px; font-weight: bold;"></div>
            </div>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 15px;">
                <p style="font-style: italic; color: #6c757d; margin: 0;">
                    <strong>Instructions:</strong> Listen carefully to the audio conversation, then answer the question below.
                    You can replay the audio up to 2 times.
                </p>
            </div>
        </div>
        '''

        audio_script = f'''
        let currentAudio;
        let replaysLeft = 2;

        function playAudio() {{
            if (replaysLeft <= 0) {{
                document.getElementById('audioStatus').innerHTML = '❌ No more replays available';
                document.getElementById('audioStatus').style.color = '#dc3545';
                return;
            }}

            // Stop any existing audio
            stopAudio();

            // Create speech synthesis
            const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
            utterance.rate = 0.8;  // Slower for better comprehension
            utterance.pitch = 1.0;
            utterance.volume = 0.9;

            utterance.onstart = function() {{
                document.getElementById('audioStatus').innerHTML = '🔊 Playing audio...';
                document.getElementById('audioStatus').style.color = '#28a745';
            }};

            utterance.onend = function() {{
                replaysLeft--;
                document.getElementById('replaysLeft').innerText = replaysLeft;
                document.getElementById('audioStatus').innerHTML = '✅ Audio finished. Answer the question below.';
                document.getElementById('audioStatus').style.color = '#17a2b8';

                if (replaysLeft <= 0) {{
                    document.getElementById('replayCount').innerHTML = '<span style="color: #dc3545;">No more replays available</span>';
                }}
            }};

            utterance.onerror = function(event) {{
                document.getElementById('audioStatus').innerHTML = '❌ Audio error: ' + event.error;
                document.getElementById('audioStatus').style.color = '#dc3545';
            }};

            speechSynthesis.speak(utterance);
            currentAudio = utterance;
        }}

        function stopAudio() {{
            if (currentAudio) {{
                speechSynthesis.cancel();
                document.getElementById('audioStatus').innerHTML = '⏹️ Audio stopped';
                document.getElementById('audioStatus').style.color = '#6c757d';
            }}
        }}
        '''

    # Generate options HTML
    if q["type"] in ["listening", "grammar"]:
        options_html = ""
        for i, option in enumerate(q["options"]):
            letter = chr(65 + i)  # A, B, C, D
            options_html += f'''
            <label style="display: block; padding: 15px; margin: 10px 0; background: #f8f9fa; border-radius: 5px; cursor: pointer; border: 2px solid transparent;"
                   onclick="selectAnswer('{option}', this)">
                <input type="radio" name="answer" value="{option}" style="margin-right: 10px;">
                <strong>{letter})</strong> {option}
            </label>
            '''
    else:
        options_html = f'''
        <input type="text" name="answer" placeholder="Enter your answer"
               style="width: 300px; padding: 15px; border: 2px solid #ddd; border-radius: 5px; font-size: 16px;"
               onchange="selectAnswer(this.value)">
        '''

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {q_num} - Audio Assessment</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
            .btn:disabled {{ background: #6c757d; cursor: not-allowed; }}
            .progress {{ background: #e9ecef; height: 15px; border-radius: 10px; margin: 20px 0; }}
            .progress-bar {{ background: #28a745; height: 100%; border-radius: 10px; width: {progress}%; }}
            .selected {{ background-color: #d1ecf1 !important; border-color: #1e3a8a !important; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <h2>Question {q_num} of 3</h2>
                <span style="background: #e8f4fd; padding: 5px 15px; border-radius: 15px; color: #1e3a8a; font-weight: bold;">
                    {q["type"].replace("_", " ").title()} {"🎧" if q["type"] == "listening" else "📝"}
                </span>
            </div>

            <div class="progress">
                <div class="progress-bar"></div>
            </div>

            {audio_section}

            <div style="background: #f8f9fa; padding: 25px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #1e3a8a;">{q["question"]}</h3>

                <form id="answerForm" action="/submit/{q_num}" method="post">
                    {options_html}
                </form>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" id="submitBtn" onclick="submitAnswer()" disabled>Submit Answer</button>
            </div>
        </div>

        <script>
            let selectedAnswer = '';

            {audio_script}

            function selectAnswer(answer, element) {{
                selectedAnswer = answer;
                document.getElementById('submitBtn').disabled = false;

                // Visual feedback for radio buttons
                if (element) {{
                    document.querySelectorAll('label').forEach(label => {{
                        label.classList.remove('selected');
                    }});
                    element.classList.add('selected');
                }}
            }}

            function submitAnswer() {{
                if (!selectedAnswer.trim()) {{
                    alert('Please select an answer');
                    return;
                }}

                // Stop any playing audio
                {"stopAudio();" if q["type"] == "listening" else ""}

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
        raise HTTPException(status_code=404, detail="Invalid question")

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

    # Audio feedback
    audio_feedback = ""
    if q["type"] == "listening":
        audio_feedback = f'''
        <div style="background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <h4>🎧 Audio Review:</h4>
            <p><strong>What you heard:</strong> "{q["audio_text"]}"</p>
            <button onclick="reviewAudio()" class="btn" style="background: #17a2b8; font-size: 14px; padding: 10px 20px;">🔄 Listen Again</button>
        </div>
        <script>
            function reviewAudio() {{
                const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
                utterance.rate = 0.8;
                speechSynthesis.speak(utterance);
            }}
        </script>
        '''

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
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
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

            {audio_feedback}

            <div class="feedback">
                <h3>Your Answer:</h3>
                <p style="font-size: 18px; font-weight: bold;">"{answer}"</p>

                <h3>Correct Answer:</h3>
                <p style="font-size: 18px; color: {result_color}; font-weight: bold;">"{q["correct"]}"</p>

                <h3>Explanation:</h3>
                <p>{"Great! You understood the audio correctly." if is_correct and q["type"] == "listening" else "Great! You used correct service grammar." if is_correct else "Listen more carefully to the specific details mentioned in the audio." if q["type"] == "listening" else "This is polite hospitality language used in professional settings."}</p>
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

    # Count listening questions
    listening_correct = sum(1 for q_num, ans_data in user_score["answers"].items()
                           if QUESTIONS[q_num]["type"] == "listening" and ans_data["correct"])
    total_listening = sum(1 for q_num in user_score["answers"].keys()
                         if QUESTIONS[q_num]["type"] == "listening")

    # Individual question results
    questions_html = ""
    for q_num in range(1, 4):
        if q_num in user_score["answers"]:
            ans_data = user_score["answers"][q_num]
            icon = "✓" if ans_data["correct"] else "✗"
            color = "#28a745" if ans_data["correct"] else "#dc3545"
            q_type = QUESTIONS[q_num]["type"]
            audio_icon = "🎧" if q_type == "listening" else "📝"

            questions_html += f'''
            <div style="padding: 15px; margin: 10px 0; background: white; border-left: 5px solid {color}; border-radius: 5px;">
                <strong>Question {q_num} ({q_type.title()}) {audio_icon}:</strong> {icon} {ans_data["answer"]}
                {f"<br><small style='color: #6c757d;'>Correct answer: {QUESTIONS[q_num]['correct']}</small>" if not ans_data["correct"] else ""}
            </div>
            '''

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio Assessment Results</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0; }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; margin: 10px; }}
            .score {{ background: {grade_color}; color: white; padding: 40px; border-radius: 10px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="text-align: center; color: #1e3a8a;">🎧 Audio Assessment Complete!</h1>

            <div class="score">
                <h2>Final Score: {user_score["correct"]}/{user_score["total"]} ({percentage:.0f}%)</h2>
                <h3>Result: {grade}</h3>
                <p>{"🎉 Congratulations! You passed the Hotel Operations audio assessment." if passed else "📚 You need 70% to pass. Focus on listening skills and try again."}</p>
            </div>
        </div>

        <div class="card">
            <h3>📊 Performance Breakdown:</h3>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 5px;">
                <p><strong>🎧 Listening Questions:</strong> {listening_correct}/{total_listening} correct</p>
                <p><strong>📝 Grammar Questions:</strong> {user_score["correct"] - listening_correct}/{user_score["total"] - total_listening} correct</p>
                <p><strong>Overall Performance:</strong> {percentage:.0f}%</p>
            </div>
        </div>

        <div class="card">
            <h3>Question-by-Question Results:</h3>
            {questions_html}
        </div>

        <div class="card">
            <h3>🎓 Assessment Summary:</h3>
            <ul>
                <li><strong>Division:</strong> Hotel Operations (Cruise Ship Hospitality)</li>
                <li><strong>Audio Technology:</strong> Browser text-to-speech with replay functionality</li>
                <li><strong>Question Types:</strong> Listening comprehension + Grammar</li>
                <li><strong>Total Questions:</strong> 3 (2 audio + 1 text)</li>
                <li><strong>Pass Threshold:</strong> 70% (2+ correct answers)</li>
                <li><strong>Your Score:</strong> {percentage:.0f}%</li>
                <li><strong>Final Result:</strong> {grade}</li>
            </ul>
        </div>

        <div style="text-align: center;">
            <a href="/" class="btn">🔄 Take Assessment Again</a>
            <a href="/audio-test" class="btn" style="background: #17a2b8;">🔊 Test Audio System</a>
        </div>

        <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
            <p style="margin: 0; color: #155724;"><strong>✨ Audio Feature Active!</strong> You experienced real listening comprehension with speech playback and replay functionality.</p>
        </div>
    </body>
    </html>
    ''')

if __name__ == "__main__":
    print("Starting English Assessment with Audio...")
    print("Audio Assessment: http://127.0.0.1:8003")
    print("Audio Test: http://127.0.0.1:8003/audio-test")
    uvicorn.run(app, host="127.0.0.1", port=8003)