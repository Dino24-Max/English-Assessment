"""
Generate Sample Question Bank for Cruise Employee English Assessment Platform

This script generates 288 high-quality questions across 16 departments:
- 18 questions per department
- Distributed across 6 modules (Listening, Time & Numbers, Grammar, Vocabulary, Reading, Speaking)
- Based on 10 realistic scenarios per department
- Output: question_bank_sample.json

Author: Claude Code
Date: 2025-09-30
"""

import json
import random
from typing import Dict, List, Any
from datetime import datetime


class QuestionBankGenerator:
    """Generate comprehensive question bank for all departments"""

    def __init__(self):
        self.questions = []
        self.question_counter = 1

        # Department structure (16 correct departments)
        self.departments = {
            "HOTEL": [
                ("AUX SERV", "AUX"),
                ("BEVERAGE GUEST SERV", "BGS"),
                ("CULINARY ARTS", "CUL"),
                ("GUEST SERVICES", "GSV"),
                ("HOUSEKEEPING", "HSK"),
                ("LAUNDRY", "LND"),
                ("PHOTO", "PHT"),
                ("PROVISIONS", "PRV"),
                ("REST. SERVICE", "RST"),
                ("SHORE EXCURS", "SHR")
            ],
            "MARINE": [
                ("Deck", "DCK"),
                ("Engine", "ENG"),
                ("Security Services", "SEC")
            ],
            "CASINO": [
                ("Table Games", "TBL"),
                ("Slot Machines", "SLT"),
                ("Casino Services", "CSN")
            ]
        }

        # Module distribution (18 questions per department)
        self.module_distribution = {
            "Listening": 4,
            "TimeNumbers": 2,
            "Grammar": 4,
            "Vocabulary": 4,
            "Reading": 2,
            "Speaking": 2
        }

    def generate_all_questions(self) -> List[Dict[str, Any]]:
        """Generate all 288 questions across all departments"""

        for operation, depts in self.departments.items():
            for dept_name, dept_code in depts:
                self._generate_department_questions(operation, dept_name, dept_code)

        return self.questions

    def _generate_department_questions(self, operation: str, dept_name: str, dept_code: str):
        """Generate 18 questions for a specific department"""

        # Generate questions for each module
        for module, count in self.module_distribution.items():
            for i in range(count):
                scenario_id = random.randint(1, 10)

                if module == "Listening":
                    question = self._generate_listening_question(
                        operation, dept_name, dept_code, scenario_id, i + 1
                    )
                elif module == "TimeNumbers":
                    question = self._generate_time_numbers_question(
                        operation, dept_name, dept_code, scenario_id, i + 1
                    )
                elif module == "Grammar":
                    question = self._generate_grammar_question(
                        operation, dept_name, dept_code, scenario_id, i + 1
                    )
                elif module == "Vocabulary":
                    question = self._generate_vocabulary_question(
                        operation, dept_name, dept_code, scenario_id, i + 1
                    )
                elif module == "Reading":
                    question = self._generate_reading_question(
                        operation, dept_name, dept_code, scenario_id, i + 1
                    )
                elif module == "Speaking":
                    question = self._generate_speaking_question(
                        operation, dept_name, dept_code, scenario_id, i + 1
                    )

                self.questions.append(question)

    def _generate_listening_question(self, operation: str, dept_name: str,
                                    dept_code: str, scenario_id: int, q_num: int) -> Dict[str, Any]:
        """Generate realistic listening question"""

        question_id = f"{operation}_{dept_code}_L_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        # Department-specific listening scenarios
        listening_scenarios = self._get_listening_scenarios(dept_name)
        scenario = random.choice(listening_scenarios)

        difficulty = random.choice(["easy", "medium", "hard"])
        points = {"easy": 3, "medium": 4, "hard": 5}[difficulty]

        return {
            "question_id": question_id,
            "department": dept_name,
            "operation": operation,
            "scenario_id": scenario_id,
            "module": "Listening",
            "difficulty": difficulty,
            "points": points,
            "question_type": "multiple_choice",
            "question_text": scenario["question"],
            "audio_text": scenario["audio"],
            "options": scenario["options"],
            "correct_answer": scenario["correct"],
            "explanation": scenario["explanation"]
        }

    def _generate_time_numbers_question(self, operation: str, dept_name: str,
                                       dept_code: str, scenario_id: int, q_num: int) -> Dict[str, Any]:
        """Generate time and numbers question"""

        question_id = f"{operation}_{dept_code}_TN_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        time_number_scenarios = self._get_time_numbers_scenarios(dept_name)
        scenario = random.choice(time_number_scenarios)

        return {
            "question_id": question_id,
            "department": dept_name,
            "operation": operation,
            "scenario_id": scenario_id,
            "module": "TimeNumbers",
            "difficulty": "medium",
            "points": 4,
            "question_type": "fill_blank",
            "question_text": scenario["question"],
            "context": scenario["context"],
            "correct_answer": scenario["answer"],
            "explanation": scenario["explanation"]
        }

    def _generate_grammar_question(self, operation: str, dept_name: str,
                                  dept_code: str, scenario_id: int, q_num: int) -> Dict[str, Any]:
        """Generate grammar question"""

        question_id = f"{operation}_{dept_code}_G_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        grammar_scenarios = self._get_grammar_scenarios(dept_name)
        scenario = random.choice(grammar_scenarios)

        difficulty = random.choice(["easy", "medium", "hard"])
        points = {"easy": 3, "medium": 4, "hard": 5}[difficulty]

        return {
            "question_id": question_id,
            "department": dept_name,
            "operation": operation,
            "scenario_id": scenario_id,
            "module": "Grammar",
            "difficulty": difficulty,
            "points": points,
            "question_type": "multiple_choice",
            "question_text": scenario["question"],
            "options": scenario["options"],
            "correct_answer": scenario["correct"],
            "explanation": scenario["explanation"]
        }

    def _generate_vocabulary_question(self, operation: str, dept_name: str,
                                     dept_code: str, scenario_id: int, q_num: int) -> Dict[str, Any]:
        """Generate vocabulary matching question"""

        question_id = f"{operation}_{dept_code}_V_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        vocab_scenarios = self._get_vocabulary_scenarios(dept_name)
        scenario = random.choice(vocab_scenarios)

        return {
            "question_id": question_id,
            "department": dept_name,
            "operation": operation,
            "scenario_id": scenario_id,
            "module": "Vocabulary",
            "difficulty": "medium",
            "points": 4,
            "question_type": "matching",
            "question_text": scenario["question"],
            "terms": scenario["terms"],
            "definitions": scenario["definitions"],
            "correct_matches": scenario["matches"],
            "explanation": scenario["explanation"]
        }

    def _generate_reading_question(self, operation: str, dept_name: str,
                                  dept_code: str, scenario_id: int, q_num: int) -> Dict[str, Any]:
        """Generate reading comprehension question"""

        question_id = f"{operation}_{dept_code}_R_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        reading_scenarios = self._get_reading_scenarios(dept_name)
        scenario = random.choice(reading_scenarios)

        difficulty = random.choice(["medium", "hard"])
        points = {"medium": 4, "hard": 5}[difficulty]

        return {
            "question_id": question_id,
            "department": dept_name,
            "operation": operation,
            "scenario_id": scenario_id,
            "module": "Reading",
            "difficulty": difficulty,
            "points": points,
            "question_type": "title_selection",
            "question_text": scenario["passage"],
            "options": scenario["options"],
            "correct_answer": scenario["correct"],
            "explanation": scenario["explanation"]
        }

    def _generate_speaking_question(self, operation: str, dept_name: str,
                                   dept_code: str, scenario_id: int, q_num: int) -> Dict[str, Any]:
        """Generate speaking question"""

        question_id = f"{operation}_{dept_code}_S_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        speaking_scenarios = self._get_speaking_scenarios(dept_name)
        scenario = random.choice(speaking_scenarios)

        return {
            "question_id": question_id,
            "department": dept_name,
            "operation": operation,
            "scenario_id": scenario_id,
            "module": "Speaking",
            "difficulty": "hard",
            "points": 10,
            "question_type": "speaking_response",
            "question_text": scenario["prompt"],
            "scenario_context": scenario["context"],
            "expected_keywords": scenario["keywords"],
            "rubric": scenario["rubric"],
            "explanation": scenario["explanation"]
        }

    # Scenario generators for each module type

    def _get_listening_scenarios(self, dept_name: str) -> List[Dict[str, Any]]:
        """Get listening scenarios based on department"""

        scenarios = {
            "Front Desk": [
                {
                    "question": "A guest says: 'I'd like to book a table for six at seven-thirty this evening.' What time is the reservation?",
                    "audio": "Hello, I'd like to book a table for six people at seven-thirty this evening, please.",
                    "options": ["6:00 PM", "6:30 PM", "7:00 PM", "7:30 PM"],
                    "correct": "7:30 PM",
                    "explanation": "The guest clearly states 'seven-thirty this evening' which is 7:30 PM."
                },
                {
                    "question": "Guest complaint: 'The air conditioning in room 9342 is not working.' What is the room number?",
                    "audio": "Excuse me, the air conditioning in room nine-three-four-two is not working at all.",
                    "options": ["9234", "9324", "9342", "9432"],
                    "correct": "9342",
                    "explanation": "The room number is clearly stated as nine-three-four-two (9342)."
                },
                {
                    "question": "Shore excursion inquiry: 'We'll be back at the ship by 4:15 PM.' What is the return time?",
                    "audio": "The tour will take about 6 hours, and we'll be back at the ship by four-fifteen PM.",
                    "options": ["3:45 PM", "4:00 PM", "4:15 PM", "4:45 PM"],
                    "correct": "4:15 PM",
                    "explanation": "The return time is stated as four-fifteen PM (4:15 PM)."
                }
            ],
            "Housekeeping": [
                {
                    "question": "Guest request: 'Could you bring 3 extra towels to cabin 7856?' How many towels?",
                    "audio": "Hi, could you please bring three extra bath towels to cabin seven-eight-five-six?",
                    "options": ["2 towels", "3 towels", "4 towels", "5 towels"],
                    "correct": "3 towels",
                    "explanation": "The guest requests 'three extra bath towels'."
                },
                {
                    "question": "Maintenance report: 'The bathroom light in 8523 needs replacing.' What needs repair?",
                    "audio": "I need to report that the bathroom light in room eight-five-two-three needs replacing.",
                    "options": ["TV", "AC", "Light", "Toilet"],
                    "correct": "Light",
                    "explanation": "The issue is specifically about the 'bathroom light' needing replacement."
                },
                {
                    "question": "Service timing: 'Please clean our room after 2 PM.' When should cleaning occur?",
                    "audio": "We're going to be in the room until two PM, so please clean our cabin after that time.",
                    "options": ["Before 2 PM", "After 2 PM", "At 2 PM exactly", "Before noon"],
                    "correct": "After 2 PM",
                    "explanation": "The guest requests cleaning 'after two PM'."
                }
            ],
            "Food & Beverage": [
                {
                    "question": "Dietary restriction: 'I'm allergic to shellfish.' What is the allergy?",
                    "audio": "I need to let you know that I'm severely allergic to shellfish, including shrimp and lobster.",
                    "options": ["Nuts", "Dairy", "Shellfish", "Gluten"],
                    "correct": "Shellfish",
                    "explanation": "The guest clearly states being allergic to 'shellfish'."
                },
                {
                    "question": "Table reservation: 'Party of 8 at 6:45 PM.' How many guests?",
                    "audio": "I'd like to make a reservation for a party of eight at six-forty-five this evening.",
                    "options": ["6 guests", "7 guests", "8 guests", "9 guests"],
                    "correct": "8 guests",
                    "explanation": "The reservation is for 'a party of eight' (8 guests)."
                },
                {
                    "question": "Special request: 'Can we get a high chair for our 18-month-old?' What age is the child?",
                    "audio": "We have an eighteen-month-old baby with us. Can we get a high chair please?",
                    "options": ["8 months", "12 months", "18 months", "24 months"],
                    "correct": "18 months",
                    "explanation": "The child is described as 'eighteen-month-old'."
                }
            ],
            "Bar Service": [
                {
                    "question": "Drink order: 'Two mojitos and one margarita, please.' How many total drinks?",
                    "audio": "I'd like to order two mojitos and one margarita, please.",
                    "options": ["2 drinks", "3 drinks", "4 drinks", "5 drinks"],
                    "correct": "3 drinks",
                    "explanation": "Two mojitos plus one margarita equals 3 drinks total."
                },
                {
                    "question": "Happy hour timing: 'Happy hour is from 5 to 7 PM.' When does it end?",
                    "audio": "Just to let you know, our happy hour runs from five PM to seven PM daily.",
                    "options": ["6 PM", "6:30 PM", "7 PM", "8 PM"],
                    "correct": "7 PM",
                    "explanation": "Happy hour ends at 'seven PM'."
                },
                {
                    "question": "Beverage package: 'The premium package is $65 per day.' What is the cost?",
                    "audio": "The premium beverage package costs sixty-five dollars per person per day.",
                    "options": ["$55", "$60", "$65", "$70"],
                    "correct": "$65",
                    "explanation": "The premium package costs 'sixty-five dollars' ($65)."
                }
            ],
            "Guest Services": [
                {
                    "question": "Shore excursion: 'The bus leaves at 9:15 AM from deck 4.' What deck?",
                    "audio": "Your shore excursion bus departs at nine-fifteen AM from deck four.",
                    "options": ["Deck 2", "Deck 3", "Deck 4", "Deck 5"],
                    "correct": "Deck 4",
                    "explanation": "The departure location is 'deck four'."
                },
                {
                    "question": "Spa appointment: 'Your massage is scheduled for 3:30 PM.' What time?",
                    "audio": "I've booked your massage for three-thirty PM this afternoon in the spa.",
                    "options": ["2:30 PM", "3:00 PM", "3:30 PM", "4:00 PM"],
                    "correct": "3:30 PM",
                    "explanation": "The massage time is 'three-thirty PM' (3:30 PM)."
                },
                {
                    "question": "WiFi package: 'The unlimited package is $25 per day.' What's the price?",
                    "audio": "Our unlimited WiFi package costs twenty-five dollars per day per device.",
                    "options": ["$20", "$25", "$30", "$35"],
                    "correct": "$25",
                    "explanation": "The unlimited WiFi package costs 'twenty-five dollars' ($25)."
                }
            ],
            "Cabin Service": [
                {
                    "question": "Room service: 'Please deliver to cabin 6789 by 8:30 AM.' What time?",
                    "audio": "I'd like breakfast room service delivered to cabin six-seven-eight-nine by eight-thirty AM.",
                    "options": ["8:00 AM", "8:15 AM", "8:30 AM", "9:00 AM"],
                    "correct": "8:30 AM",
                    "explanation": "Delivery time requested is 'eight-thirty AM' (8:30 AM)."
                },
                {
                    "question": "Maintenance request: 'The TV remote in 5432 isn't working.' What's the issue?",
                    "audio": "The TV remote control in cabin five-four-three-two isn't working properly.",
                    "options": ["TV screen broken", "Remote not working", "No channels", "Sound issue"],
                    "correct": "Remote not working",
                    "explanation": "The problem is the 'TV remote control isn't working'."
                },
                {
                    "question": "Special arrangement: 'Anniversary setup for cabin 8765 at 6 PM.' What time?",
                    "audio": "We need the anniversary setup completed for cabin eight-seven-six-five by six PM.",
                    "options": ["5 PM", "5:30 PM", "6 PM", "6:30 PM"],
                    "correct": "6 PM",
                    "explanation": "The setup must be ready 'by six PM' (6 PM)."
                }
            ],
            "Auxiliary Service": [
                {
                    "question": "Supply request: 'We need 50 additional chairs for the event.' How many chairs?",
                    "audio": "Can you arrange for fifty additional chairs to be brought to the main deck for the event?",
                    "options": ["40 chairs", "45 chairs", "50 chairs", "55 chairs"],
                    "correct": "50 chairs",
                    "explanation": "The request is for 'fifty additional chairs'."
                },
                {
                    "question": "Staff allocation: '3 extra servers needed for captain's dinner.' How many servers?",
                    "audio": "We'll need three extra servers for the captain's dinner tonight at seven PM.",
                    "options": ["2 servers", "3 servers", "4 servers", "5 servers"],
                    "correct": "3 servers",
                    "explanation": "The requirement is 'three extra servers'."
                },
                {
                    "question": "Emergency supply: 'Priority delivery by 11:45 AM.' What's the deadline?",
                    "audio": "This is a priority request - we need delivery by eleven-forty-five AM today.",
                    "options": ["11:15 AM", "11:30 AM", "11:45 AM", "12:00 PM"],
                    "correct": "11:45 AM",
                    "explanation": "The deadline is 'eleven-forty-five AM' (11:45 AM)."
                }
            ],
            "Laundry": [
                {
                    "question": "Express service: 'I need these back by 2 PM today.' What's the deadline?",
                    "audio": "This is urgent - I need these items cleaned and back by two PM today.",
                    "options": ["1 PM", "1:30 PM", "2 PM", "2:30 PM"],
                    "correct": "2 PM",
                    "explanation": "The items must be returned 'by two PM' (2 PM)."
                },
                {
                    "question": "Item count: 'I have 7 shirts and 3 pairs of pants.' Total items?",
                    "audio": "I'm sending down seven shirts and three pairs of pants for cleaning.",
                    "options": ["9 items", "10 items", "11 items", "12 items"],
                    "correct": "10 items",
                    "explanation": "Seven shirts plus three pants equals 10 items total."
                },
                {
                    "question": "Dry cleaning: 'The evening gown for cabin 4567.' What is the cabin number?",
                    "audio": "Please send the dry-cleaned evening gown to cabin four-five-six-seven.",
                    "options": ["4576", "4657", "4567", "4765"],
                    "correct": "4567",
                    "explanation": "The cabin number is 'four-five-six-seven' (4567)."
                }
            ],
            "Photo": [
                {
                    "question": "Photo package: 'The deluxe package is $120 for 15 photos.' What's the price?",
                    "audio": "Our deluxe photo package includes fifteen photos for one hundred twenty dollars.",
                    "options": ["$100", "$110", "$120", "$130"],
                    "correct": "$120",
                    "explanation": "The deluxe package costs 'one hundred twenty dollars' ($120)."
                },
                {
                    "question": "Photography session: 'Family portrait at 10:30 AM on deck 12.' What time?",
                    "audio": "Your family portrait session is scheduled for ten-thirty AM on deck twelve.",
                    "options": ["10:00 AM", "10:15 AM", "10:30 AM", "11:00 AM"],
                    "correct": "10:30 AM",
                    "explanation": "The session time is 'ten-thirty AM' (10:30 AM)."
                },
                {
                    "question": "Print order: '12 copies in 8x10 size.' How many copies?",
                    "audio": "I'd like to order twelve copies of this photo in eight-by-ten size.",
                    "options": ["10 copies", "11 copies", "12 copies", "15 copies"],
                    "correct": "12 copies",
                    "explanation": "The order is for 'twelve copies'."
                }
            ],
            "Provisions": [
                {
                    "question": "Food inventory: 'We need 200 pounds of fresh produce.' How much?",
                    "audio": "For tomorrow's resupply, we need two hundred pounds of fresh produce.",
                    "options": ["150 lbs", "200 lbs", "250 lbs", "300 lbs"],
                    "correct": "200 lbs",
                    "explanation": "The order is for 'two hundred pounds'."
                },
                {
                    "question": "Beverage order: '48 cases of bottled water.' How many cases?",
                    "audio": "Please add forty-eight cases of bottled water to the next supply order.",
                    "options": ["38 cases", "43 cases", "48 cases", "58 cases"],
                    "correct": "48 cases",
                    "explanation": "The order is for 'forty-eight cases'."
                },
                {
                    "question": "Delivery time: 'Supply truck arrives at 7:30 AM.' What time?",
                    "audio": "The supply truck is scheduled to arrive at the port at seven-thirty AM.",
                    "options": ["7:00 AM", "7:15 AM", "7:30 AM", "8:00 AM"],
                    "correct": "7:30 AM",
                    "explanation": "Arrival time is 'seven-thirty AM' (7:30 AM)."
                }
            ],
            "Deck Department": [
                {
                    "question": "Navigation: 'Current heading is 285 degrees.' What's the heading?",
                    "audio": "Bridge to deck, our current heading is two-eight-five degrees.",
                    "options": ["258°", "285°", "528°", "582°"],
                    "correct": "285°",
                    "explanation": "The heading is 'two-eight-five degrees' (285°)."
                },
                {
                    "question": "Safety drill: 'All crew to muster station 6.' Which station?",
                    "audio": "Attention all crew members, report to muster station six for safety drill.",
                    "options": ["Station 4", "Station 5", "Station 6", "Station 7"],
                    "correct": "Station 6",
                    "explanation": "Crew must report to 'muster station six'."
                },
                {
                    "question": "Port arrival: 'ETA to port is 0615 hours.' What time?",
                    "audio": "Estimated time of arrival to port is zero-six-fifteen hours.",
                    "options": ["0545", "0600", "0615", "0630"],
                    "correct": "0615",
                    "explanation": "ETA is 'zero-six-fifteen hours' (0615)."
                }
            ],
            "Engine Department": [
                {
                    "question": "Engine status: 'Main engine RPM is 450.' What's the RPM?",
                    "audio": "Engine control room reporting main engine at four hundred fifty RPM.",
                    "options": ["400", "425", "450", "475"],
                    "correct": "450",
                    "explanation": "RPM is 'four hundred fifty' (450)."
                },
                {
                    "question": "Fuel level: 'Fuel tank at 75% capacity.' What percentage?",
                    "audio": "Current fuel status shows tank at seventy-five percent capacity.",
                    "options": ["65%", "70%", "75%", "80%"],
                    "correct": "75%",
                    "explanation": "Fuel level is 'seventy-five percent' (75%)."
                },
                {
                    "question": "Maintenance schedule: 'Next service in 120 operating hours.' How many hours?",
                    "audio": "Next scheduled maintenance is due in one hundred twenty operating hours.",
                    "options": ["100 hours", "110 hours", "120 hours", "130 hours"],
                    "correct": "120 hours",
                    "explanation": "Service is due in 'one hundred twenty operating hours'."
                }
            ],
            "Security Department": [
                {
                    "question": "Security alert: 'Suspicious person on deck 9.' Which deck?",
                    "audio": "Security alert - suspicious person reported on deck nine near the pool area.",
                    "options": ["Deck 7", "Deck 8", "Deck 9", "Deck 10"],
                    "correct": "Deck 9",
                    "explanation": "The alert is for 'deck nine'."
                },
                {
                    "question": "Patrol schedule: 'Complete rounds every 45 minutes.' How often?",
                    "audio": "Security team should complete patrol rounds every forty-five minutes.",
                    "options": ["30 minutes", "35 minutes", "45 minutes", "60 minutes"],
                    "correct": "45 minutes",
                    "explanation": "Rounds are 'every forty-five minutes'."
                },
                {
                    "question": "Lost item: 'Wallet found in theater row 12.' Which row?",
                    "audio": "Guest wallet has been found in the theater, row twelve, seat eight.",
                    "options": ["Row 10", "Row 11", "Row 12", "Row 13"],
                    "correct": "Row 12",
                    "explanation": "The wallet was in 'row twelve'."
                }
            ],
            "Table Games": [
                {
                    "question": "Table limits: 'Minimum bet is $25, maximum $500.' What's the minimum?",
                    "audio": "Table limits are twenty-five dollars minimum, five hundred maximum.",
                    "options": ["$20", "$25", "$30", "$50"],
                    "correct": "$25",
                    "explanation": "Minimum bet is 'twenty-five dollars' ($25)."
                },
                {
                    "question": "Tournament: 'Registration closes at 1:45 PM.' What time?",
                    "audio": "Poker tournament registration closes at one-forty-five PM today.",
                    "options": ["1:15 PM", "1:30 PM", "1:45 PM", "2:00 PM"],
                    "correct": "1:45 PM",
                    "explanation": "Registration closes at 'one-forty-five PM' (1:45 PM)."
                },
                {
                    "question": "Chip exchange: 'Three hundred dollars in chips, please.' How much?",
                    "audio": "I'd like to exchange three hundred dollars for chips, please.",
                    "options": ["$200", "$250", "$300", "$350"],
                    "correct": "$300",
                    "explanation": "The amount is 'three hundred dollars' ($300)."
                }
            ],
            "Slot Machines": [
                {
                    "question": "Jackpot amount: 'Progressive jackpot at $28,500.' What's the amount?",
                    "audio": "Current progressive jackpot stands at twenty-eight thousand five hundred dollars.",
                    "options": ["$25,800", "$28,500", "$28,800", "$30,500"],
                    "correct": "$28,500",
                    "explanation": "Jackpot is 'twenty-eight thousand five hundred dollars' ($28,500)."
                },
                {
                    "question": "Machine number: 'Malfunction on machine 147.' Which machine?",
                    "audio": "Technical team, we have a malfunction on slot machine one-four-seven.",
                    "options": ["Machine 117", "Machine 147", "Machine 174", "Machine 417"],
                    "correct": "Machine 147",
                    "explanation": "The machine is 'one-four-seven' (147)."
                },
                {
                    "question": "Winner payout: 'Verify payout of $3,250.' What's the amount?",
                    "audio": "Need supervisor to verify winner payout of three thousand two hundred fifty dollars.",
                    "options": ["$2,350", "$3,150", "$3,250", "$3,550"],
                    "correct": "$3,250",
                    "explanation": "Payout is 'three thousand two hundred fifty dollars' ($3,250)."
                }
            ],
            "Casino Services": [
                {
                    "question": "Membership tier: 'You've reached Gold status with 5,000 points.' How many points?",
                    "audio": "Congratulations! You've reached Gold membership status with five thousand points.",
                    "options": ["4,000", "4,500", "5,000", "5,500"],
                    "correct": "5,000",
                    "explanation": "Points accumulated are 'five thousand' (5,000)."
                },
                {
                    "question": "Tournament buy-in: '$150 entry with one rebuy allowed.' What's the entry fee?",
                    "audio": "Tournament buy-in is one hundred fifty dollars with one rebuy allowed.",
                    "options": ["$100", "$125", "$150", "$175"],
                    "correct": "$150",
                    "explanation": "Entry fee is 'one hundred fifty dollars' ($150)."
                },
                {
                    "question": "Comp dollars: 'You have $85 in comp credits.' How much?",
                    "audio": "Your account shows eighty-five dollars in complimentary credits available.",
                    "options": ["$75", "$80", "$85", "$90"],
                    "correct": "$85",
                    "explanation": "Comp credits are 'eighty-five dollars' ($85)."
                }
            ]
        }

        return scenarios.get(dept_name, scenarios["Front Desk"])

    def _get_time_numbers_scenarios(self, dept_name: str) -> List[Dict[str, Any]]:
        """Get time and numbers scenarios"""

        scenarios = {
            "Front Desk": [
                {"question": "Check-in begins at ___ AM.", "context": "7:00 AM", "answer": "7:00", "explanation": "Standard cruise check-in time."},
                {"question": "Your cabin number is ___.", "context": "Suite 8254", "answer": "8254", "explanation": "Four-digit cabin number."},
                {"question": "Ship departs at ___ PM sharp.", "context": "5:30 PM", "answer": "5:30", "explanation": "Departure time must be exact."}
            ],
            "Housekeeping": [
                {"question": "Daily cabin cleaning between ___ AM and 3 PM.", "context": "9:00 AM - 3:00 PM", "answer": "9:00", "explanation": "Standard housekeeping hours."},
                {"question": "Turndown service starts at ___ PM.", "context": "6:00 PM", "answer": "6:00", "explanation": "Evening service timing."}
            ],
            "Food & Beverage": [
                {"question": "Breakfast served until ___ AM.", "context": "10:30 AM", "answer": "10:30", "explanation": "Breakfast service end time."},
                {"question": "Dinner reservations for party of ___.", "context": "8 people", "answer": "8", "explanation": "Group size for reservation."}
            ],
            "Bar Service": [
                {"question": "Happy hour: 5 PM to ___ PM.", "context": "7:00 PM", "answer": "7:00", "explanation": "Two-hour happy hour period."},
                {"question": "Premium cocktails are $___ each.", "context": "$15", "answer": "15", "explanation": "Beverage pricing."}
            ],
            "Guest Services": [
                {"question": "Shore excursion departs at ___ AM.", "context": "9:15 AM", "answer": "9:15", "explanation": "Excursion departure time."},
                {"question": "WiFi package: $___ per day.", "context": "$25", "answer": "25", "explanation": "Internet package pricing."}
            ],
            "Cabin Service": [
                {"question": "Room service available ___ hours.", "context": "24 hours", "answer": "24", "explanation": "Round-the-clock availability."},
                {"question": "Breakfast delivery by ___ AM.", "context": "8:00 AM", "answer": "8:00", "explanation": "Morning service timing."}
            ],
            "Auxiliary Service": [
                {"question": "Supply delivery by ___ AM.", "context": "10:00 AM", "answer": "10:00", "explanation": "Morning supply schedule."},
                {"question": "Event setup requires ___ hours notice.", "context": "4 hours", "answer": "4", "explanation": "Advance notice requirement."}
            ],
            "Laundry": [
                {"question": "Express service within ___ hours.", "context": "4 hours", "answer": "4", "explanation": "Rush service timeframe."},
                {"question": "Standard turnaround: ___ hours.", "context": "24 hours", "answer": "24", "explanation": "Normal processing time."}
            ],
            "Photo": [
                {"question": "Photo prints ready in ___ hours.", "context": "2 hours", "answer": "2", "explanation": "Photo processing time."},
                {"question": "Deluxe package: $___ for 20 photos.", "context": "$150", "answer": "150", "explanation": "Package pricing."}
            ],
            "Provisions": [
                {"question": "Order ___ cases of water.", "context": "50 cases", "answer": "50", "explanation": "Bulk supply quantity."},
                {"question": "Supply arrives at ___ AM.", "context": "7:00 AM", "answer": "7:00", "explanation": "Early morning delivery."}
            ],
            "Deck Department": [
                {"question": "Current heading: ___ degrees.", "context": "270 degrees", "answer": "270", "explanation": "Compass heading direction."},
                {"question": "Distance to port: ___ nautical miles.", "context": "185 nm", "answer": "185", "explanation": "Maritime distance measurement."}
            ],
            "Engine Department": [
                {"question": "Engine running at ___ RPM.", "context": "450 RPM", "answer": "450", "explanation": "Engine rotation speed."},
                {"question": "Oil change every ___ hours.", "context": "500 hours", "answer": "500", "explanation": "Maintenance interval."}
            ],
            "Security Department": [
                {"question": "Patrol rounds every ___ minutes.", "context": "45 minutes", "answer": "45", "explanation": "Security patrol frequency."},
                {"question": "Curfew for minors: ___ PM.", "context": "11:00 PM", "answer": "11:00", "explanation": "Youth curfew policy."}
            ],
            "Table Games": [
                {"question": "Minimum bet: $___.", "context": "$25", "answer": "25", "explanation": "Table minimum wager."},
                {"question": "Blackjack pays ___ to 2.", "context": "3 to 2", "answer": "3", "explanation": "Standard blackjack payout."}
            ],
            "Slot Machines": [
                {"question": "Jackpot: $___,000.", "context": "$35,000", "answer": "35", "explanation": "Progressive jackpot amount."},
                {"question": "Machine ___ needs service.", "context": "Machine 247", "answer": "247", "explanation": "Equipment identification."}
            ],
            "Casino Services": [
                {"question": "Tournament buy-in: $___.", "context": "$100", "answer": "100", "explanation": "Entry fee amount."},
                {"question": "Gold tier at ___,000 points.", "context": "5,000 points", "answer": "5", "explanation": "Membership threshold."}
            ]
        }

        return scenarios.get(dept_name, scenarios["Front Desk"])

    def _get_grammar_scenarios(self, dept_name: str) -> List[Dict[str, Any]]:
        """Get grammar scenarios"""

        # Universal grammar questions applicable to all departments
        grammar_pool = [
            {
                "question": "___ I help you with your luggage?",
                "options": ["May", "Do", "Will", "Am"],
                "correct": "May",
                "explanation": "Use 'May' for polite offers of assistance."
            },
            {
                "question": "The guest ___ arrived at the port this morning.",
                "options": ["have", "has", "had", "having"],
                "correct": "has",
                "explanation": "Use 'has' with singular subject 'guest'."
            },
            {
                "question": "If you need anything, please ___ hesitate to call.",
                "options": ["not", "don't", "doesn't", "won't"],
                "correct": "don't",
                "explanation": "Use 'don't' in imperative negative sentences."
            },
            {
                "question": "___ you like to make a reservation?",
                "options": ["Would", "Will", "Are", "Do"],
                "correct": "Would",
                "explanation": "Use 'Would' for polite offers and requests."
            },
            {
                "question": "The restaurant ___ open from 6 PM to 10 PM.",
                "options": ["is", "are", "was", "been"],
                "correct": "is",
                "explanation": "Use 'is' with singular subject 'restaurant'."
            },
            {
                "question": "We ___ serving dinner in the main dining room.",
                "options": ["is", "am", "are", "been"],
                "correct": "are",
                "explanation": "Use 'are' with plural subject 'we'."
            },
            {
                "question": "Could you please ___ me to the spa?",
                "options": ["direct", "directing", "directed", "direction"],
                "correct": "direct",
                "explanation": "Use base form verb after 'please' in requests."
            },
            {
                "question": "The ship ___ at the port tomorrow morning.",
                "options": ["arrive", "arrives", "arriving", "arrived"],
                "correct": "arrives",
                "explanation": "Use present tense for scheduled future events."
            },
            {
                "question": "All crew members ___ attend the safety briefing.",
                "options": ["must", "can", "might", "could"],
                "correct": "must",
                "explanation": "Use 'must' for strong obligations and requirements."
            },
            {
                "question": "The guests ___ enjoying the entertainment show.",
                "options": ["is", "am", "are", "be"],
                "correct": "are",
                "explanation": "Use 'are' with plural subject 'guests'."
            },
            {
                "question": "I ___ be happy to assist you with that.",
                "options": ["will", "shall", "would", "should"],
                "correct": "would",
                "explanation": "Use 'would' to express willingness politely."
            },
            {
                "question": "The captain ___ announced our arrival time.",
                "options": ["have", "has", "had", "having"],
                "correct": "has",
                "explanation": "Use 'has' with singular subject in present perfect."
            }
        ]

        return grammar_pool

    def _get_vocabulary_scenarios(self, dept_name: str) -> List[Dict[str, Any]]:
        """Get vocabulary matching scenarios"""

        vocab_sets = {
            "Front Desk": [
                {
                    "question": "Match cruise ship terms:",
                    "terms": ["Embarkation", "Disembarkation", "Port of call", "Home port"],
                    "definitions": ["Original departure port", "Boarding the ship", "Destination stop", "Leaving the ship"],
                    "matches": {"Embarkation": "Boarding the ship", "Disembarkation": "Leaving the ship",
                               "Port of call": "Destination stop", "Home port": "Original departure port"},
                    "explanation": "Essential cruise terminology for front desk operations."
                },
                {
                    "question": "Match guest services terms:",
                    "terms": ["Concierge", "Shore excursion", "Stateroom", "Tender"],
                    "definitions": ["Cabin on ship", "Small transport boat", "Land tour", "Guest services specialist"],
                    "matches": {"Concierge": "Guest services specialist", "Shore excursion": "Land tour",
                               "Stateroom": "Cabin on ship", "Tender": "Small transport boat"},
                    "explanation": "Common terms used in guest service interactions."
                }
            ],
            "Housekeeping": [
                {
                    "question": "Match housekeeping items:",
                    "terms": ["Amenities", "Turndown service", "Linen", "Toiletries"],
                    "definitions": ["Bathroom products", "Evening bed preparation", "Sheets and towels", "Guest room facilities"],
                    "matches": {"Amenities": "Guest room facilities", "Turndown service": "Evening bed preparation",
                               "Linen": "Sheets and towels", "Toiletries": "Bathroom products"},
                    "explanation": "Standard housekeeping vocabulary."
                }
            ],
            "Food & Beverage": [
                {
                    "question": "Match dining terms:",
                    "terms": ["Appetizer", "Entree", "Dessert", "Buffet"],
                    "definitions": ["Self-service meal", "First course", "Main course", "Final course"],
                    "matches": {"Appetizer": "First course", "Entree": "Main course",
                               "Dessert": "Final course", "Buffet": "Self-service meal"},
                    "explanation": "Essential restaurant terminology."
                }
            ],
            "Bar Service": [
                {
                    "question": "Match beverage terms:",
                    "terms": ["Mocktail", "On the rocks", "Neat", "Vintage"],
                    "definitions": ["Wine year", "Non-alcoholic cocktail", "Pure without ice", "Served with ice"],
                    "matches": {"Mocktail": "Non-alcoholic cocktail", "On the rocks": "Served with ice",
                               "Neat": "Pure without ice", "Vintage": "Wine year"},
                    "explanation": "Bar service terminology for beverage preparation."
                }
            ],
            "Guest Services": [
                {
                    "question": "Match service terms:",
                    "terms": ["Itinerary", "Muster drill", "All aboard", "Gangway"],
                    "definitions": ["Final boarding call", "Safety briefing", "Travel schedule", "Ship boarding ramp"],
                    "matches": {"Itinerary": "Travel schedule", "Muster drill": "Safety briefing",
                               "All aboard": "Final boarding call", "Gangway": "Ship boarding ramp"},
                    "explanation": "Guest services communication vocabulary."
                }
            ],
            "Deck Department": [
                {
                    "question": "Match nautical terms:",
                    "terms": ["Port", "Starboard", "Bow", "Stern"],
                    "definitions": ["Back of ship", "Left side", "Front of ship", "Right side"],
                    "matches": {"Port": "Left side", "Starboard": "Right side",
                               "Bow": "Front of ship", "Stern": "Back of ship"},
                    "explanation": "Basic directional nautical terminology."
                }
            ],
            "Engine Department": [
                {
                    "question": "Match engineering terms:",
                    "terms": ["Propulsion", "RPM", "Auxiliary", "Redundancy"],
                    "definitions": ["Backup system", "Engine rotation speed", "Support equipment", "Forward movement system"],
                    "matches": {"Propulsion": "Forward movement system", "RPM": "Engine rotation speed",
                               "Auxiliary": "Support equipment", "Redundancy": "Backup system"},
                    "explanation": "Marine engineering vocabulary."
                }
            ],
            "Security Department": [
                {
                    "question": "Match security terms:",
                    "terms": ["Surveillance", "Patrol", "Access control", "Incident report"],
                    "definitions": ["Entry restriction", "Monitoring system", "Regular inspection", "Event documentation"],
                    "matches": {"Surveillance": "Monitoring system", "Patrol": "Regular inspection",
                               "Access control": "Entry restriction", "Incident report": "Event documentation"},
                    "explanation": "Security operations terminology."
                }
            ],
            "Table Games": [
                {
                    "question": "Match gaming terms:",
                    "terms": ["House edge", "Push", "Bust", "Double down"],
                    "definitions": ["Exceed 21", "Casino advantage", "Tie game", "Double bet option"],
                    "matches": {"House edge": "Casino advantage", "Push": "Tie game",
                               "Bust": "Exceed 21", "Double down": "Double bet option"},
                    "explanation": "Table games terminology."
                }
            ],
            "Slot Machines": [
                {
                    "question": "Match slot machine terms:",
                    "terms": ["Payline", "Progressive", "RTP", "Jackpot"],
                    "definitions": ["Maximum prize", "Return to player", "Winning combination line", "Accumulating prize"],
                    "matches": {"Payline": "Winning combination line", "Progressive": "Accumulating prize",
                               "RTP": "Return to player", "Jackpot": "Maximum prize"},
                    "explanation": "Slot machine operations vocabulary."
                }
            ],
            "Casino Services": [
                {
                    "question": "Match casino terms:",
                    "terms": ["Comp", "High roller", "Pit boss", "Cage"],
                    "definitions": ["Cashier area", "VIP gambler", "Floor supervisor", "Complimentary reward"],
                    "matches": {"Comp": "Complimentary reward", "High roller": "VIP gambler",
                               "Pit boss": "Floor supervisor", "Cage": "Cashier area"},
                    "explanation": "Casino operations terminology."
                }
            ]
        }

        # Use department-specific vocab or default to Front Desk
        return vocab_sets.get(dept_name, vocab_sets["Front Desk"])

    def _get_reading_scenarios(self, dept_name: str) -> List[Dict[str, Any]]:
        """Get reading comprehension scenarios"""

        readings = {
            "Front Desk": [
                {
                    "passage": "GUEST CHECK-IN PROCEDURES: All guests must present valid photo identification and boarding passes at embarkation. Room keys will be issued after verification. Guests should familiarize themselves with emergency muster station locations posted in their staterooms. Late check-in after 4:00 PM requires advance notification.",
                    "options": ["Check-in Requirements", "Emergency Procedures", "Hotel Policies", "Travel Guidelines"],
                    "correct": "Check-in Requirements",
                    "explanation": "The passage focuses on guest check-in procedures and requirements."
                },
                {
                    "passage": "ROOM UPGRADE POLICY: Upgrades are subject to availability and may incur additional charges. Ocean view and balcony suites command premium rates. Guests wishing to upgrade should inquire at the front desk during embarkation. Last-minute upgrades may be offered at discounted rates on departure day.",
                    "options": ["Pricing Structure", "Room Upgrade Guidelines", "Booking Instructions", "Cancellation Policy"],
                    "correct": "Room Upgrade Guidelines",
                    "explanation": "The passage explains the room upgrade policy and procedures."
                }
            ],
            "Housekeeping": [
                {
                    "passage": "CABIN CLEANING STANDARDS: All staterooms must be serviced daily between 9:00 AM and 3:00 PM unless guest requests otherwise. Turndown service is provided each evening starting at 6:00 PM. Bed linens are changed every three days or upon request. Guests requiring privacy should display 'Do Not Disturb' signs.",
                    "options": ["Daily Cleaning Schedule", "Guest Privacy Policy", "Service Standards", "Room Maintenance"],
                    "correct": "Daily Cleaning Schedule",
                    "explanation": "The passage outlines the daily housekeeping schedule and standards."
                }
            ],
            "Food & Beverage": [
                {
                    "passage": "SPECIAL DIETARY REQUIREMENTS: Guests with food allergies or dietary restrictions should notify dining staff at least 24 hours in advance. Our culinary team can accommodate vegetarian, vegan, gluten-free, and religious dietary needs. All menu items can be modified to exclude allergens. Cross-contamination prevention protocols are strictly followed.",
                    "options": ["Menu Options", "Allergy Management Protocol", "Dining Reservations", "Kitchen Safety Rules"],
                    "correct": "Allergy Management Protocol",
                    "explanation": "The passage focuses on managing special dietary needs and allergies."
                }
            ],
            "Bar Service": [
                {
                    "passage": "BEVERAGE PACKAGE OPTIONS: The Premium package includes cocktails, beer, wine, and soft drinks for $65 per day. The Deluxe package adds premium spirits and specialty coffees for $85 per day. Packages must be purchased for the entire cruise duration. Guests under 21 are not eligible for alcoholic beverage packages.",
                    "options": ["Drink Pricing", "Beverage Package Information", "Bar Hours", "Alcohol Policies"],
                    "correct": "Beverage Package Information",
                    "explanation": "The passage explains the different beverage package options and pricing."
                }
            ],
            "Deck Department": [
                {
                    "passage": "SAFETY DRILL REQUIREMENTS: All passengers and crew must participate in the mandatory muster drill before departure. The drill typically occurs 30 minutes prior to sailing. Guests should bring their room keys to their assigned muster stations. Failure to attend may result in denied boarding. Life jackets are not required during the drill.",
                    "options": ["Safety Equipment", "Muster Drill Procedures", "Emergency Response", "Boarding Requirements"],
                    "correct": "Muster Drill Procedures",
                    "explanation": "The passage details mandatory safety drill procedures and requirements."
                }
            ],
            "Engine Department": [
                {
                    "passage": "MAINTENANCE LOG PROTOCOL: All engine room equipment must be inspected daily and logged in the maintenance system. Temperature, pressure, and RPM readings should be recorded every four hours during operation. Any abnormal readings must be reported immediately to the chief engineer. Preventive maintenance schedules must be strictly adhered to.",
                    "options": ["Equipment Monitoring", "Maintenance Record Keeping", "Safety Inspection", "Engineering Standards"],
                    "correct": "Maintenance Record Keeping",
                    "explanation": "The passage focuses on proper maintenance logging procedures."
                }
            ],
            "Security Department": [
                {
                    "passage": "SECURITY SCREENING PROCESS: All guests and baggage must pass through security screening at embarkation. Prohibited items include weapons, illegal substances, and flammable materials. Security reserves the right to inspect any item. Guests refusing screening will be denied boarding. Report suspicious activity to security immediately.",
                    "options": ["Boarding Security Procedures", "Prohibited Items List", "Guest Safety Rules", "Emergency Protocols"],
                    "correct": "Boarding Security Procedures",
                    "explanation": "The passage describes the security screening process at embarkation."
                }
            ],
            "Table Games": [
                {
                    "passage": "TABLE GAME RULES: Minimum and maximum bets vary by table and are clearly posted. Players must place bets before the dealer announces 'No more bets.' Cell phone use at tables is prohibited. Guests should exchange cash for chips at the cashier before playing. Tipping dealers is appreciated but not required.",
                    "options": ["Gaming Regulations", "Table Game Guidelines", "Casino Etiquette", "Betting Limits"],
                    "correct": "Table Game Guidelines",
                    "explanation": "The passage outlines rules and guidelines for playing table games."
                }
            ],
            "Casino Services": [
                {
                    "passage": "PLAYER REWARDS PROGRAM: Earn points for every dollar wagered. Silver tier reached at 1,000 points, Gold at 5,000 points, and Platinum at 10,000 points. Higher tiers receive complimentary drinks, priority seating, and exclusive tournament invitations. Points expire after 12 months of inactivity.",
                    "options": ["Loyalty Program Benefits", "Gaming Rewards", "Membership Tiers", "Casino Promotions"],
                    "correct": "Loyalty Program Benefits",
                    "explanation": "The passage explains the player rewards program structure and benefits."
                }
            ]
        }

        # Provide default readings for departments not specifically listed
        default_reading = [
            {
                "passage": "DEPARTMENTAL PROCEDURES: All staff must adhere to established protocols and safety guidelines. Regular training sessions are mandatory to maintain service standards. Guest satisfaction is our top priority. Report any equipment malfunctions or safety concerns immediately to your supervisor. Attendance and punctuality are essential.",
                "options": ["Staff Guidelines", "Safety Protocol", "Training Requirements", "Service Standards"],
                "correct": "Staff Guidelines",
                "explanation": "The passage covers general staff guidelines and procedures."
            }
        ]

        return readings.get(dept_name, default_reading)

    def _get_speaking_scenarios(self, dept_name: str) -> List[Dict[str, Any]]:
        """Get speaking response scenarios"""

        speaking_prompts = {
            "Front Desk": [
                {
                    "prompt": "A guest complains: 'My room is too noisy and I can't sleep.' Respond professionally.",
                    "context": "Guest complaint about room noise",
                    "keywords": ["apologize", "sorry", "understand", "move", "change room", "quiet", "comfortable", "resolve"],
                    "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3},
                    "explanation": "Should apologize, show empathy, and offer solution like room change."
                },
                {
                    "prompt": "A guest asks: 'What shore excursions do you recommend for families?' Provide helpful suggestions.",
                    "context": "Shore excursion recommendation request",
                    "keywords": ["family-friendly", "children", "kids", "recommend", "popular", "beach", "tour", "activities"],
                    "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2},
                    "explanation": "Should suggest appropriate family activities and explain options clearly."
                }
            ],
            "Housekeeping": [
                {
                    "prompt": "A guest says: 'I need extra towels and pillows.' Respond appropriately.",
                    "context": "Guest request for additional items",
                    "keywords": ["certainly", "right away", "deliver", "bring", "how many", "anything else", "happy to help"],
                    "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4},
                    "explanation": "Should acknowledge request and confirm delivery timeframe."
                }
            ],
            "Food & Beverage": [
                {
                    "prompt": "A guest asks: 'I'm allergic to shellfish. What can I order?' Explain options.",
                    "context": "Food allergy inquiry",
                    "keywords": ["allergy", "safe", "alternative", "recommend", "chef", "accommodate", "notify", "careful"],
                    "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2},
                    "explanation": "Should reassure guest and explain safe menu options."
                }
            ],
            "Bar Service": [
                {
                    "prompt": "A guest says: 'What signature cocktails do you recommend?' Make suggestions.",
                    "context": "Beverage recommendation request",
                    "keywords": ["recommend", "popular", "signature", "special", "flavor", "ingredients", "try", "favorite"],
                    "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2},
                    "explanation": "Should describe signature drinks and match to guest preferences."
                }
            ],
            "Deck Department": [
                {
                    "prompt": "Report to bridge: 'Equipment issue spotted during deck inspection.' Make proper report.",
                    "context": "Safety equipment report to bridge",
                    "keywords": ["report", "spotted", "equipment", "location", "inspection", "require", "maintenance", "safety"],
                    "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3},
                    "explanation": "Should report clearly with location and nature of issue."
                }
            ],
            "Engine Department": [
                {
                    "prompt": "Inform chief engineer: 'Unusual temperature reading in main engine.' Report the situation.",
                    "context": "Equipment anomaly report",
                    "keywords": ["temperature", "unusual", "reading", "engine", "monitoring", "check", "normal range", "investigate"],
                    "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3},
                    "explanation": "Should provide specific details and current status."
                }
            ],
            "Security Department": [
                {
                    "prompt": "A guest reports: 'I saw someone acting suspiciously near the pool.' Respond professionally.",
                    "context": "Security concern reported by guest",
                    "keywords": ["thank you", "report", "investigate", "describe", "location", "safety", "patrol", "monitor"],
                    "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3},
                    "explanation": "Should acknowledge concern and explain action to be taken."
                }
            ],
            "Table Games": [
                {
                    "prompt": "A new guest asks: 'I've never played blackjack. Can you explain?' Teach the basics.",
                    "context": "Teaching game rules to new player",
                    "keywords": ["objective", "21", "cards", "dealer", "hit", "stand", "rules", "simple", "try"],
                    "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2},
                    "explanation": "Should explain basic rules clearly and encourage participation."
                }
            ],
            "Casino Services": [
                {
                    "prompt": "A guest asks: 'What are the benefits of joining your loyalty program?' Explain the program.",
                    "context": "Loyalty program explanation",
                    "keywords": ["benefits", "points", "rewards", "tiers", "complimentary", "exclusive", "earn", "redeem"],
                    "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2},
                    "explanation": "Should highlight benefits and explain how to earn rewards."
                }
            ]
        }

        # Default speaking prompts for departments not specifically listed
        default_speaking = [
            {
                "prompt": "A guest asks: 'Can you help me with this?' Respond professionally.",
                "context": "General guest assistance request",
                "keywords": ["help", "assist", "happy", "certainly", "what", "need", "service"],
                "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4},
                "explanation": "Should offer assistance willingly and ask for details."
            }
        ]

        return speaking_prompts.get(dept_name, default_speaking)

    def save_to_json(self, output_path: str):
        """Save generated questions to JSON file"""

        output_data = {
            "metadata": {
                "title": "Cruise Employee English Assessment Question Bank",
                "version": "1.0",
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "total_questions": len(self.questions),
                "departments": 16,
                "questions_per_department": 18,
                "modules": ["Listening", "Time & Numbers", "Grammar", "Vocabulary", "Reading", "Speaking"]
            },
            "statistics": {
                "total_questions": len(self.questions),
                "by_operation": {
                    "HOTEL": len([q for q in self.questions if q["operation"] == "HOTEL"]),
                    "MARINE": len([q for q in self.questions if q["operation"] == "MARINE"]),
                    "CASINO": len([q for q in self.questions if q["operation"] == "CASINO"])
                },
                "by_module": {
                    "Listening": len([q for q in self.questions if q["module"] == "Listening"]),
                    "TimeNumbers": len([q for q in self.questions if q["module"] == "TimeNumbers"]),
                    "Grammar": len([q for q in self.questions if q["module"] == "Grammar"]),
                    "Vocabulary": len([q for q in self.questions if q["module"] == "Vocabulary"]),
                    "Reading": len([q for q in self.questions if q["module"] == "Reading"]),
                    "Speaking": len([q for q in self.questions if q["module"] == "Speaking"])
                },
                "by_difficulty": {
                    "easy": len([q for q in self.questions if q.get("difficulty") == "easy"]),
                    "medium": len([q for q in self.questions if q.get("difficulty") == "medium"]),
                    "hard": len([q for q in self.questions if q.get("difficulty") == "hard"])
                }
            },
            "questions": self.questions
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"[SUCCESS] Successfully generated {len(self.questions)} questions")
        print(f"[SUCCESS] Saved to: {output_path}")
        print(f"\nStatistics:")
        print(f"  - Hotel Operations: {output_data['statistics']['by_operation']['HOTEL']} questions")
        print(f"  - Marine Operations: {output_data['statistics']['by_operation']['MARINE']} questions")
        print(f"  - Casino Operations: {output_data['statistics']['by_operation']['CASINO']} questions")
        print(f"\nModule Distribution:")
        for module, count in output_data['statistics']['by_module'].items():
            print(f"  - {module}: {count} questions")


def main():
    """Main execution function"""

    print("="*70)
    print("Cruise Employee English Assessment Platform")
    print("Question Bank Generator")
    print("="*70)
    print()

    # Initialize generator
    generator = QuestionBankGenerator()

    # Generate all questions
    print("Generating questions...")
    print("  - 16 departments")
    print("  - 18 questions per department")
    print("  - 6 modules per department")
    print("  - Total: 288 questions")
    print()

    questions = generator.generate_all_questions()

    # Save to JSON
    output_path = r"C:\Users\szh2051\OneDrive - Carnival Corporation\Desktop\Python\Claude Demo\src\main\python\data\question_bank_sample.json"
    generator.save_to_json(output_path)

    print()
    print("="*70)
    print("Question bank generation complete!")
    print("="*70)


if __name__ == "__main__":
    main()
