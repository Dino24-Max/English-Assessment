#!/usr/bin/env python3
"""
Simple test server for English Assessment Platform
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="English Assessment Platform")

@app.get("/")
def read_root():
    return HTMLResponse("""
    <html>
    <head><title>English Assessment Platform</title></head>
    <body style="font-family: Arial; padding: 20px; max-width: 800px; margin: 0 auto;">
        <h1>🚢 Cruise Employee English Assessment Platform</h1>
        <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h2>✅ Application Status: RUNNING</h2>
        </div>

        <div style="background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>📋 Test Links</h3>
            <ul>
                <li><a href="/health" target="_blank">🔍 Health Check API</a></li>
                <li><a href="/test-data" target="_blank">📊 Sample Test Data</a></li>
                <li><a href="/assessment-info" target="_blank">📝 Assessment Information</a></li>
            </ul>
        </div>

        <div style="background: #fff5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>🏨 Divisions Available</h3>
            <ul>
                <li><strong>Hotel Operations:</strong> 8 departments (Guest Services, Housekeeping, etc.)</li>
                <li><strong>Marine Operations:</strong> 3 departments (Deck, Engine, Security)</li>
                <li><strong>Casino Operations:</strong> 3 departments (Gaming, Cashier, VIP)</li>
            </ul>
        </div>

        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>📊 Assessment Modules (100 points total)</h3>
            <ul>
                <li>🎧 Listening (16 points) - AI dialogues</li>
                <li>⏰ Time & Numbers (16 points) - Fill blanks</li>
                <li>📝 Grammar (16 points) - Multiple choice</li>
                <li>📚 Vocabulary (16 points) - Category matching</li>
                <li>📖 Reading (16 points) - Title selection</li>
                <li>🗣️ Speaking (20 points) - AI analysis</li>
            </ul>
        </div>

        <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3>✅ Implementation Status</h3>
            <ul>
                <li>✅ FastAPI backend with 25+ files</li>
                <li>✅ 630+ division-specific questions</li>
                <li>✅ AI speech analysis integration</li>
                <li>✅ Complete scoring system</li>
                <li>✅ GitHub backup enabled</li>
            </ul>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "English Assessment Platform",
        "version": "1.0.0",
        "features": {
            "divisions": ["hotel", "marine", "casino"],
            "modules": ["listening", "time_numbers", "grammar", "vocabulary", "reading", "speaking"],
            "total_questions": "630+",
            "ai_integration": "enabled"
        }
    }

@app.get("/test-data")
def get_test_data():
    return {
        "sample_candidate": {
            "first_name": "John",
            "last_name": "Smith",
            "email": "john.smith@example.com",
            "nationality": "Philippines",
            "division": "hotel",
            "department": "guest_services"
        },
        "sample_assessment": {
            "division": "hotel",
            "total_questions": 21,
            "time_limit": "120 minutes",
            "pass_criteria": {
                "total_score": 70,
                "safety_questions": "80%",
                "speaking_minimum": 12
            }
        },
        "sample_questions": {
            "listening": "Guest says: 'I'd like a table for 4 at 7 PM'",
            "grammar": "___ I help you with your luggage? (May/Do/Will/Am)",
            "vocabulary": "Match: amenities, turndown, linen (Room Items category)"
        }
    }

@app.get("/assessment-info")
def assessment_info():
    return HTMLResponse("""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2>📝 English Assessment Information</h2>
        <h3>🎯 Test Structure:</h3>
        <ul>
            <li><strong>Duration:</strong> 120 minutes maximum</li>
            <li><strong>Total Questions:</strong> 21 (20 multiple modules + 1 speaking)</li>
            <li><strong>Scoring:</strong> 100 points total</li>
            <li><strong>Pass Threshold:</strong> 70+ points</li>
        </ul>

        <h3>📊 Module Breakdown:</h3>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #f0f0f0;">
                <th>Module</th><th>Questions</th><th>Points</th><th>Type</th>
            </tr>
            <tr><td>Listening</td><td>4</td><td>16</td><td>Multiple Choice</td></tr>
            <tr><td>Time & Numbers</td><td>4</td><td>16</td><td>Fill Blanks</td></tr>
            <tr><td>Grammar</td><td>4</td><td>16</td><td>Multiple Choice</td></tr>
            <tr><td>Vocabulary</td><td>4</td><td>16</td><td>Category Match</td></tr>
            <tr><td>Reading</td><td>4</td><td>16</td><td>Title Selection</td></tr>
            <tr><td>Speaking</td><td>1</td><td>20</td><td>AI Analysis</td></tr>
        </table>

        <h3>🏢 Division Examples:</h3>
        <p><strong>Hotel:</strong> "Guest says: 'The AC is too cold in room 8254.'"</p>
        <p><strong>Marine:</strong> "Bridge communication: 'Heading 270 degrees.'"</p>
        <p><strong>Casino:</strong> "Player asks: 'What's the minimum bet?'"</p>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("Starting English Assessment Platform...")
    print("Dashboard: http://127.0.0.1:8000")
    print("Health: http://127.0.0.1:8000/health")
    uvicorn.run(app, host="127.0.0.1", port=8000)