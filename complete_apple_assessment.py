#!/usr/bin/env python3
"""
Complete Apple-Style Assessment - All 6 Modules
Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import json

app = FastAPI(title="Complete Apple-Style Assessment")

# Complete questions data - 21 questions across 6 modules
QUESTIONS = {
    # LISTENING MODULE (3 questions)
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
        "module": "listening",
        "question": "What deck is the guest looking for?",
        "audio_text": "I'm trying to find the buffet restaurant. Is it on deck twelve or deck fourteen?",
        "options": ["Deck 10", "Deck 12", "Deck 14", "Deck 16"],
        "correct": "Deck 12",
        "points": 4
    },

    # TIME & NUMBERS MODULE (3 questions)
    4: {
        "module": "time_numbers",
        "question": "What time does breakfast start?",
        "audio_text": "Good morning! Breakfast is served from seven AM to ten-thirty AM daily in the main dining room.",
        "correct": "7:00",
        "points": 4
    },
    5: {
        "module": "time_numbers",
        "question": "How many guests are in the reservation?",
        "audio_text": "We need a table for eight people at six-thirty tonight. Can you accommodate us?",
        "correct": "8",
        "points": 4
    },
    6: {
        "module": "time_numbers",
        "question": "What is the cabin number?",
        "audio_text": "I'm in cabin nine-one-seven-three and my safe isn't working properly. Could you send maintenance?",
        "correct": "9173",
        "points": 4
    },

    # GRAMMAR MODULE (4 questions)
    7: {
        "module": "grammar",
        "question": "___ I help you with your luggage?",
        "options": ["May", "Do", "Will", "Am"],
        "correct": "May",
        "points": 4
    },
    8: {
        "module": "grammar",
        "question": "The guest ___ arrived at the port this morning.",
        "options": ["have", "has", "had", "having"],
        "correct": "has",
        "points": 4
    },
    9: {
        "module": "grammar",
        "question": "Could you please ___ me to the spa?",
        "options": ["direct", "directing", "directed", "direction"],
        "correct": "direct",
        "points": 4
    },
    10: {
        "module": "grammar",
        "question": "The restaurant is ___ the third deck.",
        "options": ["in", "on", "at", "by"],
        "correct": "on",
        "points": 4
    },

    # VOCABULARY MODULE (4 questions)
    11: {
        "module": "vocabulary",
        "question": "Match the cruise ship terms with their meanings:",
        "terms": ["Bridge", "Gangway", "Tender", "Muster"],
        "definitions": ["Ship's walkway to shore", "Emergency assembly", "Small boat for shore trips", "Ship's control center"],
        "correct_matches": {
            "Bridge": "Ship's control center",
            "Gangway": "Ship's walkway to shore",
            "Tender": "Small boat for shore trips",
            "Muster": "Emergency assembly"
        },
        "points": 8
    },
    12: {
        "module": "vocabulary",
        "question": "Match the hospitality terms:",
        "terms": ["Concierge", "Amenities", "Excursion", "Embark"],
        "definitions": ["To board the ship", "Guest services specialist", "Shore activities", "Hotel facilities"],
        "correct_matches": {
            "Concierge": "Guest services specialist",
            "Amenities": "Hotel facilities",
            "Excursion": "Shore activities",
            "Embark": "To board the ship"
        },
        "points": 8
    },
    13: {
        "module": "vocabulary",
        "question": "Match the dining terms:",
        "terms": ["Buffet", "A la carte", "Galley", "Sommelier"],
        "definitions": ["Wine expert", "Self-service dining", "Ship's kitchen", "Menu with individual prices"],
        "correct_matches": {
            "Buffet": "Self-service dining",
            "A la carte": "Menu with individual prices",
            "Galley": "Ship's kitchen",
            "Sommelier": "Wine expert"
        },
        "points": 8
    },
    14: {
        "module": "vocabulary",
        "question": "Match the safety terms:",
        "terms": ["Muster drill", "Life jacket", "Assembly station", "All aboard"],
        "definitions": ["Final boarding call", "Safety meeting", "Personal flotation device", "Emergency meeting point"],
        "correct_matches": {
            "Muster drill": "Safety meeting",
            "Life jacket": "Personal flotation device",
            "Assembly station": "Emergency meeting point",
            "All aboard": "Final boarding call"
        },
        "points": 8
    },

    # READING MODULE (4 questions)
    15: {
        "module": "reading",
        "question": "What should guests do if they miss the ship's departure?",
        "passage": "IMPORTANT NOTICE: Ship departures are strictly scheduled. Guests who miss departure must contact the Port Agent immediately. The ship cannot delay departure for individual passengers. Guests are responsible for reaching the next port independently and rejoining the cruise. Travel insurance is recommended to cover unexpected expenses.",
        "options": ["Wait at the port", "Contact the Port Agent", "Call the cruise line", "Take a taxi to catch up"],
        "correct": "Contact the Port Agent",
        "points": 6
    },
    16: {
        "module": "reading",
        "question": "What time does the casino close?",
        "passage": "CASINO HOURS: Our casino operates daily with the following schedule: Sea Days: 8:00 AM - 2:00 AM | Port Days: 6:00 PM - 2:00 AM. Please note: Casino operations are subject to maritime laws and may be suspended while in territorial waters. Guests must be 21+ to gamble. Valid ID required.",
        "options": ["12:00 AM", "1:00 AM", "2:00 AM", "3:00 AM"],
        "correct": "2:00 AM",
        "points": 6
    },
    17: {
        "module": "reading",
        "question": "What is required for the specialty restaurant?",
        "passage": "SPECIALTY DINING: Reservations required for all specialty restaurants. Cover charges apply: $25-$45 per person. Dress code: Smart casual after 6 PM (no shorts, flip-flops, or tank tops). Dietary restrictions can be accommodated with 24-hour advance notice. Children's menus available upon request.",
        "options": ["Formal attire", "Reservations", "Advance payment", "Group booking"],
        "correct": "Reservations",
        "points": 6
    },
    18: {
        "module": "reading",
        "question": "When is the muster drill scheduled?",
        "passage": "SAFETY FIRST: All guests must participate in the mandatory muster drill before departure. Drill times: Embarkation Day at 4:00 PM. Listen for announcements and proceed to your assigned muster station. Attendance is required by maritime law. Life jackets are not required during the drill but muster station locations are posted in your stateroom.",
        "options": ["3:00 PM", "4:00 PM", "5:00 PM", "6:00 PM"],
        "correct": "4:00 PM",
        "points": 6
    },

    # SPEAKING MODULE (3 questions)
    19: {
        "module": "speaking",
        "question": "A guest says: 'The air conditioning in my room is too cold.' Please respond appropriately.",
        "expected_keywords": ["apologize", "sorry", "send someone", "fix", "adjust", "maintenance", "comfortable"],
        "min_duration": 5,
        "points": 20
    },
    20: {
        "module": "speaking",
        "question": "A guest asks: 'What time does the buffet close?' Please provide a helpful response.",
        "expected_keywords": ["buffet", "closes", "hours", "dining", "alternative", "room service", "restaurant"],
        "min_duration": 5,
        "points": 20
    },
    21: {
        "module": "speaking",
        "question": "A guest is lost and asks: 'How do I get to the spa?' Give clear directions.",
        "expected_keywords": ["elevator", "deck", "directions", "follow", "signs", "spa", "level", "floor"],
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
        <title>Complete English Assessment</title>
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
                padding: 20px;
            }

            .container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                padding: 60px 50px;
                max-width: 700px;
                width: 100%;
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

            .test-info {
                background: rgba(0, 122, 255, 0.05);
                padding: 30px;
                border-radius: 16px;
                margin: 30px 0;
            }

            .test-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin: 30px 0;
            }

            .stat {
                text-align: center;
            }

            .stat-number {
                font-size: 2.5rem;
                font-weight: 700;
                color: #007aff;
                display: block;
            }

            .stat-label {
                font-size: 1rem;
                color: #86868b;
                margin-top: 5px;
            }

            .modules {
                margin: 40px 0;
                text-align: left;
            }

            .modules-title {
                font-size: 1.5rem;
                font-weight: 600;
                color: #1d1d1f;
                margin-bottom: 25px;
                text-align: center;
            }

            .module {
                display: flex;
                align-items: center;
                margin: 15px 0;
                font-size: 1.1rem;
                color: #515154;
                padding: 15px;
                background: rgba(255, 255, 255, 0.5);
                border-radius: 12px;
            }

            .module-icon {
                width: 32px;
                height: 32px;
                background: linear-gradient(45deg, #30d158, #00c7be);
                border-radius: 8px;
                margin-right: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 16px;
            }

            .module-details {
                flex: 1;
            }

            .module-name {
                font-weight: 600;
                color: #1d1d1f;
            }

            .module-count {
                font-size: 0.9rem;
                color: #86868b;
            }

            .start-btn {
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
            <div class="logo">Complete Assessment</div>
            <div class="subtitle">Professional English Evaluation - All 6 Modules</div>

            <div class="test-stats">
                <div class="stat">
                    <span class="stat-number">21</span>
                    <span class="stat-label">Questions</span>
                </div>
                <div class="stat">
                    <span class="stat-number">6</span>
                    <span class="stat-label">Modules</span>
                </div>
                <div class="stat">
                    <span class="stat-number">15</span>
                    <span class="stat-label">Minutes</span>
                </div>
            </div>

            <div class="modules">
                <div class="modules-title">Assessment Modules</div>

                <div class="module">
                    <div class="module-icon">🎧</div>
                    <div class="module-details">
                        <div class="module-name">Listening Comprehension</div>
                        <div class="module-count">3 audio-based questions</div>
                    </div>
                </div>

                <div class="module">
                    <div class="module-icon">🔢</div>
                    <div class="module-details">
                        <div class="module-name">Time & Numbers</div>
                        <div class="module-count">3 questions with audio context</div>
                    </div>
                </div>

                <div class="module">
                    <div class="module-icon">📝</div>
                    <div class="module-details">
                        <div class="module-name">Grammar</div>
                        <div class="module-count">4 multiple choice questions</div>
                    </div>
                </div>

                <div class="module">
                    <div class="module-icon">📚</div>
                    <div class="module-details">
                        <div class="module-name">Vocabulary</div>
                        <div class="module-count">4 drag-and-drop matching</div>
                    </div>
                </div>

                <div class="module">
                    <div class="module-icon">📖</div>
                    <div class="module-details">
                        <div class="module-name">Reading Comprehension</div>
                        <div class="module-count">4 passage-based questions</div>
                    </div>
                </div>

                <div class="module">
                    <div class="module-icon">🎤</div>
                    <div class="module-details">
                        <div class="module-name">Speaking</div>
                        <div class="module-count">3 voice response questions</div>
                    </div>
                </div>
            </div>

            <a href="/question/1" class="start-btn">Begin Complete Assessment</a>
        </div>
    </body>
    </html>
    """)

@app.get("/question/{q_num}", response_class=HTMLResponse)
def show_question(q_num: int):
    if q_num not in QUESTIONS:
        return HTMLResponse("<h1>Question not found</h1>")

    q = QUESTIONS[q_num]
    progress = ((q_num - 1) / 21) * 100

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
        <input type="text" id="textAnswer" placeholder="Enter your answer"
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

    elif q["module"] == "vocabulary":
        content = f'''
        <div class="question-text">{q["question"]}</div>
        <div class="vocab-container">
            <div class="terms-section">
                <h4>Terms</h4>
                <div class="terms-list">
                    {generate_terms(q["terms"])}
                </div>
            </div>
            <div class="definitions-section">
                <h4>Definitions</h4>
                <div class="definitions-list">
                    {generate_definitions(q["definitions"])}
                </div>
            </div>
        </div>
        <div class="matches-display" id="matchesDisplay">
            <h4>Your Matches:</h4>
            <div id="matchesList"></div>
        </div>
        '''

        script = f'''
        let matches = {{}};
        let draggedTerm = null;
        const correctMatches = {json.dumps(q["correct_matches"])};

        function dragStart(e, term) {{
            draggedTerm = term;
            e.dataTransfer.effectAllowed = 'move';
        }}

        function allowDrop(e) {{
            e.preventDefault();
        }}

        function drop(e, definition) {{
            e.preventDefault();
            if (draggedTerm) {{
                matches[draggedTerm] = definition;
                updateMatchesDisplay();
                checkAllMatched();
            }}
        }}

        function updateMatchesDisplay() {{
            const matchesList = document.getElementById('matchesList');
            matchesList.innerHTML = '';
            for (const [term, def] of Object.entries(matches)) {{
                const matchDiv = document.createElement('div');
                matchDiv.className = 'match-item';
                matchDiv.innerHTML = `<strong>${{term}}</strong> → ${{def}} <button onclick="removeMatch('${{term}}')" class="remove-btn">×</button>`;
                matchesList.appendChild(matchDiv);
            }}
        }}

        function removeMatch(term) {{
            delete matches[term];
            updateMatchesDisplay();
            checkAllMatched();
        }}

        function checkAllMatched() {{
            const allMatched = Object.keys(matches).length === {len(q["terms"])};
            document.getElementById('submitBtn').disabled = !allMatched;
            if (allMatched) {{
                selectedAnswer = JSON.stringify(matches);
            }}
        }}
        '''

    elif q["module"] == "reading":
        content = f'''
        <div class="reading-passage">
            <h4>Read the following passage:</h4>
            <div class="passage-text">{q["passage"]}</div>
        </div>
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
        <title>Question {q_num} - Complete Assessment</title>
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
                max-width: 900px;
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

            .vocab-container {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                margin: 30px 0;
            }}

            .terms-section, .definitions-section {{
                background: rgba(0, 122, 255, 0.05);
                padding: 25px;
                border-radius: 16px;
            }}

            .terms-section h4, .definitions-section h4 {{
                font-size: 1.2rem;
                margin-bottom: 20px;
                color: #007aff;
                text-align: center;
            }}

            .term, .definition {{
                background: rgba(255, 255, 255, 0.9);
                padding: 15px 20px;
                margin: 10px 0;
                border-radius: 12px;
                border: 2px solid rgba(0, 122, 255, 0.2);
                cursor: grab;
                transition: all 0.3s ease;
                font-size: 1rem;
            }}

            .term:hover, .definition:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 24px rgba(0, 122, 255, 0.15);
            }}

            .term {{
                cursor: grab;
                user-select: none;
            }}

            .term:active {{
                cursor: grabbing;
            }}

            .definition {{
                min-height: 60px;
                display: flex;
                align-items: center;
            }}

            .definition.drag-over {{
                background: linear-gradient(135deg, #007aff, #5856d6);
                color: white;
                transform: scale(1.02);
            }}

            .matches-display {{
                background: rgba(48, 209, 88, 0.05);
                padding: 25px;
                border-radius: 16px;
                margin-top: 30px;
            }}

            .matches-display h4 {{
                color: #30d158;
                margin-bottom: 15px;
            }}

            .match-item {{
                background: rgba(255, 255, 255, 0.9);
                padding: 12px 15px;
                margin: 8px 0;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}

            .remove-btn {{
                background: #ff3b30;
                color: white;
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                cursor: pointer;
                font-weight: bold;
            }}

            .reading-passage {{
                background: rgba(0, 122, 255, 0.05);
                padding: 30px;
                border-radius: 16px;
                margin-bottom: 30px;
            }}

            .reading-passage h4 {{
                color: #007aff;
                margin-bottom: 20px;
                font-size: 1.2rem;
            }}

            .passage-text {{
                background: rgba(255, 255, 255, 0.9);
                padding: 25px;
                border-radius: 12px;
                line-height: 1.6;
                font-size: 1.1rem;
                color: #1d1d1f;
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

            @media (max-width: 768px) {{
                .vocab-container {{
                    grid-template-columns: 1fr;
                    gap: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="question-number">Question {q_num} of 21</div>
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

def generate_terms(terms):
    html = ""
    for term in terms:
        html += f'''
        <div class="term" draggable="true" ondragstart="dragStart(event, '{term}')">{term}</div>
        '''
    return html

def generate_definitions(definitions):
    html = ""
    for definition in definitions:
        html += f'''
        <div class="definition" ondrop="drop(event, '{definition}')" ondragover="allowDrop(event)"
             ondragenter="this.classList.add('drag-over')" ondragleave="this.classList.remove('drag-over')">{definition}</div>
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
    if next_q <= 21:
        # Direct redirect to next question - no intermediate page
        return HTMLResponse(f'<script>window.location.href = "/question/{next_q}";</script>')
    else:
        return HTMLResponse('<script>window.location.href = "/results";</script>')

def check_answer(q, answer):
    if q["module"] in ["listening", "grammar", "reading"]:
        return answer.strip().lower() == q["correct"].lower()
    elif q["module"] == "time_numbers":
        return answer.strip().replace(":", "").replace(" ", "") == str(q["correct"]).replace(":", "").replace(" ", "")
    elif q["module"] == "vocabulary":
        try:
            user_matches = json.loads(answer)
            correct_matches = q["correct_matches"]
            return user_matches == correct_matches
        except:
            return False
    elif q["module"] == "speaking":
        return not ("No speech detected" in answer or "Too short" in answer)
    return False

@app.get("/results", response_class=HTMLResponse)
def show_results():
    total_possible = sum(q["points"] for q in QUESTIONS.values())
    percentage = (user_progress["total_score"] / total_possible) * 100
    passed = percentage >= 70

    # Calculate module scores
    module_scores = {
        "listening": {"score": 0, "total": 12, "questions": 3},
        "time_numbers": {"score": 0, "total": 12, "questions": 3},
        "grammar": {"score": 0, "total": 16, "questions": 4},
        "vocabulary": {"score": 0, "total": 32, "questions": 4},
        "reading": {"score": 0, "total": 24, "questions": 4},
        "speaking": {"score": 0, "total": 60, "questions": 3}
    }

    for q_num, result in user_progress["answers"].items():
        module = QUESTIONS[q_num]["module"]
        if module in module_scores:
            module_scores[module]["score"] += result["points"]

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Complete Assessment Results</title>
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
                max-width: 1000px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                padding: 60px 50px;
                box-shadow: 0 32px 64px rgba(0, 0, 0, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}

            .title {{
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 30px;
                background: linear-gradient(45deg, #007aff, #5856d6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
            }}

            .overall-score {{
                background: {"linear-gradient(135deg, #30d158, #00c7be)" if passed else "linear-gradient(135deg, #ff3b30, #ff6961)"};
                color: white;
                padding: 40px;
                border-radius: 20px;
                margin: 30px 0;
                box-shadow: 0 16px 32px rgba(0, 0, 0, 0.2);
                text-align: center;
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

            .modules-breakdown {{
                margin: 40px 0;
            }}

            .breakdown-title {{
                font-size: 1.5rem;
                font-weight: 600;
                color: #1d1d1f;
                margin-bottom: 25px;
                text-align: center;
            }}

            .modules-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}

            .module-result {{
                background: rgba(255, 255, 255, 0.7);
                padding: 25px;
                border-radius: 16px;
                border: 2px solid rgba(0, 122, 255, 0.1);
            }}

            .module-name {{
                font-size: 1.2rem;
                font-weight: 600;
                color: #007aff;
                margin-bottom: 15px;
            }}

            .module-score {{
                font-size: 1.5rem;
                font-weight: 700;
                color: #1d1d1f;
                margin-bottom: 10px;
            }}

            .module-percentage {{
                font-size: 1rem;
                color: #86868b;
                margin-bottom: 15px;
            }}

            .module-bar {{
                background: rgba(0, 122, 255, 0.1);
                height: 8px;
                border-radius: 4px;
                overflow: hidden;
            }}

            .module-bar-fill {{
                height: 100%;
                border-radius: 4px;
                transition: width 0.5s ease;
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
                text-align: center;
            }}

            .feature-list {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                list-style: none;
            }}

            .feature-item {{
                display: flex;
                align-items: center;
                font-size: 1rem;
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
                margin: 30px auto 0;
                box-shadow: 0 8px 24px rgba(0, 122, 255, 0.25);
                display: block;
                width: fit-content;
            }}

            .restart-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 12px 32px rgba(0, 122, 255, 0.35);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="title">Complete Assessment Results</div>

            <div class="overall-score">
                <div class="score-number">{user_progress["total_score"]}/{total_possible}</div>
                <div class="score-text">{percentage:.1f}% Overall Score</div>
                <div class="result-status">{"PASS" if passed else "FAIL"}</div>
            </div>

            <div class="modules-breakdown">
                <div class="breakdown-title">Module Breakdown</div>
                <div class="modules-grid">
                    {generate_module_results(module_scores)}
                </div>
            </div>

            <div class="features-verified">
                <div class="features-title">All Features Successfully Tested</div>
                <ul class="feature-list">
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Listening: Audio-only comprehension
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Time & Numbers: Audio context
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Grammar: Professional communication
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Vocabulary: Drag-and-drop matching
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Reading: Passage comprehension
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Speaking: Voice analysis
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Direct flow: No interruptions
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">✓</div>
                        Apple-style design
                    </li>
                </ul>
            </div>

            <a href="/" class="restart-btn">Take Assessment Again</a>
        </div>
    </body>
    </html>
    ''')

def generate_module_results(module_scores):
    html = ""
    module_names = {
        "listening": "🎧 Listening",
        "time_numbers": "🔢 Time & Numbers",
        "grammar": "📝 Grammar",
        "vocabulary": "📚 Vocabulary",
        "reading": "📖 Reading",
        "speaking": "🎤 Speaking"
    }

    for module, data in module_scores.items():
        percentage = (data["score"] / data["total"]) * 100 if data["total"] > 0 else 0
        bar_color = "#30d158" if percentage >= 70 else "#ff3b30" if percentage < 50 else "#ffd60a"

        html += f'''
        <div class="module-result">
            <div class="module-name">{module_names.get(module, module.title())}</div>
            <div class="module-score">{data["score"]}/{data["total"]} points</div>
            <div class="module-percentage">{percentage:.1f}% ({data["questions"]} questions)</div>
            <div class="module-bar">
                <div class="module-bar-fill" style="width: {percentage}%; background: {bar_color};"></div>
            </div>
        </div>
        '''
    return html

if __name__ == "__main__":
    print("Starting Complete Apple-Style Assessment...")
    print("21 questions across 6 modules")
    print("URL: http://127.0.0.1:8009")
    uvicorn.run(app, host="127.0.0.1", port=8009)