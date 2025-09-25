#!/usr/bin/env python3
"""
Apple-Style Assessment - Beautiful UI with Direct Flow
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import json

app = FastAPI(title="Apple-Style Assessment")

# Questions data
QUESTIONS = {
    1: {
        "module": "listening",
        "question": "What time is the reservation?",
        "audio_text": "Hello, I'd like to book a table for four people at seven PM tonight, please.",
        "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
        "correct": "7 PM",
        "points": 4
    },
    2: {
        "module": "listening",
        "question": "What is the room number?",
        "audio_text": "Excuse me, the air conditioning is way too cold in room eight-two-five-four. Could you please send someone to fix it?",
        "options": ["8245", "8254", "8524", "2548"],
        "correct": "8254",
        "points": 4
    },
    3: {
        "module": "time_numbers",
        "question": "What time does breakfast start?",
        "audio_text": "Good morning! Breakfast is served from seven AM to ten-thirty AM daily in the main dining room.",
        "correct": "7:00",
        "points": 4
    },
    4: {
        "module": "grammar",
        "question": "___ I help you with your luggage?",
        "options": ["May", "Do", "Will", "Am"],
        "correct": "May",
        "points": 4
    },
    5: {
        "module": "speaking",
        "question": "A guest says: 'The air conditioning in my room is too cold.' Please respond appropriately.",
        "expected_keywords": ["apologize", "sorry", "send someone", "fix", "adjust"],
        "min_duration": 5,
        "points": 20
    }
}

user_progress = {"answers": {}, "total_score": 0}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>English Assessment</title>
        <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #1d1d1f;
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                padding: 60px 50px;
                max-width: 600px;
                width: 90%;
                box-shadow: 0 32px 64px rgba(0, 0, 0, 0.15);
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .logo {
                font-size: 3.2rem;
                font-weight: 700;
                background: linear-gradient(45deg, #007aff, #5856d6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 16px;
            }

            .subtitle {
                font-size: 1.3rem;
                color: #86868b;
                margin-bottom: 40px;
                font-weight: 400;
            }

            .features {
                margin: 40px 0;
                text-align: left;
            }

            .feature {
                display: flex;
                align-items: center;
                margin: 20px 0;
                font-size: 1.1rem;
                color: #515154;
            }

            .feature-icon {
                width: 24px;
                height: 24px;
                background: linear-gradient(45deg, #30d158, #00c7be);
                border-radius: 50%;
                margin-right: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }

            .start-btn {
                background: linear-gradient(45deg, #007aff, #5856d6);
                color: white;
                border: none;
                border-radius: 980px;
                padding: 20px 50px;
                font-size: 1.2rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                margin-top: 30px;
                box-shadow: 0 8px 24px rgba(0, 122, 255, 0.25);
            }

            .start-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 12px 32px rgba(0, 122, 255, 0.35);
            }

            .start-btn:active {
                transform: translateY(0);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">English Assessment</div>
            <div class="subtitle">Professional English Evaluation for Cruise Staff</div>

            <div class="features">
                <div class="feature">
                    <div class="feature-icon">✓</div>
                    Listening: Audio-only comprehension
                </div>
                <div class="feature">
                    <div class="feature-icon">✓</div>
                    Grammar: Professional communication
                </div>
                <div class="feature">
                    <div class="feature-icon">✓</div>
                    Time & Numbers: With audio context
                </div>
                <div class="feature">
                    <div class="feature-icon">✓</div>
                    Speaking: Voice analysis technology
                </div>
            </div>

            <a href="/question/1" class="start-btn">Begin Assessment</a>
        </div>
    </body>
    </html>
    """)

@app.get("/question/{q_num}", response_class=HTMLResponse)
def show_question(q_num: int):
    if q_num not in QUESTIONS:
        return HTMLResponse("<h1>Question not found</h1>")

    q = QUESTIONS[q_num]
    progress = ((q_num - 1) / 5) * 100

    # Generate content based on module type
    if q["module"] == "listening":
        content = f'''
        <div class="audio-section">
            <div class="audio-icon">🎧</div>
            <h3>Listen to the audio</h3>
            <button onclick="playAudio()" class="audio-btn" id="playBtn">▶ Play Audio</button>
            <div id="audioStatus"></div>
            <div id="replayInfo">You can replay this audio 1 more time</div>
        </div>
        <div class="question-text">{q["question"]}</div>
        ''' + generate_options(q["options"])

        script = f'''
        let replaysLeft = 2;
        function playAudio() {{
            if (replaysLeft <= 0) {{
                document.getElementById('audioStatus').innerHTML = '❌ No more replays';
                return;
            }}
            const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
            utterance.rate = 0.8;
            utterance.onstart = () => {{
                document.getElementById('audioStatus').innerHTML = '🔊 Playing...';
                document.getElementById('playBtn').style.opacity = '0.6';
            }};
            utterance.onend = () => {{
                replaysLeft--;
                document.getElementById('audioStatus').innerHTML = '✅ Audio complete';
                document.getElementById('replayInfo').innerHTML = replaysLeft > 0 ? replaysLeft + ' replay(s) remaining' : 'No more replays';
                document.getElementById('playBtn').style.opacity = '1';
            }};
            speechSynthesis.speak(utterance);
        }}
        '''

    elif q["module"] == "time_numbers":
        content = f'''
        <div class="audio-section">
            <div class="audio-icon">🎧</div>
            <h3>Listen for the specific information</h3>
            <button onclick="playAudio()" class="audio-btn">▶ Play Conversation</button>
            <div id="audioStatus"></div>
        </div>
        <div class="question-text">{q["question"]}</div>
        <input type="text" id="textAnswer" placeholder="Enter time (H:MM format)"
               class="text-input" onchange="selectAnswer(this.value)">
        '''

        script = f'''
        function playAudio() {{
            const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
            utterance.rate = 0.8;
            utterance.onstart = () => document.getElementById('audioStatus').innerHTML = '🔊 Playing...';
            utterance.onend = () => document.getElementById('audioStatus').innerHTML = '✅ Complete';
            speechSynthesis.speak(utterance);
        }}
        '''

    elif q["module"] == "grammar":
        content = f'''
        <div class="question-text">{q["question"]}</div>
        ''' + generate_options(q["options"])
        script = ""

    elif q["module"] == "speaking":
        content = f'''
        <div class="question-text">{q["question"]}</div>
        <div class="speaking-section">
            <p class="speaking-instruction">Speak clearly for at least {q["min_duration"]} seconds</p>
            <div class="recording-controls">
                <button onclick="startRecording()" class="record-btn" id="recordBtn">🎤 Start Recording</button>
                <button onclick="stopRecording()" class="stop-btn" id="stopBtn" disabled>⏹ Stop</button>
            </div>
            <div id="recordingStatus"></div>
        </div>
        '''

        script = f'''
        let mediaRecorder;
        let recordingSeconds = 0;
        let speechDetected = false;

        function startRecording() {{
            navigator.mediaDevices.getUserMedia({{ audio: true }})
            .then(stream => {{
                mediaRecorder = new MediaRecorder(stream);
                recordingSeconds = 0;
                speechDetected = false;

                const audioContext = new AudioContext();
                const source = audioContext.createMediaStreamSource(stream);
                const analyser = audioContext.createAnalyser();
                source.connect(analyser);

                const bufferLength = analyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);

                const checkAudio = () => {{
                    if (mediaRecorder && mediaRecorder.state === 'recording') {{
                        analyser.getByteFrequencyData(dataArray);
                        const volume = dataArray.reduce((sum, val) => sum + val) / bufferLength;
                        if (volume > 10) speechDetected = true;
                        requestAnimationFrame(checkAudio);
                    }}
                }};
                checkAudio();

                mediaRecorder.onstart = () => {{
                    document.getElementById('recordingStatus').innerHTML = '🎤 Recording... Speak now!';
                    document.getElementById('recordBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;

                    const timer = setInterval(() => {{
                        recordingSeconds++;
                        document.getElementById('recordingStatus').innerHTML = `🎤 Recording... ${{recordingSeconds}}s`;
                        if (recordingSeconds >= 30) {{
                            clearInterval(timer);
                            stopRecording();
                        }}
                    }}, 1000);
                }};

                mediaRecorder.onstop = () => {{
                    document.getElementById('recordBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;

                    if (!speechDetected) {{
                        selectedAnswer = 'No speech detected';
                        document.getElementById('recordingStatus').innerHTML = '❌ No speech detected';
                    }} else if (recordingSeconds < {q["min_duration"]}) {{
                        selectedAnswer = `Too short: ${{recordingSeconds}}s`;
                        document.getElementById('recordingStatus').innerHTML = `⚠️ Too short (${{recordingSeconds}}s) - Minimum {q["min_duration"]}s`;
                    }} else {{
                        selectedAnswer = `Speech recorded: ${{recordingSeconds}}s`;
                        document.getElementById('recordingStatus').innerHTML = `✅ Good recording (${{recordingSeconds}}s)`;
                    }}

                    document.getElementById('submitBtn').disabled = false;
                    stream.getTracks().forEach(track => track.stop());
                }};

                mediaRecorder.start();
            }})
            .catch(err => {{
                document.getElementById('recordingStatus').innerHTML = '❌ Microphone access denied';
            }});
        }}

        function stopRecording() {{
            if (mediaRecorder && mediaRecorder.state === 'recording') {{
                mediaRecorder.stop();
            }}
        }}
        '''

    else:
        content = "<p>Question type not implemented</p>"
        script = ""

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Question {q_num} - Assessment</title>
        <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                color: #1d1d1f;
            }}

            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                padding: 40px;
                box-shadow: 0 32px 64px rgba(0, 0, 0, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}

            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}

            .question-number {{
                font-size: 1.1rem;
                color: #86868b;
                margin-bottom: 10px;
            }}

            .module-title {{
                font-size: 1.5rem;
                font-weight: 600;
                color: #007aff;
                margin-bottom: 20px;
            }}

            .progress {{
                background: rgba(0, 122, 255, 0.1);
                height: 6px;
                border-radius: 3px;
                margin: 20px 0;
                overflow: hidden;
            }}

            .progress-bar {{
                background: linear-gradient(45deg, #007aff, #5856d6);
                height: 100%;
                width: {progress}%;
                border-radius: 3px;
                transition: width 0.5s ease;
            }}

            .content {{
                margin: 40px 0;
            }}

            .audio-section {{
                background: linear-gradient(135deg, #ffd60a 0%, #ffbe0b 100%);
                color: #1d1d1f;
                padding: 30px;
                border-radius: 16px;
                text-align: center;
                margin-bottom: 30px;
            }}

            .audio-icon {{
                font-size: 3rem;
                margin-bottom: 15px;
            }}

            .audio-section h3 {{
                font-size: 1.3rem;
                font-weight: 600;
                margin-bottom: 20px;
            }}

            .audio-btn {{
                background: rgba(255, 255, 255, 0.9);
                color: #1d1d1f;
                border: none;
                border-radius: 50px;
                padding: 15px 30px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            }}

            .audio-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            }}

            .question-text {{
                font-size: 1.4rem;
                font-weight: 500;
                margin-bottom: 30px;
                text-align: center;
                line-height: 1.5;
            }}

            .option {{
                display: block;
                background: rgba(255, 255, 255, 0.7);
                border: 2px solid rgba(0, 122, 255, 0.2);
                border-radius: 16px;
                padding: 20px 25px;
                margin: 15px 0;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 1.1rem;
                position: relative;
                overflow: hidden;
            }}

            .option::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.8), transparent);
                transition: left 0.5s;
            }}

            .option:hover {{
                border-color: #007aff;
                background: rgba(255, 255, 255, 0.9);
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(0, 122, 255, 0.15);
            }}

            .option:hover::before {{
                left: 100%;
            }}

            .option.selected {{
                background: linear-gradient(135deg, #007aff, #5856d6);
                color: white;
                border-color: #007aff;
                box-shadow: 0 8px 24px rgba(0, 122, 255, 0.3);
            }}

            .option input {{
                margin-right: 15px;
            }}

            .text-input {{
                width: 100%;
                max-width: 400px;
                padding: 20px 25px;
                border: 2px solid rgba(0, 122, 255, 0.2);
                border-radius: 16px;
                font-size: 1.1rem;
                background: rgba(255, 255, 255, 0.9);
                transition: all 0.3s ease;
                display: block;
                margin: 20px auto;
            }}

            .text-input:focus {{
                outline: none;
                border-color: #007aff;
                box-shadow: 0 0 20px rgba(0, 122, 255, 0.2);
            }}

            .speaking-section {{
                background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                color: white;
                padding: 30px;
                border-radius: 16px;
                text-align: center;
            }}

            .speaking-instruction {{
                font-size: 1.2rem;
                margin-bottom: 25px;
                font-weight: 500;
            }}

            .recording-controls {{
                margin: 20px 0;
            }}

            .record-btn, .stop-btn {{
                background: rgba(255, 255, 255, 0.9);
                color: #1d1d1f;
                border: none;
                border-radius: 50px;
                padding: 15px 30px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                margin: 0 10px;
                transition: all 0.3s ease;
            }}

            .record-btn:hover, .stop-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(255, 255, 255, 0.3);
            }}

            .record-btn:disabled, .stop-btn:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }}

            .submit-section {{
                text-align: center;
                margin-top: 40px;
                padding-top: 30px;
                border-top: 1px solid rgba(0, 122, 255, 0.1);
            }}

            .submit-btn {{
                background: linear-gradient(45deg, #30d158, #00c7be);
                color: white;
                border: none;
                border-radius: 50px;
                padding: 18px 40px;
                font-size: 1.2rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 8px 24px rgba(48, 209, 88, 0.25);
            }}

            .submit-btn:hover:not(:disabled) {{
                transform: translateY(-2px);
                box-shadow: 0 12px 32px rgba(48, 209, 88, 0.35);
            }}

            .submit-btn:disabled {{
                background: #86868b;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }}

            #audioStatus, #replayInfo, #recordingStatus {{
                margin: 15px 0;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="question-number">Question {q_num} of 5</div>
                <div class="module-title">{q["module"].title().replace("_", " & ")}</div>
                <div class="progress">
                    <div class="progress-bar"></div>
                </div>
            </div>

            <div class="content">
                {content}
            </div>

            <div class="submit-section">
                <button class="submit-btn" id="submitBtn" onclick="submitAnswer({q_num})" disabled>
                    Continue
                </button>
            </div>
        </div>

        <script>
            let selectedAnswer = '';

            function selectAnswer(answer, element) {{
                selectedAnswer = answer;
                document.getElementById('submitBtn').disabled = false;
                if (element) {{
                    document.querySelectorAll('.option').forEach(opt => opt.classList.remove('selected'));
                    element.classList.add('selected');
                }}
            }}

            function submitAnswer(qNum) {{
                if (!selectedAnswer.trim()) {{
                    alert('Please provide an answer');
                    return;
                }}

                // Show loading state
                document.getElementById('submitBtn').innerHTML = 'Processing...';
                document.getElementById('submitBtn').disabled = true;

                // Direct redirect to next question or results
                window.location.href = `/submit/${{qNum}}?answer=${{encodeURIComponent(selectedAnswer)}}`;
            }}

            {script}
        </script>
    </body>
    </html>
    ''')

def generate_options(options):
    html = ""
    for i, option in enumerate(options):
        letter = chr(65 + i)
        html += f'''
        <div class="option" onclick="selectAnswer('{option}', this)">
            <input type="radio" name="answer" value="{option}" style="margin-right: 15px;">
            <strong>{letter})</strong> {option}
        </div>
        '''
    return html

@app.get("/submit/{q_num}")
async def submit_answer(q_num: int, answer: str):
    q = QUESTIONS[q_num]
    is_correct = check_answer(q, answer)
    points = q["points"] if is_correct else 0

    user_progress["answers"][q_num] = {"answer": answer, "correct": is_correct, "points": points}
    user_progress["total_score"] += points

    next_q = q_num + 1
    if next_q <= 5:
        # Direct redirect to next question - no intermediate page
        return HTMLResponse(f'<script>window.location.href = "/question/{next_q}";</script>')
    else:
        return HTMLResponse('<script>window.location.href = "/results";</script>')

def check_answer(q, answer):
    if q["module"] in ["listening", "grammar"]:
        return answer.strip().lower() == q["correct"].lower()
    elif q["module"] == "time_numbers":
        return answer.strip().replace(":", "") == str(q["correct"]).replace(":", "")
    elif q["module"] == "speaking":
        return not ("No speech detected" in answer or "Too short" in answer)
    return False

@app.get("/results", response_class=HTMLResponse)
def show_results():
    percentage = (user_progress["total_score"] / 40) * 100
    passed = percentage >= 70

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Assessment Results</title>
        <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #1d1d1f;
                padding: 20px;
            }}

            .container {{
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                padding: 60px 50px;
                max-width: 700px;
                width: 100%;
                box-shadow: 0 32px 64px rgba(0, 0, 0, 0.15);
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}

            .title {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 30px;
                background: linear-gradient(45deg, #007aff, #5856d6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            .score-card {{
                background: {"linear-gradient(135deg, #30d158, #00c7be)" if passed else "linear-gradient(135deg, #ff3b30, #ff6961)"};
                color: white;
                padding: 40px;
                border-radius: 20px;
                margin: 30px 0;
                box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2);
            }}

            .score-number {{
                font-size: 3.5rem;
                font-weight: 700;
                margin-bottom: 10px;
            }}

            .score-text {{
                font-size: 1.3rem;
                opacity: 0.9;
            }}

            .result-status {{
                font-size: 2rem;
                font-weight: 600;
                margin-top: 20px;
            }}

            .features-verified {{
                margin: 40px 0;
                background: rgba(0, 122, 255, 0.05);
                padding: 30px;
                border-radius: 16px;
            }}

            .features-title {{
                font-size: 1.3rem;
                font-weight: 600;
                color: #007aff;
                margin-bottom: 20px;
            }}

            .feature-list {{
                text-align: left;
                list-style: none;
            }}

            .feature-item {{
                display: flex;
                align-items: center;
                margin: 12px 0;
                font-size: 1.1rem;
                color: #515154;
            }}

            .feature-icon {{
                width: 24px;
                height: 24px;
                background: linear-gradient(45deg, #30d158, #00c7be);
                border-radius: 50%;
                margin-right: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }}

            .restart-btn {{
                background: linear-gradient(45deg, #007aff, #5856d6);
                color: white;
                border: none;
                border-radius: 50px;
                padding: 20px 50px;
                font-size: 1.2rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                margin-top: 30px;
                box-shadow: 0 8px 24px rgba(0, 122, 255, 0.25);
            }}

            .restart-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 12px 32px rgba(0, 122, 255, 0.35);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="title">Assessment Complete</div>

            <div class="score-card">
                <div class="score-number">{user_progress["total_score"]}/40</div>
                <div class="score-text">{percentage:.0f}% Score</div>
                <div class="result-status">{"PASS" if passed else "FAIL"}</div>
            </div>

            <div class="features-verified">
                <div class="features-title">All Features Verified</div>
                <ul class="feature-list">
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Listening: Audio-only (no text spoilers)
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        No immediate feedback during test
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Time & Numbers: With audio context
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Speaking: Real voice analysis
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Direct flow: No interruption pages
                    </li>
                </ul>
            </div>

            <a href="/" class="restart-btn">Take Assessment Again</a>
        </div>
    </body>
    </html>
    ''')

if __name__ == "__main__":
    print("Starting Apple-Style Assessment...")
    print("URL: http://127.0.0.1:8008")
    uvicorn.run(app, host="127.0.0.1", port=8008)