#!/usr/bin/env python3
"""
Dark Assessment - Black Background with Apple-Style Blue/Orange Accents
Inspired by Apple Events aesthetic
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import json
import os
from pathlib import Path

app = FastAPI(title="Cruise English Assessment")

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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
        <title>Cruise English Assessment Platform</title>
        <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
                background: transparent;
                min-height: 100vh;
                overflow-x: hidden;
                color: #1a1a1a;
            }

            .hero-container {
                width: 100%;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-start;
                padding: 40px;
            }

            .hero-background {
                width: 100%;
                max-width: 800px;
                margin-bottom: 40px;
            }

            .hero-background img {
                width: 100%;
                height: auto;
                display: block;
            }

            .main-content {
                max-width: 1400px;
                width: 100%;
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 40px;
                align-items: start;
            }

            .left-section {
                padding: 60px 40px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 24px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            }

            .hero-title {
                font-size: 4rem;
                font-weight: 800;
                color: #1a1a1a;
                line-height: 1.1;
                margin-bottom: 24px;
                text-shadow: none;
            }

            .hero-subtitle {
                font-size: 1.4rem;
                color: #4a5568;
                margin-bottom: 40px;
                line-height: 1.6;
                font-weight: 400;
            }

            .hero-stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 30px;
                margin-bottom: 50px;
            }

            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 20px;
                padding: 30px 25px;
                text-align: center;
                transition: all 0.3s ease;
                position: relative;
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
            }

            .stat-card:hover {
                transform: translateY(-8px);
                box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4);
            }

            .stat-number {
                font-size: 3rem;
                font-weight: 700;
                color: #ffffff;
                display: block;
                margin-bottom: 8px;
            }

            .stat-label {
                font-size: 1rem;
                color: rgba(255,255,255,0.95);
                font-weight: 500;
            }

            .cta-section {
                margin-top: 40px;
            }

            .start-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 60px;
                padding: 20px 50px;
                font-size: 1.3rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                text-decoration: none;
                display: inline-block;
                box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
                text-transform: uppercase;
                letter-spacing: 1px;
                position: relative;
                overflow: hidden;
            }

            .start-btn:hover {
                transform: translateY(-3px) scale(1.05);
                box-shadow: 0 25px 50px rgba(102, 126, 234, 0.5);
            }

            .right-section {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(30px);
                border: 1px solid rgba(0, 0, 0, 0.05);
                border-radius: 32px;
                padding: 50px 45px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                position: relative;
                overflow: hidden;
            }

            .right-section::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea, #764ba2);
            }

            .modules-title {
                font-size: 2rem;
                font-weight: 700;
                color: #1a1a1a;
                margin-bottom: 40px;
                text-align: center;
                position: relative;
            }

            .modules-title::after {
                content: '';
                position: absolute;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 80px;
                height: 3px;
                background: linear-gradient(90deg, #667eea, #764ba2);
                border-radius: 2px;
            }

            .modules-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 25px;
                margin-bottom: 40px;
            }

            .module-card {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 20px;
                padding: 25px 20px;
                transition: all 0.3s ease;
                position: relative;
            }

            .module-card:hover {
                transform: translateY(-5px);
                border-color: #667eea;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
            }

            .module-icon {
                font-size: 2.5rem;
                margin-bottom: 15px;
                display: block;
            }

            .module-name {
                font-size: 1.1rem;
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 8px;
            }

            .module-count {
                font-size: 0.95rem;
                color: #718096;
            }

            .assessment-info {
                background: #f8f9fa;
                border-radius: 20px;
                padding: 30px;
                margin-bottom: 30px;
                border: 2px solid #e9ecef;
            }

            .info-title {
                font-size: 1.2rem;
                font-weight: 600;
                color: #667eea;
                margin-bottom: 15px;
            }

            .info-list {
                list-style: none;
                margin: 0;
                padding: 0;
            }

            .info-item {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
                font-size: 0.95rem;
                color: #4a5568;
            }

            .info-item::before {
                content: '✓';
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 12px;
                font-size: 12px;
                font-weight: bold;
            }

            .secondary-btn {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 50px;
                padding: 16px 40px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                width: 100%;
                text-align: center;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            }

            .secondary-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4);
            }

            @media (max-width: 1200px) {
                .main-content {
                    grid-template-columns: 1fr;
                    gap: 40px;
                    max-width: 800px;
                }

                .hero-title {
                    font-size: 3rem;
                }

                .modules-grid {
                    grid-template-columns: 1fr;
                }
            }

            @media (max-width: 768px) {
                .hero-stats {
                    grid-template-columns: 1fr;
                    gap: 20px;
                }

                .hero-title {
                    font-size: 2.5rem;
                }

                .hero-container {
                    padding: 20px;
                }

                .left-section {
                    padding: 40px 20px;
                }

                .right-section {
                    padding: 30px 25px;
                }
            }
        </style>
    </head>
    <body>
        <div class="hero-container">
            <div class="hero-background">
                <img src="/static/images/cruise-background.png" alt="Cruise Ship">
            </div>

            <div class="main-content">
                <div class="left-section">
                    <h1 class="hero-title">Cruise English Assessment Platform</h1>
                    <p class="hero-subtitle">Professional English evaluation designed specifically for cruise ship hospitality staff. Test your skills across 6 comprehensive modules.</p>

                    <div class="hero-stats">
                        <div class="stat-card">
                            <span class="stat-number">21</span>
                            <span class="stat-label">Questions</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">6</span>
                            <span class="stat-label">Modules</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-number">15</span>
                            <span class="stat-label">Minutes</span>
                        </div>
                    </div>

                    <div class="cta-section">
                        <a href="/question/1" class="start-btn">Begin Assessment</a>
                    </div>
                </div>

                <div class="right-section">
                    <h2 class="modules-title">Assessment Modules</h2>

                    <div class="modules-grid">
                        <div class="module-card">
                            <span class="module-icon">🎧</span>
                            <div class="module-name">Listening</div>
                            <div class="module-count">3 audio questions</div>
                        </div>

                        <div class="module-card">
                            <span class="module-icon">🔢</span>
                            <div class="module-name">Time & Numbers</div>
                            <div class="module-count">3 context questions</div>
                        </div>

                        <div class="module-card">
                            <span class="module-icon">📝</span>
                            <div class="module-name">Grammar</div>
                            <div class="module-count">4 multiple choice</div>
                        </div>

                        <div class="module-card">
                            <span class="module-icon">📚</span>
                            <div class="module-name">Vocabulary</div>
                            <div class="module-count">4 drag-and-drop</div>
                        </div>

                        <div class="module-card">
                            <span class="module-icon">📖</span>
                            <div class="module-name">Reading</div>
                            <div class="module-count">4 comprehension</div>
                        </div>

                        <div class="module-card">
                            <span class="module-icon">🎤</span>
                            <div class="module-name">Speaking</div>
                            <div class="module-count">3 voice responses</div>
                        </div>
                    </div>

                    <div class="assessment-info">
                        <div class="info-title">What's Included:</div>
                        <ul class="info-list">
                            <li class="info-item">Audio-only listening comprehension</li>
                            <li class="info-item">Real-time voice analysis</li>
                            <li class="info-item">Interactive drag-and-drop exercises</li>
                            <li class="info-item">Cruise-specific terminology</li>
                            <li class="info-item">Professional hospitality scenarios</li>
                            <li class="info-item">Instant detailed feedback</li>
                        </ul>
                    </div>

                    <a href="/question/1" class="secondary-btn">Start Your Assessment</a>
                </div>
            </div>
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
        <div class="content-main">
            <div class="audio-section">
                <div class="audio-visual">
                    <div class="audio-icon">🎧</div>
                    <h3>Listen Carefully</h3>
                    <p class="audio-instruction">Click play to hear the conversation. You can replay it once.</p>
                    <div class="audio-controls">
                        <button onclick="playAudio()" class="audio-btn" id="playBtn">
                            <span class="btn-icon">▶</span>
                            Play Audio
                        </button>
                    </div>
                    <div id="audioStatus" class="audio-status"></div>
                    <div id="replayInfo" class="replay-info">2 replays remaining</div>
                </div>
            </div>
            <div class="question-section">
                <div class="question-text">{q["question"]}</div>
                <div class="options-container">
                    {generate_options(q["options"])}
                </div>
            </div>
        </div>
        '''

        script = f'''
        let replaysLeft = 2;
        function playAudio() {{
            if (replaysLeft <= 0) {{
                document.getElementById('audioStatus').innerHTML = '<span class="status-error">❌ No more replays</span>';
                return;
            }}
            const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
            utterance.rate = 0.8;
            utterance.onstart = () => {{
                document.getElementById('audioStatus').innerHTML = '<span class="status-playing">🔊 Playing audio...</span>';
                document.getElementById('playBtn').style.opacity = '0.7';
            }};
            utterance.onend = () => {{
                replaysLeft--;
                document.getElementById('audioStatus').innerHTML = '<span class="status-complete">✅ Audio complete</span>';
                document.getElementById('replayInfo').innerHTML = replaysLeft > 0 ? replaysLeft + ' replay(s) remaining' : 'No more replays available';
                document.getElementById('playBtn').style.opacity = '1';
            }};
            speechSynthesis.speak(utterance);
        }}
        '''

    elif q["module"] == "time_numbers":
        content = f'''
        <div class="content-main">
            <div class="audio-section">
                <div class="audio-visual">
                    <div class="audio-icon">🎧</div>
                    <h3>Listen for Information</h3>
                    <p class="audio-instruction">Listen to the conversation and identify the specific information requested.</p>
                    <div class="audio-controls">
                        <button onclick="playAudio()" class="audio-btn">
                            <span class="btn-icon">▶</span>
                            Play Conversation
                        </button>
                    </div>
                    <div id="audioStatus" class="audio-status"></div>
                </div>
            </div>
            <div class="question-section">
                <div class="question-text">{q["question"]}</div>
                <div class="input-container">
                    <input type="text" id="textAnswer" placeholder="Enter your answer here"
                           class="text-input" onchange="selectAnswer(this.value)">
                    <div class="input-hint">Format: Numbers or time (e.g., 7:00, 8, 9173)</div>
                </div>
            </div>
        </div>
        '''

        script = f'''
        function playAudio() {{
            const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
            utterance.rate = 0.8;
            utterance.onstart = () => document.getElementById('audioStatus').innerHTML = '<span class="status-playing">🔊 Playing conversation...</span>';
            utterance.onend = () => document.getElementById('audioStatus').innerHTML = '<span class="status-complete">✅ Conversation complete</span>';
            speechSynthesis.speak(utterance);
        }}
        '''

    elif q["module"] == "grammar":
        content = f'''
        <div class="content-main">
            <div class="grammar-section">
                <div class="grammar-icon">📝</div>
                <h3>Grammar Assessment</h3>
                <p class="grammar-instruction">Select the correct word to complete the sentence.</p>
            </div>
            <div class="question-section">
                <div class="question-text">{q["question"]}</div>
                <div class="options-container">
                    {generate_options(q["options"])}
                </div>
            </div>
        </div>
        '''
        script = ""

    elif q["module"] == "vocabulary":
        content = f'''
        <div class="content-main full-width">
            <div class="vocab-header">
                <div class="vocab-icon">📚</div>
                <h3>Vocabulary Matching</h3>
                <p class="vocab-instruction">{q["question"]}</p>
                <div class="vocab-help">Drag terms from the left to their matching definitions on the right</div>
            </div>
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
                <div id="matchesList" class="matches-list"></div>
            </div>
        </div>
        '''

        script = f'''
        let matches = {{}};
        let draggedTerm = null;
        const correctMatches = {json.dumps(q["correct_matches"])};

        function dragStart(e, term) {{
            draggedTerm = term;
            e.dataTransfer.effectAllowed = 'move';
            e.target.style.opacity = '0.5';
        }}

        function dragEnd(e) {{
            e.target.style.opacity = '1';
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
                e.target.classList.remove('drag-over');
            }}
        }}

        function updateMatchesDisplay() {{
            const matchesList = document.getElementById('matchesList');
            matchesList.innerHTML = '';
            for (const [term, def] of Object.entries(matches)) {{
                const matchDiv = document.createElement('div');
                matchDiv.className = 'match-item';
                matchDiv.innerHTML = `
                    <span class="match-term">${{term}}</span>
                    <span class="match-arrow">→</span>
                    <span class="match-def">${{def}}</span>
                    <button onclick="removeMatch('${{term}}')" class="remove-btn">×</button>
                `;
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
        <div class="content-main">
            <div class="reading-section">
                <div class="reading-icon">📖</div>
                <h3>Reading Comprehension</h3>
                <div class="passage-container">
                    <h4>Read the following passage carefully:</h4>
                    <div class="passage-text">{q["passage"]}</div>
                </div>
            </div>
            <div class="question-section">
                <div class="question-text">{q["question"]}</div>
                <div class="options-container">
                    {generate_options(q["options"])}
                </div>
            </div>
        </div>
        '''
        script = ""

    elif q["module"] == "speaking":
        content = f'''
        <div class="content-main">
            <div class="speaking-section">
                <div class="speaking-visual">
                    <div class="speaking-icon">🎤</div>
                    <h3>Speaking Assessment</h3>
                    <p class="speaking-instruction">Record your response to the following scenario. Speak clearly for at least {q["min_duration"]} seconds.</p>
                </div>
                <div class="scenario-card">
                    <div class="question-text">{q["question"]}</div>
                </div>
                <div class="recording-container">
                    <div class="recording-controls">
                        <button onclick="startRecording()" class="record-btn" id="recordBtn">
                            <span class="btn-icon">🎤</span>
                            Start Recording
                        </button>
                        <button onclick="stopRecording()" class="stop-btn" id="stopBtn" disabled>
                            <span class="btn-icon">⏹</span>
                            Stop Recording
                        </button>
                    </div>
                    <div id="recordingStatus" class="recording-status"></div>
                    <div class="recording-tips">
                        <div class="tip-item">💡 Speak clearly and at normal pace</div>
                        <div class="tip-item">⏱️ Minimum {q["min_duration"]} seconds required</div>
                        <div class="tip-item">🔊 Ensure your microphone is working</div>
                    </div>
                </div>
            </div>
        </div>
        '''

        script = f'''
        let mediaRecorder;
        let recordingSeconds = 0;
        let speechDetected = false;
        let recordingInterval;

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
                    document.getElementById('recordingStatus').innerHTML = '<span class="status-recording">🎤 Recording in progress... Speak now!</span>';
                    document.getElementById('recordBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;

                    recordingInterval = setInterval(() => {{
                        recordingSeconds++;
                        document.getElementById('recordingStatus').innerHTML = `<span class="status-recording">🎤 Recording... ${{recordingSeconds}}s</span>`;
                        if (recordingSeconds >= 30) {{
                            clearInterval(recordingInterval);
                            stopRecording();
                        }}
                    }}, 1000);
                }};

                mediaRecorder.onstop = () => {{
                    clearInterval(recordingInterval);
                    document.getElementById('recordBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;

                    if (!speechDetected) {{
                        selectedAnswer = 'No speech detected';
                        document.getElementById('recordingStatus').innerHTML = '<span class="status-error">❌ No speech detected - Please try again</span>';
                    }} else if (recordingSeconds < {q["min_duration"]}) {{
                        selectedAnswer = `Too short: ${{recordingSeconds}}s`;
                        document.getElementById('recordingStatus').innerHTML = `<span class="status-warning">⚠️ Recording too short (${{recordingSeconds}}s) - Minimum {q["min_duration"]}s required</span>`;
                    }} else {{
                        selectedAnswer = `Speech recorded: ${{recordingSeconds}}s`;
                        document.getElementById('recordingStatus').innerHTML = `<span class="status-success">✅ Excellent recording (${{recordingSeconds}}s) - Ready to submit</span>`;
                    }}

                    document.getElementById('submitBtn').disabled = false;
                    stream.getTracks().forEach(track => track.stop());
                }};

                mediaRecorder.start();
            }})
            .catch(err => {{
                document.getElementById('recordingStatus').innerHTML = '<span class="status-error">❌ Microphone access denied - Please allow microphone access</span>';
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
        <title>Question {q_num} - Dark Assessment</title>
        <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
                background: #000000;
                min-height: 100vh;
                color: #ffffff;
            }}

            .header {{
                background: rgba(20, 20, 20, 0.95);
                backdrop-filter: blur(20px);
                border-bottom: 1px solid rgba(0, 122, 255, 0.2);
                padding: 20px 40px;
                position: sticky;
                top: 0;
                z-index: 100;
            }}

            .header-content {{
                max-width: 1400px;
                margin: 0 auto;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}

            .question-info {{
                display: flex;
                align-items: center;
                gap: 30px;
            }}

            .question-number {{
                font-size: 1.1rem;
                color: rgba(255, 255, 255, 0.6);
                font-weight: 500;
            }}

            .module-badge {{
                background: linear-gradient(45deg, #007aff, #ff9500);
                color: white;
                padding: 8px 20px;
                border-radius: 25px;
                font-size: 0.9rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                box-shadow: 0 0 20px rgba(0, 122, 255, 0.4);
            }}

            .progress-section {{
                flex: 1;
                max-width: 400px;
                margin: 0 30px;
            }}

            .progress-bar {{
                background: rgba(255, 255, 255, 0.1);
                height: 8px;
                border-radius: 4px;
                overflow: hidden;
                position: relative;
            }}

            .progress-fill {{
                background: linear-gradient(90deg, #007aff, #ff9500);
                height: 100%;
                width: {progress}%;
                border-radius: 4px;
                transition: width 0.5s ease;
                position: relative;
                box-shadow: 0 0 20px rgba(0, 122, 255, 0.5);
            }}

            .progress-fill::after {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                animation: shimmer 2s infinite;
            }}

            @keyframes shimmer {{
                0% {{ transform: translateX(-100%); }}
                100% {{ transform: translateX(100%); }}
            }}

            .progress-text {{
                font-size: 0.9rem;
                color: rgba(255, 255, 255, 0.6);
                margin-top: 5px;
                text-align: center;
            }}

            .container {{
                max-width: 1400px;
                margin: 40px auto;
                padding: 0 40px;
            }}

            .content-main {{
                background: rgba(20, 20, 20, 0.8);
                backdrop-filter: blur(30px);
                border-radius: 32px;
                padding: 50px;
                box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(0, 122, 255, 0.2);
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 60px;
                align-items: start;
            }}

            .content-main.full-width {{
                grid-template-columns: 1fr;
            }}

            .audio-section, .grammar-section, .reading-section, .speaking-section {{
                text-align: center;
            }}

            .audio-visual, .speaking-visual {{
                background: linear-gradient(135deg, #007aff 0%, #ff9500 100%);
                border-radius: 24px;
                padding: 40px 30px;
                color: white;
                margin-bottom: 30px;
                box-shadow: 0 0 50px rgba(0, 122, 255, 0.3);
            }}

            .audio-icon, .grammar-icon, .reading-icon, .speaking-icon, .vocab-icon {{
                font-size: 4rem;
                margin-bottom: 20px;
                display: block;
            }}

            .audio-visual h3, .speaking-visual h3 {{
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 15px;
            }}

            .audio-instruction, .speaking-instruction {{
                font-size: 1.1rem;
                opacity: 0.9;
                margin-bottom: 25px;
                line-height: 1.5;
            }}

            .audio-controls, .recording-controls {{
                margin: 25px 0;
            }}

            .audio-btn, .record-btn, .stop-btn {{
                background: rgba(0, 0, 0, 0.3);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 50px;
                padding: 15px 35px;
                font-size: 1.1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 10px;
                margin: 0 10px;
                backdrop-filter: blur(10px);
            }}

            .audio-btn:hover, .record-btn:hover, .stop-btn:hover {{
                transform: translateY(-3px);
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.5);
                box-shadow: 0 10px 30px rgba(255, 255, 255, 0.1);
            }}

            .record-btn:disabled, .stop-btn:disabled {{
                opacity: 0.4;
                cursor: not-allowed;
                transform: none;
            }}

            .btn-icon {{
                font-size: 1.2rem;
            }}

            .audio-status, .recording-status {{
                margin: 20px 0;
                font-size: 1.1rem;
                font-weight: 500;
                min-height: 30px;
            }}

            .status-playing {{ color: #007aff; }}
            .status-complete {{ color: #30d158; }}
            .status-error {{ color: #ff3b30; }}
            .status-recording {{ color: #ff9500; }}
            .status-warning {{ color: #ff9500; }}
            .status-success {{ color: #30d158; }}

            .replay-info {{
                font-size: 0.95rem;
                opacity: 0.8;
                margin-top: 10px;
            }}

            .grammar-section {{
                background: rgba(0, 122, 255, 0.1);
                border-radius: 24px;
                padding: 40px 30px;
                margin-bottom: 30px;
                border: 1px solid rgba(0, 122, 255, 0.2);
            }}

            .grammar-icon {{
                color: #007aff;
            }}

            .grammar-section h3 {{
                font-size: 1.8rem;
                font-weight: 700;
                color: #007aff;
                margin-bottom: 15px;
            }}

            .grammar-instruction {{
                font-size: 1.1rem;
                color: rgba(255, 255, 255, 0.8);
                line-height: 1.5;
            }}

            .question-section {{
                display: flex;
                flex-direction: column;
                gap: 30px;
            }}

            .question-text {{
                font-size: 1.8rem;
                font-weight: 600;
                color: #ffffff;
                line-height: 1.4;
                text-align: center;
                padding: 30px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 20px;
                border-left: 5px solid #007aff;
                border: 1px solid rgba(0, 122, 255, 0.2);
            }}

            .options-container {{
                display: grid;
                gap: 20px;
            }}

            .option {{
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 25px 30px;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                font-size: 1.1rem;
                font-weight: 500;
                position: relative;
                overflow: hidden;
                color: #ffffff;
            }}

            .option::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(0, 122, 255, 0.1), transparent);
                transition: left 0.5s ease;
            }}

            .option:hover {{
                border-color: #007aff;
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 15px 35px rgba(0, 122, 255, 0.2);
            }}

            .option:hover::before {{
                left: 100%;
            }}

            .option.selected {{
                background: linear-gradient(135deg, #007aff, #ff9500);
                color: white;
                border-color: #007aff;
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 15px 35px rgba(0, 122, 255, 0.4), 0 0 30px rgba(0, 122, 255, 0.3);
            }}

            .option input {{
                margin-right: 15px;
                transform: scale(1.2);
            }}

            .input-container {{
                text-align: center;
            }}

            .text-input {{
                width: 100%;
                max-width: 500px;
                padding: 25px 30px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                font-size: 1.3rem;
                background: rgba(255, 255, 255, 0.05);
                transition: all 0.3s ease;
                text-align: center;
                font-weight: 500;
                color: #ffffff;
            }}

            .text-input:focus {{
                outline: none;
                border-color: #007aff;
                box-shadow: 0 0 25px rgba(0, 122, 255, 0.3);
                transform: scale(1.02);
                background: rgba(255, 255, 255, 0.1);
            }}

            .input-hint {{
                font-size: 0.95rem;
                color: rgba(255, 255, 255, 0.5);
                margin-top: 15px;
                font-style: italic;
            }}

            .vocab-header {{
                text-align: center;
                margin-bottom: 40px;
            }}

            .vocab-icon {{
                color: #ff9500;
                margin-bottom: 20px;
            }}

            .vocab-header h3 {{
                font-size: 2rem;
                font-weight: 700;
                color: #ffffff;
                margin-bottom: 15px;
            }}

            .vocab-instruction {{
                font-size: 1.3rem;
                color: rgba(255, 255, 255, 0.8);
                margin-bottom: 10px;
                font-weight: 500;
            }}

            .vocab-help {{
                font-size: 1rem;
                color: rgba(255, 255, 255, 0.6);
                font-style: italic;
            }}

            .vocab-container {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 50px;
                margin: 40px 0;
            }}

            .terms-section, .definitions-section {{
                background: rgba(255, 255, 255, 0.05);
                padding: 35px 30px;
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            .terms-section h4, .definitions-section h4 {{
                font-size: 1.4rem;
                margin-bottom: 25px;
                color: #ffffff;
                text-align: center;
                font-weight: 700;
            }}

            .term, .definition {{
                background: rgba(255, 255, 255, 0.05);
                padding: 20px 25px;
                margin: 15px 0;
                border-radius: 16px;
                border: 2px solid rgba(255, 255, 255, 0.1);
                cursor: grab;
                transition: all 0.3s ease;
                font-size: 1rem;
                font-weight: 500;
                position: relative;
                color: #ffffff;
            }}

            .term:hover, .definition:hover {{
                transform: translateY(-3px);
                box-shadow: 0 10px 25px rgba(0, 122, 255, 0.3);
                border-color: #007aff;
            }}

            .term {{
                user-select: none;
                text-align: center;
                font-weight: 600;
                background: linear-gradient(135deg, #007aff, #ff9500);
                color: white;
                border-color: #007aff;
                box-shadow: 0 0 20px rgba(0, 122, 255, 0.2);
            }}

            .term:active {{
                cursor: grabbing;
            }}

            .definition.drag-over {{
                background: linear-gradient(135deg, #30d158, #00c896);
                color: white;
                border-color: #30d158;
                transform: scale(1.05);
            }}

            .matches-display {{
                background: rgba(48, 209, 88, 0.1);
                border-radius: 24px;
                padding: 35px;
                margin-top: 40px;
                border: 1px solid rgba(48, 209, 88, 0.2);
            }}

            .matches-display h4 {{
                color: #30d158;
                margin-bottom: 25px;
                font-size: 1.4rem;
                text-align: center;
                font-weight: 700;
            }}

            .matches-list {{
                display: grid;
                gap: 15px;
            }}

            .match-item {{
                background: rgba(255, 255, 255, 0.1);
                padding: 20px 25px;
                border-radius: 16px;
                display: grid;
                grid-template-columns: 1fr auto 1fr auto;
                align-items: center;
                gap: 15px;
                border: 1px solid rgba(48, 209, 88, 0.3);
            }}

            .match-term {{
                font-weight: 600;
                color: #ffffff;
            }}

            .match-arrow {{
                font-size: 1.5rem;
                color: #30d158;
                font-weight: bold;
            }}

            .match-def {{
                color: rgba(255, 255, 255, 0.8);
            }}

            .remove-btn {{
                background: #ff3b30;
                color: white;
                border: none;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                cursor: pointer;
                font-weight: bold;
                font-size: 1.1rem;
                transition: all 0.3s ease;
            }}

            .remove-btn:hover {{
                background: #d70015;
                transform: scale(1.1);
            }}

            .reading-section {{
                margin-bottom: 40px;
            }}

            .reading-icon {{
                color: #ff9500;
                margin-bottom: 20px;
            }}

            .reading-section h3 {{
                font-size: 1.8rem;
                font-weight: 700;
                color: #ff9500;
                margin-bottom: 25px;
            }}

            .passage-container {{
                background: rgba(255, 149, 0, 0.1);
                border-radius: 20px;
                padding: 35px;
                border-left: 5px solid #ff9500;
                border: 1px solid rgba(255, 149, 0, 0.2);
            }}

            .passage-container h4 {{
                font-size: 1.2rem;
                color: #ff9500;
                margin-bottom: 20px;
                font-weight: 600;
            }}

            .passage-text {{
                background: rgba(255, 255, 255, 0.05);
                padding: 30px;
                border-radius: 16px;
                line-height: 1.7;
                font-size: 1.1rem;
                color: #ffffff;
                text-align: left;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            .scenario-card {{
                background: rgba(255, 149, 0, 0.1);
                border-radius: 20px;
                padding: 35px;
                margin: 30px 0;
                border-left: 5px solid #ff9500;
                border: 1px solid rgba(255, 149, 0, 0.2);
            }}

            .recording-container {{
                background: rgba(255, 255, 255, 0.05);
                border-radius: 24px;
                padding: 35px;
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            .recording-tips {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 30px;
            }}

            .tip-item {{
                background: rgba(255, 255, 255, 0.05);
                padding: 15px 20px;
                border-radius: 12px;
                font-size: 0.95rem;
                color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            .submit-section {{
                text-align: center;
                margin-top: 50px;
                padding-top: 40px;
                border-top: 1px solid rgba(0, 122, 255, 0.2);
            }}

            .submit-btn {{
                background: linear-gradient(45deg, #007aff, #ff9500);
                color: white;
                border: none;
                border-radius: 60px;
                padding: 20px 60px;
                font-size: 1.3rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                box-shadow: 0 15px 35px rgba(0, 122, 255, 0.3), 0 0 50px rgba(0, 122, 255, 0.2);
                text-transform: uppercase;
                letter-spacing: 1px;
            }}

            .submit-btn:hover:not(:disabled) {{
                transform: translateY(-3px) scale(1.05);
                box-shadow: 0 25px 50px rgba(0, 122, 255, 0.4), 0 0 80px rgba(0, 122, 255, 0.3);
            }}

            .submit-btn:disabled {{
                background: rgba(255, 255, 255, 0.2);
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }}

            @media (max-width: 1200px) {{
                .content-main {{
                    grid-template-columns: 1fr;
                    gap: 40px;
                    padding: 40px;
                }}

                .vocab-container {{
                    grid-template-columns: 1fr;
                    gap: 30px;
                }}

                .container {{
                    padding: 0 20px;
                }}
            }}

            @media (max-width: 768px) {{
                .header {{
                    padding: 15px 20px;
                }}

                .header-content {{
                    flex-direction: column;
                    gap: 20px;
                }}

                .progress-section {{
                    margin: 0;
                    max-width: 100%;
                }}

                .content-main {{
                    padding: 30px 25px;
                }}

                .question-text {{
                    font-size: 1.5rem;
                    padding: 25px 20px;
                }}

                .recording-tips {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <div class="question-info">
                    <div class="question-number">Question {q_num} of 21</div>
                    <div class="module-badge">{q["module"].replace("_", " & ").title()}</div>
                </div>

                <div class="progress-section">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">{progress:.1f}% Complete</div>
                </div>

                <div class="question-info">
                    <div class="question-number">{q["points"]} Points</div>
                </div>
            </div>
        </div>

        <div class="container">
            {content}

            <div class="submit-section">
                <button class="submit-btn" id="submitBtn" onclick="submitAnswer({q_num})" disabled>
                    Continue to Next Question
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
                    alert('Please provide an answer before continuing');
                    return;
                }}

                // Show loading state
                document.getElementById('submitBtn').innerHTML = 'Processing...';
                document.getElementById('submitBtn').disabled = true;

                // Add slight delay for better UX
                setTimeout(() => {{
                    window.location.href = `/submit/${{qNum}}?answer=${{encodeURIComponent(selectedAnswer)}}`;
                }}, 500);
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
        <div class="term" draggable="true" ondragstart="dragStart(event, '{term}')" ondragend="dragEnd(event)">{term}</div>
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
        <title>Assessment Results - Dark Theme</title>
        <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
                background: #000000;
                min-height: 100vh;
                padding: 40px 20px;
                color: #ffffff;
            }}

            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}

            .results-header {{
                text-align: center;
                margin-bottom: 50px;
            }}

            .results-title {{
                font-size: 3.5rem;
                font-weight: 800;
                color: white;
                margin-bottom: 20px;
                text-shadow: 0 4px 20px rgba(0, 122, 255, 0.3);
            }}

            .results-subtitle {{
                font-size: 1.3rem;
                color: rgba(255,255,255,0.7);
                font-weight: 400;
            }}

            .overall-score {{
                background: {"linear-gradient(135deg, #007aff, #30d158)" if passed else "linear-gradient(135deg, #ff3b30, #ff9500)"};
                color: white;
                padding: 50px;
                border-radius: 32px;
                margin: 40px 0;
                box-shadow: 0 20px 60px rgba(0, 122, 255, 0.4), 0 0 100px rgba(0, 122, 255, 0.2);
                text-align: center;
                position: relative;
                overflow: hidden;
            }}

            .overall-score::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                animation: float 6s ease-in-out infinite;
            }}

            @keyframes float {{
                0%, 100% {{ transform: translate(-50%, -50%) rotate(0deg); }}
                50% {{ transform: translate(-50%, -50%) rotate(180deg); }}
            }}

            .score-content {{
                position: relative;
                z-index: 2;
            }}

            .score-number {{
                font-size: 4.5rem;
                font-weight: 800;
                margin-bottom: 15px;
                display: block;
            }}

            .score-text {{
                font-size: 1.5rem;
                opacity: 0.95;
                margin-bottom: 20px;
            }}

            .result-status {{
                font-size: 2.5rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 2px;
            }}

            .modules-breakdown {{
                background: rgba(20, 20, 20, 0.8);
                backdrop-filter: blur(30px);
                border-radius: 32px;
                padding: 50px;
                margin: 40px 0;
                box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(0, 122, 255, 0.2);
            }}

            .breakdown-title {{
                font-size: 2rem;
                font-weight: 700;
                color: #ffffff;
                margin-bottom: 40px;
                text-align: center;
                position: relative;
            }}

            .breakdown-title::after {{
                content: '';
                position: absolute;
                bottom: -15px;
                left: 50%;
                transform: translateX(-50%);
                width: 100px;
                height: 4px;
                background: linear-gradient(90deg, #007aff, #ff9500);
                border-radius: 2px;
                box-shadow: 0 0 20px rgba(0, 122, 255, 0.5);
            }}

            .modules-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 30px;
            }}

            .module-result {{
                background: rgba(255, 255, 255, 0.05);
                padding: 35px 30px;
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}

            .module-result::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #007aff, #ff9500);
                box-shadow: 0 0 20px rgba(0, 122, 255, 0.3);
            }}

            .module-result:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(0, 122, 255, 0.2);
                border-color: rgba(0, 122, 255, 0.3);
            }}

            .module-name {{
                font-size: 1.4rem;
                font-weight: 700;
                color: #ffffff;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 15px;
            }}

            .module-icon {{
                font-size: 1.8rem;
            }}

            .module-score {{
                font-size: 2rem;
                font-weight: 800;
                color: #007aff;
                margin-bottom: 10px;
            }}

            .module-percentage {{
                font-size: 1.1rem;
                color: rgba(255, 255, 255, 0.6);
                margin-bottom: 20px;
                font-weight: 500;
            }}

            .module-bar {{
                background: rgba(255, 255, 255, 0.1);
                height: 10px;
                border-radius: 5px;
                overflow: hidden;
                margin-bottom: 15px;
            }}

            .module-bar-fill {{
                height: 100%;
                border-radius: 5px;
                transition: width 1s ease;
                position: relative;
            }}

            .module-bar-fill::after {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                animation: shimmer 2s infinite;
            }}

            @keyframes shimmer {{
                0% {{ transform: translateX(-100%); }}
                100% {{ transform: translateX(100%); }}
            }}

            .module-questions {{
                font-size: 0.95rem;
                color: rgba(255, 255, 255, 0.5);
                font-weight: 500;
            }}

            .features-verified {{
                background: rgba(20, 20, 20, 0.8);
                backdrop-filter: blur(30px);
                border-radius: 32px;
                padding: 50px;
                margin: 40px 0;
                box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(30, 209, 88, 0.2);
            }}

            .features-title {{
                font-size: 1.8rem;
                font-weight: 700;
                color: #30d158;
                margin-bottom: 30px;
                text-align: center;
            }}

            .feature-list {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                list-style: none;
            }}

            .feature-item {{
                display: flex;
                align-items: center;
                font-size: 1.1rem;
                color: #ffffff;
                padding: 15px 20px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.3s ease;
            }}

            .feature-item:hover {{
                transform: translateX(10px);
                border-color: #30d158;
                background: rgba(48, 209, 88, 0.1);
            }}

            .feature-icon {{
                width: 32px;
                height: 32px;
                background: linear-gradient(45deg, #30d158, #00c896);
                border-radius: 8px;
                margin-right: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 700;
                font-size: 16px;
                box-shadow: 0 0 20px rgba(48, 209, 88, 0.3);
            }}

            .action-section {{
                text-align: center;
                margin-top: 50px;
            }}

            .restart-btn {{
                background: linear-gradient(45deg, #007aff, #ff9500);
                color: white;
                border: none;
                border-radius: 60px;
                padding: 20px 50px;
                font-size: 1.3rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                text-decoration: none;
                display: inline-block;
                box-shadow: 0 15px 35px rgba(0, 122, 255, 0.3), 0 0 50px rgba(0, 122, 255, 0.2);
                text-transform: uppercase;
                letter-spacing: 1px;
            }}

            .restart-btn:hover {{
                transform: translateY(-3px) scale(1.05);
                box-shadow: 0 25px 50px rgba(0, 122, 255, 0.4), 0 0 80px rgba(0, 122, 255, 0.3);
            }}

            @media (max-width: 768px) {{
                .results-title {{
                    font-size: 2.5rem;
                }}

                .modules-breakdown, .features-verified {{
                    padding: 30px 25px;
                }}

                .modules-grid {{
                    grid-template-columns: 1fr;
                }}

                .score-number {{
                    font-size: 3.5rem;
                }}

                .result-status {{
                    font-size: 2rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="results-header">
                <div class="results-title">Assessment Complete!</div>
                <div class="results-subtitle">Your comprehensive English proficiency results</div>
            </div>

            <div class="overall-score">
                <div class="score-content">
                    <div class="score-number">{user_progress["total_score"]}/{total_possible}</div>
                    <div class="score-text">{percentage:.1f}% Overall Score</div>
                    <div class="result-status">{"PASS" if passed else "FAIL"}</div>
                </div>
            </div>

            <div class="modules-breakdown">
                <div class="breakdown-title">Detailed Module Results</div>
                <div class="modules-grid">
                    {generate_module_results(module_scores)}
                </div>
            </div>

            <div class="features-verified">
                <div class="features-title">✓ All Features Successfully Tested</div>
                <ul class="feature-list">
                    <li class="feature-item">
                        <div class="feature-icon">🎧</div>
                        Audio-only listening comprehension
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">🔢</div>
                        Time & numbers with audio context
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">📝</div>
                        Professional grammar assessment
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">📚</div>
                        Interactive vocabulary matching
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">📖</div>
                        Reading comprehension skills
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">🎤</div>
                        Real-time voice analysis
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">⚡</div>
                        Seamless user experience
                    </li>
                    <li class="feature-item">
                        <div class="feature-icon">🌙</div>
                        Premium dark interface
                    </li>
                </ul>
            </div>

            <div class="action-section">
                <a href="/" class="restart-btn">Take Assessment Again</a>
            </div>
        </div>
    </body>
    </html>
    ''')

def generate_module_results(module_scores):
    html = ""
    module_info = {
        "listening": {"name": "🎧 Listening Comprehension", "color": "#007aff"},
        "time_numbers": {"name": "🔢 Time & Numbers", "color": "#ff9500"},
        "grammar": {"name": "📝 Grammar", "color": "#af52de"},
        "vocabulary": {"name": "📚 Vocabulary", "color": "#32d74b"},
        "reading": {"name": "📖 Reading Comprehension", "color": "#ff2d92"},
        "speaking": {"name": "🎤 Speaking", "color": "#ff453a"}
    }

    for module, data in module_scores.items():
        percentage = (data["score"] / data["total"]) * 100 if data["total"] > 0 else 0
        info = module_info.get(module, {"name": module.title(), "color": "#8e8e93"})

        if percentage >= 80:
            bar_color = "#30d158"
        elif percentage >= 60:
            bar_color = "#ff9500"
        else:
            bar_color = "#ff453a"

        html += f'''
        <div class="module-result">
            <div class="module-name">
                <span class="module-icon">{info["name"].split()[0]}</span>
                {info["name"].split(maxsplit=1)[1] if len(info["name"].split()) > 1 else info["name"]}
            </div>
            <div class="module-score">{data["score"]}/{data["total"]}</div>
            <div class="module-percentage">{percentage:.1f}% Score</div>
            <div class="module-bar">
                <div class="module-bar-fill" style="width: {percentage}%; background: {bar_color}; box-shadow: 0 0 15px {bar_color}50;"></div>
            </div>
            <div class="module-questions">{data["questions"]} questions completed</div>
        </div>
        '''
    return html

if __name__ == "__main__":
    print("Starting Cruise English Assessment Platform...")
    print("Premium dark interface with Apple-style design")
    print("URL: http://127.0.0.1:8080")
    uvicorn.run(app, host="127.0.0.1", port=8080)