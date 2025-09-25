#!/usr/bin/env python3
"""
Complete English Assessment - All 6 Modules
Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking
"""

from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
import uvicorn
import json

app = FastAPI(title="Complete English Assessment - All Modules")

# All 6 modules with sample questions (21 questions total)
QUESTIONS = {
    # LISTENING MODULE (4 questions × 4 points = 16 points)
    1: {
        "module": "listening",
        "question": "Guest says: 'I'd like to book a table for four at 7 PM.' What time is the reservation?",
        "audio_text": "Hello, I'd like to book a table for four people at seven PM tonight, please.",
        "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
        "correct": "7 PM",
        "points": 4
    },
    2: {
        "module": "listening",
        "question": "Guest complaint: 'The air conditioning is too cold in room 8254.' What is the room number?",
        "audio_text": "Excuse me, the air conditioning is way too cold in room eight-two-five-four. Could you please send someone to fix it?",
        "options": ["8245", "8254", "8524", "2548"],
        "correct": "8254",
        "points": 4
    },
    3: {
        "module": "listening",
        "question": "Lost and found: 'I left my sunglasses at the pool yesterday.' Where were they left?",
        "audio_text": "Hi, I think I left my sunglasses at the pool area yesterday afternoon. Have you seen them?",
        "options": ["Beach", "Pool", "Spa", "Restaurant"],
        "correct": "Pool",
        "points": 4
    },
    4: {
        "module": "listening",
        "question": "Room service: 'Your dinner will be delivered in 15 minutes.' When will it arrive?",
        "audio_text": "Good evening, this is room service. Your dinner will be delivered to your cabin in approximately fifteen minutes.",
        "options": ["5 minutes", "15 minutes", "50 minutes", "1 hour"],
        "correct": "15 minutes",
        "points": 4
    },

    # TIME & NUMBERS MODULE (4 questions × 4 points = 16 points)
    5: {
        "module": "time_numbers",
        "question": "Breakfast is served from ___ to 10:30 AM.",
        "correct": "7:00",
        "hint": "Enter time in H:MM format",
        "context": "Standard breakfast hours",
        "points": 4
    },
    6: {
        "module": "time_numbers",
        "question": "Your cabin number is ___.",
        "correct": "8254",
        "hint": "4-digit room number",
        "context": "Guest room assignment",
        "points": 4
    },
    7: {
        "module": "time_numbers",
        "question": "The spa closes at ___ PM.",
        "correct": "9",
        "hint": "Evening closing time",
        "context": "Spa operating hours",
        "points": 4
    },
    8: {
        "module": "time_numbers",
        "question": "Party of ___ at 6:30 PM.",
        "correct": "8",
        "hint": "Number of guests",
        "context": "Restaurant reservation",
        "points": 4
    },

    # GRAMMAR MODULE (4 questions × 4 points = 16 points)
    9: {
        "module": "grammar",
        "question": "___ I help you with your luggage?",
        "options": ["May", "Do", "Will", "Am"],
        "correct": "May",
        "explanation": "May is the most polite form for offering help",
        "points": 4
    },
    10: {
        "module": "grammar",
        "question": "Your room ___ been cleaned and is ready.",
        "options": ["have", "has", "had", "having"],
        "correct": "has",
        "explanation": "Singular subject 'room' requires 'has'",
        "points": 4
    },
    11: {
        "module": "grammar",
        "question": "If you need anything, please ___ hesitate to call.",
        "options": ["not", "don't", "doesn't", "won't"],
        "correct": "don't",
        "explanation": "Standard polite expression in hospitality",
        "points": 4
    },
    12: {
        "module": "grammar",
        "question": "___ you like to make a restaurant reservation?",
        "options": ["Would", "Will", "Are", "Do"],
        "correct": "Would",
        "explanation": "Would is more polite than 'will' for offers",
        "points": 4
    },

    # VOCABULARY MODULE (4 questions × 4 points = 16 points)
    13: {
        "module": "vocabulary",
        "question": "Match these HOUSEKEEPING terms to the correct category:",
        "categories": {
            "Room Items": ["amenities", "turndown", "linen"],
            "Service Types": ["housekeeping", "maintenance", "laundry"],
            "Guest Needs": ["toiletries", "towels", "pillows"]
        },
        "words": ["amenities", "turndown", "linen", "housekeeping", "maintenance", "laundry", "toiletries", "towels", "pillows"],
        "correct": {"Room Items": ["amenities", "turndown", "linen"]},
        "points": 4
    },
    14: {
        "module": "vocabulary",
        "question": "Match these DINING terms to the correct category:",
        "categories": {
            "Menu Items": ["appetizer", "entree", "dessert"],
            "Service Areas": ["buffet", "restaurant", "room service"],
            "Beverages": ["wine", "cocktail", "coffee"]
        },
        "words": ["appetizer", "entree", "dessert", "buffet", "restaurant", "room service", "wine", "cocktail", "coffee"],
        "correct": {"Menu Items": ["appetizer", "entree", "dessert"]},
        "points": 4
    },
    15: {
        "module": "vocabulary",
        "question": "Match these GUEST SERVICES terms to the correct category:",
        "categories": {
            "Staff Roles": ["concierge", "bellhop", "valet"],
            "Services": ["check-in", "wake-up call", "dry cleaning"],
            "Facilities": ["gymnasium", "spa", "pool"]
        },
        "words": ["concierge", "bellhop", "valet", "check-in", "wake-up call", "dry cleaning", "gymnasium", "spa", "pool"],
        "correct": {"Staff Roles": ["concierge", "bellhop", "valet"]},
        "points": 4
    },
    16: {
        "module": "vocabulary",
        "question": "Match these SERVICE QUALITY terms to the correct category:",
        "categories": {
            "Positive Qualities": ["courteous", "efficient", "attentive"],
            "Service Actions": ["assist", "accommodate", "provide"],
            "Guest Satisfaction": ["comfortable", "satisfied", "pleased"]
        },
        "words": ["courteous", "efficient", "attentive", "assist", "accommodate", "provide", "comfortable", "satisfied", "pleased"],
        "correct": {"Positive Qualities": ["courteous", "efficient", "attentive"]},
        "points": 4
    },

    # READING MODULE (4 questions × 4 points = 16 points)
    17: {
        "module": "reading",
        "question": "Choose the best title for this text:",
        "text": "Our recent survey shows 94% guest satisfaction with housekeeping services. Room cleanliness scored highest, while bathroom amenity restocking needs improvement. Staff friendliness received excellent ratings across all departments.",
        "options": [
            "Housekeeping Performance Review",
            "Guest Complaint Summary",
            "Staff Training Manual",
            "Hotel Revenue Report"
        ],
        "correct": "Housekeeping Performance Review",
        "points": 4
    },
    18: {
        "module": "reading",
        "question": "Choose the best title for this text:",
        "text": "Guest in Suite 7234 has severe nut allergy. All meals must be prepared in nut-free environment. Kitchen staff should use separate utensils and prep areas. Please coordinate with chef for all room service orders.",
        "options": [
            "Kitchen Safety Protocol",
            "Allergy Management Notice",
            "Room Service Menu",
            "Staff Scheduling Update"
        ],
        "correct": "Allergy Management Notice",
        "points": 4
    },
    19: {
        "module": "reading",
        "question": "Choose the best title for this text:",
        "text": "Tonight's entertainment features live jazz music in the main lounge from 8-11 PM. The dance floor will be open with DJ music from 10 PM until midnight. Dress code is smart casual for all evening events.",
        "options": [
            "Dining Schedule Update",
            "Evening Entertainment Program",
            "Dress Code Requirements",
            "Lounge Renovation Notice"
        ],
        "correct": "Evening Entertainment Program",
        "points": 4
    },
    20: {
        "module": "reading",
        "question": "Choose the best title for this text:",
        "text": "Due to rough weather conditions, all outdoor deck activities are suspended until further notice. Passengers should remain in interior areas. Pool and spa services continue normal operations. Safety briefing at 3 PM in the main theater.",
        "options": [
            "Weather Safety Advisory",
            "Entertainment Schedule Change",
            "Pool Maintenance Notice",
            "Theater Show Information"
        ],
        "correct": "Weather Safety Advisory",
        "points": 4
    },

    # SPEAKING MODULE (1 question × 20 points = 20 points)
    21: {
        "module": "speaking",
        "question": "SCENARIO: Guest says 'The air conditioning in my room is too cold.' Give an appropriate response.",
        "expected_response": "I apologize for the inconvenience. I'll send someone to adjust the temperature right away. Is there anything else I can help you with?",
        "scenario_context": "Front desk interaction with guest complaint",
        "scoring_criteria": {
            "content_accuracy": 8,  # Does it address the issue?
            "politeness": 4,        # Uses polite language?
            "completeness": 4,      # Offers solution + follow-up?
            "clarity": 4           # Clear pronunciation/grammar?
        },
        "points": 20
    }
}

user_progress = {
    "current_question": 1,
    "answers": {},
    "total_score": 0,
    "module_scores": {
        "listening": 0,
        "time_numbers": 0,
        "grammar": 0,
        "vocabulary": 0,
        "reading": 0,
        "speaking": 0
    }
}

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complete English Assessment - All 6 Modules</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            .card { background: white; padding: 25px; border-radius: 10px; margin: 20px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .header { background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; text-align: center; padding: 40px; border-radius: 15px; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 10px; text-decoration: none; display: inline-block; }
            .btn:hover { background: #1e40af; transform: translateY(-2px); }
            .module-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin: 20px 0; }
            .module-card { background: #f8fafc; padding: 20px; border-radius: 8px; border-left: 5px solid #1e3a8a; }
            .stats { background: #e8f4fd; padding: 20px; border-radius: 8px; border: 2px solid #3b82f6; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚢 Complete English Assessment Platform</h1>
            <h2>All 6 Modules - Hotel Operations Division</h2>
            <p style="font-size: 18px; margin-top: 20px;">✨ Full Cruise Employee Assessment Experience ✨</p>
        </div>

        <div class="stats">
            <h3>📊 Complete Assessment Overview</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; text-align: center;">
                <div><strong>Total Questions:</strong><br>21 Questions</div>
                <div><strong>Total Points:</strong><br>100 Points</div>
                <div><strong>Time Limit:</strong><br>45 minutes</div>
                <div><strong>Pass Score:</strong><br>70+ Points</div>
            </div>
        </div>

        <div class="card">
            <h3>🎯 All 6 Assessment Modules</h3>
            <div class="module-grid">
                <div class="module-card">
                    <h4>🎧 1. Listening (16 pts)</h4>
                    <p>4 questions with real audio</p>
                    <p><small>Guest conversations, complaints, requests</small></p>
                </div>
                <div class="module-card">
                    <h4>⏰ 2. Time & Numbers (16 pts)</h4>
                    <p>4 fill-in-the-blank questions</p>
                    <p><small>Times, room numbers, schedules</small></p>
                </div>
                <div class="module-card">
                    <h4>📝 3. Grammar (16 pts)</h4>
                    <p>4 multiple choice questions</p>
                    <p><small>Polite service language, verb forms</small></p>
                </div>
                <div class="module-card">
                    <h4>📚 4. Vocabulary (16 pts)</h4>
                    <p>4 category matching questions</p>
                    <p><small>Hotel terms, service language</small></p>
                </div>
                <div class="module-card">
                    <h4>📖 5. Reading (16 pts)</h4>
                    <p>4 title selection questions</p>
                    <p><small>Work documents, policies, notices</small></p>
                </div>
                <div class="module-card">
                    <h4>🗣️ 6. Speaking (20 pts)</h4>
                    <p>1 scenario response</p>
                    <p><small>Guest service interaction (audio response)</small></p>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>✅ Assessment Features</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                <ul>
                    <li>✅ Real audio playback (2 replays max)</li>
                    <li>✅ Voice recording for speaking</li>
                    <li>✅ Progress tracking</li>
                    <li>✅ Immediate feedback</li>
                </ul>
                <ul>
                    <li>✅ Module-by-module scoring</li>
                    <li>✅ Professional scenarios</li>
                    <li>✅ Timed responses</li>
                    <li>✅ Final certificate</li>
                </ul>
            </div>
        </div>

        <div class="card">
            <h3>🏨 Hotel Operations Scenarios</h3>
            <p>All questions focus on realistic cruise ship hospitality situations:</p>
            <ul>
                <li><strong>Guest Services:</strong> Check-in, room assignments, complaints</li>
                <li><strong>Housekeeping:</strong> Room service, maintenance, amenities</li>
                <li><strong>Food & Beverage:</strong> Restaurant reservations, room service</li>
                <li><strong>Customer Relations:</strong> Problem-solving, assistance</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <a href="/assessment/start" class="btn" style="background: #28a745; font-size: 20px; padding: 20px 40px;">
                🚀 START COMPLETE ASSESSMENT
            </a>
            <br><br>
            <a href="/audio-test" class="btn">🔊 Test Audio First</a>
            <a href="/preview" class="btn" style="background: #17a2b8;">📋 Preview All Modules</a>
        </div>
    </body>
    </html>
    """)

@app.get("/assessment/start", response_class=HTMLResponse)
def start_complete_assessment():
    # Reset progress
    user_progress["current_question"] = 1
    user_progress["answers"] = {}
    user_progress["total_score"] = 0
    user_progress["module_scores"] = {k: 0 for k in user_progress["module_scores"]}

    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Assessment Started - All Modules</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; }
            .progress { background: #e5e7eb; height: 25px; border-radius: 15px; margin: 20px 0; overflow: hidden; }
            .progress-bar { background: linear-gradient(90deg, #10b981, #34d399); height: 100%; width: 0%; transition: width 0.3s; }
            .instructions { background: #f0f9ff; padding: 25px; border-radius: 10px; border-left: 5px solid #3b82f6; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="text-align: center; color: #1e3a8a;">🎯 Complete Assessment Started!</h1>

            <div class="progress">
                <div class="progress-bar" style="width: 0%;"></div>
            </div>
            <p style="text-align: center;"><strong>Progress:</strong> 0 of 21 questions completed (0 points)</p>

            <div class="instructions">
                <h3>📋 Assessment Instructions</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                    <div>
                        <h4>🎧 Listening Module:</h4>
                        <ul>
                            <li>Listen to audio conversations</li>
                            <li>You can replay each audio twice</li>
                            <li>Answer multiple choice questions</li>
                        </ul>
                    </div>
                    <div>
                        <h4>⏰ Time & Numbers:</h4>
                        <ul>
                            <li>Fill in missing times or numbers</li>
                            <li>Type your answer in the text box</li>
                            <li>Follow the format hints provided</li>
                        </ul>
                    </div>
                    <div>
                        <h4>📝 Grammar & 📚 Vocabulary:</h4>
                        <ul>
                            <li>Multiple choice and matching</li>
                            <li>Select the best answer</li>
                            <li>Focus on hospitality language</li>
                        </ul>
                    </div>
                    <div>
                        <h4>📖 Reading & 🗣️ Speaking:</h4>
                        <ul>
                            <li>Read texts and choose titles</li>
                            <li>Record spoken responses</li>
                            <li>Professional service scenarios</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div style="background: #fef3c7; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h4 style="color: #92400e;">⚠️ Important Notes:</h4>
                <ul style="color: #92400e;">
                    <li><strong>Time Limit:</strong> Complete all 21 questions</li>
                    <li><strong>No Going Back:</strong> Answer carefully before submitting</li>
                    <li><strong>Pass Score:</strong> You need 70+ points to pass (70%)</li>
                    <li><strong>Audio:</strong> Make sure your speakers/microphone work</li>
                </ul>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <a href="/question/1" class="btn" style="background: #28a745; font-size: 18px; padding: 20px 40px;">
                    ➡️ Begin Question 1 (Listening Module)
                </a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/question/{q_num}", response_class=HTMLResponse)
def show_question(q_num: int):
    if q_num not in QUESTIONS:
        return HTMLResponse("<h1>Question not found</h1>", status_code=404)

    q = QUESTIONS[q_num]
    progress = ((q_num - 1) / 21) * 100
    module = q["module"]

    # Module-specific styling and icons
    module_info = {
        "listening": {"icon": "🎧", "color": "#3b82f6", "name": "Listening"},
        "time_numbers": {"icon": "⏰", "color": "#8b5cf6", "name": "Time & Numbers"},
        "grammar": {"icon": "📝", "color": "#10b981", "name": "Grammar"},
        "vocabulary": {"icon": "📚", "color": "#f59e0b", "name": "Vocabulary"},
        "reading": {"icon": "📖", "color": "#ef4444", "name": "Reading"},
        "speaking": {"icon": "🗣️", "color": "#ec4899", "name": "Speaking"}
    }

    mod_info = module_info[module]

    # Generate question content based on module type
    question_content = generate_question_content(q, q_num)

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {q_num} - {mod_info["name"]} Module</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; }}
            .btn:disabled {{ background: #9ca3af; cursor: not-allowed; }}
            .progress {{ background: #e5e7eb; height: 20px; border-radius: 10px; margin: 20px 0; }}
            .progress-bar {{ background: linear-gradient(90deg, #10b981, #34d399); height: 100%; border-radius: 10px; width: {progress}%; transition: width 0.5s; }}
            .module-badge {{ background: {mod_info["color"]}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; display: inline-block; }}
            .selected {{ background-color: #dbeafe !important; border-color: #1e3a8a !important; }}
            .question-content {{ background: #f8fafc; padding: 25px; border-radius: 8px; margin: 20px 0; border-left: 5px solid {mod_info["color"]}; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>Question {q_num} of 21</h2>
                <span class="module-badge">{mod_info["icon"]} {mod_info["name"]}</span>
            </div>

            <div class="progress">
                <div class="progress-bar"></div>
            </div>
            <p style="text-align: center; color: #6b7280;">
                Progress: {q_num-1}/21 completed • {user_progress["total_score"]} points earned
            </p>

            <div class="question-content">
                {question_content}
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button class="btn" id="submitBtn" onclick="submitAnswer({q_num})" disabled>
                    Submit Answer
                </button>
            </div>
        </div>

        <script>
            let selectedAnswer = '';
            {generate_question_script(q, q_num)}
        </script>
    </body>
    </html>
    ''')

def generate_question_content(q, q_num):
    """Generate HTML content based on question module type"""
    module = q["module"]

    if module == "listening":
        return f'''
        <div style="background: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 8px;">
            <h4>🎧 Listen to the Audio:</h4>
            <div style="text-align: center; margin: 20px 0;">
                <button onclick="playAudio()" class="btn" style="background: #28a745; margin: 5px;">▶️ Play Audio</button>
                <button onclick="stopAudio()" class="btn" style="background: #dc3545; margin: 5px;">⏹️ Stop</button>
                <div id="replayCount" style="margin-top: 10px; font-weight: bold;">Replays remaining: <span id="replaysLeft">2</span></div>
                <div id="audioStatus" style="margin-top: 10px; font-weight: bold;"></div>
            </div>
        </div>
        <h3>{q["question"]}</h3>
        ''' + generate_multiple_choice_options(q["options"])

    elif module == "time_numbers":
        return f'''
        <h3>{q["question"]}</h3>
        <p style="color: #6b7280; font-style: italic;">Context: {q["context"]}</p>
        <input type="text" id="textAnswer" placeholder="Enter your answer"
               style="width: 300px; padding: 15px; border: 2px solid #d1d5db; border-radius: 8px; font-size: 16px;"
               onchange="selectAnswer(this.value)">
        <p style="color: #6b7280; margin-top: 10px;"><strong>Hint:</strong> {q["hint"]}</p>
        '''

    elif module in ["grammar"]:
        return f'''
        <h3>{q["question"]}</h3>
        ''' + generate_multiple_choice_options(q["options"])

    elif module == "vocabulary":
        return generate_vocabulary_question(q)

    elif module == "reading":
        return f'''
        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h4>📖 Read the following text:</h4>
            <p style="font-size: 16px; line-height: 1.6; background: white; padding: 15px; border-radius: 5px;">
                "{q["text"]}"
            </p>
        </div>
        <h3>{q["question"]}</h3>
        ''' + generate_multiple_choice_options(q["options"])

    elif module == "speaking":
        return f'''
        <div style="background: #fdf2f8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h4>🗣️ Speaking Scenario:</h4>
            <p><strong>Context:</strong> {q["scenario_context"]}</p>
        </div>
        <h3>{q["question"]}</h3>
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <p><strong>Instructions:</strong> Click "Start Recording" and speak your response clearly. Maximum 20 seconds.</p>
            <button onclick="startRecording()" class="btn" style="background: #dc2626; margin: 10px;" id="recordBtn">🎤 Start Recording</button>
            <button onclick="stopRecording()" class="btn" style="background: #7c2d12; margin: 10px;" id="stopBtn" disabled>⏹️ Stop Recording</button>
            <div id="recordingStatus" style="margin-top: 15px; font-weight: bold;"></div>
            <div id="recordingTime" style="margin-top: 10px; color: #dc2626;"></div>
        </div>
        '''

def generate_multiple_choice_options(options):
    """Generate HTML for multiple choice options"""
    html = ""
    for i, option in enumerate(options):
        letter = chr(65 + i)  # A, B, C, D
        html += f'''
        <label style="display: block; padding: 15px; margin: 10px 0; background: #f9fafb; border-radius: 8px; cursor: pointer; border: 2px solid transparent;"
               onclick="selectAnswer('{option}', this)">
            <input type="radio" name="answer" value="{option}" style="margin-right: 15px; transform: scale(1.2);">
            <strong>{letter})</strong> {option}
        </label>
        '''
    return html

def generate_vocabulary_question(q):
    """Generate vocabulary matching question"""
    words_html = ""
    for word in q["words"]:
        words_html += f'''
        <span class="word-tag" onclick="selectWord('{word}')" data-word="{word}"
              style="display: inline-block; background: #e5e7eb; padding: 8px 15px; margin: 5px; border-radius: 20px; cursor: pointer; user-select: none;">
            {word}
        </span>
        '''

    categories_html = ""
    for category in q["categories"]:
        categories_html += f'''
        <div class="category-box" data-category="{category}"
             style="background: #f3f4f6; padding: 15px; margin: 10px; border-radius: 8px; min-height: 60px; border: 2px dashed #d1d5db;">
            <h4 style="margin-top: 0; color: #374151;">{category}</h4>
            <div class="category-words" id="cat-{category.replace(' ', '-').lower()}"></div>
        </div>
        '''

    return f'''
    <h3>{q["question"]}</h3>
    <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h4>📝 Available Words:</h4>
        <div id="wordBank" style="margin: 15px 0;">
            {words_html}
        </div>
    </div>
    <div style="background: #f8fafc; padding: 20px; border-radius: 8px;">
        <h4>📋 Categories (drag words here):</h4>
        {categories_html}
    </div>
    <p style="color: #6b7280; font-style: italic; margin-top: 15px;">
        Click words to select them, then click on a category to place them. You need to match 3 words per category correctly.
    </p>
    '''

def generate_question_script(q, q_num):
    """Generate JavaScript for specific question types"""
    module = q["module"]

    if module == "listening":
        return f'''
        let currentAudio;
        let replaysLeft = 2;

        function playAudio() {{
            if (replaysLeft <= 0) {{
                document.getElementById('audioStatus').innerHTML = '❌ No more replays available';
                return;
            }}

            stopAudio();
            const utterance = new SpeechSynthesisUtterance("{q['audio_text']}");
            utterance.rate = 0.8;
            utterance.onstart = () => document.getElementById('audioStatus').innerHTML = '🔊 Playing audio...';
            utterance.onend = () => {{
                replaysLeft--;
                document.getElementById('replaysLeft').innerText = replaysLeft;
                document.getElementById('audioStatus').innerHTML = '✅ Audio finished';
            }};
            speechSynthesis.speak(utterance);
            currentAudio = utterance;
        }}

        function stopAudio() {{
            speechSynthesis.cancel();
        }}

        function selectAnswer(answer, element) {{
            selectedAnswer = answer;
            document.getElementById('submitBtn').disabled = false;
            document.querySelectorAll('label').forEach(l => l.classList.remove('selected'));
            if (element) element.classList.add('selected');
        }}

        function submitAnswer(qNum) {{
            stopAudio();
            if (!selectedAnswer) {{ alert('Please select an answer'); return; }}
            window.location.href = `/submit/${{qNum}}?answer=${{encodeURIComponent(selectedAnswer)}}`;
        }}
        '''

    elif module in ["time_numbers"]:
        return '''
        function selectAnswer(answer) {
            selectedAnswer = answer;
            document.getElementById('submitBtn').disabled = answer.trim() === '';
        }

        function submitAnswer(qNum) {
            if (!selectedAnswer.trim()) { alert('Please enter an answer'); return; }
            window.location.href = `/submit/${qNum}?answer=${encodeURIComponent(selectedAnswer)}`;
        }
        '''

    elif module in ["grammar", "reading"]:
        return '''
        function selectAnswer(answer, element) {
            selectedAnswer = answer;
            document.getElementById('submitBtn').disabled = false;
            document.querySelectorAll('label').forEach(l => l.classList.remove('selected'));
            if (element) element.classList.add('selected');
        }

        function submitAnswer(qNum) {
            if (!selectedAnswer) { alert('Please select an answer'); return; }
            window.location.href = `/submit/${qNum}?answer=${encodeURIComponent(selectedAnswer)}`;
        }
        '''

    elif module == "vocabulary":
        return '''
        let selectedWords = [];
        let categoryAssignments = {};

        function selectWord(word) {
            const wordTag = document.querySelector(`[data-word="${word}"]`);
            if (selectedWords.includes(word)) {
                selectedWords = selectedWords.filter(w => w !== word);
                wordTag.style.background = '#e5e7eb';
                wordTag.style.color = 'black';
            } else {
                selectedWords.push(word);
                wordTag.style.background = '#3b82f6';
                wordTag.style.color = 'white';
            }

            if (selectedWords.length > 0) {
                document.querySelectorAll('.category-box').forEach(box => {
                    box.style.cursor = 'pointer';
                    box.onclick = () => assignWordsToCategory(box.dataset.category);
                });
            }
        }

        function assignWordsToCategory(category) {
            const categoryDiv = document.getElementById(`cat-${category.replace(' ', '-').toLowerCase()}`);
            selectedWords.forEach(word => {
                const wordSpan = document.createElement('span');
                wordSpan.textContent = word;
                wordSpan.style.cssText = 'background: #10b981; color: white; padding: 5px 10px; margin: 3px; border-radius: 15px; display: inline-block; font-size: 14px;';
                categoryDiv.appendChild(wordSpan);

                // Remove from word bank
                const originalWord = document.querySelector(`[data-word="${word}"]`);
                if (originalWord) originalWord.style.display = 'none';

                // Track assignment
                if (!categoryAssignments[category]) categoryAssignments[category] = [];
                categoryAssignments[category].push(word);
            });

            selectedWords = [];
            document.querySelectorAll('.word-tag').forEach(tag => {
                if (tag.style.display !== 'none') {
                    tag.style.background = '#e5e7eb';
                    tag.style.color = 'black';
                }
            });

            // Check if we have enough assignments
            const totalAssigned = Object.values(categoryAssignments).reduce((sum, arr) => sum + arr.length, 0);
            if (totalAssigned >= 3) {
                selectedAnswer = JSON.stringify(categoryAssignments);
                document.getElementById('submitBtn').disabled = false;
            }
        }

        function submitAnswer(qNum) {
            if (!selectedAnswer) { alert('Please assign at least 3 words to categories'); return; }
            window.location.href = `/submit/${qNum}?answer=${encodeURIComponent(selectedAnswer)}`;
        }
        '''

    elif module == "speaking":
        return '''
        let mediaRecorder;
        let recordedBlobs = [];
        let recordingTimer;
        let recordingSeconds = 0;

        function startRecording() {
            navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                recordedBlobs = [];

                mediaRecorder.ondataavailable = event => {
                    if (event.data.size > 0) recordedBlobs.push(event.data);
                };

                mediaRecorder.onstart = () => {
                    document.getElementById('recordingStatus').innerHTML = '🎤 Recording in progress...';
                    document.getElementById('recordBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;
                    recordingSeconds = 0;
                    recordingTimer = setInterval(() => {
                        recordingSeconds++;
                        document.getElementById('recordingTime').innerHTML = `Time: ${recordingSeconds}s / 20s`;
                        if (recordingSeconds >= 20) stopRecording();
                    }, 1000);
                };

                mediaRecorder.onstop = () => {
                    clearInterval(recordingTimer);
                    document.getElementById('recordingStatus').innerHTML = '✅ Recording complete!';
                    document.getElementById('recordBtn').disabled = false;
                    document.getElementById('stopBtn').disabled = true;

                    // Create audio blob
                    const blob = new Blob(recordedBlobs, { type: 'audio/wav' });
                    selectedAnswer = `Recording completed (${recordingSeconds}s)`;
                    document.getElementById('submitBtn').disabled = false;
                };

                mediaRecorder.start();
            })
            .catch(err => {
                document.getElementById('recordingStatus').innerHTML = '❌ Microphone access denied';
            });
        }

        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }
        }

        function submitAnswer(qNum) {
            if (!selectedAnswer) { alert('Please record your response first'); return; }
            // For demo purposes, we'll just submit the recording status
            window.location.href = `/submit/${qNum}?answer=${encodeURIComponent(selectedAnswer)}`;
        }
        '''

    return ""

@app.get("/submit/{q_num}")
async def submit_answer_get(q_num: int, answer: str):
    """Handle answer submission"""
    if q_num not in QUESTIONS:
        return HTMLResponse("<h1>Invalid question</h1>", status_code=404)

    q = QUESTIONS[q_num]
    is_correct = check_answer_correctness(q, answer)
    points_earned = q["points"] if is_correct else 0

    # Update user progress
    user_progress["answers"][q_num] = {
        "answer": answer,
        "correct": is_correct,
        "points_earned": points_earned
    }
    user_progress["total_score"] += points_earned
    user_progress["module_scores"][q["module"]] += points_earned

    # Show result
    next_q = q_num + 1
    if next_q <= 21:
        next_button = f'<a href="/question/{next_q}"><button class="btn">Next Question</button></a>'
    else:
        next_button = '<a href="/final-results"><button class="btn" style="background: #10b981;">View Final Results</button></a>'

    result_color = "#10b981" if is_correct else "#ef4444"
    result_icon = "✅" if is_correct else "❌"

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Question {q_num} Result</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; }}
            .result {{ background: {result_color}; color: white; padding: 25px; border-radius: 10px; text-align: center; margin: 20px 0; }}
            .feedback {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 5px solid {result_color}; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="result">
                <h2>{result_icon} {"Correct!" if is_correct else "Incorrect"}</h2>
                <p><strong>Points earned:</strong> {points_earned}/{q["points"]}</p>
                <p><strong>Progress:</strong> Question {q_num} of 21 • Total score: {user_progress["total_score"]} points</p>
            </div>

            <div class="feedback">
                <h3>Your Answer:</h3>
                <p style="font-size: 16px;"><strong>"{answer}"</strong></p>

                <h3>Correct Answer:</h3>
                <p style="font-size: 16px; color: {result_color};"><strong>"{get_correct_answer(q)}"</strong></p>

                {generate_explanation(q, is_correct)}
            </div>

            <div style="text-align: center;">
                {next_button}
            </div>
        </div>
    </body>
    </html>
    ''')

def check_answer_correctness(q, answer):
    """Check if answer is correct based on question type"""
    module = q["module"]

    if module in ["listening", "grammar", "reading"]:
        return answer.strip().lower() == q["correct"].lower()

    elif module == "time_numbers":
        # Flexible matching for time/numbers
        answer_clean = answer.strip().replace(":", "").replace(" ", "").lower()
        correct_clean = q["correct"].strip().replace(":", "").replace(" ", "").lower()
        return answer_clean == correct_clean or answer.strip() in q["correct"]

    elif module == "vocabulary":
        try:
            user_assignments = json.loads(answer)
            correct_assignments = q["correct"]
            # Check if at least one category is correctly matched
            for category, words in correct_assignments.items():
                if category in user_assignments:
                    user_words = set(user_assignments[category])
                    correct_words = set(words)
                    if user_words == correct_words:
                        return True
            return False
        except:
            return False

    elif module == "speaking":
        # For demo, consider any recording attempt as partial credit
        return "Recording completed" in answer

    return False

def get_correct_answer(q):
    """Get the correct answer string for display"""
    if q["module"] == "vocabulary":
        return str(q["correct"])
    return q.get("correct", "Sample answer provided")

def generate_explanation(q, is_correct):
    """Generate explanation based on question type"""
    if is_correct:
        return '<p style="color: #10b981;">Great job! You understood the scenario correctly.</p>'
    else:
        explanation = q.get("explanation", "Review the material and try similar questions.")
        return f'<p style="color: #6b7280;"><strong>Explanation:</strong> {explanation}</p>'

@app.get("/final-results", response_class=HTMLResponse)
def final_results():
    percentage = (user_progress["total_score"] / 100) * 100
    passed = percentage >= 70
    grade = "PASS" if passed else "FAIL"

    # Generate detailed results
    module_results = ""
    for module, score in user_progress["module_scores"].items():
        max_points = 20 if module == "speaking" else 16
        module_percentage = (score / max_points) * 100
        status_color = "#10b981" if module_percentage >= 70 else "#ef4444"

        module_results += f'''
        <div style="background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 5px solid {status_color};">
            <strong>{module.replace("_", " ").title()}:</strong> {score}/{max_points} points ({module_percentage:.0f}%)
        </div>
        '''

    return HTMLResponse(f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complete Assessment Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 20px 0; }}
            .btn {{ background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; margin: 10px; }}
            .score {{ background: {"#10b981" if passed else "#ef4444"}; color: white; padding: 40px; border-radius: 15px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="text-align: center; color: #1e3a8a;">🎉 Complete Assessment Finished!</h1>

            <div class="score">
                <h2>Final Score: {user_progress["total_score"]}/100 ({percentage:.0f}%)</h2>
                <h3>Result: {grade}</h3>
                <p>{"🎉 Congratulations! You passed all 6 modules of the Hotel Operations assessment!" if passed else "📚 You need 70+ points to pass. Review the modules and try again."}</p>
            </div>
        </div>

        <div class="card">
            <h3>📊 Module-by-Module Performance:</h3>
            {module_results}
        </div>

        <div class="card">
            <h3>🎓 Assessment Summary:</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <div>
                    <h4>✅ Modules Completed:</h4>
                    <ul>
                        <li>🎧 Listening (4 questions)</li>
                        <li>⏰ Time & Numbers (4 questions)</li>
                        <li>📝 Grammar (4 questions)</li>
                        <li>📚 Vocabulary (4 questions)</li>
                        <li>📖 Reading (4 questions)</li>
                        <li>🗣️ Speaking (1 question)</li>
                    </ul>
                </div>
                <div>
                    <h4>📈 Performance Stats:</h4>
                    <ul>
                        <li><strong>Total Questions:</strong> 21</li>
                        <li><strong>Points Earned:</strong> {user_progress["total_score"]}/100</li>
                        <li><strong>Pass Threshold:</strong> 70%</li>
                        <li><strong>Your Score:</strong> {percentage:.0f}%</li>
                        <li><strong>Result:</strong> {grade}</li>
                    </ul>
                </div>
            </div>
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <a href="/" class="btn">🔄 Take Assessment Again</a>
            <a href="/certificate" class="btn" style="background: #10b981;">📜 {"Generate Certificate" if passed else "View Performance Report"}</a>
        </div>

        <div style="background: #d1fae5; padding: 20px; border-radius: 10px; text-align: center;">
            <p style="margin: 0; color: #065f46; font-weight: bold;">
                🚢 Thank you for completing the Cruise Employee English Assessment!
                {"You're ready for Hotel Operations duties!" if passed else "Keep studying and try again!"}
            </p>
        </div>
    </body>
    </html>
    ''')

@app.get("/audio-test", response_class=HTMLResponse)
def audio_test():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audio & Microphone Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 20px 0; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 10px; }
            .audio-player { background: #f0f9ff; padding: 20px; border-radius: 8px; text-align: center; border: 2px solid #3b82f6; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🔊 Audio & Microphone Test</h1>

            <div class="audio-player">
                <h3>🎧 Speaker Test:</h3>
                <button onclick="testSpeakers()" class="btn" style="background: #10b981;">▶️ Test Speakers</button>
                <div id="speakerStatus" style="margin: 15px 0;"></div>
            </div>

            <div class="audio-player">
                <h3>🎤 Microphone Test:</h3>
                <button onclick="testMicrophone()" class="btn" style="background: #dc2626;">🎤 Test Microphone</button>
                <div id="micStatus" style="margin: 15px 0;"></div>
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <a href="/"><button class="btn">✅ Tests Complete - Start Assessment</button></a>
            </div>
        </div>

        <script>
            function testSpeakers() {
                const utterance = new SpeechSynthesisUtterance("This is a test of your speakers for the English assessment. Can you hear this clearly?");
                utterance.rate = 0.9;
                utterance.onstart = () => document.getElementById('speakerStatus').innerHTML = '🔊 Playing test audio...';
                utterance.onend = () => document.getElementById('speakerStatus').innerHTML = '✅ Speaker test complete';
                speechSynthesis.speak(utterance);
            }

            function testMicrophone() {
                navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    document.getElementById('micStatus').innerHTML = '✅ Microphone access granted - Ready for speaking module!';
                    setTimeout(() => stream.getTracks().forEach(track => track.stop()), 1000);
                })
                .catch(err => {
                    document.getElementById('micStatus').innerHTML = '❌ Microphone access denied - Speaking module may not work';
                });
            }
        </script>
    </body>
    </html>
    """)

@app.get("/preview", response_class=HTMLResponse)
def preview_all_modules():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>All Modules Preview</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
            .module { background: white; padding: 25px; margin: 20px 0; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .module-header { background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .sample { background: #f8fafc; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 5px solid #3b82f6; }
            .btn { background: #1e3a8a; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; }
        </style>
    </head>
    <body>
        <h1 style="text-align: center;">📋 Complete Assessment Preview - All 6 Modules</h1>

        <div class="module">
            <div class="module-header">
                <h3>🎧 Module 1: Listening (16 points)</h3>
                <p>4 questions with real audio conversations</p>
            </div>
            <div class="sample">
                <strong>Sample:</strong> "Hello, I'd like to book a table for four people at seven PM tonight, please."<br>
                <strong>Question:</strong> What time is the reservation? (Multiple choice)
            </div>
        </div>

        <div class="module">
            <div class="module-header">
                <h3>⏰ Module 2: Time & Numbers (16 points)</h3>
                <p>4 fill-in-the-blank questions</p>
            </div>
            <div class="sample">
                <strong>Sample:</strong> "Breakfast is served from ___ to 10:30 AM."<br>
                <strong>Answer:</strong> 7:00 (Type in text box)
            </div>
        </div>

        <div class="module">
            <div class="module-header">
                <h3>📝 Module 3: Grammar (16 points)</h3>
                <p>4 multiple choice questions focusing on polite service language</p>
            </div>
            <div class="sample">
                <strong>Sample:</strong> "___ I help you with your luggage?"<br>
                <strong>Options:</strong> May | Do | Will | Am (Answer: May)
            </div>
        </div>

        <div class="module">
            <div class="module-header">
                <h3>📚 Module 4: Vocabulary (16 points)</h3>
                <p>4 category matching questions with hospitality terms</p>
            </div>
            <div class="sample">
                <strong>Sample:</strong> Match housekeeping terms to categories<br>
                <strong>Words:</strong> amenities, turndown, linen → Room Items category
            </div>
        </div>

        <div class="module">
            <div class="module-header">
                <h3>📖 Module 5: Reading (16 points)</h3>
                <p>4 text comprehension questions - choose best title</p>
            </div>
            <div class="sample">
                <strong>Sample Text:</strong> "Our recent survey shows 94% guest satisfaction with housekeeping..."<br>
                <strong>Best Title:</strong> Housekeeping Performance Review
            </div>
        </div>

        <div class="module">
            <div class="module-header">
                <h3>🗣️ Module 6: Speaking (20 points)</h3>
                <p>1 scenario-based response with voice recording</p>
            </div>
            <div class="sample">
                <strong>Scenario:</strong> Guest says "The air conditioning in my room is too cold."<br>
                <strong>Your Response:</strong> Record appropriate service response (20 seconds max)
            </div>
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <a href="/" class="btn">🏠 Back to Home</a>
            <a href="/assessment/start" class="btn" style="background: #10b981;">🚀 Start Complete Assessment</a>
        </div>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("Starting Complete English Assessment - All 6 Modules...")
    print("Complete Assessment: http://127.0.0.1:8004")
    print("Audio Test: http://127.0.0.1:8004/audio-test")
    print("Module Preview: http://127.0.0.1:8004/preview")
    uvicorn.run(app, host="127.0.0.1", port=8004)