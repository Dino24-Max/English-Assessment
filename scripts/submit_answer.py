"""
Programmatic answer submission utility for testing assessment flow.
Submits answers for questions 11-21 to a running server (default http://127.0.0.1:8000).
"""
import json
import requests

session = requests.Session()

questions = {
    11: json.dumps({"Bridge": "Ship's control center", "Gangway": "Ship's walkway to shore", "Tender": "Small boat for shore trips", "Muster": "Emergency assembly"}),
    12: json.dumps({"Port": "Left side of ship", "Starboard": "Right side of ship", "Bow": "Front of ship", "Stern": "Back of ship"}),
    13: json.dumps({"Galley": "Ship's kitchen", "Cabin": "Passenger room", "Deck": "Floor level", "Hull": "Ship's body"}),
    14: json.dumps({"Captain": "Ship commander", "Purser": "Finance officer", "Steward": "Cabin attendant", "Chef": "Head cook"}),
    15: "The Perfect Cruise Experience",  # Reading - title selection
    16: "Excellent Service Standards",  # Reading
    17: "Safety First at Sea",  # Reading
    18: "recorded_10s|Hello, welcome to the cruise ship.",  # Speaking
    19: "recorded_15s|I would be happy to help you find your cabin.",  # Speaking
    20: "recorded_20s|The dining room is located on deck 5. You can take the elevator or stairs.",  # Speaking
    21: "recorded_25s|In case of emergency, please proceed to your muster station as indicated on your cabin card.",  # Speaking (final)
}

for q_num, answer in questions.items():
    data = {
        'question_num': q_num,
        'answer': answer,
        'operation': 'HOTEL'
    }
    r = session.post('http://127.0.0.1:8000/submit', data=data, allow_redirects=False)
    print(f'Q{q_num}: Status={r.status_code}, Location={r.headers.get("Location", "none")}')
