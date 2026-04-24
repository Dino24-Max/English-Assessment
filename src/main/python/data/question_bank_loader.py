"""
Question Bank Loader
Loads comprehensive question banks for all divisions and modules
Supports both legacy format and new 1600-question full bank
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from models.assessment import Question, Assessment, ModuleType, DivisionType, QuestionType, AssessmentStatus
from config.departments import normalize_department


def _time_numbers_audio_sentence(question_text: str, context: str = None, correct_answer: str = None) -> str:
    """Build the sentence to be read for Time & Numbers: fill blank with context or correct_answer so TTS speaks the answer."""
    # Prefer correct_answer; context can contain extra unit/suffix text.
    fill = (correct_answer or context or "").strip()
    if not fill:
        return question_text
    sentence = question_text.replace("___", fill)
    sentence = sentence.replace("$$", "$")
    sentence = re.sub(r"\b(AM|PM)\s+\1\b", r"\1", sentence, flags=re.IGNORECASE)
    return " ".join(sentence.split())


# Listen-and-repeat phrases (2–3 sentences). Used when bank rows are legacy "scenario" items.
_SPEAKING_LISTEN_REPEAT_PHRASES = [
    "Good morning! Welcome aboard. My name is Maria and I will be your cabin steward during this voyage.",
    "The pool deck is located on deck twelve. Please remember to bring your cruise card for towel service.",
    "The spa is on deck twelve, forward. Take the midship elevators up two levels, then follow the signs to the wellness center.",
    "Tonight we have a comedy show in the main theater at eight PM. The musical revue starts at nine thirty in the lounge.",
    "Your muster station is on deck four, starboard side. Please follow the signs and wear your life jacket only if instructed.",
    "The buffet is open until eleven PM. For specialty dining, please confirm your reservation at the guest services desk.",
]

_SPEAKING_KW_STOPWORDS = frozenset(
    {
        "the", "and", "for", "you", "your", "are", "can", "our", "has", "was", "not", "but", "with",
        "this", "that", "from", "have", "please", "then", "two", "any", "all", "will", "may", "get",
        "way", "how", "who", "its", "did", "say", "let", "put", "too", "out", "off", "now", "one",
        "her", "him", "his", "she", "ask", "use", "here", "only", "just", "also", "what", "when",
        "where", "which", "about", "into", "than", "them", "very", "well", "each", "some", "such",
        "make", "like", "been", "more", "most", "take", "come", "back", "over", "after", "before",
        "under", "above", "between", "through", "during", "upon", "until", "while", "being", "both",
        "either", "neither", "whether", "because", "since", "though", "although", "unless", "however",
        "therefore", "within", "without", "against", "among", "around", "toward", "towards", "across",
        "behind", "beyond", "beside", "besides", "except", "including", "regarding", "concerning",
        "according", "another", "other", "own", "same", "these", "those", "every", "little", "much",
        "many", "few", "several", "enough", "quite", "rather", "really", "even", "ever", "never",
        "always", "often", "sometimes", "usually", "perhaps", "maybe", "might", "could", "would",
        "should", "must", "shall", "need", "ought",
    }
)


def _stable_speaking_phrase_index(question_id: str) -> int:
    key = (question_id or "default").encode("utf-8")
    return int(hashlib.md5(key).hexdigest(), 16) % len(_SPEAKING_LISTEN_REPEAT_PHRASES)


def _speaking_keywords_from_audio(text: str, max_kw: int = 14) -> List[str]:
    words = re.findall(r"[A-Za-z]{3,}", (text or "").lower())
    out: List[str] = []
    seen = set()
    for w in words:
        if w in _SPEAKING_KW_STOPWORDS or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= max_kw:
            break
    return out


def _loader_semantic_hash(q_data: dict, department: Optional[str]) -> str:
    """Match generator storage hash when JSON row omits semantic_hash."""
    existing = q_data.get("semantic_hash")
    if existing:
        return str(existing)
    qid = str(q_data.get("question_id") or q_data.get("id") or "")
    opts = q_data.get("options")
    if isinstance(opts, list):
        options_sorted: Any = sorted(opts)
    else:
        options_sorted = json.dumps(opts or {}, sort_keys=True, default=str)
    payload = {
        "question_text": (q_data.get("question_text") or "").strip(),
        "options": options_sorted,
        "correct_answer": (q_data.get("correct_answer") or "").strip(),
    }
    fp = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    dept = (department or "").strip()
    raw = f"{fp}|{dept}|{qid}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_speaking_listen_repeat(q_data: dict, metadata: dict) -> dict:
    """
    Ensure speaking rows are listen-and-repeat: metadata has speaking_type repeat, audio_text, expected_keywords.
    Legacy scenario-only rows get a stable phrase from the pool so UI and scoring match product requirements.
    """
    meta = dict(metadata or {})
    st = (meta.get("speaking_type") or "").lower()
    audio = (meta.get("audio_text") or "").strip()
    has_file = bool(q_data.get("audio_file_path") or meta.get("audio_file_path"))

    has_repeat_content = (st == "repeat") and (bool(audio) or has_file)
    if not has_repeat_content:
        qid = str(q_data.get("question_id") or q_data.get("id") or "")
        idx = _stable_speaking_phrase_index(qid)
        phrase = _SPEAKING_LISTEN_REPEAT_PHRASES[idx]
        meta["speaking_type"] = "repeat"
        meta["audio_text"] = phrase
        meta["expected_keywords"] = _speaking_keywords_from_audio(phrase)
        meta.setdefault("min_duration", 3)
        q_data["question_text"] = (
            "Listen to the audio and repeat exactly what you hear. "
            "Your score is based on how many key words you say clearly."
        )
    else:
        meta["speaking_type"] = "repeat"
        meta.setdefault("min_duration", 3)

    if (meta.get("speaking_type") or "").lower() == "repeat" and (meta.get("audio_text") or "").strip():
        if not meta.get("expected_keywords"):
            meta["expected_keywords"] = _speaking_keywords_from_audio(str(meta["audio_text"]))
    return meta


class QuestionBankLoader:
    """Loads question banks into database"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def clear_all_questions(self) -> int:
        """Delete all questions from database. Returns count of deleted rows."""
        result = await self.db.execute(delete(Question))
        await self.db.commit()
        return result.rowcount or 0

    async def reset_assessments_question_order(self) -> int:
        """Clear question_order on in-progress and not-started assessments so they get fresh questions. Returns count of updated rows."""
        from sqlalchemy import or_
        result = await self.db.execute(
            update(Assessment)
            .where(
                or_(
                    Assessment.status == AssessmentStatus.IN_PROGRESS,
                    Assessment.status == AssessmentStatus.NOT_STARTED,
                )
            )
            .values(question_order=None)
        )
        await self.db.commit()
        return result.rowcount or 0

    async def load_full_question_bank(self, json_file_path: str = None, clear_first: bool = False):
        """
        Load complete 1600-question bank from JSON file
        
        Args:
            json_file_path: Path to question_bank_full.json (optional)
            clear_first: If True, delete all existing questions before loading
        """
        if clear_first:
            reset = await self.reset_assessments_question_order()
            print(f"Reset question_order on {reset} in-progress/not-started assessments.")
            deleted = await self.clear_all_questions()
            print(f"Cleared {deleted} existing questions before load.")
        if not json_file_path:
            # Default path: question_bank_full.json in same directory as this module
            data_dir = Path(__file__).parent
            full_path = data_dir / "question_bank_full.json"
            sample_path = data_dir / "question_bank_sample.json"
            if full_path.exists():
                json_file_path = full_path
            elif sample_path.exists():
                json_file_path = sample_path
                print("question_bank_full.json not found; using question_bank_sample.json (department-specific).")
            else:
                raise FileNotFoundError(f"No question bank found: {full_path} or {sample_path}")
        else:
            json_file_path = Path(json_file_path)
            if not json_file_path.exists():
                raise FileNotFoundError(f"Question bank file not found: {json_file_path}")
        
        print(f"Loading full question bank from: {json_file_path}")
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            bank_data = json.load(f)
        
        questions_data = bank_data.get("questions", [])
        print(f"Found {len(questions_data)} questions to load")

        added = 0
        skipped_duplicates = 0

        for i, q_data in enumerate(questions_data, 1):
            # Map module to ModuleType enum (support both JSON and DB naming)
            module_map = {
                "listening": ModuleType.LISTENING,
                "Listening": ModuleType.LISTENING,
                "grammar": ModuleType.GRAMMAR,
                "Grammar": ModuleType.GRAMMAR,
                "vocabulary": ModuleType.VOCABULARY,
                "Vocabulary": ModuleType.VOCABULARY,
                "reading": ModuleType.READING,
                "Reading": ModuleType.READING,
                "time_numbers": ModuleType.TIME_NUMBERS,
                "TimeNumbers": ModuleType.TIME_NUMBERS,
                "speaking": ModuleType.SPEAKING,
                "Speaking": ModuleType.SPEAKING,
            }
            
            # Map division to DivisionType enum (also accept "operation" from JSON)
            division_map = {
                "hotel": DivisionType.HOTEL,
                "marine": DivisionType.MARINE,
                "casino": DivisionType.CASINO,
                "HOTEL": DivisionType.HOTEL,
                "MARINE": DivisionType.MARINE,
                "CASINO": DivisionType.CASINO,
            }
            
            # Map question_type string to QuestionType enum
            type_map = {
                "multiple_choice": QuestionType.MULTIPLE_CHOICE,
                "fill_blank": QuestionType.FILL_BLANK,
                "category_match": QuestionType.CATEGORY_MATCH,
                "title_selection": QuestionType.TITLE_SELECTION,
                "speaking_response": QuestionType.SPEAKING_RESPONSE
            }
            
            # Build question_metadata: merge explicit JSON metadata with top-level fields (same keys as generator output)
            metadata = q_data.get("question_metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            else:
                metadata = dict(metadata)
            for key in ("audio_text", "passage", "terms", "definitions", "correct_matches",
                        "speaking_type", "min_duration", "expected_keywords"):
                if key in q_data and q_data[key] is not None:
                    metadata.setdefault(key, q_data[key])
            if q_data.get("audio") and not metadata.get("audio_text"):
                metadata["audio_text"] = q_data["audio"]
            if q_data.get("audio_context") and not metadata.get("audio_text"):
                metadata["audio_text"] = q_data["audio_context"]

            mod = (q_data.get("module_type") or q_data.get("module") or "").lower()
            # Time & Numbers: audio must speak the answer-bearing sentence, not the prompt.
            if (mod in ("time_numbers", "timenumbers")) and not metadata.get("audio_text"):
                metadata["audio_text"] = _time_numbers_audio_sentence(
                    q_data.get("question_text", ""),
                    q_data.get("context"),
                    q_data.get("correct_answer"),
                )

            if mod == "speaking":
                metadata = _normalize_speaking_listen_repeat(q_data, metadata)

            metadata = metadata if metadata else None

            # Normalize department to canonical name (e.g. "Housekeeping" -> "HOUSEKEEPING")
            # so it matches invitation/assessment department and engine can filter by department
            raw_dept = q_data.get("department")
            department = normalize_department(raw_dept) if raw_dept else None

            semantic_hash = _loader_semantic_hash(q_data, department)
            grammar_type = q_data.get("grammar_type")
            grammar_topic = q_data.get("grammar_topic")

            question = Question(
                module_type=module_map.get(q_data.get("module_type", q_data.get("module")), ModuleType.LISTENING),
                division=division_map.get(q_data.get("division") or q_data.get("operation"), DivisionType.HOTEL),
                question_type=type_map.get(q_data.get("question_type"), QuestionType.MULTIPLE_CHOICE),
                question_text=q_data.get("question_text", ""),
                options=q_data.get("options"),
                correct_answer=q_data.get("correct_answer", ""),
                audio_file_path=q_data.get("audio_file_path"),
                difficulty_level=q_data.get("difficulty_level", 2),
                is_safety_related=q_data.get("is_safety_related", False),
                points=q_data.get("points", 4),
                department=department,
                scenario_id=q_data.get("scenario_id"),
                scenario_description=q_data.get("scenario_description"),
                cefr_level=q_data.get("cefr_level"),
                question_metadata=metadata,
                semantic_hash=semantic_hash,
                grammar_type=grammar_type,
                grammar_topic=grammar_topic,
            )

            try:
                async with self.db.begin_nested():
                    self.db.add(question)
                    await self.db.flush()
                added += 1
            except IntegrityError:
                skipped_duplicates += 1

            if i % 100 == 0:
                await self.db.commit()
                print(
                    f"  [OK] Committed progress {i}/{len(questions_data)} "
                    f"(added={added}, skipped_duplicates={skipped_duplicates})"
                )

        await self.db.commit()
        print(
            f"[OK] Load complete: {added} questions inserted, "
            f"{skipped_duplicates} skipped (duplicate semantic_hash)."
        )

        return added

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

                # Build question_metadata (include audio_text for listening from audio_context or audio_text)
                q_meta = dict(q_data.get("metadata") or q_data.get("question_metadata") or {})
                if module_type == ModuleType.LISTENING:
                    if q_data.get("audio_text") and "audio_text" not in q_meta:
                        q_meta["audio_text"] = q_data["audio_text"]
                    if q_data.get("audio_context") and "audio_text" not in q_meta:
                        q_meta["audio_text"] = q_data["audio_context"]
                elif module_type == ModuleType.TIME_NUMBERS and not q_meta.get("audio_text"):
                    q_meta["audio_text"] = _time_numbers_audio_sentence(
                        q_data.get("question_text", ""),
                        q_data.get("context"),
                        q_data.get("correct_answer"),
                    )

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
                    question_metadata=q_meta if q_meta else None
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