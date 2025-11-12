"""
Question Bank Loader
Loads comprehensive question banks for all divisions and modules
Supports both legacy format and new 1600-question full bank
"""

import json
from typing import Dict, List, Any
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from models.assessment import Question, ModuleType, DivisionType, QuestionType


class QuestionBankLoader:
    """Loads question banks into database"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_full_question_bank(self, json_file_path: str = None):
        """
        Load complete 1600-question bank from JSON file
        
        Args:
            json_file_path: Path to question_bank_full.json (optional)
        """
        if not json_file_path:
            # Default path
            data_dir = Path(__file__).parent.parent.parent.parent / "data"
            json_file_path = data_dir / "question_bank_full.json"
        
        print(f"Loading full question bank from: {json_file_path}")
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            bank_data = json.load(f)
        
        questions_data = bank_data.get("questions", [])
        print(f"Found {len(questions_data)} questions to load")
        
        # Batch insert for performance
        questions_to_add = []
        
        for i, q_data in enumerate(questions_data, 1):
            # Map module to ModuleType enum
            module_map = {
                "listening": ModuleType.LISTENING,
                "grammar": ModuleType.GRAMMAR,
                "vocabulary": ModuleType.VOCABULARY,
                "reading": ModuleType.READING,
                "time_numbers": ModuleType.TIME_NUMBERS,
                "speaking": ModuleType.SPEAKING
            }
            
            # Map division to DivisionType enum
            division_map = {
                "hotel": DivisionType.HOTEL,
                "marine": DivisionType.MARINE,
                "casino": DivisionType.CASINO
            }
            
            # Map question_type string to QuestionType enum
            type_map = {
                "multiple_choice": QuestionType.MULTIPLE_CHOICE,
                "fill_blank": QuestionType.FILL_BLANK,
                "category_match": QuestionType.CATEGORY_MATCH,
                "title_selection": QuestionType.TITLE_SELECTION,
                "speaking_response": QuestionType.SPEAKING_RESPONSE
            }
            
            question = Question(
                module_type=module_map.get(q_data.get("module_type", q_data.get("module")), ModuleType.LISTENING),
                division=division_map.get(q_data.get("division"), DivisionType.HOTEL),
                question_type=type_map.get(q_data.get("question_type"), QuestionType.MULTIPLE_CHOICE),
                question_text=q_data.get("question_text", ""),
                options=q_data.get("options"),
                correct_answer=q_data.get("correct_answer", ""),
                audio_file_path=q_data.get("audio_file_path"),
                difficulty_level=q_data.get("difficulty_level", 2),
                is_safety_related=q_data.get("is_safety_related", False),
                points=q_data.get("points", 4),
                department=q_data.get("department"),
                scenario_id=q_data.get("scenario_id"),
                scenario_description=q_data.get("scenario_description"),
                question_metadata=q_data.get("question_metadata")
            )
            
            questions_to_add.append(question)
            
            # Batch commit every 100 questions for progress
            if i % 100 == 0:
                self.db.add_all(questions_to_add)
                await self.db.commit()
                print(f"  ✅ Loaded {i}/{len(questions_data)} questions")
                questions_to_add = []
        
        # Commit remaining questions
        if questions_to_add:
            self.db.add_all(questions_to_add)
            await self.db.commit()
        
        print(f"✅ Successfully loaded {len(questions_data)} questions into database!")
        
        return len(questions_data)

    async def load_all_questions(self):
        """Load all question banks for all divisions (legacy method)"""

        # Hotel Operations Questions
        await self._load_hotel_questions()

        # Marine Operations Questions
        await self._load_marine_questions()

        # Casino Operations Questions
        await self._load_casino_questions()

        await self.db.commit()

    async def _load_hotel_questions(self):
        """Load Hotel Operations questions"""

        # LISTENING MODULE - Hotel Operations
        hotel_listening = [
            {
                "question_text": "Guest says: 'I'd like to book a table for four at 7 PM.' What time is the reservation?",
                "options": ["6 PM", "7 PM", "8 PM", "4 PM"],
                "correct_answer": "7 PM",
                "audio_context": "I'd like to book a table for four at seven PM tonight."
            },
            {
                "question_text": "Guest complaint: 'The air conditioning is too cold in room 8254.' What is the room number?",
                "options": ["8245", "8254", "8524", "2548"],
                "correct_answer": "8254",
                "audio_context": "The air conditioning is way too cold in room eight-two-five-four."
            },
            {
                "question_text": "Guest request: 'Can you send fresh towels to the spa by 10:30?' When are towels needed?",
                "options": ["10:00", "10:15", "10:30", "11:30"],
                "correct_answer": "10:30",
                "audio_context": "Can you please send fresh towels to the spa by ten-thirty?"
            },
            {
                "question_text": "Lost and found inquiry: 'I left my sunglasses at the pool yesterday.' Where were the sunglasses left?",
                "options": ["Beach", "Pool", "Spa", "Deck"],
                "correct_answer": "Pool",
                "audio_context": "I think I left my sunglasses at the pool area yesterday afternoon."
            }
        ]

        # TIME & NUMBERS MODULE - Hotel Operations
        hotel_time_numbers = [
            {
                "question_text": "Breakfast is served from ___ to 10:30 AM.",
                "correct_answer": "7:00",
                "context": "7:00 AM"
            },
            {
                "question_text": "Your cabin number is ___.",
                "correct_answer": "8254",
                "context": "Cabin 8254"
            },
            {
                "question_text": "The spa closes at ___ PM.",
                "correct_answer": "9",
                "context": "9 PM"
            },
            {
                "question_text": "Party of ___ at 6:30 PM.",
                "correct_answer": "8",
                "context": "Party of eight"
            }
        ]

        # GRAMMAR MODULE - Hotel Operations
        hotel_grammar = [
            {
                "question_text": "___ I help you with your luggage?",
                "options": ["May", "Do", "Will", "Am"],
                "correct_answer": "May"
            },
            {
                "question_text": "Your room ___ been cleaned and is ready.",
                "options": ["have", "has", "had", "having"],
                "correct_answer": "has"
            },
            {
                "question_text": "If you need anything, please ___ hesitate to call.",
                "options": ["not", "don't", "doesn't", "won't"],
                "correct_answer": "don't"
            },
            {
                "question_text": "___ you like to make a restaurant reservation?",
                "options": ["Would", "Will", "Are", "Do"],
                "correct_answer": "Would"
            }
        ]

        # VOCABULARY MODULE - Hotel Operations
        hotel_vocabulary = [
            {
                "question_text": "Match housekeeping terms:",
                "categories": {
                    "Room Items": ["amenities", "turndown", "linen"],
                    "Service Types": ["housekeeping", "maintenance", "laundry"],
                    "Guest Needs": ["toiletries", "towels", "pillows"]
                },
                "correct_answer": "Room Items: amenities, turndown, linen"
            },
            {
                "question_text": "Match dining terms:",
                "categories": {
                    "Menu Items": ["appetizer", "entree", "dessert"],
                    "Service Areas": ["buffet", "restaurant", "room service"],
                    "Beverages": ["wine", "cocktail", "coffee"]
                },
                "correct_answer": "Menu Items: appetizer, entree, dessert"
            }
        ]

        # READING MODULE - Hotel Operations
        hotel_reading = [
            {
                "question_text": """GUEST SATISFACTION SURVEY RESULTS
                Our recent survey shows 94% guest satisfaction with housekeeping services.
                Room cleanliness scored highest, while bathroom amenity restocking needs improvement.
                Staff friendliness received excellent ratings across all departments.""",
                "options": [
                    "Housekeeping Performance Review",
                    "Guest Complaint Summary",
                    "Staff Training Manual",
                    "Hotel Revenue Report"
                ],
                "correct_answer": "Housekeeping Performance Review"
            },
            {
                "question_text": """SPECIAL DIETARY REQUIREMENTS NOTICE
                Guest in Suite 7234 has severe nut allergy. All meals must be prepared in nut-free environment.
                Kitchen staff should use separate utensils and prep areas.
                Please coordinate with chef for all room service orders.""",
                "options": [
                    "Kitchen Safety Protocol",
                    "Allergy Management Notice",
                    "Room Service Menu",
                    "Staff Scheduling Update"
                ],
                "correct_answer": "Allergy Management Notice"
            }
        ]

        # SPEAKING MODULE - Hotel Operations
        hotel_speaking = [
            {
                "question_text": "Guest says: 'The air conditioning in my room is too cold.' Respond appropriately.",
                "expected_response": "I apologize for the inconvenience. I'll send someone to adjust the temperature right away. Is there anything else I can help you with?",
                "scenario_context": "Front desk interaction with guest complaint"
            },
            {
                "question_text": "Guest asks: 'What time does the main restaurant close?' Provide the information.",
                "expected_response": "The main restaurant closes at 10 PM. However, room service is available 24 hours if you need anything later.",
                "scenario_context": "Guest services information request"
            }
        ]

        # Load Hotel questions
        await self._create_questions_for_division(
            DivisionType.HOTEL,
            {
                ModuleType.LISTENING: hotel_listening,
                ModuleType.TIME_NUMBERS: hotel_time_numbers,
                ModuleType.GRAMMAR: hotel_grammar,
                ModuleType.VOCABULARY: hotel_vocabulary,
                ModuleType.READING: hotel_reading,
                ModuleType.SPEAKING: hotel_speaking
            }
        )

    async def _load_marine_questions(self):
        """Load Marine Operations questions"""

        # LISTENING MODULE - Marine Operations
        marine_listening = [
            {
                "question_text": "Bridge communication: 'Current heading is 270 degrees.' What is the heading?",
                "options": ["270 degrees", "207 degrees", "720 degrees", "072 degrees"],
                "correct_answer": "270 degrees",
                "audio_context": "Current heading is two-seven-zero degrees."
            },
            {
                "question_text": "Safety announcement: 'All crew report to muster station 4.' Which station?",
                "options": ["Station 2", "Station 3", "Station 4", "Station 5"],
                "correct_answer": "Station 4",
                "audio_context": "All crew members report to muster station four immediately."
            },
            {
                "question_text": "Weather update: 'Wind speed 25 knots from the northeast.' What is the wind speed?",
                "options": ["15 knots", "25 knots", "35 knots", "52 knots"],
                "correct_answer": "25 knots",
                "audio_context": "Current wind speed is twenty-five knots from the northeast."
            },
            {
                "question_text": "Port communication: 'ETA to next port is 0600 hours.' What time is arrival?",
                "options": ["0600", "0060", "6000", "0006"],
                "correct_answer": "0600",
                "audio_context": "Estimated time of arrival to next port is zero-six-hundred hours."
            }
        ]

        # TIME & NUMBERS MODULE - Marine Operations
        marine_time_numbers = [
            {
                "question_text": "Watch starts at ___ hours.",
                "correct_answer": "0400",
                "context": "0400 hours"
            },
            {
                "question_text": "Current speed: ___ knots.",
                "correct_answer": "18",
                "context": "18 knots"
            },
            {
                "question_text": "Heading ___ degrees.",
                "correct_answer": "270",
                "context": "270 degrees"
            },
            {
                "question_text": "___ nautical miles to port.",
                "correct_answer": "240",
                "context": "240 nautical miles"
            }
        ]

        # GRAMMAR MODULE - Marine Operations
        marine_grammar = [
            {
                "question_text": "All crew members ___ report to muster stations immediately.",
                "options": ["must", "can", "might", "could"],
                "correct_answer": "must"
            },
            {
                "question_text": "The engine ___ inspected every 500 hours.",
                "options": ["is", "are", "was", "were"],
                "correct_answer": "is"
            },
            {
                "question_text": "We ___ approaching the port now.",
                "options": ["is", "am", "are", "been"],
                "correct_answer": "are"
            },
            {
                "question_text": "___ all safety equipment before departure.",
                "options": ["Check", "Checking", "Checked", "Checks"],
                "correct_answer": "Check"
            }
        ]

        # VOCABULARY MODULE - Marine Operations
        marine_vocabulary = [
            {
                "question_text": "Match navigation terms:",
                "categories": {
                    "Directions": ["port", "starboard", "bow"],
                    "Equipment": ["compass", "radar", "GPS"],
                    "Measurements": ["knots", "degrees", "nautical miles"]
                },
                "correct_answer": "Directions: port, starboard, bow"
            },
            {
                "question_text": "Match safety equipment:",
                "categories": {
                    "Life Safety": ["lifeboat", "life vest", "EPIRB"],
                    "Fire Safety": ["extinguisher", "fire alarm", "sprinkler"],
                    "Communication": ["radio", "whistle", "flare"]
                },
                "correct_answer": "Life Safety: lifeboat, life vest, EPIRB"
            }
        ]

        # READING MODULE - Marine Operations
        marine_reading = [
            {
                "question_text": """SAFETY BULLETIN - WEATHER WARNING
                Severe weather approaching from southwest. All crew secure loose equipment on deck.
                Passenger activities on outer decks suspended until further notice.
                Engine room maintain full power for maneuvering.""",
                "options": [
                    "Weather Safety Protocol",
                    "Equipment Maintenance Notice",
                    "Passenger Activity Schedule",
                    "Engine Room Procedures"
                ],
                "correct_answer": "Weather Safety Protocol"
            },
            {
                "question_text": """MAINTENANCE LOG ENTRY
                Engine inspection completed at 14:00 hours. Oil levels normal,
                temperature readings within acceptable range.
                Next scheduled maintenance in 72 hours. All systems operational.""",
                "options": [
                    "Daily Operations Report",
                    "Engine Maintenance Record",
                    "Safety Inspection Results",
                    "Crew Schedule Update"
                ],
                "correct_answer": "Engine Maintenance Record"
            }
        ]

        # SPEAKING MODULE - Marine Operations
        marine_speaking = [
            {
                "question_text": "Report: 'Oil leak spotted in engine room.' Make appropriate announcement.",
                "expected_response": "Bridge, this is Engine Room. We have discovered an oil leak in the main engine compartment. Investigating the source and will report back within 10 minutes.",
                "scenario_context": "Emergency reporting to bridge"
            },
            {
                "question_text": "Captain asks for status update. Provide current situation report.",
                "expected_response": "Captain, current position stable, all systems operational. Engine running normally, weather conditions fair. No issues to report at this time.",
                "scenario_context": "Bridge communication with captain"
            }
        ]

        # Load Marine questions
        await self._create_questions_for_division(
            DivisionType.MARINE,
            {
                ModuleType.LISTENING: marine_listening,
                ModuleType.TIME_NUMBERS: marine_time_numbers,
                ModuleType.GRAMMAR: marine_grammar,
                ModuleType.VOCABULARY: marine_vocabulary,
                ModuleType.READING: marine_reading,
                ModuleType.SPEAKING: marine_speaking
            }
        )

    async def _load_casino_questions(self):
        """Load Casino Operations questions"""

        # LISTENING MODULE - Casino Operations
        casino_listening = [
            {
                "question_text": "Player asks: 'What's the minimum bet at this table?' Dealer responds: 'The minimum bet is $25.' What is the minimum?",
                "options": ["$15", "$20", "$25", "$35"],
                "correct_answer": "$25",
                "audio_context": "The minimum bet at this table is twenty-five dollars."
            },
            {
                "question_text": "Tournament announcement: 'Registration closes at 2 PM.' When does registration close?",
                "options": ["12 PM", "2 PM", "3 PM", "4 PM"],
                "correct_answer": "2 PM",
                "audio_context": "Tournament registration closes at two PM today."
            },
            {
                "question_text": "Cashier interaction: 'Current jackpot is $15,000.' What is the jackpot amount?",
                "options": ["$5,000", "$15,000", "$50,000", "$150,000"],
                "correct_answer": "$15,000",
                "audio_context": "The current progressive jackpot is fifteen thousand dollars."
            },
            {
                "question_text": "Player inquiry: 'What are the table limits?' Response: '$10 to $500.' What is the maximum bet?",
                "options": ["$50", "$100", "$500", "$5000"],
                "correct_answer": "$500",
                "audio_context": "Table limits are ten dollars minimum to five hundred dollars maximum."
            }
        ]

        # TIME & NUMBERS MODULE - Casino Operations
        casino_time_numbers = [
            {
                "question_text": "Minimum bet is $___.",
                "correct_answer": "25",
                "context": "$25"
            },
            {
                "question_text": "Tournament starts at ___ PM.",
                "correct_answer": "2",
                "context": "2 PM"
            },
            {
                "question_text": "Jackpot amount: $___,000.",
                "correct_answer": "15",
                "context": "$15,000"
            },
            {
                "question_text": "Table limits: $10-$___.",
                "correct_answer": "500",
                "context": "$500"
            }
        ]

        # GRAMMAR MODULE - Casino Operations
        casino_grammar = [
            {
                "question_text": "___ you like to double down on this hand?",
                "options": ["Would", "Will", "Are", "Can"],
                "correct_answer": "Would"
            },
            {
                "question_text": "Blackjack ___ 3 to 2.",
                "options": ["pay", "pays", "paying", "paid"],
                "correct_answer": "pays"
            },
            {
                "question_text": "If you get 21, you ___ automatically.",
                "options": ["win", "wins", "won", "winning"],
                "correct_answer": "win"
            },
            {
                "question_text": "The dealer ___ hit on soft 17.",
                "options": ["must", "can", "might", "should"],
                "correct_answer": "must"
            }
        ]

        # VOCABULARY MODULE - Casino Operations
        casino_vocabulary = [
            {
                "question_text": "Match card game terms:",
                "categories": {
                    "Games": ["blackjack", "poker", "baccarat"],
                    "Actions": ["hit", "stand", "fold"],
                    "Equipment": ["chips", "cards", "shoe"]
                },
                "correct_answer": "Games: blackjack, poker, baccarat"
            },
            {
                "question_text": "Match casino staff roles:",
                "categories": {
                    "Table Staff": ["dealer", "pit boss", "supervisor"],
                    "Money Handling": ["cashier", "banker", "attendant"],
                    "Customer Service": ["host", "server", "security"]
                },
                "correct_answer": "Table Staff: dealer, pit boss, supervisor"
            }
        ]

        # READING MODULE - Casino Operations
        casino_reading = [
            {
                "question_text": """TOURNAMENT RULES UPDATE
                Saturday poker tournament buy-in is $100 with $50 rebuy option.
                Registration starts at 1 PM, tournament begins at 2 PM sharp.
                Late entries accepted until level 3. Prizes for top 20% of field.""",
                "options": [
                    "Poker Tournament Information",
                    "Casino Revenue Report",
                    "Staff Schedule Update",
                    "Gaming Regulation Notice"
                ],
                "correct_answer": "Poker Tournament Information"
            },
            {
                "question_text": """RESPONSIBLE GAMING NOTICE
                All staff must monitor for signs of problem gambling.
                Look for excessive time at tables, large bet increases, or emotional distress.
                Report concerns to shift supervisor immediately. Customer assistance resources available 24/7.""",
                "options": [
                    "Staff Training Manual",
                    "Problem Gambling Protocol",
                    "Customer Service Guidelines",
                    "Casino Security Procedures"
                ],
                "correct_answer": "Problem Gambling Protocol"
            }
        ]

        # SPEAKING MODULE - Casino Operations
        casino_speaking = [
            {
                "question_text": "Player asks: 'How do I play roulette?' Explain the basic rules.",
                "expected_response": "In roulette, you place bets on numbers or colors, then I spin the wheel. If the ball lands on your selection, you win. Red and black pay even money, single numbers pay 35 to 1.",
                "scenario_context": "Customer instruction at roulette table"
            },
            {
                "question_text": "Handle situation: 'Guest thinks dealer made an error.' Respond professionally.",
                "expected_response": "I understand your concern. Let me review what happened and call my supervisor over to clarify the situation. We want to ensure everything is handled correctly.",
                "scenario_context": "Dispute resolution at gaming table"
            }
        ]

        # Load Casino questions
        await self._create_questions_for_division(
            DivisionType.CASINO,
            {
                ModuleType.LISTENING: casino_listening,
                ModuleType.TIME_NUMBERS: casino_time_numbers,
                ModuleType.GRAMMAR: casino_grammar,
                ModuleType.VOCABULARY: casino_vocabulary,
                ModuleType.READING: casino_reading,
                ModuleType.SPEAKING: casino_speaking
            }
        )

    async def _create_questions_for_division(self, division: DivisionType,
                                           modules: Dict[ModuleType, List[Dict[str, Any]]]):
        """Create questions for a specific division"""

        for module_type, questions in modules.items():
            for q_data in questions:
                # Determine question type and points based on module
                if module_type == ModuleType.LISTENING:
                    question_type = QuestionType.MULTIPLE_CHOICE
                    points = 4
                elif module_type == ModuleType.TIME_NUMBERS:
                    question_type = QuestionType.FILL_BLANK
                    points = 4
                elif module_type == ModuleType.GRAMMAR:
                    question_type = QuestionType.MULTIPLE_CHOICE
                    points = 4
                elif module_type == ModuleType.VOCABULARY:
                    question_type = QuestionType.CATEGORY_MATCH
                    points = 4
                elif module_type == ModuleType.READING:
                    question_type = QuestionType.TITLE_SELECTION
                    points = 4
                elif module_type == ModuleType.SPEAKING:
                    question_type = QuestionType.SPEAKING_RESPONSE
                    points = 20
                else:
                    question_type = QuestionType.MULTIPLE_CHOICE
                    points = 4

                # Create question record
                question = Question(
                    module_type=module_type,
                    division=division,
                    question_type=question_type,
                    question_text=q_data["question_text"],
                    options=q_data.get("options"),
                    correct_answer=q_data["correct_answer"],
                    points=points,
                    is_safety_related=self._is_safety_question(q_data["question_text"]),
                    metadata=q_data.get("metadata", {})
                )

                self.db.add(question)

    def _is_safety_question(self, question_text: str) -> bool:
        """Determine if a question is safety-related"""
        safety_keywords = [
            "safety", "emergency", "muster", "lifeboat", "fire", "evacuation",
            "alarm", "drill", "rescue", "danger", "hazard", "accident",
            "injury", "medical", "first aid", "security"
        ]

        text_lower = question_text.lower()
        return any(keyword in text_lower for keyword in safety_keywords)