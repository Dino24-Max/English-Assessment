"""
Generate Question Bank for Cruise Employee English Assessment Platform

Generates 3,000 questions across 30 departments:
- 100 questions per department
- CEFR distribution per module (A1-C2)
- Output format compatible with question_bank_loader.py
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.departments import (
    DEPARTMENTS,
    DEPARTMENT_COUNT,
    DEPARTMENT_TO_CONTENT_POOL,
    HOTEL_OPERATION,
    MARINE_OPERATION,
)
from data.cefr_spec import MODULE_CEFR_DISTRIBUTION, CEFR_LEVELS

# Loader-friendly module keys
MODULE_TO_LOADER = {
    "Listening": "listening",
    "TimeNumbers": "time_numbers",
    "Grammar": "grammar",
    "Vocabulary": "vocabulary",
    "Reading": "reading",
    "Speaking": "speaking",
}

# Vocabulary term pools: 20 (band, term, definition) tuples per content area.
# The generator builds unique 4-term matching sets from non-overlapping slices,
# guaranteeing distinct content keys for the assessment engine dedup logic.
VOCAB_TERM_POOLS = {
    "Front Desk": [
        ("basic", "Embarkation", "Boarding the ship"),
        ("basic", "Disembarkation", "Leaving the ship"),
        ("basic", "Port of call", "Destination stop"),
        ("basic", "Home port", "Original departure port"),
        ("basic", "Gangway", "Ship entrance ramp"),
        ("basic", "Key card", "Electronic room access"),
        ("basic", "Folio", "Guest account record"),
        ("basic", "Cabin", "Guest sleeping quarters"),
        ("intermediate", "Concierge", "Guest services specialist"),
        ("intermediate", "Shore excursion", "Organized land tour"),
        ("intermediate", "Stateroom", "Guest cabin on ship"),
        ("intermediate", "Tender", "Small transport boat"),
        ("intermediate", "Manifest", "Passenger list document"),
        ("intermediate", "Maiden voyage", "Ship first sailing"),
        ("intermediate", "Purser", "Ship financial officer"),
        ("intermediate", "Lido deck", "Pool and sun area"),
        ("advanced", "Revenue management", "Dynamic pricing strategy"),
        ("advanced", "Occupancy rate", "Room utilization percentage"),
        ("advanced", "Yield per cabin", "Revenue per available room"),
        ("advanced", "Debarkation protocol", "Organized departure procedures"),
    ],
    "Housekeeping": [
        ("basic", "Amenities", "Guest room facilities"),
        ("basic", "Turndown service", "Evening bed preparation"),
        ("basic", "Linen", "Sheets and towels"),
        ("basic", "Toiletries", "Bathroom products"),
        ("basic", "Pillow", "Head support for sleeping"),
        ("basic", "Blanket", "Bed covering for warmth"),
        ("basic", "Towel rack", "Towel hanging fixture"),
        ("basic", "Do Not Disturb", "Privacy request sign"),
        ("intermediate", "Sanitize", "Disinfect surfaces thoroughly"),
        ("intermediate", "Deep clean", "Thorough room washing"),
        ("intermediate", "Inspection", "Quality standards check"),
        ("intermediate", "Inventory count", "Supply level tracking"),
        ("intermediate", "Mini-bar", "In-room beverage cabinet"),
        ("intermediate", "Bathrobe", "Guest lounging garment"),
        ("intermediate", "Room safe", "Secure valuables storage"),
        ("intermediate", "Cabin steward", "Room attendant staff"),
        ("advanced", "Occupancy turnover", "Room changeover process"),
        ("advanced", "Cross-contamination", "Unintended germ transfer"),
        ("advanced", "Quality audit", "Standards compliance review"),
        ("advanced", "Standard procedure", "Formalized work method"),
    ],
    "Food & Beverage": [
        ("basic", "Waiter", "Table service staff"),
        ("basic", "Chef", "Kitchen cooking professional"),
        ("basic", "Menu", "Food selection list"),
        ("basic", "Gratuity", "Service tip amount"),
        ("basic", "Breakfast", "Morning meal service"),
        ("basic", "Lunch", "Midday meal service"),
        ("basic", "Dinner", "Evening meal service"),
        ("basic", "Snack", "Light between-meal food"),
        ("intermediate", "Appetizer", "First course dish"),
        ("intermediate", "Entree", "Main course dish"),
        ("intermediate", "Dessert", "Final sweet course"),
        ("intermediate", "Buffet", "Self-service meal setup"),
        ("intermediate", "Sommelier", "Wine service expert"),
        ("intermediate", "A la carte", "Individual item ordering"),
        ("intermediate", "Table d hote", "Fixed price set menu"),
        ("intermediate", "Garnish", "Decorative food topping"),
        ("advanced", "HACCP", "Food safety management system"),
        ("advanced", "Allergen log", "Allergy tracking record"),
        ("advanced", "Cross-contact", "Unintended allergen transfer"),
        ("advanced", "Mise en place", "Kitchen preparation setup"),
    ],
    "Bar Service": [
        ("basic", "Cocktail", "Mixed alcoholic drink"),
        ("basic", "Beer", "Brewed grain beverage"),
        ("basic", "Wine", "Fermented grape drink"),
        ("basic", "Soda", "Carbonated soft drink"),
        ("basic", "Ice", "Frozen water cubes"),
        ("basic", "Garnish", "Drink decoration item"),
        ("basic", "Straw", "Drinking tube accessory"),
        ("basic", "Coaster", "Glass protection pad"),
        ("intermediate", "Mocktail", "Non-alcoholic cocktail"),
        ("intermediate", "On the rocks", "Served over ice"),
        ("intermediate", "Neat", "Pure spirit without ice"),
        ("intermediate", "Vintage", "Wine production year"),
        ("intermediate", "Aperitif", "Pre-dinner drink"),
        ("intermediate", "Digestif", "After-dinner drink"),
        ("intermediate", "Draft", "Beer from tap"),
        ("intermediate", "Proof", "Alcohol strength measure"),
        ("advanced", "Mixologist", "Expert cocktail creator"),
        ("advanced", "Decant", "Pour wine for aeration"),
        ("advanced", "Infusion", "Flavored spirit blend"),
        ("advanced", "Bitters", "Concentrated herbal extract"),
    ],
    "Guest Services": [
        ("basic", "Deck", "Ship floor level"),
        ("basic", "Cabin", "Guest room onboard"),
        ("basic", "Pool", "Swimming water area"),
        ("basic", "Spa", "Wellness treatment center"),
        ("basic", "Excursion", "Organized shore trip"),
        ("basic", "Port", "Harbor stopping point"),
        ("basic", "Tender", "Small shuttle boat"),
        ("basic", "Dock", "Ship mooring area"),
        ("intermediate", "Itinerary", "Travel schedule plan"),
        ("intermediate", "Muster drill", "Mandatory safety briefing"),
        ("intermediate", "All aboard", "Final boarding announcement"),
        ("intermediate", "Gangway", "Ship boarding ramp"),
        ("intermediate", "Debarkation", "Leaving the ship"),
        ("intermediate", "Promenade", "Outdoor walking deck"),
        ("intermediate", "Lido", "Pool entertainment area"),
        ("intermediate", "Shore pass", "Port departure permit"),
        ("advanced", "Concierge service", "Personalized guest assistance"),
        ("advanced", "Guest relations", "Customer satisfaction management"),
        ("advanced", "Service recovery", "Problem resolution process"),
        ("advanced", "Net Promoter Score", "Guest satisfaction metric"),
    ],
    "Auxiliary Service": [
        ("basic", "Microphone", "Voice amplification device"),
        ("basic", "Speaker", "Sound output equipment"),
        ("basic", "Stage", "Performance platform area"),
        ("basic", "Screen", "Display projection surface"),
        ("basic", "Cable", "Electrical connection wire"),
        ("basic", "Chair", "Seating furniture piece"),
        ("basic", "Table", "Flat surface furniture"),
        ("basic", "Podium", "Speaker standing platform"),
        ("intermediate", "Projector", "Image display device"),
        ("intermediate", "Soundboard", "Audio mixing console"),
        ("intermediate", "Setup", "Equipment assembly work"),
        ("intermediate", "Breakdown", "Equipment teardown work"),
        ("intermediate", "Spotlight", "Focused lighting beam"),
        ("intermediate", "Rigging", "Stage suspension system"),
        ("intermediate", "Backdrop", "Stage background display"),
        ("intermediate", "Cue", "Performance timing signal"),
        ("advanced", "AV technician", "Audio-visual equipment operator"),
        ("advanced", "Sound check", "Pre-event audio test"),
        ("advanced", "Gain level", "Audio signal strength"),
        ("advanced", "Feedback loop", "Unwanted audio resonance"),
    ],
    "Laundry": [
        ("basic", "Shirt", "Upper body garment"),
        ("basic", "Pants", "Lower body garment"),
        ("basic", "Dress", "One-piece formal garment"),
        ("basic", "Uniform", "Standard work clothing"),
        ("basic", "Wash", "Clean with water"),
        ("basic", "Dry", "Remove all moisture"),
        ("basic", "Fold", "Crease garment neatly"),
        ("basic", "Iron", "Press wrinkles smooth"),
        ("intermediate", "Press", "Iron garments flat"),
        ("intermediate", "Dry clean", "Chemical solvent cleaning"),
        ("intermediate", "Express", "Rush priority service"),
        ("intermediate", "Stain removal", "Spot cleaning treatment"),
        ("intermediate", "Bleach", "Chemical whitening agent"),
        ("intermediate", "Fabric softener", "Textile softening liquid"),
        ("intermediate", "Detergent", "Cleaning solution soap"),
        ("intermediate", "Lint", "Loose textile fibers"),
        ("advanced", "Industrial press", "Heavy-duty garment iron"),
        ("advanced", "Chemical treatment", "Specialized cleaning process"),
        ("advanced", "Batch processing", "Group item handling"),
        ("advanced", "Quality inspection", "Standards compliance check"),
    ],
    "Photo": [
        ("basic", "Camera", "Image capturing device"),
        ("basic", "Flash", "Bright photography light"),
        ("basic", "Lens", "Camera focusing glass"),
        ("basic", "Photo", "Captured image print"),
        ("basic", "Smile", "Happy facial expression"),
        ("basic", "Pose", "Body position for photo"),
        ("basic", "Frame", "Photo border holder"),
        ("basic", "Album", "Photo collection book"),
        ("intermediate", "Print", "Physical photo copy"),
        ("intermediate", "Digital album", "Online photo gallery"),
        ("intermediate", "Portrait", "Posed person photograph"),
        ("intermediate", "Background", "Photo scene backdrop"),
        ("intermediate", "Retouching", "Photo editing improvement"),
        ("intermediate", "Composition", "Photo scene arrangement"),
        ("intermediate", "Exposure", "Camera light setting"),
        ("intermediate", "Resolution", "Image quality clarity"),
        ("advanced", "White balance", "Color temperature setting"),
        ("advanced", "Depth of field", "Focus range distance"),
        ("advanced", "RAW format", "Uncompressed image file"),
        ("advanced", "Post-production", "After-capture editing work"),
    ],
    "Provisions": [
        ("basic", "Fruit", "Fresh edible produce"),
        ("basic", "Vegetable", "Plant-based food item"),
        ("basic", "Meat", "Animal protein food"),
        ("basic", "Dairy", "Milk-based products"),
        ("basic", "Box", "Cardboard storage container"),
        ("basic", "Crate", "Wooden transport container"),
        ("basic", "Pallet", "Flat shipping platform"),
        ("basic", "Cooler", "Insulated cold storage"),
        ("intermediate", "Inventory", "Current stock count"),
        ("intermediate", "FIFO", "First in first out"),
        ("intermediate", "Cold storage", "Refrigerated storage area"),
        ("intermediate", "Order lead time", "Supplier delivery delay"),
        ("intermediate", "Vendor", "Product supply company"),
        ("intermediate", "Invoice", "Payment request document"),
        ("intermediate", "Purchase order", "Formal buy request"),
        ("intermediate", "Receiving", "Goods acceptance process"),
        ("advanced", "Supply chain", "Distribution network system"),
        ("advanced", "Perishable goods", "Items with limited shelf life"),
        ("advanced", "Traceability", "Origin tracking capability"),
        ("advanced", "Par level", "Minimum stock threshold"),
    ],
    "Deck Department": [
        ("basic", "Port", "Left side of ship"),
        ("basic", "Starboard", "Right side of ship"),
        ("basic", "Bow", "Front of the ship"),
        ("basic", "Stern", "Back of the ship"),
        ("basic", "Anchor", "Ship holding device"),
        ("basic", "Rope", "Mooring tie line"),
        ("basic", "Lifeboat", "Emergency rescue craft"),
        ("basic", "Compass", "Direction finding tool"),
        ("intermediate", "Bridge", "Ship command center"),
        ("intermediate", "Helm", "Ship steering wheel"),
        ("intermediate", "Draft", "Ship water depth"),
        ("intermediate", "Knot", "Nautical speed unit"),
        ("intermediate", "Mooring", "Ship securing process"),
        ("intermediate", "Windlass", "Anchor lifting winch"),
        ("intermediate", "Bollard", "Dock mooring post"),
        ("intermediate", "Hawser", "Heavy mooring rope"),
        ("advanced", "Dead reckoning", "Position estimation method"),
        ("advanced", "Bearing", "Directional angle measurement"),
        ("advanced", "Buoyancy", "Floating force principle"),
        ("advanced", "Displacement", "Water volume moved by ship"),
    ],
    "Engine Department": [
        ("basic", "Engine", "Ship power source"),
        ("basic", "Fuel", "Energy supply liquid"),
        ("basic", "Oil", "Machine lubricant fluid"),
        ("basic", "Pump", "Fluid moving device"),
        ("basic", "Pipe", "Fluid transport tube"),
        ("basic", "Wrench", "Bolt turning tool"),
        ("basic", "Gauge", "Measurement reading device"),
        ("basic", "Filter", "Impurity removal device"),
        ("intermediate", "Generator", "Electricity producing unit"),
        ("intermediate", "Boiler", "Steam generating unit"),
        ("intermediate", "Condenser", "Vapor cooling unit"),
        ("intermediate", "Compressor", "Gas pressurizing unit"),
        ("intermediate", "Valve", "Flow control device"),
        ("intermediate", "Bearing", "Rotation support part"),
        ("intermediate", "Turbine", "Rotary power converter"),
        ("intermediate", "Switchboard", "Power distribution panel"),
        ("advanced", "Propulsion", "Forward movement system"),
        ("advanced", "RPM", "Engine rotation speed"),
        ("advanced", "Auxiliary", "Support backup equipment"),
        ("advanced", "Redundancy", "Backup safety system"),
    ],
    "Medical Department": [
        ("basic", "Doctor", "Medical physician professional"),
        ("basic", "Nurse", "Patient care provider"),
        ("basic", "Patient", "Person receiving treatment"),
        ("basic", "Medicine", "Therapeutic treatment drug"),
        ("basic", "Bandage", "Wound covering dressing"),
        ("basic", "Thermometer", "Temperature measuring device"),
        ("basic", "Stethoscope", "Heart and lung listener"),
        ("basic", "Wheelchair", "Mobile seated transport"),
        ("intermediate", "Vitals", "Key body measurements"),
        ("intermediate", "Sick call", "Medical visit request"),
        ("intermediate", "Triage", "Priority assessment process"),
        ("intermediate", "Prescription", "Written medication order"),
        ("intermediate", "Quarantine", "Disease isolation period"),
        ("intermediate", "Vaccination", "Preventive disease injection"),
        ("intermediate", "Defibrillator", "Heart rhythm restorer"),
        ("intermediate", "Infirmary", "Ship medical facility"),
        ("advanced", "Medevac", "Emergency medical evacuation"),
        ("advanced", "Prophylaxis", "Preventive medical treatment"),
        ("advanced", "Telemedicine", "Remote medical consultation"),
        ("advanced", "Epidemiology", "Disease pattern study"),
    ],
    "Security Department": [
        ("basic", "Guard", "Security patrol officer"),
        ("basic", "Camera", "Video monitoring device"),
        ("basic", "Badge", "Identity display card"),
        ("basic", "Lock", "Door securing device"),
        ("basic", "Key", "Lock opening tool"),
        ("basic", "Alarm", "Warning sound system"),
        ("basic", "Radio", "Communication walkie-talkie"),
        ("basic", "Uniform", "Official security clothing"),
        ("intermediate", "Surveillance", "Continuous monitoring system"),
        ("intermediate", "Patrol", "Regular inspection rounds"),
        ("intermediate", "Access control", "Entry restriction system"),
        ("intermediate", "Incident report", "Event documentation form"),
        ("intermediate", "Checkpoint", "Security inspection station"),
        ("intermediate", "Contraband", "Prohibited banned items"),
        ("intermediate", "Evacuation", "Emergency area departure"),
        ("intermediate", "Perimeter", "Secured boundary area"),
        ("advanced", "Threat assessment", "Risk evaluation analysis"),
        ("advanced", "Chain of custody", "Evidence handling procedure"),
        ("advanced", "Biometrics", "Body-based identification"),
        ("advanced", "Forensics", "Scientific crime investigation"),
    ],
    "Table Games": [
        ("basic", "Cards", "Playing game cards"),
        ("basic", "Dice", "Random number cubes"),
        ("basic", "Chips", "Betting value tokens"),
        ("basic", "Dealer", "Game card operator"),
        ("basic", "Bet", "Money wagered amount"),
        ("basic", "Win", "Prize gained reward"),
        ("basic", "Lose", "Wager lost result"),
        ("basic", "Jackpot", "Maximum prize payout"),
        ("intermediate", "House edge", "Casino statistical advantage"),
        ("intermediate", "Push", "Tied game result"),
        ("intermediate", "Bust", "Exceeding twenty-one points"),
        ("intermediate", "Double down", "Double bet option"),
        ("intermediate", "Shuffle", "Randomize card order"),
        ("intermediate", "Ante", "Initial required bet"),
        ("intermediate", "Fold", "Surrender current hand"),
        ("intermediate", "Split", "Divide pair into two"),
        ("advanced", "Pit boss", "Gaming floor supervisor"),
        ("advanced", "Shoe", "Multi-deck card dispenser"),
        ("advanced", "Rake", "House commission percentage"),
        ("advanced", "Marker", "Casino credit slip"),
    ],
    "Slot Machines": [
        ("basic", "Slot", "Gaming machine type"),
        ("basic", "Reel", "Spinning symbol column"),
        ("basic", "Coin", "Inserted payment token"),
        ("basic", "Button", "Machine control press"),
        ("basic", "Screen", "Display monitor panel"),
        ("basic", "Lights", "Machine indicator signals"),
        ("basic", "Sound", "Audio alert effect"),
        ("basic", "Ticket", "Payout voucher slip"),
        ("intermediate", "Payline", "Winning combination line"),
        ("intermediate", "Progressive", "Accumulating prize pool"),
        ("intermediate", "RTP", "Return to player percentage"),
        ("intermediate", "Jackpot", "Maximum prize amount"),
        ("intermediate", "Scatter", "Bonus trigger symbol"),
        ("intermediate", "Wild", "Substitute match symbol"),
        ("intermediate", "Free spin", "No-cost bonus round"),
        ("intermediate", "Multiplier", "Prize increase factor"),
        ("advanced", "Volatility", "Prize frequency variance"),
        ("advanced", "Hit frequency", "Win occurrence rate"),
        ("advanced", "Denomination", "Minimum bet increment"),
        ("advanced", "Hopper", "Coin payout mechanism"),
    ],
    "Casino Services": [
        ("basic", "Casino", "Gaming entertainment area"),
        ("basic", "Player", "Gaming participant guest"),
        ("basic", "Reward", "Earned loyalty benefit"),
        ("basic", "Member", "Loyalty program participant"),
        ("basic", "Points", "Earned loyalty credits"),
        ("basic", "Card", "Player membership card"),
        ("basic", "Prize", "Won gaming reward"),
        ("basic", "Cashier", "Money exchange counter"),
        ("intermediate", "Comp", "Complimentary reward benefit"),
        ("intermediate", "High roller", "VIP high-stakes gambler"),
        ("intermediate", "Pit boss", "Floor gaming supervisor"),
        ("intermediate", "Cage", "Casino cashier area"),
        ("intermediate", "Buy-in", "Tournament entry fee"),
        ("intermediate", "Credit", "Borrowed gaming funds"),
        ("intermediate", "Loyalty tier", "Membership rank level"),
        ("intermediate", "Host", "VIP guest coordinator"),
        ("advanced", "Responsible gaming", "Problem gambling prevention"),
        ("advanced", "Wagering requirement", "Bonus play-through condition"),
        ("advanced", "Hold percentage", "Casino revenue margin"),
        ("advanced", "Junket", "Organized VIP gaming trip"),
    ],
    "Cabin Service": [
        ("basic", "Cabin", "Guest sleeping room"),
        ("basic", "Bed", "Sleeping furniture"),
        ("basic", "Pillow", "Head rest cushion"),
        ("basic", "Blanket", "Warm bed covering"),
        ("basic", "Lamp", "Room light fixture"),
        ("basic", "Mirror", "Reflective glass surface"),
        ("basic", "Closet", "Clothing storage space"),
        ("basic", "Balcony", "Outdoor cabin area"),
        ("intermediate", "Room service", "In-cabin food delivery"),
        ("intermediate", "Wake-up call", "Morning alarm service"),
        ("intermediate", "Mini-bar", "In-room refreshments"),
        ("intermediate", "Butler service", "Personal cabin attendant"),
        ("intermediate", "Turndown", "Evening bed preparation"),
        ("intermediate", "Complimentary", "Free of charge item"),
        ("intermediate", "Amenity kit", "Guest toiletry package"),
        ("intermediate", "Cabin category", "Room type classification"),
        ("advanced", "Suite upgrade", "Premium room enhancement"),
        ("advanced", "Concierge level", "Premium service tier"),
        ("advanced", "Personalization", "Customized guest preference"),
        ("advanced", "Guest profile", "Stored preference record"),
    ],
}


def _cefr_band(cefr_level: str) -> str:
    """Map CEFR level to content complexity band for scenario selection."""
    if cefr_level in ("A1", "A2"):
        return "basic"
    if cefr_level in ("B1", "B2"):
        return "intermediate"
    return "advanced"


def _require(d: dict, key: str, context: str) -> Any:
    """Explicit lookup—no fallback. Raises KeyError if content pool key is missing."""
    if key not in d:
        raise KeyError(f"Missing {context} for content pool key: {key}")
    return d[key]


def _filter_scenarios_by_band(
    scenarios: List[Dict[str, Any]], cefr_level: str
) -> List[Dict[str, Any]]:
    """Filter scenario list by CEFR band; fallback to intermediate or all if no match."""
    if not scenarios:
        return []
    band = _cefr_band(cefr_level)
    by_band = [s for s in scenarios if isinstance(s, dict) and s.get("cefr_band") == band]
    if by_band:
        return by_band
    fallback = [s for s in scenarios if isinstance(s, dict) and s.get("cefr_band") == "intermediate"]
    return fallback if fallback else scenarios


class QuestionBankGenerator:
    """Generate comprehensive question bank for all 30 departments with CEFR levels"""

    def __init__(self):
        self.questions = []
        self.question_counter = 1
        self._scenario_idx: Dict[str, int] = {}
        self._scenario_order: Dict[str, List[Dict[str, Any]]] = {}

    def _pick_scenario(self, scenarios: List[Dict[str, Any]], tracker_key: str) -> Dict[str, Any]:
        """Round-robin selection: shuffles once, then cycles through all items before repeating."""
        if tracker_key not in self._scenario_order:
            shuffled = list(scenarios)
            random.shuffle(shuffled)
            self._scenario_order[tracker_key] = shuffled
        order = self._scenario_order[tracker_key]
        idx = self._scenario_idx.get(tracker_key, 0) % len(order)
        self._scenario_idx[tracker_key] = idx + 1
        return order[idx]

    def generate_all_questions(self) -> List[Dict[str, Any]]:
        """Generate 3,000 questions across 30 departments (100 per department)"""

        for operation, depts in DEPARTMENTS.items():
            for dept_name in depts:
                self._generate_department_questions(operation, dept_name)

        return self.questions

    def _generate_department_questions(self, operation: str, dept_name: str):
        """Generate 100 questions for a department with CEFR distribution"""

        division = operation  # hotel or marine
        if dept_name not in DEPARTMENT_TO_CONTENT_POOL:
            raise ValueError(f"No content pool mapping for department: {dept_name}")
        scenario_key = DEPARTMENT_TO_CONTENT_POOL[dept_name]
        dept_code = dept_name[:3].upper().replace(" ", "").replace("/", "") or "GEN"

        # Build (module, cefr_level) pairs from MODULE_CEFR_DISTRIBUTION
        for module, cefr_counts in MODULE_CEFR_DISTRIBUTION.items():
            for cefr_level, count in cefr_counts.items():
                for i in range(count):
                    scenario_id = random.randint(1, 10)

                    if module == "Listening":
                        question = self._generate_listening_question(
                            division, dept_name, dept_code, scenario_key, scenario_id, cefr_level, i + 1
                        )
                    elif module == "TimeNumbers":
                        question = self._generate_time_numbers_question(
                            division, dept_name, dept_code, scenario_key, scenario_id, cefr_level, i + 1
                        )
                    elif module == "Grammar":
                        question = self._generate_grammar_question(
                            division, dept_name, dept_code, scenario_key, scenario_id, cefr_level, i + 1
                        )
                    elif module == "Vocabulary":
                        question = self._generate_vocabulary_question(
                            division, dept_name, dept_code, scenario_key, scenario_id, cefr_level, i + 1
                        )
                    elif module == "Reading":
                        question = self._generate_reading_question(
                            division, dept_name, dept_code, scenario_key, scenario_id, cefr_level, i + 1
                        )
                    elif module == "Speaking":
                        question = self._generate_speaking_question(
                            division, dept_name, dept_code, scenario_key, scenario_id, cefr_level, i + 1
                        )

                    self.questions.append(question)

    def _generate_listening_question(self, division: str, dept_name: str,
                                    dept_code: str, scenario_key: str, scenario_id: int,
                                    cefr_level: str, q_num: int) -> Dict[str, Any]:
        """Generate realistic listening question"""

        question_id = f"{division}_{dept_code}_L_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        listening_scenarios = self._get_listening_scenarios(scenario_key, cefr_level)
        scenario = random.choice(listening_scenarios)

        difficulty = random.choice(["easy", "medium", "hard"])
        points = {"easy": 3, "medium": 4, "hard": 5}[difficulty]

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "listening",
            "cefr_level": cefr_level,
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

    def _generate_time_numbers_question(self, division: str, dept_name: str,
                                       dept_code: str, scenario_key: str, scenario_id: int,
                                       cefr_level: str, q_num: int) -> Dict[str, Any]:
        """Generate time and numbers question"""

        question_id = f"{division}_{dept_code}_TN_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        time_number_scenarios = self._get_time_numbers_scenarios(scenario_key, cefr_level)
        scenario = random.choice(time_number_scenarios)

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "time_numbers",
            "cefr_level": cefr_level,
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

    def _generate_grammar_question(self, division: str, dept_name: str,
                                  dept_code: str, scenario_key: str, scenario_id: int,
                                  cefr_level: str, q_num: int) -> Dict[str, Any]:
        """Generate grammar question"""

        question_id = f"{division}_{dept_code}_G_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        grammar_scenarios = self._get_grammar_scenarios(scenario_key, cefr_level)
        scenario = random.choice(grammar_scenarios)

        difficulty = random.choice(["easy", "medium", "hard"])
        points = {"easy": 3, "medium": 4, "hard": 5}[difficulty]

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "grammar",
            "cefr_level": cefr_level,
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

    def _generate_vocabulary_question(self, division: str, dept_name: str,
                                     dept_code: str, scenario_key: str, scenario_id: int,
                                     cefr_level: str, q_num: int) -> Dict[str, Any]:
        """Generate vocabulary matching question"""

        question_id = f"{division}_{dept_code}_V_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        vocab_scenarios = self._get_vocabulary_scenarios(scenario_key, cefr_level)
        scenario = self._pick_scenario(vocab_scenarios, f"{scenario_key}|vocab|{cefr_level}")

        # Loader expects options and correct_answer for category_match
        options = scenario.get("categories", {
            "terms": scenario.get("terms", []),
            "definitions": scenario.get("definitions", [])
        })
        correct_answer = scenario.get("correct_answer") or ", ".join(
            f"{k}: {v}" for k, v in (scenario.get("matches", {}) or {}).items()
        )

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "vocabulary",
            "cefr_level": cefr_level,
            "scenario_id": scenario_id,
            "module": "Vocabulary",
            "difficulty": "medium",
            "points": 4,
            "question_type": "category_match",
            "question_text": scenario["question"],
            "options": options,
            "correct_answer": correct_answer,
            "terms": scenario.get("terms"),
            "definitions": scenario.get("definitions"),
            "correct_matches": scenario.get("matches"),
            "explanation": scenario.get("explanation")
        }

    def _generate_reading_question(self, division: str, dept_name: str,
                                  dept_code: str, scenario_key: str, scenario_id: int,
                                  cefr_level: str, q_num: int) -> Dict[str, Any]:
        """Generate reading comprehension question"""

        question_id = f"{division}_{dept_code}_R_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        reading_scenarios = self._get_reading_scenarios(scenario_key, cefr_level)
        scenario = self._pick_scenario(reading_scenarios, f"{scenario_key}|reading|{cefr_level}")

        difficulty = random.choice(["medium", "hard"])
        points = {"medium": 4, "hard": 5}[difficulty]

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "reading",
            "cefr_level": cefr_level,
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

    def _generate_speaking_question(self, division: str, dept_name: str,
                                   dept_code: str, scenario_key: str, scenario_id: int,
                                   cefr_level: str, q_num: int) -> Dict[str, Any]:
        """Generate speaking question"""

        question_id = f"{division}_{dept_code}_S_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        speaking_scenarios = self._get_speaking_scenarios(scenario_key, cefr_level)
        scenario = self._pick_scenario(speaking_scenarios, f"{scenario_key}|speaking|{cefr_level}")

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "speaking",
            "cefr_level": cefr_level,
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

    def _get_listening_scenarios(self, scenario_key: str, cefr_level: str) -> List[Dict[str, Any]]:
        """Get listening scenarios based on department and CEFR level."""

        scenarios = {
            "Front Desk": [
                {
                    "cefr_band": "basic",
                    "question": "What time did the guest request for the reservation?",
                    "audio": "Good evening. How may I help you? I'd like to book a table for tonight. Of course. How many in your party? Six. And what time would you prefer? Seven-thirty, please.",
                    "options": ["6:00 PM", "6:30 PM", "7:00 PM", "7:30 PM"],
                    "correct": "7:30 PM",
                    "explanation": "The guest says 'seven-thirty' which is 7:30 PM."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the room number mentioned in the complaint?",
                    "audio": "Guest Services, how can I assist you? Excuse me, I have a problem. The air conditioning in my room is not working at all. It's been running nonstop or not at all. I'm sorry to hear that. May I have your room number? It's room nine-three-four-two.",
                    "options": ["9234", "9324", "9342", "9432"],
                    "correct": "9342",
                    "explanation": "The room number is clearly stated as nine-three-four-two (9342)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "According to the tour guide, when will the group return to the ship?",
                    "audio": "The tour will take approximately six hours. We'll visit the botanical gardens first, then the colonial district, and finally the beach. We'll be back at the ship by four-fifteen PM, so you'll have plenty of time before departure.",
                    "options": ["3:45 PM", "4:00 PM", "4:15 PM", "4:45 PM"],
                    "correct": "4:15 PM",
                    "explanation": "The return time is stated as four-fifteen PM (4:15 PM)."
                }
            ],
            "Housekeeping": [
                {
                    "cefr_band": "basic",
                    "question": "How many towels did the guest request?",
                    "audio": "Housekeeping, this is cabin seven-eight-five-six. Yes, how can I help? I need some extra towels, please. How many would you like? Three towels, please.",
                    "options": ["2 towels", "3 towels", "4 towels", "5 towels"],
                    "correct": "3 towels",
                    "explanation": "The guest requests three towels."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What item in the room needs to be repaired?",
                    "audio": "Maintenance, how can I help? I need to report an issue. The bathroom light in room eight-five-two-three keeps flickering. I think it needs replacing. I'll send someone up right away.",
                    "options": ["TV", "AC", "Light", "Toilet"],
                    "correct": "Light",
                    "explanation": "The issue is specifically about the 'bathroom light' needing replacement."
                },
                {
                    "cefr_band": "advanced",
                    "question": "When does the guest want their cabin cleaned?",
                    "audio": "We're going to be in the room until two PM for a video call. Could you please clean our cabin after that time? Of course, ma'am. I'll come by after two.",
                    "options": ["Before 2 PM", "After 2 PM", "At 2 PM exactly", "Before noon"],
                    "correct": "After 2 PM",
                    "explanation": "The guest requests cleaning 'after two PM'."
                }
            ],
            "Food & Beverage": [
                {
                    "cefr_band": "basic",
                    "question": "What food allergy does the guest mention?",
                    "audio": "Welcome. Do you have any allergies we should know about? Yes. I am allergic to shellfish. I need to avoid shrimp, lobster, and crab. I'll let the chef know right away.",
                    "options": ["Nuts", "Dairy", "Shellfish", "Gluten"],
                    "correct": "Shellfish",
                    "explanation": "The guest says shellfish."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many people is the reservation for?",
                    "audio": "Restaurant reservations, how can I help? I'd like to make a reservation for this evening. Certainly. How many in your party? A party of eight. And what time? Six-forty-five would be perfect.",
                    "options": ["6 guests", "7 guests", "8 guests", "9 guests"],
                    "correct": "8 guests",
                    "explanation": "The reservation is for 'a party of eight' (8 guests)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How old is the child who needs a high chair?",
                    "audio": "Table for four? Yes, and we have a baby with us. No problem. We have high chairs. How old is your little one? She's eighteen months old. Can we get a high chair please? Of course.",
                    "options": ["8 months", "12 months", "18 months", "24 months"],
                    "correct": "18 months",
                    "explanation": "The child is described as 'eighteen-month-old'."
                }
            ],
            "Bar Service": [
                {
                    "cefr_band": "basic",
                    "question": "How many drinks did the guest order in total?",
                    "audio": "What can I get you? I'd like two mojitos for my friends and one margarita for me. So that's two mojitos and one margarita. Coming right up.",
                    "options": ["2 drinks", "3 drinks", "4 drinks", "5 drinks"],
                    "correct": "3 drinks",
                    "explanation": "Two plus one equals 3 drinks."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "When does happy hour end?",
                    "audio": "Do you have happy hour? Yes. Our happy hour runs from five PM to seven PM daily. Drinks are half price during that time. Great, so it ends at seven. That's correct.",
                    "options": ["6 PM", "6:30 PM", "7 PM", "8 PM"],
                    "correct": "7 PM",
                    "explanation": "Happy hour ends at 'seven PM'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How much does the premium beverage package cost per day?",
                    "audio": "I'm interested in the beverage package. We have the standard and the premium. What's the difference? The premium includes top-shelf spirits and specialty cocktails. And the price? It costs sixty-five dollars per person per day.",
                    "options": ["$55", "$60", "$65", "$70"],
                    "correct": "$65",
                    "explanation": "The premium package costs 'sixty-five dollars' ($65)."
                }
            ],
            "Guest Services": [
                {
                    "cefr_band": "basic",
                    "question": "On which deck should guests meet for the excursion bus?",
                    "audio": "Where do we meet for the shore excursion? The bus will pick you up at nine-fifteen AM. Which deck? Deck four, by the gangway. Thank you.",
                    "options": ["Deck 2", "Deck 3", "Deck 4", "Deck 5"],
                    "correct": "Deck 4",
                    "explanation": "Deck four."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What time is the spa massage scheduled?",
                    "audio": "I've booked your massage for this afternoon. What time is it? Three-thirty PM in the spa on deck twelve. Perfect, I'll be there.",
                    "options": ["2:30 PM", "3:00 PM", "3:30 PM", "4:00 PM"],
                    "correct": "3:30 PM",
                    "explanation": "The massage time is 'three-thirty PM' (3:30 PM)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the daily price for the unlimited WiFi package?",
                    "audio": "I need WiFi for my laptop. We have several packages. What about unlimited? Our unlimited WiFi package allows you to stream and work without limits. How much? Twenty-five dollars per day per device.",
                    "options": ["$20", "$25", "$30", "$35"],
                    "correct": "$25",
                    "explanation": "The unlimited WiFi package costs 'twenty-five dollars' ($25)."
                }
            ],
            "Cabin Service": [
                {
                    "cefr_band": "basic",
                    "question": "By what time does the guest want breakfast delivered?",
                    "audio": "Room service. I'd like to order breakfast for tomorrow morning. Certainly. What cabin? Cabin six-seven-eight-nine. And when would you like it? By eight-thirty AM, please. We have an early excursion.",
                    "options": ["8:00 AM", "8:15 AM", "8:30 AM", "9:00 AM"],
                    "correct": "8:30 AM",
                    "explanation": "Delivery time requested is 'eight-thirty AM' (8:30 AM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the problem reported in the cabin?",
                    "audio": "This is cabin five-four-three-two. I have an issue. What seems to be the problem? The TV remote control isn't working properly. I can't change channels. I'll send someone up with a replacement right away.",
                    "options": ["TV screen broken", "Remote not working", "No channels", "Sound issue"],
                    "correct": "Remote not working",
                    "explanation": "The problem is the 'TV remote control isn't working'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "By what time must the anniversary setup be ready?",
                    "audio": "We're celebrating our anniversary tonight. Wonderful. We can arrange something special. Yes, please. What cabin? Eight-seven-six-five. We need champagne, roses, and chocolates. By when? By six PM. We have dinner reservations at seven.",
                    "options": ["5 PM", "5:30 PM", "6 PM", "6:30 PM"],
                    "correct": "6 PM",
                    "explanation": "The setup must be ready 'by six PM' (6 PM)."
                }
            ],
            "Auxiliary Service": [
                {
                    "cefr_band": "basic",
                    "question": "How many additional chairs are needed for the event?",
                    "audio": "We have the wedding reception on the main deck tomorrow. Do we have enough seating? Let me check. We're short. Can you arrange for more chairs? How many do you need? Fifty additional chairs should do it. I'll have them brought up right away.",
                    "options": ["40 chairs", "45 chairs", "50 chairs", "55 chairs"],
                    "correct": "50 chairs",
                    "explanation": "The request is for 'fifty additional chairs'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many extra servers are needed for the captain's dinner?",
                    "audio": "The captain's dinner tonight is fully booked. We're going to need more staff. How many extra servers? I'd say we'll need three extra servers to handle the tables. I'll arrange that with HR.",
                    "options": ["2 servers", "3 servers", "4 servers", "5 servers"],
                    "correct": "3 servers",
                    "explanation": "The requirement is 'three extra servers'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the delivery deadline for the priority request?",
                    "audio": "This is a priority request. We're running low on water bottles for the excursion. We need a delivery as soon as possible. What's the latest you can wait? We need it by eleven-forty-five AM today. The buses leave at noon. Understood. I'll prioritize it.",
                    "options": ["11:15 AM", "11:30 AM", "11:45 AM", "12:00 PM"],
                    "correct": "11:45 AM",
                    "explanation": "The deadline is 'eleven-forty-five AM' (11:45 AM)."
                }
            ],
            "Laundry": [
                {
                    "cefr_band": "basic",
                    "question": "By what time does the guest need their laundry back?",
                    "audio": "I need these clothes for tonight's formal dinner. Is express service available? Yes, we can do express. When do you need them back? I need them back by two PM today. I'll mark it urgent.",
                    "options": ["1 PM", "1:30 PM", "2 PM", "2:30 PM"],
                    "correct": "2 PM",
                    "explanation": "The items must be returned 'by two PM' (2 PM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many items is the guest sending for cleaning?",
                    "audio": "I'm sending down some items for laundering. What do you have? Seven shirts and three pairs of pants. So that's ten items total. Yes, that's correct.",
                    "options": ["9 items", "10 items", "11 items", "12 items"],
                    "correct": "10 items",
                    "explanation": "Seven shirts plus three pants equals 10 items total."
                },
                {
                    "cefr_band": "advanced",
                    "question": "To which cabin should the dry-cleaned gown be delivered?",
                    "audio": "I dropped off my evening gown for dry cleaning yesterday. It should be ready. What's your cabin number? Cabin four-five-six-seven. I'll have it sent up within the hour.",
                    "options": ["4576", "4657", "4567", "4765"],
                    "correct": "4567",
                    "explanation": "The cabin number is 'four-five-six-seven' (4567)."
                }
            ],
            "Photo": [
                {
                    "cefr_band": "basic",
                    "question": "How much does the deluxe photo package cost?",
                    "audio": "I'm interested in a photo package. We have the standard and deluxe. What's in the deluxe? Fifteen digital photos plus prints. And the price? One hundred twenty dollars. Great, I'll take that one.",
                    "options": ["$100", "$110", "$120", "$130"],
                    "correct": "$120",
                    "explanation": "The deluxe package costs 'one hundred twenty dollars' ($120)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What time is the family portrait session scheduled?",
                    "audio": "I booked a family portrait. Let me check. Your session is on deck twelve. What time? Ten-thirty AM. We'll need to be there ten minutes early.",
                    "options": ["10:00 AM", "10:15 AM", "10:30 AM", "11:00 AM"],
                    "correct": "10:30 AM",
                    "explanation": "The session time is 'ten-thirty AM' (10:30 AM)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How many copies of the photo did the guest order?",
                    "audio": "I love this photo from last night's dinner. I'd like to get some prints. How many copies? Twelve copies, please. And what size? Eight by ten. Coming right up.",
                    "options": ["10 copies", "11 copies", "12 copies", "15 copies"],
                    "correct": "12 copies",
                    "explanation": "The order is for 'twelve copies'."
                }
            ],
            "Provisions": [
                {
                    "cefr_band": "basic",
                    "question": "How much fresh produce is needed for tomorrow's resupply?",
                    "audio": "Provisions for tomorrow. What do we need? The galley is low on fresh produce. How much? Two hundred pounds. Fruit and vegetables. I'll add it to the order.",
                    "options": ["150 lbs", "200 lbs", "250 lbs", "300 lbs"],
                    "correct": "200 lbs",
                    "explanation": "The order is for 'two hundred pounds'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many cases of bottled water should be added to the supply order?",
                    "audio": "We're running low on bottled water for excursions. How many cases do we need? Let me check the inventory. We should add forty-eight cases to the next supply order. Got it.",
                    "options": ["38 cases", "43 cases", "48 cases", "58 cases"],
                    "correct": "48 cases",
                    "explanation": "The order is for 'forty-eight cases'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What time is the supply truck scheduled to arrive?",
                    "audio": "When does the supply truck get here? It's scheduled for seven-thirty AM at the port. We need to have the dock crew ready by seven. Understood.",
                    "options": ["7:00 AM", "7:15 AM", "7:30 AM", "8:00 AM"],
                    "correct": "7:30 AM",
                    "explanation": "Arrival time is 'seven-thirty AM' (7:30 AM)."
                }
            ],
            "Deck Department": [
                {
                    "cefr_band": "basic",
                    "question": "What is the current heading reported by the bridge?",
                    "audio": "Bridge to deck. Deck. What's our heading? Our current heading is two-eight-five degrees. Two-eight-five, copy.",
                    "options": ["258°", "285°", "528°", "582°"],
                    "correct": "285°",
                    "explanation": "The heading is 'two-eight-five degrees' (285°)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "To which muster station should crew report for the safety drill?",
                    "audio": "Attention all crew members. Safety drill in fifteen minutes. Report to your assigned muster stations. Deck team, that's muster station six. Repeat, muster station six.",
                    "options": ["Station 4", "Station 5", "Station 6", "Station 7"],
                    "correct": "Station 6",
                    "explanation": "Crew must report to 'muster station six'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the estimated time of arrival to port?",
                    "audio": "Port authority, this is the vessel. What's your ETA? Estimated time of arrival to port is zero-six-fifteen hours. Zero-six-fifteen. We'll have the berth ready.",
                    "options": ["0545", "0600", "0615", "0630"],
                    "correct": "0615",
                    "explanation": "ETA is 'zero-six-fifteen hours' (0615)."
                }
            ],
            "Engine Department": [
                {
                    "cefr_band": "basic",
                    "question": "What RPM is the main engine currently running at?",
                    "audio": "Engine control room to bridge. Go ahead. Main engine status? We're running steady. Current RPM? Four hundred fifty. Four-five-zero, copy.",
                    "options": ["400", "425", "450", "475"],
                    "correct": "450",
                    "explanation": "RPM is 'four hundred fifty' (450)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What percentage of fuel capacity does the tank currently show?",
                    "audio": "Can you give me a fuel status report? Current fuel status shows the main tank at seventy-five percent capacity. That should get us to the next port. Good.",
                    "options": ["65%", "70%", "75%", "80%"],
                    "correct": "75%",
                    "explanation": "Fuel level is 'seventy-five percent' (75%)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "In how many operating hours is the next maintenance due?",
                    "audio": "When is the next engine service due? According to the schedule, next maintenance is due in one hundred twenty operating hours. Better order the parts now.",
                    "options": ["100 hours", "110 hours", "120 hours", "130 hours"],
                    "correct": "120 hours",
                    "explanation": "Service is due in 'one hundred twenty operating hours'."
                }
            ],
            "Medical Department": [
                {
                    "cefr_band": "basic",
                    "question": "Which cabin requested the sick call?",
                    "audio": "Medical team, we have a sick call. Which cabin? Cabin forty-two fourteen. Guest says she has a headache and feels dizzy. On our way.",
                    "options": ["4212", "4214", "4216", "4224"],
                    "correct": "4214",
                    "explanation": "The cabin number is 'forty-two fourteen' (4214)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the patient's systolic blood pressure reading?",
                    "audio": "Nurse, can you report the vitals? Blood pressure is one-twenty over eighty. Pulse normal. Good, the systolic looks fine.",
                    "options": ["110", "115", "120", "130"],
                    "correct": "120",
                    "explanation": "Systolic is 'one-twenty' (120)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "At what times should the medication be administered daily?",
                    "audio": "Doctor, when should the patient take this medication? Administer at eight AM and eight PM daily. Twice a day, twelve hours apart. I'll note it on the chart.",
                    "options": ["6 AM and 6 PM", "8 AM and 8 PM", "10 AM and 10 PM", "12 PM and 12 AM"],
                    "correct": "8 AM and 8 PM",
                    "explanation": "Dosing times are 'eight AM and eight PM' (8:00 and 20:00)."
                }
            ],
            "Security Department": [
                {
                    "cefr_band": "basic",
                    "question": "On which deck was the suspicious person reported?",
                    "audio": "Security, we have a report. Go ahead. A guest says they saw someone acting oddly near the pool. Which deck? Deck nine. Sending a team now.",
                    "options": ["Deck 7", "Deck 8", "Deck 9", "Deck 10"],
                    "correct": "Deck 9",
                    "explanation": "The alert is for 'deck nine'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How often should security complete patrol rounds?",
                    "audio": "What's the patrol schedule for tonight? Security team should complete full rounds every forty-five minutes. That's the standard for overnight. Understood.",
                    "options": ["30 minutes", "35 minutes", "45 minutes", "60 minutes"],
                    "correct": "45 minutes",
                    "explanation": "Rounds are 'every forty-five minutes'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "In which row of the theater was the wallet found?",
                    "audio": "Lost and found here. A guest just turned in a wallet. Where was it found? In the main theater. Row twelve, seat eight. I'll log it and contact the owner.",
                    "options": ["Row 10", "Row 11", "Row 12", "Row 13"],
                    "correct": "Row 12",
                    "explanation": "The wallet was in 'row twelve'."
                }
            ],
            "Table Games": [
                {
                    "cefr_band": "basic",
                    "question": "What is the minimum bet at this table?",
                    "audio": "What are the table limits? Twenty-five dollars minimum, five hundred maximum. So I can start with twenty-five? That's correct.",
                    "options": ["$20", "$25", "$30", "$50"],
                    "correct": "$25",
                    "explanation": "Minimum bet is 'twenty-five dollars' ($25)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "When does poker tournament registration close today?",
                    "audio": "Is it too late to sign up for the poker tournament? Registration closes at one-forty-five PM. You have about twenty minutes. I'll sign up now.",
                    "options": ["1:15 PM", "1:30 PM", "1:45 PM", "2:00 PM"],
                    "correct": "1:45 PM",
                    "explanation": "Registration closes at 'one-forty-five PM' (1:45 PM)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How much money did the guest want to exchange for chips?",
                    "audio": "Cage, I'd like to buy chips. How much? Three hundred dollars, please. Three hundred. Here are your chips. Thank you.",
                    "options": ["$200", "$250", "$300", "$350"],
                    "correct": "$300",
                    "explanation": "The amount is 'three hundred dollars' ($300)."
                }
            ],
            "Slot Machines": [
                {
                    "cefr_band": "basic",
                    "question": "What is the current amount of the progressive jackpot?",
                    "audio": "How much is the jackpot on that machine? The current progressive jackpot stands at twenty-eight thousand five hundred dollars. It's been growing all week. Wow, that's huge.",
                    "options": ["$25,800", "$28,500", "$28,800", "$30,500"],
                    "correct": "$28,500",
                    "explanation": "Jackpot is 'twenty-eight thousand five hundred dollars' ($28,500)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "Which slot machine has a malfunction?",
                    "audio": "Technical team, we have a problem. Which machine? Slot machine one-four-seven. The display went blank and it's not paying out. I'll send someone over.",
                    "options": ["Machine 117", "Machine 147", "Machine 174", "Machine 417"],
                    "correct": "Machine 147",
                    "explanation": "The machine is 'one-four-seven' (147)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What amount does the supervisor need to verify for the winner payout?",
                    "audio": "I need a supervisor at machine 203. We have a jackpot winner. What's the payout? Three thousand two hundred fifty dollars. I need verification. On my way.",
                    "options": ["$2,350", "$3,150", "$3,250", "$3,550"],
                    "correct": "$3,250",
                    "explanation": "Payout is 'three thousand two hundred fifty dollars' ($3,250)."
                }
            ],
            "Casino Services": [
                {
                    "cefr_band": "basic",
                    "question": "How many points did the guest earn to reach Gold status?",
                    "audio": "Let me check your players club status. You've been playing a lot. Congratulations! You've reached Gold membership. How many points? Five thousand points. You get free drinks and priority boarding now.",
                    "options": ["4,000", "4,500", "5,000", "5,500"],
                    "correct": "5,000",
                    "explanation": "Points accumulated are 'five thousand' (5,000)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the entry fee for the tournament?",
                    "audio": "I'm interested in the poker tournament. What's the buy-in? One hundred fifty dollars. You get one rebuy allowed. So one-fifty to enter? That's correct.",
                    "options": ["$100", "$125", "$150", "$175"],
                    "correct": "$150",
                    "explanation": "Entry fee is 'one hundred fifty dollars' ($150)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How much does the guest have in complimentary credits?",
                    "audio": "Can you check my comp balance? Your account shows eighty-five dollars in complimentary credits available. You can use them at any restaurant or for shore excursions. Eighty-five dollars. Great, thank you.",
                    "options": ["$75", "$80", "$85", "$90"],
                    "correct": "$85",
                    "explanation": "Comp credits are 'eighty-five dollars' ($85)."
                }
            ]
        }

        raw = _require(scenarios, scenario_key, "listening scenarios")
        return _filter_scenarios_by_band(raw, cefr_level)

    def _get_time_numbers_scenarios(self, scenario_key: str, cefr_level: str) -> List[Dict[str, Any]]:
        """Get time and numbers scenarios"""

        scenarios = {
            "Front Desk": [
                {"cefr_band": "basic", "question": "Check-in begins at ___ AM.", "context": "7:00 AM", "answer": "7:00", "explanation": "Standard cruise check-in time."},
                {"cefr_band": "intermediate", "question": "Your cabin number is ___.", "context": "Suite 8254", "answer": "8254", "explanation": "Four-digit cabin number."},
                {"cefr_band": "advanced", "question": "Ship departs at ___ PM sharp.", "context": "5:30 PM", "answer": "5:30", "explanation": "Departure time must be exact."}
            ],
            "Housekeeping": [
                {"cefr_band": "basic", "question": "Daily cabin cleaning between ___ AM and 3 PM.", "context": "9:00 AM - 3:00 PM", "answer": "9:00", "explanation": "Standard housekeeping hours."},
                {"cefr_band": "intermediate", "question": "Turndown service starts at ___ PM.", "context": "6:00 PM", "answer": "6:00", "explanation": "Evening service timing."}
            ],
            "Food & Beverage": [
                {"cefr_band": "basic", "question": "Breakfast served until ___ AM.", "context": "10:30 AM", "answer": "10:30", "explanation": "Breakfast service end time."},
                {"cefr_band": "intermediate", "question": "Dinner reservations for party of ___.", "context": "8 people", "answer": "8", "explanation": "Group size for reservation."}
            ],
            "Bar Service": [
                {"cefr_band": "basic", "question": "Happy hour: 5 PM to ___ PM.", "context": "7:00 PM", "answer": "7:00", "explanation": "Two-hour happy hour period."},
                {"cefr_band": "intermediate", "question": "Premium cocktails are $___ each.", "context": "$15", "answer": "15", "explanation": "Beverage pricing."}
            ],
            "Guest Services": [
                {"cefr_band": "basic", "question": "Shore excursion departs at ___ AM.", "context": "9:15 AM", "answer": "9:15", "explanation": "Excursion departure time."},
                {"cefr_band": "intermediate", "question": "WiFi package: $___ per day.", "context": "$25", "answer": "25", "explanation": "Internet package pricing."}
            ],
            "Cabin Service": [
                {"cefr_band": "basic", "question": "Room service available ___ hours.", "context": "24 hours", "answer": "24", "explanation": "Round-the-clock availability."},
                {"cefr_band": "intermediate", "question": "Breakfast delivery by ___ AM.", "context": "8:00 AM", "answer": "8:00", "explanation": "Morning service timing."}
            ],
            "Auxiliary Service": [
                {"cefr_band": "basic", "question": "Supply delivery by ___ AM.", "context": "10:00 AM", "answer": "10:00", "explanation": "Morning supply schedule."},
                {"cefr_band": "intermediate", "question": "Event setup requires ___ hours notice.", "context": "4 hours", "answer": "4", "explanation": "Advance notice requirement."}
            ],
            "Laundry": [
                {"cefr_band": "basic", "question": "Express service within ___ hours.", "context": "4 hours", "answer": "4", "explanation": "Rush service timeframe."},
                {"cefr_band": "intermediate", "question": "Standard turnaround: ___ hours.", "context": "24 hours", "answer": "24", "explanation": "Normal processing time."}
            ],
            "Photo": [
                {"cefr_band": "basic", "question": "Photo prints ready in ___ hours.", "context": "2 hours", "answer": "2", "explanation": "Photo processing time."},
                {"cefr_band": "intermediate", "question": "Deluxe package: $___ for 20 photos.", "context": "$150", "answer": "150", "explanation": "Package pricing."}
            ],
            "Provisions": [
                {"cefr_band": "basic", "question": "Order ___ cases of water.", "context": "50 cases", "answer": "50", "explanation": "Bulk supply quantity."},
                {"cefr_band": "intermediate", "question": "Supply arrives at ___ AM.", "context": "7:00 AM", "answer": "7:00", "explanation": "Early morning delivery."}
            ],
            "Deck Department": [
                {"cefr_band": "basic", "question": "Current heading: ___ degrees.", "context": "270 degrees", "answer": "270", "explanation": "Compass heading direction."},
                {"cefr_band": "intermediate", "question": "Distance to port: ___ nautical miles.", "context": "185 nm", "answer": "185", "explanation": "Maritime distance measurement."}
            ],
            "Engine Department": [
                {"cefr_band": "basic", "question": "Engine running at ___ RPM.", "context": "450 RPM", "answer": "450", "explanation": "Engine rotation speed."},
                {"cefr_band": "intermediate", "question": "Oil change every ___ hours.", "context": "500 hours", "answer": "500", "explanation": "Maintenance interval."}
            ],
            "Medical Department": [
                {"cefr_band": "basic", "question": "Sick call: cabin ___.", "context": "Cabin 2148", "answer": "2148", "explanation": "Guest cabin number for medical visit."},
                {"cefr_band": "intermediate", "question": "Temperature reading: ___°C.", "context": "37.2°C", "answer": "37.2", "explanation": "Patient temperature in Celsius."}
            ],
            "Security Department": [
                {"cefr_band": "basic", "question": "Patrol rounds every ___ minutes.", "context": "45 minutes", "answer": "45", "explanation": "Security patrol frequency."},
                {"cefr_band": "intermediate", "question": "Curfew for minors: ___ PM.", "context": "11:00 PM", "answer": "11:00", "explanation": "Youth curfew policy."}
            ],
            "Table Games": [
                {"cefr_band": "basic", "question": "Minimum bet: $___.", "context": "$25", "answer": "25", "explanation": "Table minimum wager."},
                {"cefr_band": "intermediate", "question": "Blackjack pays ___ to 2.", "context": "3 to 2", "answer": "3", "explanation": "Standard blackjack payout."}
            ],
            "Slot Machines": [
                {"cefr_band": "basic", "question": "Jackpot: $___,000.", "context": "$35,000", "answer": "35", "explanation": "Progressive jackpot amount."},
                {"cefr_band": "intermediate", "question": "Machine ___ needs service.", "context": "Machine 247", "answer": "247", "explanation": "Equipment identification."}
            ],
            "Casino Services": [
                {"cefr_band": "basic", "question": "Tournament buy-in: $___.", "context": "$100", "answer": "100", "explanation": "Entry fee amount."},
                {"cefr_band": "intermediate", "question": "Gold tier at ___,000 points.", "context": "5,000 points", "answer": "5", "explanation": "Membership threshold."}
            ]
        }

        raw = _require(scenarios, scenario_key, "time/numbers scenarios")
        return _filter_scenarios_by_band(raw, cefr_level)

    def _get_grammar_scenarios(self, scenario_key: str, cefr_level: str) -> List[Dict[str, Any]]:
        """Get grammar scenarios filtered by CEFR band"""

        # Universal grammar questions applicable to all departments
        grammar_pool = [
            {"cefr_band": "basic", "question": "___ I help you with your luggage?", "options": ["May", "Do", "Will", "Am"], "correct": "May", "explanation": "Use 'May' for polite offers of assistance."},
            {"cefr_band": "basic", "question": "The guest ___ arrived at the port this morning.", "options": ["have", "has", "had", "having"], "correct": "has", "explanation": "Use 'has' with singular subject 'guest'."},
            {"cefr_band": "basic", "question": "The restaurant ___ open from 6 PM to 10 PM.", "options": ["is", "are", "was", "been"], "correct": "is", "explanation": "Use 'is' with singular subject 'restaurant'."},
            {"cefr_band": "basic", "question": "We ___ serving dinner in the main dining room.", "options": ["is", "am", "are", "been"], "correct": "are", "explanation": "Use 'are' with plural subject 'we'."},
            {"cefr_band": "intermediate", "question": "If you need anything, please ___ hesitate to call.", "options": ["not", "don't", "doesn't", "won't"], "correct": "don't", "explanation": "Use 'don't' in imperative negative sentences."},
            {"cefr_band": "intermediate", "question": "___ you like to make a reservation?", "options": ["Would", "Will", "Are", "Do"], "correct": "Would", "explanation": "Use 'Would' for polite offers and requests."},
            {"cefr_band": "intermediate", "question": "Could you please ___ me to the spa?", "options": ["direct", "directing", "directed", "direction"], "correct": "direct", "explanation": "Use base form verb after 'please' in requests."},
            {"cefr_band": "intermediate", "question": "The ship ___ at the port tomorrow morning.", "options": ["arrive", "arrives", "arriving", "arrived"], "correct": "arrives", "explanation": "Use present tense for scheduled future events."},
            {"cefr_band": "advanced", "question": "All crew members ___ attend the safety briefing.", "options": ["must", "can", "might", "could"], "correct": "must", "explanation": "Use 'must' for strong obligations and requirements."},
            {"cefr_band": "advanced", "question": "The guests ___ enjoying the entertainment show.", "options": ["is", "am", "are", "be"], "correct": "are", "explanation": "Use 'are' with plural subject 'guests'."},
            {"cefr_band": "advanced", "question": "I ___ be happy to assist you with that.", "options": ["will", "shall", "would", "should"], "correct": "would", "explanation": "Use 'would' to express willingness politely."},
            {"cefr_band": "advanced", "question": "The captain ___ announced our arrival time.", "options": ["have", "has", "had", "having"], "correct": "has", "explanation": "Use 'has' with singular subject in present perfect."}
        ]

        return _filter_scenarios_by_band(grammar_pool, cefr_level)

    def _get_vocabulary_scenarios(self, scenario_key: str, cefr_level: str) -> List[Dict[str, Any]]:
        """Build vocabulary matching scenarios programmatically from VOCAB_TERM_POOLS.

        Creates multiple non-overlapping 4-term subsets per CEFR band so the
        assessment engine's content-key deduplication sees each as unique.
        """
        if scenario_key not in VOCAB_TERM_POOLS:
            raise KeyError(f"Missing vocabulary term pool for content pool key: {scenario_key}")

        pool = VOCAB_TERM_POOLS[scenario_key]
        band = _cefr_band(cefr_level)

        band_terms = [(t, d) for (b, t, d) in pool if b == band]
        if len(band_terms) < 4:
            band_terms = [(t, d) for (b, t, d) in pool if b == "intermediate"]
        if len(band_terms) < 4:
            band_terms = [(t, d) for (b, t, d) in pool]

        scenarios: List[Dict[str, Any]] = []
        shuffled = list(band_terms)
        random.shuffle(shuffled)

        for i in range(0, len(shuffled) - 3, 4):
            group = shuffled[i:i + 4]
            terms = [t for t, _ in group]
            defs = [d for _, d in group]
            matches = {t: d for t, d in group}
            shuffled_defs = list(defs)
            random.shuffle(shuffled_defs)

            label = scenario_key.replace("Department", "").strip()
            scenarios.append({
                "cefr_band": band,
                "question": f"Match {label} terms ({', '.join(terms[:2])}, ...):",
                "terms": terms,
                "definitions": shuffled_defs,
                "matches": matches,
                "explanation": f"{label} vocabulary at {band} level."
            })

        if not scenarios:
            first_four = band_terms[:4]
            terms = [t for t, _ in first_four]
            defs = [d for _, d in first_four]
            scenarios.append({
                "cefr_band": band,
                "question": f"Match {scenario_key} terms:",
                "terms": terms,
                "definitions": defs,
                "matches": {t: d for t, d in first_four},
                "explanation": f"{scenario_key} vocabulary."
            })

        return scenarios

    def _get_reading_scenarios(self, scenario_key: str, cefr_level: str) -> List[Dict[str, Any]]:
        """Get reading comprehension scenarios — 5+ unique passages per content pool."""

        readings = {
            "Front Desk": [
                {"cefr_band": "basic", "passage": "GUEST CHECK-IN PROCEDURES: All guests must present valid photo identification and boarding passes at embarkation. Room keys will be issued after verification. Guests should familiarize themselves with emergency muster station locations posted in their staterooms. Late check-in after 4:00 PM requires advance notification.", "options": ["Check-in Requirements", "Emergency Procedures", "Hotel Policies", "Travel Guidelines"], "correct": "Check-in Requirements", "explanation": "The passage focuses on guest check-in procedures and requirements."},
                {"cefr_band": "basic", "passage": "CABIN TYPES: Inside cabins offer no window and are the most affordable option. Ocean-view cabins feature a porthole or window. Balcony cabins include a private outdoor area. Suite categories provide separate living areas and enhanced amenities. All cabins include daily housekeeping and towel service.", "options": ["Cabin Categories Overview", "Pricing Guide", "Amenities List", "Booking Instructions"], "correct": "Cabin Categories Overview", "explanation": "The passage describes different cabin types available to guests."},
                {"cefr_band": "intermediate", "passage": "ROOM UPGRADE POLICY: Upgrades are subject to availability and may incur additional charges. Ocean view and balcony suites command premium rates. Guests wishing to upgrade should inquire at the front desk during embarkation. Last-minute upgrades may be offered at discounted rates on departure day.", "options": ["Pricing Structure", "Room Upgrade Guidelines", "Booking Instructions", "Cancellation Policy"], "correct": "Room Upgrade Guidelines", "explanation": "The passage explains the room upgrade policy and procedures."},
                {"cefr_band": "intermediate", "passage": "CHECK-OUT PROCEDURES: Guests must settle their onboard accounts the evening before disembarkation. Express check-out allows charges to be billed to the card on file. Self-carry luggage must be taken by hand; tagged luggage is collected the night before. Final bills are slipped under the cabin door by 5:00 AM on departure day.", "options": ["Departure Instructions", "Check-out Process", "Billing Procedures", "Luggage Policy"], "correct": "Check-out Process", "explanation": "The passage outlines the check-out and disembarkation process."},
                {"cefr_band": "advanced", "passage": "GUEST COMPLAINT RESOLUTION PROTOCOL: Staff should use the HEARD method—Hear, Empathize, Apologize, Resolve, Delight. Document every complaint in the CRM within one hour. Escalate unresolved issues to the hotel director. Offer compensation within authorized limits. Follow up within 24 hours to confirm guest satisfaction.", "options": ["Staff Training Manual", "Complaint Handling Protocol", "Service Recovery Standards", "Quality Assurance Checklist"], "correct": "Complaint Handling Protocol", "explanation": "The passage details the structured approach for resolving guest complaints."}
            ],
            "Housekeeping": [
                {"cefr_band": "basic", "passage": "CABIN CLEANING STANDARDS: All staterooms must be serviced daily between 9:00 AM and 3:00 PM unless guest requests otherwise. Turndown service is provided each evening starting at 6:00 PM. Bed linens are changed every three days or upon request. Guests requiring privacy should display 'Do Not Disturb' signs.", "options": ["Daily Cleaning Schedule", "Guest Privacy Policy", "Service Standards", "Room Maintenance"], "correct": "Daily Cleaning Schedule", "explanation": "The passage outlines the daily housekeeping schedule and standards."},
                {"cefr_band": "basic", "passage": "TOWEL AND LINEN POLICY: Bath towels are replaced daily. Pool towels must be exchanged at the pool deck towel station. Extra blankets and pillows are available upon request through housekeeping. Guests should place used towels on the bathroom floor for replacement.", "options": ["Linen Exchange Policy", "Pool Rules", "Guest Instructions", "Room Amenities"], "correct": "Linen Exchange Policy", "explanation": "The passage explains the towel and linen replacement policy."},
                {"cefr_band": "intermediate", "passage": "STATEROOM AMENITY REPLENISHMENT: Soap, shampoo, and lotion dispensers are refilled during daily service. Complimentary water bottles are provided at turndown. Coffee and tea supplies are restocked each morning. Special requests such as hypoallergenic pillows must be placed 24 hours in advance through Guest Services.", "options": ["Supply Ordering", "Amenity Restocking Procedures", "Guest Request Process", "Housekeeping Inventory"], "correct": "Amenity Restocking Procedures", "explanation": "The passage details how stateroom amenities are replenished."},
                {"cefr_band": "intermediate", "passage": "LOST AND FOUND PROTOCOL: Items found in staterooms after checkout must be logged, tagged, and stored in the housekeeping office. Guests can claim items within 30 days by contacting the cruise line. Unclaimed valuables are held for 90 days. Perishable or low-value items are disposed of after 7 days.", "options": ["Item Return Policy", "Lost and Found Procedures", "Guest Checkout Rules", "Storage Guidelines"], "correct": "Lost and Found Procedures", "explanation": "The passage describes the lost and found handling process."},
                {"cefr_band": "advanced", "passage": "DEEP CLEANING SCHEDULE: Cabins receive a deep clean every turnaround day between voyages. This includes carpet shampooing, mattress rotation, air vent cleaning, and balcony furniture inspection. The process requires coordination between housekeeping, maintenance, and the hotel director. Completion must be verified before new guest boarding begins.", "options": ["Turnaround Day Operations", "Deep Cleaning Protocol", "Maintenance Schedule", "Quality Inspection Checklist"], "correct": "Deep Cleaning Protocol", "explanation": "The passage outlines the deep cleaning procedures between voyages."}
            ],
            "Food & Beverage": [
                {"cefr_band": "basic", "passage": "DINING ROOM HOURS: Breakfast is served from 7:00 AM to 9:30 AM. Lunch service runs from 12:00 PM to 2:00 PM. Dinner has two seatings: early at 5:30 PM and late at 8:00 PM. The buffet is available from 6:00 AM to midnight for casual dining.", "options": ["Meal Schedule", "Restaurant Hours", "Menu Options", "Reservation Policy"], "correct": "Restaurant Hours", "explanation": "The passage lists the dining room operating hours for each meal."},
                {"cefr_band": "basic", "passage": "ROOM SERVICE MENU: A limited room service menu is available 24 hours. Continental breakfast delivery is complimentary until 10:00 AM. Hot meals ordered after midnight carry a service charge. Orders typically arrive within 30 minutes. Trays should be placed in the hallway after use.", "options": ["Room Service Options", "Breakfast Menu", "Delivery Guidelines", "Service Charges"], "correct": "Room Service Options", "explanation": "The passage describes room service availability and policies."},
                {"cefr_band": "intermediate", "passage": "SPECIAL DIETARY REQUIREMENTS: Guests with food allergies or dietary restrictions should notify dining staff at least 24 hours in advance. Our culinary team can accommodate vegetarian, vegan, gluten-free, and religious dietary needs. All menu items can be modified to exclude allergens. Cross-contamination prevention protocols are strictly followed.", "options": ["Menu Options", "Allergy Management Protocol", "Dining Reservations", "Kitchen Safety Rules"], "correct": "Allergy Management Protocol", "explanation": "The passage focuses on managing special dietary needs and allergies."},
                {"cefr_band": "intermediate", "passage": "FOOD SAFETY STANDARDS: All kitchen staff must wash hands every 30 minutes and after handling raw proteins. Cooked foods must be held above 140°F or below 40°F. Date labels are mandatory on all prepared items. The executive chef conducts daily temperature audits. Violations are logged and corrective actions documented immediately.", "options": ["Hygiene Policy", "Food Safety Compliance", "Kitchen Training Manual", "Temperature Guidelines"], "correct": "Food Safety Compliance", "explanation": "The passage outlines food safety standards and compliance requirements."},
                {"cefr_band": "advanced", "passage": "SPECIALTY RESTAURANT OPERATIONS: Cover charges apply to all specialty venues and must be disclosed at booking. Chef's table experiences require 48-hour advance reservation. Wine pairing menus rotate weekly and are curated by the onboard sommelier. Guest feedback forms are collected after every specialty dinner and reviewed by the F&B director.", "options": ["Venue Pricing", "Specialty Dining Operations", "Wine Program Details", "Reservation Management"], "correct": "Specialty Dining Operations", "explanation": "The passage describes specialty restaurant policies and operations."}
            ],
            "Bar Service": [
                {"cefr_band": "basic", "passage": "BAR HOURS: The pool bar opens at 10:00 AM and closes at 6:00 PM. The main lounge bar operates from 4:00 PM to midnight. Late-night service is available at the casino bar until 2:00 AM. All bars close 30 minutes before port arrival for inventory.", "options": ["Bar Operating Hours", "Drink Menu", "Happy Hour Schedule", "Venue Locations"], "correct": "Bar Operating Hours", "explanation": "The passage lists bar hours for different venues onboard."},
                {"cefr_band": "basic", "passage": "DRINK ORDERING BASICS: Guests may order drinks at any bar using their room key card. Non-alcoholic options include fresh juices, mocktails, and specialty coffees. Minors are not served alcoholic beverages under any circumstances. Bartenders may refuse service to visibly intoxicated guests.", "options": ["Ordering Process", "Drink Order Guidelines", "Alcohol Regulations", "Bar Etiquette"], "correct": "Drink Order Guidelines", "explanation": "The passage explains basic drink ordering procedures and rules."},
                {"cefr_band": "intermediate", "passage": "BEVERAGE PACKAGE OPTIONS: The Premium package includes cocktails, beer, wine, and soft drinks for $65 per day. The Deluxe package adds premium spirits and specialty coffees for $85 per day. Packages must be purchased for the entire cruise duration. Guests under 21 are not eligible for alcoholic beverage packages.", "options": ["Drink Pricing", "Beverage Package Information", "Bar Hours", "Alcohol Policies"], "correct": "Beverage Package Information", "explanation": "The passage explains the different beverage package options and pricing."},
                {"cefr_band": "intermediate", "passage": "RESPONSIBLE SERVICE POLICY: Bar staff must complete responsible beverage service training. Signs of intoxication include slurred speech, unsteady movement, and aggressive behavior. Staff should offer water and food alternatives. Incidents must be documented and reported to the beverage manager. Guest safety is the top priority.", "options": ["Staff Training", "Responsible Service Standards", "Safety Procedures", "Guest Behavior Policy"], "correct": "Responsible Service Standards", "explanation": "The passage outlines the responsible alcohol service policy."},
                {"cefr_band": "advanced", "passage": "COCKTAIL PROGRAM DEVELOPMENT: Each voyage features a rotating signature cocktail menu designed by the head mixologist. Ingredients are sourced from port destinations when possible. Cocktail presentations include garnishes, glassware selection, and themed accompaniments. Staff must memorize recipe cards and presentation standards before each sailing.", "options": ["Menu Design", "Cocktail Program Standards", "Bartender Training", "Ingredient Sourcing"], "correct": "Cocktail Program Standards", "explanation": "The passage details the cocktail program development process."}
            ],
            "Guest Services": [
                {"cefr_band": "basic", "passage": "GUEST SERVICES DESK: The desk is located on Deck 5, midship, and operates 24 hours. Common services include currency exchange, excursion booking, and lost item inquiries. Guests can also request cabin changes and billing assistance. The busiest hours are typically between 8:00 AM and 10:00 AM.", "options": ["Desk Location Guide", "Guest Services Overview", "Hours of Operation", "Available Services"], "correct": "Guest Services Overview", "explanation": "The passage provides an overview of Guest Services desk location and services."},
                {"cefr_band": "basic", "passage": "ONBOARD ACCOUNT SYSTEM: Each guest receives a room key card linked to an onboard account. All purchases including dining, shopping, and excursions are charged to this account. Guests may set a daily spending limit. Final statements are delivered the night before disembarkation.", "options": ["Payment Methods", "Onboard Account Guide", "Shopping Policy", "Billing Information"], "correct": "Onboard Account Guide", "explanation": "The passage explains the onboard account and payment system."},
                {"cefr_band": "intermediate", "passage": "GUEST ASSISTANCE: Guest Services is available 24 hours. Common requests include room changes, lost items, excursion bookings, and billing questions. Staff should prioritize urgent matters such as medical or security concerns. Refer complex issues to the supervisor on duty.", "options": ["Service Hours", "Guest Services Procedures", "Staff Duties", "Guest Complaints"], "correct": "Guest Services Procedures", "explanation": "The passage describes Guest Services scope and procedures."},
                {"cefr_band": "intermediate", "passage": "SHORE EXCURSION BOOKING: Excursions can be booked online before the cruise or at the excursion desk onboard. Popular tours sell out quickly; early booking is recommended. Cancellations made less than 24 hours before the excursion are non-refundable. Guests must return to the ship at least 30 minutes before departure.", "options": ["Tour Options", "Shore Excursion Booking Policy", "Port Information", "Activity Schedule"], "correct": "Shore Excursion Booking Policy", "explanation": "The passage explains how shore excursions are booked and cancelled."},
                {"cefr_band": "advanced", "passage": "SPECIAL OCCASION COORDINATION: Guest Services arranges birthday celebrations, anniversary packages, and honeymoon amenities. Requests must be submitted at least 48 hours in advance. Packages include cabin decoration, a cake, and a bottle of sparkling wine. Coordination with dining, housekeeping, and entertainment is required for premium events.", "options": ["Event Planning Services", "Special Occasion Coordination", "Gift Shop Options", "Celebration Packages"], "correct": "Special Occasion Coordination", "explanation": "The passage describes how special occasions are coordinated onboard."}
            ],
            "Auxiliary Service": [
                {"cefr_band": "basic", "passage": "EQUIPMENT INVENTORY: Auxiliary staff maintain an inventory of projectors, microphones, speakers, and display screens. All items must be checked out using the log book. Damaged equipment should be reported immediately. Weekly inventory counts are conducted every Monday.", "options": ["Equipment List", "A/V Inventory Procedures", "Maintenance Schedule", "Supply Orders"], "correct": "A/V Inventory Procedures", "explanation": "The passage describes A/V equipment inventory management."},
                {"cefr_band": "basic", "passage": "VENUE SETUP BASICS: Chairs and tables must be arranged according to the event diagram provided. Stage lighting should be tested one hour before the event. Emergency exit paths must remain unblocked at all times. Staff should arrive 30 minutes before the scheduled setup time.", "options": ["Event Guidelines", "Venue Setup Requirements", "Safety Rules", "Staff Scheduling"], "correct": "Venue Setup Requirements", "explanation": "The passage outlines basic venue setup requirements."},
                {"cefr_band": "intermediate", "passage": "A/V AND EVENT SETUP: Auxiliary staff set up projectors, microphones, and seating for events. Advance notice of 4 hours is required for standard setups. Equipment must be returned within 2 hours after event end. Report any malfunctions immediately to technical support.", "options": ["Equipment Rentals", "Event Setup Procedures", "Technical Support", "Venue Reservations"], "correct": "Event Setup Procedures", "explanation": "The passage outlines A/V and event setup procedures."},
                {"cefr_band": "intermediate", "passage": "SOUND CHECK PROTOCOL: All audio equipment must be tested at least two hours before performances. Microphone levels are set during rehearsal with performers present. Background music volume should not exceed 75 decibels in dining venues. Technical staff remain on standby during all live performances.", "options": ["Audio Standards", "Sound Check Guidelines", "Performance Rules", "Volume Regulations"], "correct": "Sound Check Guidelines", "explanation": "The passage describes the sound check and audio testing protocol."},
                {"cefr_band": "advanced", "passage": "LARGE-SCALE EVENT COORDINATION: Events exceeding 200 guests require a dedicated event coordinator and a detailed run-of-show document. Lighting, sound, and video cues must be programmed and rehearsed. Contingency plans for weather-dependent outdoor events include indoor backup venues. Post-event debriefs are mandatory within 24 hours.", "options": ["Event Management Standards", "Large Event Coordination Protocol", "Venue Booking Policy", "Entertainment Planning"], "correct": "Large Event Coordination Protocol", "explanation": "The passage details the coordination process for large-scale events."}
            ],
            "Laundry": [
                {"cefr_band": "basic", "passage": "LAUNDRY DROP-OFF: Guests should place items in the laundry bag provided in their cabin. Complete the laundry form listing each item. Bags left before 9:00 AM receive same-day service. Items without a completed form will not be processed.", "options": ["Laundry Instructions", "Drop-off Procedures", "Pricing List", "Service Hours"], "correct": "Drop-off Procedures", "explanation": "The passage explains how guests submit laundry."},
                {"cefr_band": "basic", "passage": "SELF-SERVICE LAUNDRY: Coin-operated washers and dryers are available on Deck 10 forward. Detergent packets can be purchased from the vending machine nearby. Machines operate from 7:00 AM to 10:00 PM. Guests must remove items promptly when cycles complete.", "options": ["Laundry Room Location", "Self-Service Laundry Guide", "Machine Instructions", "Operating Hours"], "correct": "Self-Service Laundry Guide", "explanation": "The passage describes the self-service laundry facilities."},
                {"cefr_band": "intermediate", "passage": "LAUNDRY SERVICE: Express service is available within 4 hours for an additional fee. Standard turnaround is 24 hours. Delicate and dry-clean items require special handling. Guests should complete the laundry form and leave items in the provided bag. Missing items must be reported within 24 hours.", "options": ["Laundry Hours", "Laundry Service Guidelines", "Pricing", "Guest Instructions"], "correct": "Laundry Service Guidelines", "explanation": "The passage explains laundry service options and procedures."},
                {"cefr_band": "intermediate", "passage": "CREW UNIFORM CARE: Crew uniforms are processed separately from guest laundry. Name tags must be attached to each item. Standard turnaround is 24 hours; urgent requests are handled within 6 hours. Damaged uniforms are documented and reported to the uniform coordinator for replacement.", "options": ["Uniform Policy", "Crew Laundry Procedures", "Dress Code", "Staff Responsibilities"], "correct": "Crew Laundry Procedures", "explanation": "The passage outlines how crew uniforms are handled by laundry."},
                {"cefr_band": "advanced", "passage": "INDUSTRIAL LAUNDRY OPERATIONS: The ship processes approximately 5,000 pounds of linen daily using commercial-grade machines. Water temperature must reach 160°F for sanitization. Chemical dosing systems are calibrated weekly. Equipment maintenance logs are reviewed by the chief engineer monthly. Wastewater is treated before discharge per MARPOL regulations.", "options": ["Equipment Specifications", "Industrial Laundry Standards", "Environmental Compliance", "Maintenance Schedule"], "correct": "Industrial Laundry Standards", "explanation": "The passage describes the scale and standards of shipboard laundry operations."}
            ],
            "Photo": [
                {"cefr_band": "basic", "passage": "PHOTO GALLERY HOURS: The photo gallery on Deck 7 is open from 5:00 PM to 10:00 PM on sea days. Formal night photos are displayed the following morning. Guests can browse and purchase prints or digital copies. Staff are available to help locate specific photos.", "options": ["Gallery Schedule", "Photo Gallery Information", "Print Pricing", "Photography Services"], "correct": "Photo Gallery Information", "explanation": "The passage describes photo gallery hours and services."},
                {"cefr_band": "basic", "passage": "EMBARKATION PHOTOS: Professional photographers are stationed at the gangway to take arrival photos. These photos are available for viewing in the gallery within 24 hours. Guests are not obligated to purchase. Unsold embarkation photos are deleted at the end of the voyage.", "options": ["Welcome Photos", "Embarkation Photo Service", "Photography Pricing", "Gallery Display"], "correct": "Embarkation Photo Service", "explanation": "The passage explains the embarkation photo service."},
                {"cefr_band": "intermediate", "passage": "PHOTO PACKAGES: Digital albums and prints are available at the photo gallery. Portrait sessions can be booked in advance. Package discounts apply when purchasing multiple prints. Photos are typically ready within 2 hours. Guests may request retakes if unsatisfied with results.", "options": ["Gallery Hours", "Photo Package Details", "Pricing", "Portrait Sessions"], "correct": "Photo Package Details", "explanation": "The passage describes photo services and packages."},
                {"cefr_band": "intermediate", "passage": "PORTRAIT SESSION BOOKING: Private portrait sessions are available in the onboard studio. Sessions last 20 minutes and include up to 15 edited images. Bookings can be made at the photo gallery or through the app. Formal attire is recommended for evening portrait sessions.", "options": ["Booking Instructions", "Portrait Session Guidelines", "Photo Editing Services", "Dress Code"], "correct": "Portrait Session Guidelines", "explanation": "The passage outlines how to book and prepare for portrait sessions."},
                {"cefr_band": "advanced", "passage": "GREEN SCREEN AND THEMED PHOTOGRAPHY: Themed photo stations rotate throughout the voyage, featuring destinations, formal nights, and holiday events. Green-screen technology allows custom backgrounds. Photographers must follow brand guidelines for pose selection and lighting. All images are quality-checked before gallery display.", "options": ["Photography Standards", "Themed Photography Operations", "Event Photography", "Image Processing"], "correct": "Themed Photography Operations", "explanation": "The passage details the themed and green-screen photography operations."}
            ],
            "Provisions": [
                {"cefr_band": "basic", "passage": "RECEIVING DOCK PROCEDURES: All deliveries arrive at the designated receiving dock during port calls. Delivery personnel must show identification and a purchase order number. Items are counted and cross-referenced with the order before acceptance. Damaged goods are refused and documented.", "options": ["Dock Rules", "Delivery Receiving Steps", "Supplier Instructions", "Port Schedule"], "correct": "Delivery Receiving Steps", "explanation": "The passage describes the delivery receiving process at the dock."},
                {"cefr_band": "basic", "passage": "STORAGE AREAS: Dry goods are stored in the forward hold on Deck 1. Frozen items go to the freezer at minus 10 degrees Fahrenheit. Refrigerated produce is kept between 34 and 40 degrees. Each storage area has a temperature log that must be updated twice daily.", "options": ["Ship Layout", "Storage Area Guidelines", "Temperature Chart", "Inventory Map"], "correct": "Storage Area Guidelines", "explanation": "The passage explains the different storage areas and requirements."},
                {"cefr_band": "intermediate", "passage": "PROVISIONS RECEIVING: All deliveries must be logged and inspected upon arrival. FIFO rotation applies to perishables. Cold storage temperatures must be monitored and recorded. Order lead times vary by supplier; maintain minimum stock levels to avoid shortages during port calls.", "options": ["Delivery Schedule", "Provisions Management Procedures", "Supplier Contacts", "Storage Guidelines"], "correct": "Provisions Management Procedures", "explanation": "The passage covers provisions receiving and storage procedures."},
                {"cefr_band": "intermediate", "passage": "WASTE MANAGEMENT: Food waste is separated from recyclable materials. Cooking oil is collected in designated drums for port-side disposal. Packaging materials are compacted and stored until the next port. The provisions team coordinates waste removal schedules with the environmental officer.", "options": ["Recycling Policy", "Waste Management Procedures", "Environmental Standards", "Disposal Schedule"], "correct": "Waste Management Procedures", "explanation": "The passage outlines waste management procedures in provisions."},
                {"cefr_band": "advanced", "passage": "SUPPLY CHAIN PLANNING: Provision orders for a 7-day voyage are finalized 72 hours before embarkation. The provisions manager reviews par levels, guest count projections, and menu plans. Emergency orders at non-scheduled ports incur premium surcharges. Vendor scorecards tracking quality, delivery accuracy, and pricing are reviewed quarterly.", "options": ["Order Management", "Supply Chain Planning Process", "Budget Analysis", "Vendor Relations"], "correct": "Supply Chain Planning Process", "explanation": "The passage describes the strategic supply chain planning process."}
            ],
            "Deck Department": [
                {"cefr_band": "basic", "passage": "SAFETY DRILL REQUIREMENTS: All passengers and crew must participate in the mandatory muster drill before departure. The drill typically occurs 30 minutes prior to sailing. Guests should bring their room keys to their assigned muster stations. Failure to attend may result in denied boarding. Life jackets are not required during the drill.", "options": ["Safety Equipment", "Muster Drill Procedures", "Emergency Response", "Boarding Requirements"], "correct": "Muster Drill Procedures", "explanation": "The passage details mandatory safety drill procedures and requirements."},
                {"cefr_band": "basic", "passage": "DECK SAFETY RULES: Running on wet decks is prohibited. Children under 12 must be accompanied by an adult on open decks. Pool areas are supervised by trained lifeguards from 8:00 AM to 8:00 PM. Climbing on railings is strictly forbidden.", "options": ["Pool Rules", "Deck Safety Regulations", "Child Supervision Policy", "Lifeguard Schedule"], "correct": "Deck Safety Regulations", "explanation": "The passage lists safety rules for open deck areas."},
                {"cefr_band": "intermediate", "passage": "TENDER OPERATIONS: When the ship anchors offshore, tender boats transport guests to port. Tender tickets are distributed at Guest Services. Guests with mobility issues board first. Each tender holds 150 passengers and departs every 15 minutes. The last tender returns 30 minutes before scheduled departure.", "options": ["Port Transport", "Tender Boat Operations", "Shore Access Policy", "Embarkation Procedures"], "correct": "Tender Boat Operations", "explanation": "The passage describes tender boat operations for offshore ports."},
                {"cefr_band": "intermediate", "passage": "NAVIGATION WATCH DUTIES: Officers on watch are responsible for monitoring radar, course heading, and traffic in the area. Watch rotations are four hours on, eight hours off. All sightings of other vessels or hazards must be logged. Communication with the engine room is maintained throughout each watch.", "options": ["Bridge Procedures", "Navigation Watch Protocol", "Officer Schedule", "Radar Operations"], "correct": "Navigation Watch Protocol", "explanation": "The passage outlines duties during navigation watch."},
                {"cefr_band": "advanced", "passage": "MAN OVERBOARD PROCEDURE: Upon a man-overboard alarm, the bridge initiates the Williamson Turn. A crew member is assigned as a visual spotter. The rescue boat team reports to their station within 3 minutes. The ship's position, time, and weather conditions are recorded immediately. Coast guard notification follows per SOLAS requirements.", "options": ["Emergency Drill", "Man Overboard Response Protocol", "Rescue Operations", "Safety Equipment Procedures"], "correct": "Man Overboard Response Protocol", "explanation": "The passage details the man overboard emergency response protocol."}
            ],
            "Engine Department": [
                {"cefr_band": "basic", "passage": "ENGINE ROOM SAFETY: Hard hats, safety glasses, and steel-toe boots are required at all times in the engine room. Hearing protection must be worn near running machinery. Emergency exits are marked with illuminated signs. Fire extinguishers are located at every entrance and exit.", "options": ["Safety Gear", "Engine Room Safety Rules", "Emergency Procedures", "Equipment Guidelines"], "correct": "Engine Room Safety Rules", "explanation": "The passage lists safety requirements for the engine room."},
                {"cefr_band": "basic", "passage": "TOOL AND EQUIPMENT SIGN-OUT: All tools must be signed out from the tool room and returned after use. Missing tools must be reported to the chief engineer immediately. Portable power tools require a safety inspection tag. The tool room is open from 6:00 AM to 10:00 PM.", "options": ["Tool Room Rules", "Equipment Checkout Procedures", "Maintenance Schedule", "Safety Inspections"], "correct": "Equipment Checkout Procedures", "explanation": "The passage describes the tool and equipment sign-out process."},
                {"cefr_band": "intermediate", "passage": "FUEL MANAGEMENT: Bunkering operations require coordination between the engine room and the port fuel supplier. Fuel samples are taken before, during, and after each transfer. Overflow prevention measures include constant tank-level monitoring. Spill response kits must be staged at all transfer points during bunkering.", "options": ["Fuel Ordering", "Fuel Transfer Procedures", "Engine Specifications", "Port Operations"], "correct": "Fuel Transfer Procedures", "explanation": "The passage describes fuel management and bunkering procedures."},
                {"cefr_band": "advanced", "passage": "MAINTENANCE LOG PROTOCOL: All engine room equipment must be inspected daily and logged in the maintenance system. Temperature, pressure, and RPM readings should be recorded every four hours during operation. Any abnormal readings must be reported immediately to the chief engineer. Preventive maintenance schedules must be strictly adhered to.", "options": ["Equipment Monitoring", "Maintenance Record Keeping", "Safety Inspection", "Engineering Standards"], "correct": "Maintenance Record Keeping", "explanation": "The passage focuses on proper maintenance logging procedures."},
                {"cefr_band": "advanced", "passage": "EMERGENCY GENERATOR PROTOCOL: The emergency diesel generator must start automatically within 45 seconds of a main power failure. Monthly load tests are conducted to verify readiness. Fuel and lubricant levels are checked daily. The emergency generator powers navigation lights, fire detection systems, and emergency communication equipment.", "options": ["Power Distribution", "Emergency Generator Standards", "Backup Systems", "Electrical Safety"], "correct": "Emergency Generator Standards", "explanation": "The passage outlines emergency generator testing and readiness requirements."}
            ],
            "Medical Department": [
                {"cefr_band": "basic", "passage": "MEDICAL CENTER LOCATION: The medical center is on Deck 1 forward. It is staffed by a doctor and two nurses. Walk-in hours are 8:00 AM to 12:00 PM and 2:00 PM to 6:00 PM. For emergencies, call extension 911 from any ship phone.", "options": ["Emergency Numbers", "Medical Center Information", "Doctor Schedule", "Health Services"], "correct": "Medical Center Information", "explanation": "The passage provides basic medical center location and contact information."},
                {"cefr_band": "basic", "passage": "SEASICKNESS REMEDIES: Over-the-counter motion sickness medication is available at the medical center. Wristbands and patches can be purchased at the gift shop. Guests are advised to stay on lower, mid-ship decks for less motion. Fresh air and focusing on the horizon can also help.", "options": ["Health Tips", "Seasickness Treatment Options", "Medication Policy", "Pharmacy Services"], "correct": "Seasickness Treatment Options", "explanation": "The passage describes available seasickness remedies."},
                {"cefr_band": "intermediate", "passage": "SICK CALL PROCEDURES: Guests requiring medical attention should contact the medical center or call the emergency number. Sick call hours are 8:00 AM to 6:00 PM for non-urgent matters. Vital signs are recorded at each visit. Prescription medications from home must be declared at embarkation. Serious cases may require medical evacuation at the next port.", "options": ["Medical Center Hours", "Sick Call Procedures", "Prescription Policy", "Emergency Response"], "correct": "Sick Call Procedures", "explanation": "The passage outlines sick call procedures and medical center operations."},
                {"cefr_band": "intermediate", "passage": "MEDICAL BILLING: Medical consultations are charged to the guest's onboard account. Fees vary based on the type of visit and treatment provided. Guests should contact their travel insurance provider for reimbursement. Itemized receipts are provided upon request. Emergency treatments are billed at a higher rate.", "options": ["Insurance Information", "Medical Billing Policy", "Payment Options", "Fee Schedule"], "correct": "Medical Billing Policy", "explanation": "The passage explains how medical services are billed onboard."},
                {"cefr_band": "advanced", "passage": "MEDICAL EVACUATION PROTOCOL: When a patient requires care beyond shipboard capabilities, the ship's doctor contacts the Shoreside Medical Team. Helicopter evacuation is arranged in cooperation with coast guard services. The patient's condition, location, and weather are assessed before deciding the evacuation method. All documentation including medical records and insurance information must accompany the patient.", "options": ["Emergency Response Plan", "Medical Evacuation Procedures", "Coast Guard Coordination", "Patient Transfer Standards"], "correct": "Medical Evacuation Procedures", "explanation": "The passage details the medical evacuation decision and coordination process."}
            ],
            "Security Department": [
                {"cefr_band": "basic", "passage": "GANGWAY ACCESS CONTROL: All guests and crew must scan their key card when boarding or leaving the ship. Security officers verify identity at the gangway. Visitors are not permitted onboard without prior authorization. The gangway closes 30 minutes before sailing.", "options": ["Boarding Rules", "Gangway Access Procedures", "Visitor Policy", "Key Card Instructions"], "correct": "Gangway Access Procedures", "explanation": "The passage describes gangway access control procedures."},
                {"cefr_band": "basic", "passage": "PROHIBITED ITEMS: Guests may not bring weapons, illegal substances, flammable liquids, or outside alcohol onboard. Prohibited items discovered during screening will be confiscated. Items may be returned at the end of the voyage at the security office. A complete list of prohibited items is available on the cruise line website.", "options": ["Packing Guide", "Prohibited Items Policy", "Screening Process", "Guest Safety Rules"], "correct": "Prohibited Items Policy", "explanation": "The passage lists items prohibited from being brought onboard."},
                {"cefr_band": "intermediate", "passage": "CCTV MONITORING: The ship has over 800 security cameras covering public areas, corridors, and the gangway. Camera footage is monitored 24 hours from the security control room. Recordings are retained for 30 days. Privacy areas such as staterooms and restrooms are not monitored.", "options": ["Surveillance Policy", "CCTV Monitoring Standards", "Privacy Guidelines", "Security Technology"], "correct": "CCTV Monitoring Standards", "explanation": "The passage explains the CCTV monitoring system and policies."},
                {"cefr_band": "advanced", "passage": "SECURITY SCREENING PROCESS: All guests and baggage must pass through security screening at embarkation. Prohibited items include weapons, illegal substances, and flammable materials. Security reserves the right to inspect any item. Guests refusing screening will be denied boarding. Report suspicious activity to security immediately.", "options": ["Boarding Security Procedures", "Screening and Inspection Protocol", "Guest Safety Rules", "Emergency Protocols"], "correct": "Screening and Inspection Protocol", "explanation": "The passage describes the security screening process at embarkation."},
                {"cefr_band": "advanced", "passage": "INCIDENT RESPONSE PROCEDURE: Upon receiving an incident report, the security officer on duty assesses the severity and classifies it as low, medium, or high priority. High-priority incidents require immediate notification of the staff captain. All incidents are documented in the ship's security log within one hour. Witness statements are collected and preserved as evidence.", "options": ["Reporting Standards", "Incident Response Protocol", "Emergency Management", "Investigation Procedures"], "correct": "Incident Response Protocol", "explanation": "The passage outlines the incident response classification and documentation process."}
            ],
            "Table Games": [
                {"cefr_band": "basic", "passage": "CASINO HOURS: The casino opens when the ship is in international waters, typically one hour after departure. Table games operate from 6:00 PM to 2:00 AM on sea days. The casino closes during port calls. Guests must be 18 years or older to enter the gaming area.", "options": ["Gaming Schedule", "Casino Operating Hours", "Age Requirements", "Port Day Activities"], "correct": "Casino Operating Hours", "explanation": "The passage describes casino operating hours and age requirements."},
                {"cefr_band": "basic", "passage": "CHIP EXCHANGE: Guests exchange cash for chips at the cashier cage before playing table games. Chips cannot be used outside the casino. When finished playing, chips must be exchanged back for cash at the cage. Minimum exchange amounts may apply.", "options": ["Payment Methods", "Chip Exchange Process", "Casino Currency", "Cashier Services"], "correct": "Chip Exchange Process", "explanation": "The passage explains the chip exchange process."},
                {"cefr_band": "intermediate", "passage": "TABLE GAME RULES: Minimum and maximum bets vary by table and are clearly posted. Players must place bets before the dealer announces 'No more bets.' Cell phone use at tables is prohibited. Guests should exchange cash for chips at the cashier before playing. Tipping dealers is appreciated but not required.", "options": ["Gaming Regulations", "Table Game Guidelines", "Casino Etiquette", "Betting Limits"], "correct": "Table Game Guidelines", "explanation": "The passage outlines rules and guidelines for playing table games."},
                {"cefr_band": "intermediate", "passage": "BLACKJACK BASICS: The goal is to get cards totaling closer to 21 than the dealer without going over. Face cards are worth 10 and aces count as 1 or 11. Players signal 'hit' by tapping the table and 'stand' by waving their hand. Insurance is offered when the dealer shows an ace.", "options": ["Card Values", "Blackjack Rules Overview", "Dealer Instructions", "Game Strategy"], "correct": "Blackjack Rules Overview", "explanation": "The passage explains the basic rules of blackjack."},
                {"cefr_band": "advanced", "passage": "DEALER PROCEDURES AND COMPLIANCE: Dealers must follow a strict sequence when opening and closing tables. Cards are spread for camera verification before each shift. Cash drops are performed every two hours and witnessed by a pit supervisor. Any irregularity in chip counts or card handling triggers an immediate review of surveillance footage.", "options": ["Gaming Compliance", "Dealer Operating Procedures", "Audit Standards", "Table Management"], "correct": "Dealer Operating Procedures", "explanation": "The passage details dealer procedures and gaming compliance requirements."}
            ],
            "Casino Services": [
                {"cefr_band": "basic", "passage": "SLOT MACHINE BASICS: Insert your room key card or cash to begin playing. Press the spin button or pull the lever. Winning combinations are displayed on the pay table above each machine. Jackpot wins over $1,200 require identification for tax documentation.", "options": ["How to Play", "Slot Machine Instructions", "Jackpot Rules", "Machine Types"], "correct": "Slot Machine Instructions", "explanation": "The passage provides basic slot machine playing instructions."},
                {"cefr_band": "basic", "passage": "CASINO ETIQUETTE: Guests should not touch other players' chips or cards. Drinks are complimentary while gaming. Smoking is only permitted in the designated casino smoking area. Staff are available to explain rules for any game.", "options": ["Guest Behavior", "Casino Etiquette Guide", "Smoking Policy", "Drink Service"], "correct": "Casino Etiquette Guide", "explanation": "The passage describes basic casino etiquette for guests."},
                {"cefr_band": "intermediate", "passage": "PLAYER REWARDS PROGRAM: Earn points for every dollar wagered. Silver tier reached at 1,000 points, Gold at 5,000 points, and Platinum at 10,000 points. Higher tiers receive complimentary drinks, priority seating, and exclusive tournament invitations. Points expire after 12 months of inactivity.", "options": ["Loyalty Program Benefits", "Gaming Rewards", "Membership Tiers", "Casino Promotions"], "correct": "Loyalty Program Benefits", "explanation": "The passage explains the player rewards program structure and benefits."},
                {"cefr_band": "intermediate", "passage": "TOURNAMENT SCHEDULE: Poker and blackjack tournaments are held on sea days. Entry fees range from $25 to $100 depending on the tournament. Registration opens at the casino host desk one hour before start time. Prizes include cash, onboard credit, and free cruise vouchers.", "options": ["Event Calendar", "Tournament Information", "Prize Details", "Registration Process"], "correct": "Tournament Information", "explanation": "The passage describes casino tournament schedules and entry details."},
                {"cefr_band": "advanced", "passage": "RESPONSIBLE GAMING PROGRAM: The casino provides self-exclusion forms for guests who wish to limit their gaming. Staff are trained to identify signs of problem gambling including chasing losses and borrowing money. Informational brochures and helpline numbers are available at the casino host desk. Minors found in the gaming area are escorted out and parents are notified.", "options": ["Guest Welfare Policy", "Responsible Gaming Standards", "Problem Gambling Prevention", "Casino Safety Measures"], "correct": "Responsible Gaming Standards", "explanation": "The passage outlines the casino's responsible gaming program and support measures."}
            ]
        }

        raw = _require(readings, scenario_key, "reading scenarios")
        return _filter_scenarios_by_band(raw, cefr_level)

    def _get_speaking_scenarios(self, scenario_key: str, cefr_level: str) -> List[Dict[str, Any]]:
        """Get speaking response scenarios — 4+ unique prompts per content pool."""

        speaking_prompts = {
            "Front Desk": [
                {"cefr_band": "basic", "prompt": "A guest complains: 'My room is too noisy and I can't sleep.' Respond professionally.", "context": "Guest complaint about room noise", "keywords": ["apologize", "sorry", "understand", "move", "change room", "quiet", "comfortable", "resolve"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should apologize, show empathy, and offer solution like room change."},
                {"cefr_band": "basic", "prompt": "A guest asks: 'What time is breakfast and where is it served?' Give the information.", "context": "Guest asking about dining schedule", "keywords": ["breakfast", "time", "restaurant", "buffet", "deck", "open", "morning"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should provide clear time and location details."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'What shore excursions do you recommend for families?' Provide helpful suggestions.", "context": "Shore excursion recommendation request", "keywords": ["family-friendly", "children", "kids", "recommend", "popular", "beach", "tour", "activities"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should suggest appropriate family activities and explain options clearly."},
                {"cefr_band": "advanced", "prompt": "A guest says: 'I booked a balcony cabin online but was given an inside cabin. I want a resolution now.' Handle the escalation.", "context": "Booking discrepancy escalation", "keywords": ["apologize", "investigate", "booking", "confirmation", "upgrade", "resolve", "compensation", "supervisor"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should acknowledge the error, investigate, and offer resolution or escalation."}
            ],
            "Housekeeping": [
                {"cefr_band": "basic", "prompt": "A guest says: 'I need extra towels and pillows.' Respond appropriately.", "context": "Guest request for additional items", "keywords": ["certainly", "right away", "deliver", "bring", "how many", "anything else", "happy to help"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should acknowledge request and confirm delivery timeframe."},
                {"cefr_band": "basic", "prompt": "A guest asks: 'Can I get my cabin cleaned now instead of this afternoon?' Respond helpfully.", "context": "Schedule change request", "keywords": ["of course", "available", "shortly", "priority", "happy to", "cabin", "clean"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should accommodate request or explain timing."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The bathroom hasn't been cleaned properly. There are stains on the floor.' Respond professionally.", "context": "Cleaning quality complaint", "keywords": ["apologize", "immediately", "send", "re-clean", "standard", "sorry", "unacceptable", "resolve"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize and arrange immediate re-cleaning."},
                {"cefr_band": "advanced", "prompt": "Your supervisor asks you to explain the turndown service procedures to a new team member. Describe the full process.", "context": "Training a new employee", "keywords": ["turndown", "evening", "towels", "amenities", "curtains", "lights", "chocolate", "schedule", "steps"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should describe the complete turndown procedure clearly for training."}
            ],
            "Food & Beverage": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'What is today's soup of the day?' Tell them about the menu item.", "context": "Menu inquiry", "keywords": ["today", "soup", "ingredients", "recommend", "enjoy", "special"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should describe the dish clearly and pleasantly."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'I'm allergic to shellfish. What can I order?' Explain options.", "context": "Food allergy inquiry", "keywords": ["allergy", "safe", "alternative", "recommend", "chef", "accommodate", "notify", "careful"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should reassure guest and explain safe menu options."},
                {"cefr_band": "intermediate", "prompt": "A guest says: 'The steak I ordered is overcooked. I asked for medium-rare.' Handle the complaint.", "context": "Food quality complaint", "keywords": ["apologize", "replace", "kitchen", "medium-rare", "right away", "sorry", "new one", "chef"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize and arrange replacement promptly."},
                {"cefr_band": "advanced", "prompt": "Describe the specialty restaurant's tasting menu to a guest who is considering making a reservation.", "context": "Upselling specialty dining", "keywords": ["courses", "chef", "curated", "wine pairing", "seasonal", "reservation", "experience", "recommend"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present the menu enticingly with details about courses."}
            ],
            "Bar Service": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'Can I get a non-alcoholic drink?' Suggest some options.", "context": "Non-alcoholic beverage request", "keywords": ["mocktail", "juice", "soda", "water", "coffee", "tea", "recommend"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should offer several non-alcoholic options pleasantly."},
                {"cefr_band": "intermediate", "prompt": "A guest says: 'What signature cocktails do you recommend?' Make suggestions.", "context": "Beverage recommendation request", "keywords": ["recommend", "popular", "signature", "special", "flavor", "ingredients", "try", "favorite"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should describe signature drinks and match to guest preferences."},
                {"cefr_band": "intermediate", "prompt": "A guest appears intoxicated and orders another drink. How do you handle the situation?", "context": "Responsible service situation", "keywords": ["water", "food", "policy", "safety", "concerned", "alternative", "care", "responsible"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should decline politely and offer alternatives while following responsible service policy."},
                {"cefr_band": "advanced", "prompt": "A guest asks you to explain the wine pairing for tonight's dinner menu. Describe appropriate pairings for three courses.", "context": "Wine pairing consultation", "keywords": ["pairing", "white", "red", "complement", "flavor", "body", "course", "recommend", "tasting notes"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should describe wine pairings with relevant tasting vocabulary."}
            ],
            "Guest Services": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'Where is the shore excursion desk?' Give directions.", "context": "Direction request", "keywords": ["deck", "forward", "aft", "near", "next to", "between", "location"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should give clear, simple directions."},
                {"cefr_band": "basic", "prompt": "A guest says: 'I want to send a birthday cake to my friend's cabin.' Help them arrange it.", "context": "Special arrangement request", "keywords": ["cake", "order", "cabin", "delivery", "special", "arrange", "time"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain how to arrange the delivery."},
                {"cefr_band": "intermediate", "prompt": "A guest says: 'I lost my room key. What do I do?' Respond helpfully.", "context": "Lost key scenario", "keywords": ["replacement", "front desk", "identify", "photo", "ID", "assist", "immediately"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain replacement procedure calmly."},
                {"cefr_band": "advanced", "prompt": "A guest is upset about multiple issues during the cruise—delayed luggage, wrong dining time, and a noisy cabin. Address all concerns.", "context": "Multiple complaint resolution", "keywords": ["understand", "frustrating", "resolve", "each", "luggage", "dining", "cabin", "compensation", "follow up"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should systematically address each issue and offer resolution."}
            ],
            "Auxiliary Service": [
                {"cefr_band": "basic", "prompt": "A performer asks: 'Where can I find a microphone for tonight's show?' Help them.", "context": "Equipment location request", "keywords": ["microphone", "equipment", "room", "stage", "setup", "available", "check out"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should direct them to equipment or offer to retrieve it."},
                {"cefr_band": "intermediate", "prompt": "A team leader asks: 'Can we have the projector and screen set up in the conference room by 2 PM?' Respond professionally.", "context": "A/V setup request", "keywords": ["confirm", "2 PM", "conference", "projector", "screen", "setup", "ready"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should confirm request and timeline."},
                {"cefr_band": "intermediate", "prompt": "During an event, the speaker's microphone stops working. The event host asks you to fix it quickly. Respond and act.", "context": "Technical issue during live event", "keywords": ["backup", "replace", "check", "battery", "connection", "moment", "apologize", "working"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should troubleshoot quickly and communicate clearly."},
                {"cefr_band": "advanced", "prompt": "You need to coordinate a large outdoor deck party with lighting, sound, and live entertainment. Explain your setup plan to the entertainment director.", "context": "Large event planning discussion", "keywords": ["stage", "lighting", "speakers", "power", "timeline", "backup", "weather", "crew", "schedule"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a comprehensive and organized setup plan."}
            ],
            "Laundry": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'When will my laundry be ready?' Respond appropriately.", "context": "Laundry status inquiry", "keywords": ["express", "standard", "hours", "ready", "tomorrow", "delivery"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should state turnaround time clearly."},
                {"cefr_band": "basic", "prompt": "A guest says: 'I need this shirt cleaned for tonight's formal dinner.' Handle the urgent request.", "context": "Express laundry request", "keywords": ["express", "tonight", "ready", "hours", "rush", "formal", "clean", "iron"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain express service availability and timeline."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'My dress was damaged during dry cleaning. What will you do about it?' Handle the complaint.", "context": "Damage complaint", "keywords": ["apologize", "investigate", "compensation", "report", "supervisor", "damage", "sorry", "resolve"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize, document the damage, and explain compensation process."},
                {"cefr_band": "advanced", "prompt": "Explain the full laundry process from collection to delivery to a new crew member you are training.", "context": "Training new staff", "keywords": ["collect", "sort", "wash", "dry", "press", "fold", "label", "deliver", "inspect", "quality"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should describe the complete process step by step."}
            ],
            "Photo": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'Where can I find my embarkation photo?' Help them locate it.", "context": "Photo location inquiry", "keywords": ["gallery", "deck", "display", "day", "find", "name", "help"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should direct guest to the photo gallery and explain how to find their photo."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'Do you offer family portrait packages?' Explain the options.", "context": "Photo package inquiry", "keywords": ["package", "family", "portrait", "prints", "digital", "price", "session"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should describe portrait package options."},
                {"cefr_band": "intermediate", "prompt": "A guest is unhappy with their formal night photos and wants a retake. Respond professionally.", "context": "Photo retake request", "keywords": ["retake", "happy to", "schedule", "tonight", "lighting", "pose", "better", "no charge"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should offer retake and reassure guest."},
                {"cefr_band": "advanced", "prompt": "A guest couple wants a special sunset photo session on the top deck for their anniversary. Plan and describe the session.", "context": "Custom photo session planning", "keywords": ["sunset", "anniversary", "location", "time", "poses", "lighting", "special", "memorable", "package"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should plan the session with specific details about timing and location."}
            ],
            "Provisions": [
                {"cefr_band": "basic", "prompt": "A delivery driver arrives and says: 'I have 50 cases of produce. Where do they go?' Direct them.", "context": "Delivery receiving directions", "keywords": ["dock", "cold storage", "refrigerator", "follow", "sign", "log", "temperature"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should give clear directions to the appropriate storage area."},
                {"cefr_band": "intermediate", "prompt": "A chef asks: 'When is the produce delivery due?' Provide the information.", "context": "Delivery schedule inquiry", "keywords": ["delivery", "ETA", "produce", "schedule", "morning", "dock"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should give delivery timing clearly."},
                {"cefr_band": "intermediate", "prompt": "You discover that a delivery of chicken is above the safe temperature. Explain what you will do.", "context": "Food safety issue", "keywords": ["reject", "temperature", "unsafe", "document", "report", "supplier", "log", "discard"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain rejection and documentation procedures."},
                {"cefr_band": "advanced", "prompt": "The provisions manager asks you to brief the team on the inventory situation for the next 7-day voyage. Present the status.", "context": "Inventory briefing", "keywords": ["stock levels", "shortage", "order", "par level", "supplier", "lead time", "menu", "contingency"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present inventory status comprehensively."}
            ],
            "Deck Department": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'Where is my muster station?' Help them find it.", "context": "Muster station directions", "keywords": ["muster", "station", "deck", "number", "key card", "follow", "signs"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain how to find their assigned muster station."},
                {"cefr_band": "intermediate", "prompt": "A guest wants to know why they cannot swim in the pool during rough weather. Explain the safety reason.", "context": "Weather safety explanation", "keywords": ["safety", "weather", "waves", "closed", "conditions", "risk", "reopen", "announcement"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain the safety reasoning clearly and politely."},
                {"cefr_band": "advanced", "prompt": "Report to bridge: 'Equipment issue spotted during deck inspection.' Make proper report.", "context": "Safety equipment report to bridge", "keywords": ["report", "spotted", "equipment", "location", "inspection", "require", "maintenance", "safety"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should report clearly with location and nature of issue."},
                {"cefr_band": "advanced", "prompt": "During a lifeboat drill, explain to junior crew members the correct procedure for launching a lifeboat.", "context": "Emergency drill training", "keywords": ["lifeboat", "davit", "lower", "capacity", "procedure", "safety", "crew", "passengers", "order"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should describe the launch procedure accurately and completely."}
            ],
            "Engine Department": [
                {"cefr_band": "basic", "prompt": "A new crew member asks: 'What safety equipment do I need in the engine room?' Explain the requirements.", "context": "PPE requirements explanation", "keywords": ["hard hat", "boots", "glasses", "gloves", "ear protection", "safety", "required"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should list all required PPE clearly."},
                {"cefr_band": "intermediate", "prompt": "A colleague asks: 'The auxiliary engine oil pressure is dropping slowly. What should we do?' Advise them.", "context": "Engine diagnostics discussion", "keywords": ["pressure", "check", "monitor", "report", "chief engineer", "level", "leak", "log"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should advise on diagnostic steps and reporting."},
                {"cefr_band": "advanced", "prompt": "Inform chief engineer: 'Unusual temperature reading in main engine.' Report the situation.", "context": "Equipment anomaly report", "keywords": ["temperature", "unusual", "reading", "engine", "monitoring", "check", "normal range", "investigate"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should provide specific details and current status."},
                {"cefr_band": "advanced", "prompt": "Explain the procedure for switching from heavy fuel oil to marine diesel oil when entering an emission control area.", "context": "Fuel changeover procedure", "keywords": ["switchover", "emission", "control area", "diesel", "heavy fuel", "temperature", "viscosity", "timeline", "log"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should describe the technical fuel changeover procedure."}
            ],
            "Medical Department": [
                {"cefr_band": "basic", "prompt": "A guest says: 'I have a headache and need some medicine.' Help them.", "context": "Basic medical request", "keywords": ["medical center", "painkiller", "rest", "water", "visit", "help", "doctor"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should offer immediate guidance and direct to medical center."},
                {"cefr_band": "intermediate", "prompt": "A guest says: 'I feel unwell and need to see a nurse.' Respond appropriately.", "context": "Guest requests medical attention", "keywords": ["medical center", "sick call", "nurse", "doctor", "assist", "location", "urgent", "help"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should direct guest to medical center and offer assistance."},
                {"cefr_band": "intermediate", "prompt": "A parent asks: 'My child fell and cut their knee. Where can they get first aid?' Respond calmly.", "context": "Child injury response", "keywords": ["medical center", "first aid", "nurse", "clean", "bandage", "deck 1", "accompany", "calm"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should provide calm guidance and direct to medical center."},
                {"cefr_band": "advanced", "prompt": "Explain to a guest why they need to be medically evacuated at the next port and what the process involves.", "context": "Medical evacuation explanation", "keywords": ["condition", "beyond", "capabilities", "hospital", "helicopter", "coast guard", "insurance", "documentation", "safe"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should explain the medical reasoning and process sensitively."}
            ],
            "Security Department": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'I forgot my key card. Can I still get back to my room?' Help them.", "context": "Access without key card", "keywords": ["Guest Services", "ID", "verify", "replacement", "deck", "escort", "help"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain verification and replacement process."},
                {"cefr_band": "intermediate", "prompt": "A guest says: 'Someone stole my watch from the pool area.' Take the report.", "context": "Theft report at pool", "keywords": ["report", "describe", "when", "where", "details", "investigate", "CCTV", "form"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should collect details and explain investigation process."},
                {"cefr_band": "advanced", "prompt": "A guest reports: 'I saw someone acting suspiciously near the pool.' Respond professionally.", "context": "Security concern reported by guest", "keywords": ["thank you", "report", "investigate", "describe", "location", "safety", "patrol", "monitor"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should acknowledge concern and explain action to be taken."},
                {"cefr_band": "advanced", "prompt": "Brief your security team on enhanced screening procedures for a high-profile event onboard tonight.", "context": "Security team briefing", "keywords": ["enhanced", "screening", "VIP", "access", "checkpoints", "protocol", "communication", "perimeter", "alert"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present clear security protocol for the event."}
            ],
            "Table Games": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'How do I buy chips to play?' Explain the process.", "context": "Chip purchase inquiry", "keywords": ["cashier", "cage", "cash", "chips", "exchange", "table", "minimum"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the chip exchange process simply."},
                {"cefr_band": "intermediate", "prompt": "A new guest asks: 'I've never played blackjack. Can you explain?' Teach the basics.", "context": "Teaching game rules to new player", "keywords": ["objective", "21", "cards", "dealer", "hit", "stand", "rules", "simple", "try"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain basic rules clearly and encourage participation."},
                {"cefr_band": "intermediate", "prompt": "A guest disputes a hand result at the poker table and says: 'That's not right, I should have won.' Handle it.", "context": "Gaming dispute resolution", "keywords": ["understand", "review", "camera", "supervisor", "rules", "fair", "resolve", "policy"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should remain calm, explain the ruling, and offer supervisor review."},
                {"cefr_band": "advanced", "prompt": "A pit supervisor asks you to explain the proper procedure for handling a suspected card counter at the blackjack table.", "context": "Surveillance and compliance discussion", "keywords": ["observation", "betting pattern", "notify", "surveillance", "shuffle", "procedure", "discretion", "policy"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should describe the identification and handling procedure professionally."}
            ],
            "Casino Services": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'How do I use this slot machine?' Show them how to play.", "context": "Slot machine instruction", "keywords": ["insert", "card", "cash", "button", "spin", "pay table", "win", "lines"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain slot machine basics clearly."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'What are the benefits of joining your loyalty program?' Explain the program.", "context": "Loyalty program explanation", "keywords": ["benefits", "points", "rewards", "tiers", "complimentary", "exclusive", "earn", "redeem"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should highlight benefits and explain how to earn rewards."},
                {"cefr_band": "intermediate", "prompt": "A guest says: 'This slot machine took my money but didn't credit my play.' Help resolve the issue.", "context": "Machine malfunction complaint", "keywords": ["sorry", "technician", "check", "refund", "log", "receipt", "resolve", "machine number"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize and explain the resolution process."},
                {"cefr_band": "advanced", "prompt": "A guest shows signs of problem gambling—chasing losses and becoming agitated. How do you approach the situation?", "context": "Responsible gaming intervention", "keywords": ["concern", "break", "limit", "self-exclusion", "support", "helpline", "private", "respectful", "policy"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should approach with sensitivity and follow responsible gaming procedures."}
            ]
        }

        raw = _require(speaking_prompts, scenario_key, "speaking prompts")
        return _filter_scenarios_by_band(raw, cefr_level)

    def save_to_json(self, output_path: str):
        """Save generated questions to JSON file (loader-compatible format)"""

        output_data = {
            "metadata": {
                "title": "Cruise Employee English Assessment Question Bank",
                "version": "2.0",
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "total_questions": len(self.questions),
                "departments": DEPARTMENT_COUNT,
                "questions_per_department": 100,
                "modules": ["Listening", "Time & Numbers", "Grammar", "Vocabulary", "Reading", "Speaking"],
                "cefr_levels": CEFR_LEVELS
            },
            "statistics": {
                "total_questions": len(self.questions),
                "by_division": {
                    "hotel": len([q for q in self.questions if q.get("division") == "hotel"]),
                    "marine": len([q for q in self.questions if q.get("division") == "marine"])
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
        print(f"  - Hotel: {output_data['statistics']['by_division']['hotel']} questions")
        print(f"  - Marine: {output_data['statistics']['by_division']['marine']} questions")
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

    generator = QuestionBankGenerator()

    print("Generating questions...")
    print("  - 30 departments (26 Hotel + 4 Marine)")
    print("  - 100 questions per department")
    print("  - CEFR levels A1-C2 per module")
    print(f"  - Total: {DEPARTMENT_COUNT * 100:,} questions")
    print()

    questions = generator.generate_all_questions()

    data_dir = Path(__file__).parent
    output_path = data_dir / "question_bank_full.json"
    generator.save_to_json(str(output_path))

    print()
    print("="*70)
    print("Question bank generation complete!")
    print("="*70)


if __name__ == "__main__":
    main()
