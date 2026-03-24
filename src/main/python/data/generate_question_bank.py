"""
Generate Question Bank for Cruise Employee English Assessment Platform

Generates 3,000 questions across 30 departments:
- 100 questions per department
- CEFR distribution per module (A1-C2)
- Output format compatible with question_bank_loader.py
"""

import json
import random
import re
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

# Align with assessment_engine stopword filtering for keyword extraction from repeat audio
_SPEAKING_KEYWORD_STOPWORDS = frozenset(
    {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our",
        "out", "day", "get", "has", "him", "his", "how", "its", "let", "may", "new", "now", "old",
        "see", "two", "way", "who", "did", "she", "too", "use", "from", "that", "this", "with",
        "have", "will", "your", "been", "said", "each", "which", "their", "time", "would", "there",
        "could", "other", "about", "into", "more", "than", "then", "them", "these", "please", "remember",
        "bring", "during", "name", "good", "morning", "what", "when", "where", "very",
    }
)


def _keywords_from_repeat_audio(text: str, max_kw: int = 12) -> List[str]:
    """Derive scoring keywords from the phrase the user must repeat (same idea as engine)."""
    words = re.findall(r"[A-Za-z]{3,}", (text or "").lower())
    out: List[str] = []
    seen = set()
    for w in words:
        if w in _SPEAKING_KEYWORD_STOPWORDS or w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= max_kw:
            break
    return out if out else ["repeat", "clearly", "phrase"]


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
    "Spa & Wellness": [
        ("basic", "Facial", "Skin cleansing treatment"),
        ("basic", "Massage", "Body pressure therapy"),
        ("basic", "Sauna", "Heated steam room"),
        ("basic", "Towel", "Drying fabric piece"),
        ("basic", "Lotion", "Skin moisturizing cream"),
        ("basic", "Robe", "Spa covering garment"),
        ("basic", "Appointment", "Scheduled booking time"),
        ("basic", "Relaxation", "Calm restful state"),
        ("intermediate", "Aromatherapy", "Essential oil treatment"),
        ("intermediate", "Exfoliation", "Dead skin removal"),
        ("intermediate", "Hydrotherapy", "Therapeutic water treatment"),
        ("intermediate", "Detox wrap", "Body cleansing wrap"),
        ("intermediate", "Acupressure", "Pressure point therapy"),
        ("intermediate", "Thermal suite", "Heated wellness area"),
        ("intermediate", "Reflexology", "Foot pressure therapy"),
        ("intermediate", "Deep tissue", "Firm muscle massage"),
        ("advanced", "Thalassotherapy", "Seawater healing treatment"),
        ("advanced", "Microdermabrasion", "Skin resurfacing procedure"),
        ("advanced", "Lymphatic drainage", "Fluid circulation massage"),
        ("advanced", "Dermal infusion", "Skin nutrient delivery"),
    ],
    "Entertainment Technical": [
        ("basic", "Spotlight", "Focused stage light"),
        ("basic", "Microphone", "Voice amplification device"),
        ("basic", "Speaker", "Sound output unit"),
        ("basic", "Cable", "Electrical connecting wire"),
        ("basic", "Dimmer", "Light brightness control"),
        ("basic", "Curtain", "Stage covering fabric"),
        ("basic", "Backdrop", "Rear stage scenery"),
        ("basic", "Volume", "Sound level setting"),
        ("intermediate", "Rigging", "Overhead suspension system"),
        ("intermediate", "Soundcheck", "Pre-show audio test"),
        ("intermediate", "Mixing console", "Audio control board"),
        ("intermediate", "Fog machine", "Stage haze generator"),
        ("intermediate", "LED panel", "Light display screen"),
        ("intermediate", "Cue sheet", "Technical timing list"),
        ("intermediate", "Stage plot", "Equipment layout diagram"),
        ("intermediate", "Wireless receiver", "Signal pickup device"),
        ("advanced", "Truss system", "Structural lighting framework"),
        ("advanced", "Fly gallery", "Overhead rigging platform"),
        ("advanced", "Line array", "Vertical speaker configuration"),
        ("advanced", "DMX protocol", "Lighting control signal"),
    ],
    "Entertainment": [
        ("basic", "Performer", "Stage show artist"),
        ("basic", "Rehearsal", "Practice session time"),
        ("basic", "Audience", "Show watching guests"),
        ("basic", "Costume", "Performance wearing outfit"),
        ("basic", "Schedule", "Daily activity plan"),
        ("basic", "Trivia", "Quiz knowledge game"),
        ("basic", "Deck party", "Outdoor pool event"),
        ("basic", "Emcee", "Show hosting person"),
        ("intermediate", "Choreography", "Planned dance movements"),
        ("intermediate", "Set list", "Performance song order"),
        ("intermediate", "Cruise director", "Entertainment department head"),
        ("intermediate", "Poolside activity", "Outdoor guest event"),
        ("intermediate", "Variety show", "Mixed talent performance"),
        ("intermediate", "Guest engagement", "Passenger interaction activity"),
        ("intermediate", "Port talk", "Destination information presentation"),
        ("intermediate", "Production cast", "Main show performers"),
        ("advanced", "Residency contract", "Multi-voyage employment term"),
        ("advanced", "Headliner act", "Featured solo performer"),
        ("advanced", "Technical rehearsal", "Full production runthrough"),
        ("advanced", "Crowd management", "Audience flow control"),
    ],
    "Fleet Finance": [
        ("basic", "Payroll", "Employee wage payments"),
        ("basic", "Invoice", "Bill for services"),
        ("basic", "Cash float", "Starting register money"),
        ("basic", "Revenue", "Income from sales"),
        ("basic", "Petty cash", "Small expense fund"),
        ("basic", "Receipt", "Proof of payment"),
        ("basic", "Tip distribution", "Gratuity sharing process"),
        ("basic", "Safe drop", "Depositing excess cash"),
        ("intermediate", "Port charges", "Harbor docking fees"),
        ("intermediate", "Onboard account", "Guest spending record"),
        ("intermediate", "Variance report", "Difference analysis document"),
        ("intermediate", "Crew deduction", "Payroll withheld amount"),
        ("intermediate", "General ledger", "Master financial record"),
        ("intermediate", "Disbursement", "Authorized fund payment"),
        ("intermediate", "Voyage revenue", "Per-trip earnings total"),
        ("intermediate", "Reconciliation", "Balancing financial records"),
        ("advanced", "Intercompany transfer", "Cross-entity fund movement"),
        ("advanced", "Accrued liability", "Unpaid recognized expense"),
        ("advanced", "Foreign exchange hedge", "Currency risk protection"),
        ("advanced", "Amortization schedule", "Gradual cost allocation"),
    ],
    "Guest Technology": [
        ("basic", "WiFi hotspot", "Wireless internet zone"),
        ("basic", "Login", "Account access entry"),
        ("basic", "Touchscreen", "Finger-operated display"),
        ("basic", "Bandwidth", "Internet speed capacity"),
        ("basic", "Bluetooth", "Short-range wireless connection"),
        ("basic", "Kiosk", "Self-service terminal"),
        ("basic", "Password reset", "Credential recovery process"),
        ("basic", "Streaming", "Continuous media playback"),
        ("intermediate", "Digital signage", "Electronic information displays"),
        ("intermediate", "Guest portal", "Passenger online interface"),
        ("intermediate", "QR code", "Scannable data square"),
        ("intermediate", "Firewall", "Network security barrier"),
        ("intermediate", "Access point", "WiFi signal transmitter"),
        ("intermediate", "Mobile app", "Smartphone software application"),
        ("intermediate", "Satellite link", "Space-based internet connection"),
        ("intermediate", "Network latency", "Signal delay time"),
        ("advanced", "Content filtering", "Blocking restricted websites"),
        ("advanced", "Load balancing", "Traffic distribution management"),
        ("advanced", "VLAN segmentation", "Network partition isolation"),
        ("advanced", "Geo-fencing", "Location-based access control"),
    ],
    "Human Resources": [
        ("basic", "Crew contract", "Employment agreement document"),
        ("basic", "Shore leave", "Time off ashore"),
        ("basic", "Crew mess", "Staff dining area"),
        ("basic", "Sign-on", "Board for duty"),
        ("basic", "Sign-off", "Leave after contract"),
        ("basic", "Crew cabin", "Staff sleeping quarters"),
        ("basic", "Crew payroll", "Wage payment system"),
        ("basic", "Crew list", "Onboard personnel register"),
        ("intermediate", "Repatriation", "Return to home country"),
        ("intermediate", "Grievance procedure", "Formal complaint process"),
        ("intermediate", "Probation period", "Initial evaluation phase"),
        ("intermediate", "Crew welfare", "Staff wellbeing support"),
        ("intermediate", "Embarkation notice", "Boarding instruction document"),
        ("intermediate", "Manning agent", "Crew recruitment agency"),
        ("intermediate", "Rotation schedule", "Contract cycle timetable"),
        ("intermediate", "Performance appraisal", "Staff evaluation review"),
        ("advanced", "Collective bargaining", "Union-negotiated employment terms"),
        ("advanced", "Maritime Labour Convention", "Seafarer rights regulation"),
        ("advanced", "Disciplinary tribunal", "Formal misconduct hearing"),
        ("advanced", "Cross-cultural competency", "Multicultural workplace skill"),
    ],
    "Info Technology": [
        ("basic", "Server room", "Onboard computer centre"),
        ("basic", "Network cable", "Wired data connector"),
        ("basic", "Login credentials", "Username and password"),
        ("basic", "Help desk", "Technical support counter"),
        ("basic", "Backup drive", "Data copy storage"),
        ("basic", "Ethernet port", "Wired network socket"),
        ("basic", "Software update", "Programme version upgrade"),
        ("basic", "Work station", "Desktop computer setup"),
        ("intermediate", "Ship firewall", "Network security barrier"),
        ("intermediate", "Bandwidth allocation", "Internet speed distribution"),
        ("intermediate", "VSAT terminal", "Satellite communication dish"),
        ("intermediate", "Network switch", "Data traffic router"),
        ("intermediate", "Malware scan", "Virus detection check"),
        ("intermediate", "IP address", "Device network identifier"),
        ("intermediate", "System downtime", "Service unavailability period"),
        ("intermediate", "Data encryption", "Information security coding"),
        ("advanced", "Intrusion detection", "Unauthorised access monitor"),
        ("advanced", "Redundant array", "Fault-tolerant disk storage"),
        ("advanced", "Network architecture", "Vessel IT infrastructure design"),
        ("advanced", "Patch management", "Systematic vulnerability repair"),
    ],
    "Infotainment": [
        ("basic", "Remote", "Channel control device"),
        ("basic", "Menu", "On-screen option list"),
        ("basic", "Channel", "Broadcast program selection"),
        ("basic", "Volume", "Sound level adjustment"),
        ("basic", "Display", "Visual output screen"),
        ("basic", "Headphones", "Personal audio device"),
        ("basic", "Guide", "Program listing schedule"),
        ("basic", "Play", "Start media button"),
        ("intermediate", "Interactive TV", "Two-way cabin television"),
        ("intermediate", "On-demand", "Viewer-selected content playback"),
        ("intermediate", "Touchscreen kiosk", "Self-service digital terminal"),
        ("intermediate", "Digital concierge", "Virtual guest assistant"),
        ("intermediate", "Cabin app", "In-room mobile interface"),
        ("intermediate", "Content library", "Stored media collection"),
        ("intermediate", "Wayfinder", "Interactive ship map"),
        ("intermediate", "Smart TV", "Internet-connected cabin television"),
        ("advanced", "Middleware platform", "Content delivery integration"),
        ("advanced", "IPTV system", "Network-based television distribution"),
        ("advanced", "Content management", "Digital media administration"),
        ("advanced", "User analytics", "Viewer behaviour tracking"),
    ],
    "Musicians": [
        ("basic", "Guitar", "Stringed musical instrument"),
        ("basic", "Drums", "Percussion rhythm instrument"),
        ("basic", "Piano", "Keyboard musical instrument"),
        ("basic", "Singer", "Vocal performance artist"),
        ("basic", "Stage", "Performance raised platform"),
        ("basic", "Band", "Group of musicians"),
        ("basic", "Song", "Musical composition piece"),
        ("basic", "Tune", "Adjust instrument pitch"),
        ("intermediate", "Set list", "Planned performance order"),
        ("intermediate", "Sheet music", "Written musical notation"),
        ("intermediate", "Amplifier", "Sound boosting equipment"),
        ("intermediate", "Sound check", "Pre-show audio test"),
        ("intermediate", "Monitor wedge", "Onstage speaker unit"),
        ("intermediate", "Backing track", "Pre-recorded accompaniment audio"),
        ("intermediate", "Repertoire", "Prepared performance collection"),
        ("intermediate", "Lounge act", "Casual venue performer"),
        ("advanced", "Rider clause", "Technical performance requirements"),
        ("advanced", "In-ear monitor", "Personal audio feedback"),
        ("advanced", "Transposition", "Key change arrangement"),
        ("advanced", "Click track", "Synchronisation timing signal"),
    ],
    "Production Staff": [
        ("basic", "Stage", "Show performance area"),
        ("basic", "Costume", "Performance outfit garment"),
        ("basic", "Props", "Stage decorative objects"),
        ("basic", "Curtain", "Stage opening fabric"),
        ("basic", "Makeup", "Facial appearance cosmetics"),
        ("basic", "Cast", "Show performer group"),
        ("basic", "Scene", "Individual show segment"),
        ("basic", "Script", "Written performance dialogue"),
        ("intermediate", "Stage manager", "Production coordination leader"),
        ("intermediate", "Blocking", "Actor movement planning"),
        ("intermediate", "Fly system", "Overhead scenery rigging"),
        ("intermediate", "Quick change", "Rapid costume swap"),
        ("intermediate", "Run sheet", "Show sequence document"),
        ("intermediate", "Wardrobe call", "Costume fitting appointment"),
        ("intermediate", "Understudy", "Backup replacement performer"),
        ("intermediate", "Tech rehearsal", "Full production practice"),
        ("advanced", "Production bible", "Comprehensive show reference"),
        ("advanced", "Strike call", "Set teardown instruction"),
        ("advanced", "Cross-fade", "Overlapping scene transition"),
        ("advanced", "Dramaturgy", "Theatrical structure analysis"),
    ],
    "Shore Excursions": [
        ("basic", "Tour", "Guided group outing"),
        ("basic", "Guide", "Excursion leading person"),
        ("basic", "Ticket", "Tour admission pass"),
        ("basic", "Bus", "Group transport vehicle"),
        ("basic", "Map", "Destination location chart"),
        ("basic", "Camera", "Photo capture device"),
        ("basic", "Port", "Ship docking location"),
        ("basic", "Souvenir", "Travel keepsake memento"),
        ("intermediate", "Excursion waiver", "Liability release form"),
        ("intermediate", "Shore tender", "Port shuttle boat"),
        ("intermediate", "Pier meeting", "Dockside gathering point"),
        ("intermediate", "Cultural tour", "Heritage sightseeing trip"),
        ("intermediate", "Tour manifest", "Participant tracking list"),
        ("intermediate", "Cancellation policy", "Refund terms agreement"),
        ("intermediate", "Private tour", "Exclusive group excursion"),
        ("intermediate", "Adventure excursion", "Active outdoor activity"),
        ("advanced", "Port lecturer", "Destination education speaker"),
        ("advanced", "Concessionaire", "Licensed tour operator"),
        ("advanced", "Risk assessment", "Hazard evaluation protocol"),
        ("advanced", "Indemnification clause", "Legal liability protection"),
    ],
    "Youth Programs": [
        ("basic", "Kids", "Young child guests"),
        ("basic", "Toys", "Children play objects"),
        ("basic", "Games", "Fun structured activities"),
        ("basic", "Crafts", "Creative art projects"),
        ("basic", "Snack", "Light food serving"),
        ("basic", "Nap time", "Rest sleep period"),
        ("basic", "Playground", "Children activity area"),
        ("basic", "Story time", "Book reading session"),
        ("intermediate", "Teen club", "Adolescent social lounge"),
        ("intermediate", "Age group", "Developmental stage bracket"),
        ("intermediate", "Splash zone", "Water play area"),
        ("intermediate", "Scavenger hunt", "Clue-finding group game"),
        ("intermediate", "Parental consent", "Guardian permission form"),
        ("intermediate", "Check-in wristband", "Child identification bracelet"),
        ("intermediate", "Night owl", "Late evening childcare"),
        ("intermediate", "Group leader", "Activity supervision staff"),
        ("advanced", "Safeguarding policy", "Child protection protocol"),
        ("advanced", "Ratio compliance", "Staff-to-child requirement"),
        ("advanced", "Behavioural incident", "Conduct management report"),
        ("advanced", "Allergy action plan", "Emergency dietary protocol"),
    ],
    "Audio Visual Media": [
        ("basic", "Camera", "Video recording device"),
        ("basic", "Screen", "Visual display surface"),
        ("basic", "Projector", "Image display equipment"),
        ("basic", "Speaker", "Audio output device"),
        ("basic", "Cable", "Signal connecting wire"),
        ("basic", "Tripod", "Camera support stand"),
        ("basic", "Record", "Capture media action"),
        ("basic", "Playback", "Recorded media replay"),
        ("intermediate", "Broadcast feed", "Live signal distribution"),
        ("intermediate", "Video switcher", "Multi-source image mixer"),
        ("intermediate", "Media server", "Content storage system"),
        ("intermediate", "Closed caption", "On-screen text subtitle"),
        ("intermediate", "Satellite uplink", "Signal space transmission"),
        ("intermediate", "LED wall", "Large display panel"),
        ("intermediate", "Audio mixer", "Sound channel controller"),
        ("intermediate", "Livestream", "Real-time video broadcast"),
        ("advanced", "Signal routing matrix", "Distribution switching system"),
        ("advanced", "Colour grading", "Visual tone adjustment"),
        ("advanced", "NDI protocol", "Network video transport"),
        ("advanced", "Genlock synchronisation", "Frame timing alignment"),
    ],
    "Onboard Media": [
        ("basic", "Photo", "Captured image picture"),
        ("basic", "Video", "Moving image recording"),
        ("basic", "Printer", "Image output machine"),
        ("basic", "Frame", "Photo display border"),
        ("basic", "Pose", "Photography body position"),
        ("basic", "Smile", "Happy facial expression"),
        ("basic", "Gallery", "Photo display area"),
        ("basic", "Portrait", "Person focused photograph"),
        ("intermediate", "Green screen", "Background replacement setup"),
        ("intermediate", "Photo package", "Bundled image purchase"),
        ("intermediate", "Digital download", "Electronic file delivery"),
        ("intermediate", "Embarkation photo", "Boarding day portrait"),
        ("intermediate", "Formal night", "Elegant portrait session"),
        ("intermediate", "Roving photographer", "Mobile event photographer"),
        ("intermediate", "QR gallery", "Scannable photo collection"),
        ("intermediate", "Souvenir video", "Commemorative trip recording"),
        ("advanced", "Facial recognition", "Automated guest identification"),
        ("advanced", "Revenue per guest", "Photo sales yield metric"),
        ("advanced", "Content watermarking", "Digital ownership marking"),
        ("advanced", "Workflow automation", "Streamlined media processing"),
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
        """Generate listen-and-repeat speaking item: same audio line as listening pool; keyword scoring."""

        question_id = f"{division}_{dept_code}_S_{str(self.question_counter).zfill(3)}"
        self.question_counter += 1

        listening_scenarios = self._get_listening_scenarios(scenario_key, cefr_level)
        scenario = self._pick_scenario(
            listening_scenarios, f"{scenario_key}|speaking_repeat|{cefr_level}"
        )
        audio_text = (scenario.get("audio") or "").strip()
        if not audio_text:
            raise ValueError(f"Listening scenario for {scenario_key} missing audio for speaking repeat")

        expected_keywords = _keywords_from_repeat_audio(audio_text)
        # Match assessment: 3 speaking items → 7 + 7 + 6 = 20 points
        points_cycle = [7, 7, 6]
        points = points_cycle[(q_num - 1) % 3]

        instruction = (
            "Listen to the audio and repeat exactly what you hear. "
            "Your score is based on how many key words you say clearly."
        )

        return {
            "question_id": question_id,
            "department": dept_name,
            "division": division,
            "module_type": "speaking",
            "cefr_level": cefr_level,
            "scenario_id": scenario_id,
            "module": "Speaking",
            "difficulty": "medium",
            "points": points,
            "question_type": "speaking_response",
            "speaking_type": "repeat",
            "question_text": instruction,
            "audio_text": audio_text,
            "expected_keywords": expected_keywords,
            "min_duration": 3,
            "scenario_description": f"Listen-repeat phrase aligned with {scenario_key} listening content.",
            "explanation": "Repeat the played audio accurately; keywords in your response contribute to your score.",
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
            ],
            "Spa & Wellness": [
                {
                    "cefr_band": "basic",
                    "question": "What time is the guest's massage appointment?",
                    "audio": "Welcome to the spa. Do you have an appointment? Yes, I booked a Swedish massage. Let me check. Your appointment is at two-fifteen PM in treatment room three. Perfect, thank you.",
                    "options": ["1:45 PM", "2:00 PM", "2:15 PM", "2:30 PM"],
                    "correct": "2:15 PM",
                    "explanation": "The appointment is at 'two-fifteen PM' (2:15 PM)."
                },
                {
                    "cefr_band": "basic",
                    "question": "How long is the facial treatment?",
                    "audio": "I'd like to book a facial. Our signature facial takes fifty minutes. Is that okay? Fifty minutes sounds perfect. When can I come in?",
                    "options": ["30 minutes", "40 minutes", "50 minutes", "60 minutes"],
                    "correct": "50 minutes",
                    "explanation": "The facial treatment lasts 'fifty minutes'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How much does the couples massage package cost?",
                    "audio": "We'd like the couples massage package. That includes a sixty-minute massage for both of you, access to the thermal suite, and herbal tea. The package is two hundred forty dollars for both guests. Wonderful, we'll take it.",
                    "options": ["$200", "$220", "$240", "$260"],
                    "correct": "$240",
                    "explanation": "The couples package costs 'two hundred forty dollars' ($240)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What temperature should the sauna be set to?",
                    "audio": "The thermal suite is almost ready for opening. What temperature is the sauna at? It's at one hundred seventy degrees Fahrenheit. Standard is one-eighty. Adjust it up ten degrees, please.",
                    "options": ["160°F", "170°F", "180°F", "190°F"],
                    "correct": "170°F",
                    "explanation": "The current sauna temperature is 'one hundred seventy degrees' (170°F)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How many spa appointments need to be rescheduled due to the port day change?",
                    "audio": "We just got word that tomorrow's port schedule changed. We need to move all morning appointments. How many clients are affected? Let me check the system. We have fourteen appointments booked before noon that need rescheduling. I'll start calling them now.",
                    "options": ["12", "13", "14", "15"],
                    "correct": "14",
                    "explanation": "There are 'fourteen appointments' that need rescheduling."
                }
            ],
            "Entertainment Technical": [
                {
                    "cefr_band": "basic",
                    "question": "How many spotlights need new bulbs before tonight's show?",
                    "audio": "Stage crew, lighting check. How are the spotlights? We've got a problem. Three of the front spotlights have burnt-out bulbs. Three? Yes, three need replacing before tonight's show. I'll get the spares.",
                    "options": ["2", "3", "4", "5"],
                    "correct": "3",
                    "explanation": "There are 'three' spotlights that need new bulbs."
                },
                {
                    "cefr_band": "basic",
                    "question": "What time is the sound check scheduled?",
                    "audio": "The band wants to know about the sound check. It's set for three-forty-five PM on the main stage. Three-forty-five. Got it, I'll let them know.",
                    "options": ["3:15 PM", "3:30 PM", "3:45 PM", "4:00 PM"],
                    "correct": "3:45 PM",
                    "explanation": "The sound check is at 'three-forty-five PM' (3:45 PM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What length of cable is needed to reach the new speaker position?",
                    "audio": "We're moving the side speakers for better coverage. How much cable do we need? I measured it. We need seventy-five feet of XLR cable to reach the new position. I'll grab it from the storage room.",
                    "options": ["50 feet", "65 feet", "75 feet", "85 feet"],
                    "correct": "75 feet",
                    "explanation": "The required cable length is 'seventy-five feet'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "Which channel is the lead vocalist's microphone assigned to?",
                    "audio": "Audio check before the show. Where's the lead vocal mic? Lead vocalist is on channel twelve. Background singers are on thirteen and fourteen. Channel twelve for lead, confirmed.",
                    "options": ["Channel 10", "Channel 11", "Channel 12", "Channel 14"],
                    "correct": "Channel 12",
                    "explanation": "The lead vocalist's microphone is on 'channel twelve'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How many DMX universes are being used for the production show lighting?",
                    "audio": "The new production show has complex lighting. How many DMX universes are we running? We've programmed four DMX universes. Universe one and two handle the movers. Three is for the LED wash. Four controls the specials and hazers. That's a lot of fixtures.",
                    "options": ["2", "3", "4", "5"],
                    "correct": "4",
                    "explanation": "The show uses 'four DMX universes'."
                }
            ],
            "Entertainment": [
                {
                    "cefr_band": "basic",
                    "question": "What time does the comedy show start tonight?",
                    "audio": "Good afternoon, guests. Tonight in the main theater we have our featured comedian. What time does it start? The comedy show begins at nine-thirty PM. Doors open at nine-fifteen.",
                    "options": ["9:00 PM", "9:15 PM", "9:30 PM", "10:00 PM"],
                    "correct": "9:30 PM",
                    "explanation": "The comedy show starts at 'nine-thirty PM' (9:30 PM)."
                },
                {
                    "cefr_band": "basic",
                    "question": "How many guests signed up for the dance class?",
                    "audio": "How are registrations for the salsa class today? We have twenty-six guests signed up so far. The maximum is thirty. Should we open a second session? Let's wait and see if it fills up.",
                    "options": ["22", "24", "26", "28"],
                    "correct": "26",
                    "explanation": "There are 'twenty-six guests' registered."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "On which deck is the poolside trivia being held?",
                    "audio": "Attention guests. Our poolside trivia event has been moved due to weather. Instead of deck fourteen, we'll be hosting it in the lounge on deck seven. Deck seven, starting at two PM. Prizes for the top three teams!",
                    "options": ["Deck 5", "Deck 7", "Deck 12", "Deck 14"],
                    "correct": "Deck 7",
                    "explanation": "The trivia was moved to 'deck seven'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many performers are in tonight's production cast?",
                    "audio": "The cruise director wants a cast count for tonight. How many performers do we have? We have eighteen dancers, four lead singers, and two acrobats. So twenty-four total. That's right, twenty-four on stage tonight.",
                    "options": ["20", "22", "24", "26"],
                    "correct": "24",
                    "explanation": "The total cast is 'twenty-four' performers (18 + 4 + 2)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the budget remaining for the guest entertainer's contract rider?",
                    "audio": "The headliner's rider requires specific equipment. Where are we on budget? We've spent eighteen hundred on the sound upgrades. The total rider budget is three thousand. So we have twelve hundred left for the remaining items. That should cover the lighting request.",
                    "options": ["$1,000", "$1,100", "$1,200", "$1,400"],
                    "correct": "$1,200",
                    "explanation": "The remaining budget is 'twelve hundred' dollars ($1,200)."
                }
            ],
            "Fleet Finance": [
                {
                    "cefr_band": "basic",
                    "question": "What is the total revenue from onboard sales reported today?",
                    "audio": "Daily revenue report. What's the total onboard sales figure? Today we recorded forty-five thousand dollars in onboard revenue. That includes shops, spa, and casino. Forty-five thousand, noted.",
                    "options": ["$40,000", "$42,500", "$45,000", "$47,500"],
                    "correct": "$45,000",
                    "explanation": "Total onboard revenue is 'forty-five thousand dollars' ($45,000)."
                },
                {
                    "cefr_band": "basic",
                    "question": "By what date must the port expense reports be submitted?",
                    "audio": "All department heads, reminder: port expense reports for this voyage must be submitted by the fifteenth of the month. No extensions this time. The fifteenth? That's correct.",
                    "options": ["10th", "12th", "15th", "20th"],
                    "correct": "15th",
                    "explanation": "Reports are due 'by the fifteenth' of the month."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "By what percentage did fuel costs exceed the budget this quarter?",
                    "audio": "Let's review the quarterly fuel expenses. We budgeted one point two million but actual costs came in higher. How much over? We exceeded budget by twelve percent due to the rerouting around the storm. Twelve percent over. We'll need to adjust next quarter.",
                    "options": ["8%", "10%", "12%", "15%"],
                    "correct": "12%",
                    "explanation": "Fuel costs exceeded the budget by 'twelve percent'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many crew payroll discrepancies were flagged this pay period?",
                    "audio": "Payroll audit is complete. Any issues? We found seven discrepancies in overtime calculations this pay period. Seven? Yes, mostly in the galley department. I'll send the details for correction.",
                    "options": ["5", "6", "7", "8"],
                    "correct": "7",
                    "explanation": "There are 'seven discrepancies' in payroll."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the projected cost saving from the new vendor contract?",
                    "audio": "The new provisioning vendor contract is finalized. What savings are we looking at? Based on the negotiated rates, we project annual savings of one hundred thirty-five thousand dollars across the fleet. That's significant, especially on fresh produce and dairy.",
                    "options": ["$115,000", "$125,000", "$135,000", "$145,000"],
                    "correct": "$135,000",
                    "explanation": "Projected savings are 'one hundred thirty-five thousand dollars' ($135,000)."
                }
            ],
            "Guest Technology": [
                {
                    "cefr_band": "basic",
                    "question": "What is the WiFi password for the guest network?",
                    "audio": "How do I connect to the ship's WiFi? Select 'CruiseConnect' from your WiFi list. What's the password? The password is SAIL2025. That's S-A-I-L-two-zero-two-five. Thank you.",
                    "options": ["SAIL2024", "SAIL2025", "SHIP2025", "SAIL2026"],
                    "correct": "SAIL2025",
                    "explanation": "The WiFi password is 'SAIL2025'."
                },
                {
                    "cefr_band": "basic",
                    "question": "How many devices can be connected on the premium WiFi plan?",
                    "audio": "I bought the premium WiFi but my tablet won't connect. Let me check. The premium plan allows up to four devices simultaneously. You currently have four connected. You'll need to disconnect one first.",
                    "options": ["2", "3", "4", "5"],
                    "correct": "4",
                    "explanation": "The premium plan allows 'four devices'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "Which app version is required for the digital key feature to work?",
                    "audio": "My cabin door won't open with the app. That feature requires the latest version. What version do you have? Version three-point-one. You need version three-point-five or higher. Let me help you update it.",
                    "options": ["3.1", "3.3", "3.5", "4.0"],
                    "correct": "3.5",
                    "explanation": "The required version is 'three-point-five' (3.5) or higher."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many interactive screens need recalibration on deck six?",
                    "audio": "The wayfinding kiosks on deck six are acting up. How many are affected? I checked all of them. Eight screens need recalibration. The touch sensors are drifting. I'll schedule it for tonight after midnight.",
                    "options": ["6", "7", "8", "9"],
                    "correct": "8",
                    "explanation": "There are 'eight screens' that need recalibration."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What percentage of guests have activated the cruise line's mobile app this voyage?",
                    "audio": "Let's look at the app adoption numbers for this sailing. What's the activation rate? Sixty-three percent of guests have activated the app. That's up from fifty-eight percent last voyage. Good trend, but we need to push the onboard tutorials harder.",
                    "options": ["58%", "60%", "63%", "68%"],
                    "correct": "63%",
                    "explanation": "The activation rate is 'sixty-three percent' (63%)."
                }
            ],
            "Human Resources": [
                {
                    "cefr_band": "basic",
                    "question": "How many new crew members are joining at the next port?",
                    "audio": "HR update for the next embarkation. How many new crew? We have sixteen new crew members arriving in Miami. Sixteen? Yes. Eight for the hotel department and eight for food and beverage.",
                    "options": ["12", "14", "16", "18"],
                    "correct": "16",
                    "explanation": "There are 'sixteen new crew members' joining."
                },
                {
                    "cefr_band": "basic",
                    "question": "What time is the crew safety orientation tomorrow?",
                    "audio": "All new crew must attend safety orientation. When is it? Tomorrow at eight-forty-five AM in the crew mess. Don't be late. Eight-forty-five sharp.",
                    "options": ["8:15 AM", "8:30 AM", "8:45 AM", "9:00 AM"],
                    "correct": "8:45 AM",
                    "explanation": "The orientation is at 'eight-forty-five AM' (8:45 AM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many vacation days has the crew member accumulated?",
                    "audio": "I'd like to check my leave balance. Let me pull up your file. You've accumulated twenty-three vacation days. And how many have I used? You've used eleven so far this contract. So I have twelve remaining.",
                    "options": ["21", "22", "23", "24"],
                    "correct": "23",
                    "explanation": "The crew member has accumulated 'twenty-three vacation days'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the deadline for completing the online compliance training?",
                    "audio": "HR reminder: all crew must complete the updated compliance training modules. What's the deadline? March thirty-first. No exceptions. Anyone who misses the deadline will be flagged.",
                    "options": ["March 15th", "March 21st", "March 31st", "April 15th"],
                    "correct": "March 31st",
                    "explanation": "The deadline is 'March thirty-first'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the crew retention rate for this quarter?",
                    "audio": "Quarterly crew retention numbers are in. How are we doing? Our retention rate this quarter is eighty-seven percent. That's a two percent improvement over last quarter's eighty-five. The new welfare programs seem to be working. Let's keep the momentum going.",
                    "options": ["83%", "85%", "87%", "89%"],
                    "correct": "87%",
                    "explanation": "The retention rate is 'eighty-seven percent' (87%)."
                }
            ],
            "Info Technology": [
                {
                    "cefr_band": "basic",
                    "question": "How many help desk tickets are open right now?",
                    "audio": "IT help desk status report. How many tickets are currently open? We have thirty-two open tickets. Most are WiFi related. The rest are POS system issues. Thirty-two, got it.",
                    "options": ["28", "30", "32", "35"],
                    "correct": "32",
                    "explanation": "There are 'thirty-two open tickets'."
                },
                {
                    "cefr_band": "basic",
                    "question": "On which deck is the server room located?",
                    "audio": "I need to reboot the backup server. Where is it? The main server room is on deck two, forward section. You'll need your access badge. Deck two, forward. On my way.",
                    "options": ["Deck 1", "Deck 2", "Deck 3", "Deck 4"],
                    "correct": "Deck 2",
                    "explanation": "The server room is on 'deck two'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What time is the scheduled system maintenance window tonight?",
                    "audio": "We need to push the POS update tonight. What's the maintenance window? Maintenance window is from two AM to four AM. That gives us two hours. Will that be enough? Should be, if we pre-stage the update.",
                    "options": ["1 AM to 3 AM", "2 AM to 4 AM", "3 AM to 5 AM", "12 AM to 2 AM"],
                    "correct": "2 AM to 4 AM",
                    "explanation": "The maintenance window is 'two AM to four AM'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many access points went offline during the network issue?",
                    "audio": "We had a network blip on deck ten. How many access points dropped? Eleven access points went offline for about three minutes. They've all recovered now. Eleven APs, three-minute outage. I'll document it.",
                    "options": ["9", "10", "11", "12"],
                    "correct": "11",
                    "explanation": "There were 'eleven access points' that went offline."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the current network bandwidth utilization at peak hours?",
                    "audio": "Network performance review. What's the bandwidth situation during peak times? We're hitting seventy-eight percent utilization between eight and ten PM. That's close to saturation. We may need to throttle streaming if it hits eighty-five percent.",
                    "options": ["72%", "75%", "78%", "82%"],
                    "correct": "78%",
                    "explanation": "Peak bandwidth utilization is 'seventy-eight percent' (78%)."
                }
            ],
            "Infotainment": [
                {
                    "cefr_band": "basic",
                    "question": "How many TV channels are available in the guest cabins?",
                    "audio": "A guest is asking about the TV service. How many channels do we offer? We currently have sixty-five channels available in guest cabins. That includes live satellite, movies on demand, and ship information. Sixty-five channels.",
                    "options": ["55", "60", "65", "70"],
                    "correct": "65",
                    "explanation": "There are 'sixty-five channels' available."
                },
                {
                    "cefr_band": "basic",
                    "question": "What time does the movie on the pool deck screen start?",
                    "audio": "What's showing on the big screen tonight? We're playing the new action movie at eight-fifteen PM on the pool deck. Popcorn and blankets available. Eight-fifteen. Great, we'll be there.",
                    "options": ["8:00 PM", "8:15 PM", "8:30 PM", "9:00 PM"],
                    "correct": "8:15 PM",
                    "explanation": "The movie starts at 'eight-fifteen PM' (8:15 PM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many cabins reported issues with the interactive TV system?",
                    "audio": "The interactive TV menu isn't loading properly on some cabins. How widespread is it? We've received reports from twenty-seven cabins so far. All on deck eight. Looks like a local switch issue. I'll check the distribution panel.",
                    "options": ["23", "25", "27", "30"],
                    "correct": "27",
                    "explanation": "There are 'twenty-seven cabins' with the issue."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "On which channel is the port information broadcast?",
                    "audio": "Guests keep asking where to find the port guide on TV. Which channel is it? Port information and shore excursion previews are on channel forty-two. We should add an announcement. Good idea.",
                    "options": ["Channel 38", "Channel 40", "Channel 42", "Channel 44"],
                    "correct": "Channel 42",
                    "explanation": "Port information is on 'channel forty-two'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How many gigabytes of content were uploaded to the video-on-demand server for this voyage?",
                    "audio": "The new content library is loaded for this sailing. How much did we add? We uploaded three hundred twenty gigabytes of new movies, shows, and documentaries. That brings our total library to about one-point-two terabytes. Guests should have plenty to watch.",
                    "options": ["280 GB", "300 GB", "320 GB", "350 GB"],
                    "correct": "320 GB",
                    "explanation": "The upload was 'three hundred twenty gigabytes' (320 GB)."
                }
            ],
            "Musicians": [
                {
                    "cefr_band": "basic",
                    "question": "What time is the jazz trio's first set in the lounge?",
                    "audio": "What's the schedule for the jazz trio tonight? First set starts at seven-forty-five PM in the Sky Lounge. Second set at nine-thirty. Seven-forty-five. We'll start setting up at seven.",
                    "options": ["7:15 PM", "7:30 PM", "7:45 PM", "8:00 PM"],
                    "correct": "7:45 PM",
                    "explanation": "The first set is at 'seven-forty-five PM' (7:45 PM)."
                },
                {
                    "cefr_band": "basic",
                    "question": "How many songs are on the setlist for the pool deck performance?",
                    "audio": "The pool deck set. How many songs are you playing? We've got fifteen songs on the list. Should take about ninety minutes with breaks. Fifteen songs, sounds good.",
                    "options": ["12", "13", "15", "18"],
                    "correct": "15",
                    "explanation": "There are 'fifteen songs' on the setlist."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "In which key does the singer want the next song transposed to?",
                    "audio": "Can we change the key on that ballad? The original key is too high for me tonight. What key would you prefer? Let's bring it down to G major. G major, got it. I'll adjust the chart.",
                    "options": ["E major", "F major", "G major", "A major"],
                    "correct": "G major",
                    "explanation": "The singer requests the song be transposed to 'G major'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many musicians are needed for the captain's gala performance?",
                    "audio": "The captain's gala needs a larger ensemble. How many musicians do we need? We need nine musicians total. Five from the house band plus four string players for the classical pieces. Nine total, I'll confirm availability.",
                    "options": ["7", "8", "9", "10"],
                    "correct": "9",
                    "explanation": "The gala requires 'nine musicians' total."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What tempo in BPM does the musical director want for the opening number?",
                    "audio": "The opening number felt sluggish last night. What tempo were we at? We played it at one hundred twelve BPM. The director wants it at one hundred twenty-six BPM for more energy. One-twenty-six, that's a big jump. We'll rehearse it faster.",
                    "options": ["118 BPM", "122 BPM", "126 BPM", "130 BPM"],
                    "correct": "126 BPM",
                    "explanation": "The desired tempo is 'one hundred twenty-six BPM' (126 BPM)."
                }
            ],
            "Production Staff": [
                {
                    "cefr_band": "basic",
                    "question": "How many costume changes are in tonight's production show?",
                    "audio": "Wardrobe, how many quick changes do we have tonight? Seven costume changes for the lead and five for the ensemble. Seven for the lead. I'll have everything laid out backstage.",
                    "options": ["5", "6", "7", "8"],
                    "correct": "7",
                    "explanation": "The lead has 'seven costume changes'."
                },
                {
                    "cefr_band": "basic",
                    "question": "What time is the full cast rehearsal?",
                    "audio": "Reminder to all production staff. Full cast rehearsal today at one-thirty PM on the main stage. Be in costume by one-fifteen. One-thirty, main stage. Got it.",
                    "options": ["1:00 PM", "1:15 PM", "1:30 PM", "2:00 PM"],
                    "correct": "1:30 PM",
                    "explanation": "The rehearsal is at 'one-thirty PM' (1:30 PM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many fog machines are needed for the finale scene?",
                    "audio": "The finale needs more atmosphere. How many fog machines should we use? Set up six fog machines across the stage. Two downstage, two mid, and two upstage. Six machines positioned in three rows. I'll get them from storage.",
                    "options": ["4", "5", "6", "8"],
                    "correct": "6",
                    "explanation": "The finale requires 'six fog machines'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many minutes before showtime must the cast be in their opening positions?",
                    "audio": "Stage manager announcement. Cast, your places call will be ten minutes before showtime. I need everyone in opening positions no later than that. Ten minutes before. No exceptions tonight. We had late positions last night.",
                    "options": ["5 minutes", "8 minutes", "10 minutes", "15 minutes"],
                    "correct": "10 minutes",
                    "explanation": "Cast must be ready 'ten minutes' before showtime."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How much does the replacement aerial rigging harness cost?",
                    "audio": "One of the aerial harnesses failed inspection. We need a replacement. What's the cost? The certified replacement harness is two thousand eight hundred dollars. Plus shipping will take five days. Two thousand eight hundred. I'll submit the purchase order today.",
                    "options": ["$2,400", "$2,600", "$2,800", "$3,200"],
                    "correct": "$2,800",
                    "explanation": "The replacement harness costs 'two thousand eight hundred dollars' ($2,800)."
                }
            ],
            "Shore Excursions": [
                {
                    "cefr_band": "basic",
                    "question": "How much does the snorkeling excursion cost per person?",
                    "audio": "I'm interested in the snorkeling trip. That's our most popular excursion. It includes equipment and a guide. How much? Eighty-nine dollars per person. Eighty-nine, not bad. Sign us up for two.",
                    "options": ["$79", "$85", "$89", "$95"],
                    "correct": "$89",
                    "explanation": "The excursion costs 'eighty-nine dollars' ($89) per person."
                },
                {
                    "cefr_band": "basic",
                    "question": "What time do the buses depart for the city tour?",
                    "audio": "Guests booked on the city tour, please note. Buses depart at nine-fifteen AM from the pier. Please be there ten minutes early. Nine-fifteen departure. Don't be late, the bus won't wait.",
                    "options": ["8:45 AM", "9:00 AM", "9:15 AM", "9:30 AM"],
                    "correct": "9:15 AM",
                    "explanation": "Buses depart at 'nine-fifteen AM' (9:15 AM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many guests are booked on the catamaran sailing tour?",
                    "audio": "Shore excursion desk. What's the count for the catamaran? We have thirty-eight guests confirmed for the catamaran sailing tour. Maximum capacity is forty. Should we close bookings? Leave it open for two more spots.",
                    "options": ["34", "36", "38", "40"],
                    "correct": "38",
                    "explanation": "There are 'thirty-eight guests' booked."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "By what time must all guests return to the ship?",
                    "audio": "Important announcement for guests going ashore in Cozumel. The ship departs at five PM. All aboard time is four-thirty PM. Repeat, all guests must be back on board by four-thirty PM. No exceptions.",
                    "options": ["4:00 PM", "4:15 PM", "4:30 PM", "5:00 PM"],
                    "correct": "4:30 PM",
                    "explanation": "All aboard time is 'four-thirty PM' (4:30 PM)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What is the refund amount for the cancelled helicopter tour?",
                    "audio": "The helicopter tour was cancelled due to weather. We need to process refunds. How much per guest? The helicopter tour was one hundred ninety-five dollars per person. All forty-two guests get a full refund. That's eight thousand one hundred ninety total.",
                    "options": ["$175", "$185", "$195", "$205"],
                    "correct": "$195",
                    "explanation": "The refund amount is 'one hundred ninety-five dollars' ($195) per person."
                }
            ],
            "Youth Programs": [
                {
                    "cefr_band": "basic",
                    "question": "How many children are registered for the kids club today?",
                    "audio": "Morning count for the kids club. How many do we have today? We have thirty-four children registered. Twenty-two in the six-to-nine group and twelve in the ten-to-twelve group. Thirty-four total. We'll need three counselors.",
                    "options": ["30", "32", "34", "36"],
                    "correct": "34",
                    "explanation": "There are 'thirty-four children' registered."
                },
                {
                    "cefr_band": "basic",
                    "question": "What time does the teen zone close tonight?",
                    "audio": "Parents, the teen zone hours for tonight. We're open until eleven PM for ages thirteen to seventeen. Eleven PM? That's right. Supervised activities all evening. Pickup by eleven, please.",
                    "options": ["10:00 PM", "10:30 PM", "11:00 PM", "11:30 PM"],
                    "correct": "11:00 PM",
                    "explanation": "The teen zone closes at 'eleven PM' (11:00 PM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the minimum age for the rock climbing activity?",
                    "audio": "My son wants to do the rock climbing. Is there an age limit? Yes, the minimum age for the rock wall is eight years old. And they must be at least forty-eight inches tall. He's nine, so the age is fine. We just need to check his height.",
                    "options": ["6 years", "7 years", "8 years", "10 years"],
                    "correct": "8 years",
                    "explanation": "The minimum age is 'eight years old'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many counselors are required for the waterslide party?",
                    "audio": "We're planning the waterslide party for Saturday. How many staff do we need? Safety protocol requires five counselors for the waterslide area. Plus two at the check-in table. So seven total staff? Five at the slides, two at check-in, seven total.",
                    "options": ["5", "6", "7", "8"],
                    "correct": "7",
                    "explanation": "The total staff needed is 'seven' (5 + 2)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "What percentage of families with children have enrolled in the kids program this voyage?",
                    "audio": "Enrollment stats for the youth programs. What are we seeing? Out of all families with children on board, seventy-one percent have enrolled in at least one program. That's above our target of sixty-five percent. Great work, team. The pirate-theme nights really boosted sign-ups.",
                    "options": ["65%", "68%", "71%", "75%"],
                    "correct": "71%",
                    "explanation": "The enrollment rate is 'seventy-one percent' (71%)."
                }
            ],
            "Audio Visual Media": [
                {
                    "cefr_band": "basic",
                    "question": "How many projectors need to be set up for tomorrow's conference?",
                    "audio": "There's a corporate group using the conference center tomorrow. What AV equipment do they need? They've requested four projectors, one for each breakout room, and screens. Four projectors. I'll pull them from inventory tonight.",
                    "options": ["2", "3", "4", "5"],
                    "correct": "4",
                    "explanation": "They need 'four projectors' for the event."
                },
                {
                    "cefr_band": "basic",
                    "question": "What size screen is needed for the main presentation?",
                    "audio": "The main conference room needs a large screen. What size? The client requested a twelve-foot screen for the keynote presentation. Twelve feet. I'll set up the portable frame after dinner.",
                    "options": ["8-foot", "10-foot", "12-foot", "15-foot"],
                    "correct": "12-foot",
                    "explanation": "The screen size is 'twelve-foot'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many wireless microphones are being used for the panel discussion?",
                    "audio": "The panel discussion in the atrium needs microphones. How many panelists? There are six panelists plus a moderator. So we need seven wireless handhelds. Check the batteries on all of them. Seven handhelds, fresh batteries. On it.",
                    "options": ["5", "6", "7", "8"],
                    "correct": "7",
                    "explanation": "They need 'seven wireless' microphones (6 panelists + 1 moderator)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What resolution does the client want for the video recording?",
                    "audio": "The corporate group wants their event recorded. What specs? They need it in four-K resolution with two camera angles. We can handle that. Four-K, two cameras. I'll set up the tripods in the morning.",
                    "options": ["1080p", "2K", "4K", "8K"],
                    "correct": "4K",
                    "explanation": "The requested resolution is 'four-K' (4K)."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How many hours of raw footage were captured from the ship's promotional video shoot?",
                    "audio": "The promotional shoot wrapped up today. How much footage did we get? We captured twenty-two hours of raw footage over three days. Aerial drone shots, guest testimonials, and venue walkthroughs. Twenty-two hours to edit down to a three-minute video. That's going to be a project.",
                    "options": ["18 hours", "20 hours", "22 hours", "25 hours"],
                    "correct": "22 hours",
                    "explanation": "They captured 'twenty-two hours' of raw footage."
                }
            ],
            "Onboard Media": [
                {
                    "cefr_band": "basic",
                    "question": "How many copies of the daily newsletter need to be printed?",
                    "audio": "Good morning. How many copies of today's Cruise Compass do we need? We have three thousand two hundred guests on board. Print three thousand five hundred copies to be safe. Three thousand five hundred, starting the print run now.",
                    "options": ["3,000", "3,200", "3,500", "4,000"],
                    "correct": "3,500",
                    "explanation": "They need 'three thousand five hundred' copies printed."
                },
                {
                    "cefr_band": "basic",
                    "question": "By what time must the daily schedule be delivered to all cabins?",
                    "audio": "When do the daily schedules need to be at every cabin? They must be delivered by six AM before guests wake up. Six AM? That's early. We'll start distribution at five-thirty.",
                    "options": ["5:30 AM", "6:00 AM", "6:30 AM", "7:00 AM"],
                    "correct": "6:00 AM",
                    "explanation": "The delivery deadline is 'six AM' (6:00 AM)."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "How many photographs did the onboard media team take at last night's gala?",
                    "audio": "How did the gala coverage go last night? We got great shots. How many photos total? Four hundred eighty-five photographs from the event. The captain's table photos alone were two hundred. That's a good night. Start processing the best ones for the gallery.",
                    "options": ["385", "425", "485", "520"],
                    "correct": "485",
                    "explanation": "The team took 'four hundred eighty-five photographs'."
                },
                {
                    "cefr_band": "intermediate",
                    "question": "What is the deadline for submitting content to the ship's morning show?",
                    "audio": "If any department has announcements for the morning TV show, when's the cutoff? All content must be submitted by ten PM the night before. Ten PM, that's strict. We need time to edit and produce the segment overnight.",
                    "options": ["8 PM", "9 PM", "10 PM", "11 PM"],
                    "correct": "10 PM",
                    "explanation": "The submission deadline is 'ten PM'."
                },
                {
                    "cefr_band": "advanced",
                    "question": "How many social media posts were published across all platforms during this voyage?",
                    "audio": "Social media wrap-up for the seven-day voyage. What are the numbers? We published one hundred forty-three posts across all platforms. Instagram had the highest engagement. Facebook and TikTok were strong too. One hundred forty-three total, with an average engagement rate of four-point-seven percent.",
                    "options": ["128", "135", "143", "156"],
                    "correct": "143",
                    "explanation": "There were 'one hundred forty-three posts' published."
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
            ],
            "Spa & Wellness": [
                {"cefr_band": "basic", "question": "A hot stone massage costs $___.", "context": "$129", "answer": "129", "explanation": "Treatment pricing."},
                {"cefr_band": "basic", "question": "Facial treatment takes ___ minutes.", "context": "60 minutes", "answer": "60", "explanation": "Standard facial duration."},
                {"cefr_band": "intermediate", "question": "Couples package: $___ for 2 guests.", "context": "$349", "answer": "349", "explanation": "Couples spa bundle pricing."},
                {"cefr_band": "intermediate", "question": "Sauna temperature set to ___°F.", "context": "185°F", "answer": "185", "explanation": "Sauna operating temperature."},
                {"cefr_band": "advanced", "question": "Spa revenue target: $___ per sea day.", "context": "$8,500 revenue", "answer": "8500", "explanation": "Daily revenue target."}
            ],
            "Entertainment Technical": [
                {"cefr_band": "basic", "question": "Sound check at ___ PM.", "context": "3:00 PM", "answer": "3:00", "explanation": "Pre-show sound check time."},
                {"cefr_band": "basic", "question": "Stage lights: ___ fixtures total.", "context": "48 fixtures", "answer": "48", "explanation": "Lighting rig count."},
                {"cefr_band": "intermediate", "question": "Audio level set to ___ decibels.", "context": "92 dB", "answer": "92", "explanation": "Performance volume level."},
                {"cefr_band": "intermediate", "question": "LED wall resolution: ___x1080 pixels.", "context": "1920x1080", "answer": "1920", "explanation": "Display resolution width."},
                {"cefr_band": "advanced", "question": "Rigging load capacity: ___ kg.", "context": "2,400 kg", "answer": "2400", "explanation": "Structural weight limit for overhead rigging."}
            ],
            "Entertainment": [
                {"cefr_band": "basic", "question": "Main show starts at ___ PM.", "context": "8:30 PM", "answer": "8:30", "explanation": "Evening showtime."},
                {"cefr_band": "basic", "question": "Comedy club seats ___ guests.", "context": "150 guests", "answer": "150", "explanation": "Venue seating capacity."},
                {"cefr_band": "intermediate", "question": "Deck party runs from 10 PM to ___ AM.", "context": "1:00 AM", "answer": "1:00", "explanation": "Late-night event end time."},
                {"cefr_band": "intermediate", "question": "Cast rehearsal: ___ hours before doors.", "context": "2 hours", "answer": "2", "explanation": "Pre-show rehearsal lead time."},
                {"cefr_band": "advanced", "question": "Guest satisfaction target: ___%.", "context": "92%", "answer": "92", "explanation": "Quality benchmark across the sailing schedule."}
            ],
            "Fleet Finance": [
                {"cefr_band": "basic", "question": "Daily float: $___.", "context": "$5,000", "answer": "5000", "explanation": "Cash register starting float."},
                {"cefr_band": "basic", "question": "End-of-day report due by ___.", "context": "11:00 PM", "answer": "11:00 PM", "explanation": "Nightly financial closing deadline."},
                {"cefr_band": "intermediate", "question": "Currency exchange rate: 1 USD = ___ EUR.", "context": "0.92 EUR", "answer": "0.92", "explanation": "Foreign exchange conversion rate."},
                {"cefr_band": "intermediate", "question": "Onboard revenue this voyage: $___,000.", "context": "$1,250,000", "answer": "1250", "explanation": "Voyage revenue tracking in thousands."},
                {"cefr_band": "advanced", "question": "Variance analysis: bar spend ___% above forecast.", "context": "12% above", "answer": "12", "explanation": "Budget variance percentage against projections."}
            ],
            "Guest Technology": [
                {"cefr_band": "basic", "question": "WiFi password expires in ___ days.", "context": "7 days", "answer": "7", "explanation": "Internet access validity period."},
                {"cefr_band": "basic", "question": "Tech support open until ___ PM.", "context": "10:00 PM", "answer": "10:00", "explanation": "Help desk closing time."},
                {"cefr_band": "intermediate", "question": "Premium WiFi speed: ___ Mbps.", "context": "50 Mbps", "answer": "50", "explanation": "High-speed internet bandwidth."},
                {"cefr_band": "intermediate", "question": "Streaming package: $___ per device per day.", "context": "$20", "answer": "20", "explanation": "Per-device streaming cost."},
                {"cefr_band": "advanced", "question": "Satellite bandwidth allocation: ___ Gbps.", "context": "3.2 Gbps", "answer": "3.2", "explanation": "Ship-wide bandwidth capacity."}
            ],
            "Human Resources": [
                {"cefr_band": "basic", "question": "Contract length: ___ months.", "context": "6 months", "answer": "6", "explanation": "Standard crew contract duration."},
                {"cefr_band": "basic", "question": "Crew muster drill at ___ AM.", "context": "10:30 AM", "answer": "10:30", "explanation": "Mandatory safety drill time."},
                {"cefr_band": "intermediate", "question": "Annual leave: ___ days after 2 contracts.", "context": "60 days", "answer": "60", "explanation": "Earned vacation entitlement."},
                {"cefr_band": "intermediate", "question": "Payroll processed on the ___th of each month.", "context": "15th", "answer": "15", "explanation": "Monthly pay date."},
                {"cefr_band": "advanced", "question": "Crew retention rate: ___%.", "context": "78%", "answer": "78", "explanation": "Workforce retention metric."}
            ],
            "Info Technology": [
                {"cefr_band": "basic", "question": "Server backup at ___ AM daily.", "context": "3:00 AM", "answer": "3:00", "explanation": "Scheduled nightly backup time."},
                {"cefr_band": "basic", "question": "Help desk ticket #___.", "context": "Ticket #4817", "answer": "4817", "explanation": "Support ticket reference number."},
                {"cefr_band": "intermediate", "question": "System uptime: ___% this quarter.", "context": "99.7%", "answer": "99.7", "explanation": "Service availability metric."},
                {"cefr_band": "intermediate", "question": "Network switch on deck ___.", "context": "Deck 4", "answer": "4", "explanation": "Infrastructure location by deck."},
                {"cefr_band": "advanced", "question": "Patch deployment covers ___ servers.", "context": "86 servers", "answer": "86", "explanation": "Fleet server count in maintenance scope."}
            ],
            "Infotainment": [
                {"cefr_band": "basic", "question": "Cabin TV has ___ channels.", "context": "45 channels", "answer": "45", "explanation": "In-cabin entertainment channel count."},
                {"cefr_band": "basic", "question": "Movie starts at ___ PM on channel 12.", "context": "7:00 PM", "answer": "7:00", "explanation": "On-demand movie showtime."},
                {"cefr_band": "intermediate", "question": "Interactive map updates every ___ seconds.", "context": "30 seconds", "answer": "30", "explanation": "Voyage tracker refresh interval."},
                {"cefr_band": "intermediate", "question": "Content library: ___ movies available.", "context": "200 movies", "answer": "200", "explanation": "On-demand entertainment catalogue size."},
                {"cefr_band": "advanced", "question": "Streaming server capacity: ___ concurrent HD streams.", "context": "1,500 streams", "answer": "1500", "explanation": "Infrastructure throughput for peak demand."}
            ],
            "Musicians": [
                {"cefr_band": "basic", "question": "Set starts at ___ PM.", "context": "9:00 PM", "answer": "9:00", "explanation": "Evening performance start time."},
                {"cefr_band": "basic", "question": "Each set lasts ___ minutes.", "context": "45 minutes", "answer": "45", "explanation": "Standard set duration."},
                {"cefr_band": "intermediate", "question": "Band performs ___ sets per night.", "context": "3 sets", "answer": "3", "explanation": "Nightly performance count."},
                {"cefr_band": "intermediate", "question": "Break between sets: ___ minutes.", "context": "20 minutes", "answer": "20", "explanation": "Intermission duration."},
                {"cefr_band": "advanced", "question": "Repertoire includes ___ songs.", "context": "120 songs", "answer": "120", "explanation": "Full song catalogue size."}
            ],
            "Production Staff": [
                {"cefr_band": "basic", "question": "Costume change in ___ seconds.", "context": "90 seconds", "answer": "90", "explanation": "Quick-change timing backstage."},
                {"cefr_band": "basic", "question": "Props check at ___ PM.", "context": "4:00 PM", "answer": "4:00", "explanation": "Pre-show props inspection time."},
                {"cefr_band": "intermediate", "question": "Fog machine runs for ___ minutes during act 2.", "context": "8 minutes", "answer": "8", "explanation": "Special effects duration."},
                {"cefr_band": "intermediate", "question": "Wardrobe inventory: ___ costumes for this production.", "context": "64 costumes", "answer": "64", "explanation": "Total costume pieces per show."},
                {"cefr_band": "advanced", "question": "Tech run-through includes ___ cue-to-cue sequences.", "context": "140 cues", "answer": "140", "explanation": "Technical rehearsal complexity."}
            ],
            "Shore Excursions": [
                {"cefr_band": "basic", "question": "Tour departs at ___ AM.", "context": "8:45 AM", "answer": "8:45", "explanation": "Shore excursion departure time."},
                {"cefr_band": "basic", "question": "Snorkeling trip: $___ per person.", "context": "$75", "answer": "75", "explanation": "Excursion pricing."},
                {"cefr_band": "intermediate", "question": "Return to ship by ___ PM (all aboard).", "context": "4:30 PM", "answer": "4:30", "explanation": "Mandatory return time before sailing."},
                {"cefr_band": "intermediate", "question": "Tour group maximum: ___ guests per bus.", "context": "44 guests", "answer": "44", "explanation": "Transport capacity limit."},
                {"cefr_band": "advanced", "question": "Excursion revenue: $___,000.", "context": "$185,000", "answer": "185", "explanation": "Port-day revenue metric."}
            ],
            "Youth Programs": [
                {"cefr_band": "basic", "question": "Kids club opens at ___ AM.", "context": "9:00 AM", "answer": "9:00", "explanation": "Morning opening time."},
                {"cefr_band": "basic", "question": "Age group: ___ to 11 years.", "context": "3 to 11 years", "answer": "3", "explanation": "Minimum age for kids club."},
                {"cefr_band": "intermediate", "question": "Teen night ends at ___ PM.", "context": "11:30 PM", "answer": "11:30", "explanation": "Teen activity curfew time."},
                {"cefr_band": "intermediate", "question": "Maximum ___ children per counselor.", "context": "12 children", "answer": "12", "explanation": "Staff-to-child supervision ratio."},
                {"cefr_band": "advanced", "question": "Enrollment: ___ kids.", "context": "280 kids", "answer": "280", "explanation": "Program capacity metric."}
            ],
            "Audio Visual Media": [
                {"cefr_band": "basic", "question": "Projector in conference room ___.", "context": "Room 3", "answer": "3", "explanation": "Meeting room assignment."},
                {"cefr_band": "basic", "question": "Microphone check at ___ PM.", "context": "2:00 PM", "answer": "2:00", "explanation": "Equipment test time."},
                {"cefr_band": "intermediate", "question": "Video wall: ___ panels in a 4x3 grid.", "context": "12 panels", "answer": "12", "explanation": "Display panel count."},
                {"cefr_band": "intermediate", "question": "Camera memory card: ___ GB capacity.", "context": "256 GB", "answer": "256", "explanation": "Storage media size."},
                {"cefr_band": "advanced", "question": "Live broadcast uses ___ cameras.", "context": "6 cameras", "answer": "6", "explanation": "Multi-camera production setup complexity."}
            ],
            "Onboard Media": [
                {"cefr_band": "basic", "question": "Daily newsletter printed at ___ AM.", "context": "5:00 AM", "answer": "5:00", "explanation": "Morning print run time."},
                {"cefr_band": "basic", "question": "Digital signage updates ___ times per day.", "context": "4 times", "answer": "4", "explanation": "Content refresh frequency."},
                {"cefr_band": "intermediate", "question": "Photo gallery: ___ images from last port.", "context": "350 images", "answer": "350", "explanation": "Port-day photo collection size."},
                {"cefr_band": "intermediate", "question": "Social media post scheduled at ___ PM.", "context": "6:00 PM", "answer": "6:00", "explanation": "Peak engagement posting time."},
                {"cefr_band": "advanced", "question": "Content calendar includes ___ assets.", "context": "45 assets", "answer": "45", "explanation": "Content distribution scope metric."}
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
            ],
            "Spa & Wellness": [
                {"cefr_band": "basic", "passage": "SPA BOOKING: The spa is located on Deck 9 forward and is open from 8:00 AM to 8:00 PM on sea days. Appointments can be made at the spa reception or through the ship's app. Walk-ins are welcome but subject to availability. Guests should arrive 15 minutes before their appointment.", "options": ["Spa Location Guide", "Spa Booking Information", "Treatment Menu", "Operating Schedule"], "correct": "Spa Booking Information", "explanation": "The passage provides spa location, hours, and booking procedures."},
                {"cefr_band": "basic", "passage": "SPA ETIQUETTE: Guests should wear the robes and slippers provided in the changing rooms. Mobile phones must be switched to silent mode in all spa areas. Guests are asked to shower before using the sauna, steam room, or pool. Towels are available at the entrance to the thermal suite.", "options": ["Spa Rules", "Spa Etiquette Guidelines", "Dress Code", "Facility Information"], "correct": "Spa Etiquette Guidelines", "explanation": "The passage outlines expected guest behavior in the spa."},
                {"cefr_band": "intermediate", "passage": "TREATMENT MENU OVERVIEW: The spa offers Swedish, deep tissue, and hot stone massages ranging from 50 to 80 minutes. Facial treatments include anti-aging, hydrating, and detox options. Body wraps use marine-based ingredients sourced locally. Couples treatments are available in the dedicated couples suite by advance reservation only.", "options": ["Price List", "Treatment Menu Summary", "Wellness Packages", "Booking Options"], "correct": "Treatment Menu Summary", "explanation": "The passage summarizes the variety of spa treatments available."},
                {"cefr_band": "intermediate", "passage": "THERMAL SUITE ACCESS: The thermal suite includes a Finnish sauna, aromatic steam room, heated stone loungers, and a thalassotherapy pool. Daily passes are available for $40 or guests may purchase a full-voyage pass for $150. Children under 16 are not permitted. The suite is open from 7:00 AM to 9:00 PM.", "options": ["Fitness Center Details", "Thermal Suite Information", "Pool Schedule", "Sauna Rules"], "correct": "Thermal Suite Information", "explanation": "The passage describes the thermal suite facilities and access policy."},
                {"cefr_band": "advanced", "passage": "WELLNESS PROGRAM COORDINATION: The spa director designs a rotating wellness program each voyage that includes yoga, meditation, nutrition seminars, and acupuncture consultations. Revenue targets are tracked weekly against per-guest spend benchmarks. Therapists must complete continuing education hours each quarter. Guest satisfaction surveys are reviewed every turnaround to adjust service offerings.", "options": ["Staff Training Plan", "Wellness Program Management", "Revenue Analysis", "Guest Feedback Process"], "correct": "Wellness Program Management", "explanation": "The passage describes the strategic management of the onboard wellness program."},
                {"cefr_band": "advanced", "passage": "SPA HYGIENE AND SAFETY PROTOCOL: All equipment and treatment rooms are sanitized between clients using hospital-grade disinfectant. Therapists must wash hands and change linens before each session. Essential oils and products are patch-tested with new clients. Incident reports for allergic reactions or injuries must be filed within one hour and reviewed by the spa director.", "options": ["Cleaning Checklist", "Spa Hygiene Standards", "Product Safety Guide", "Staff Procedures"], "correct": "Spa Hygiene Standards", "explanation": "The passage outlines the strict hygiene and safety protocols in the spa."}
            ],
            "Entertainment Technical": [
                {"cefr_band": "basic", "passage": "STAGE LIGHTING BASICS: The main theater has 120 lighting fixtures controlled from the lighting booth at the rear of the house. White follow spots are used during solo performances. All lighting cues are pre-programmed before each show. Emergency house lights activate automatically if main power fails.", "options": ["Theater Layout", "Stage Lighting Overview", "Show Schedule", "Emergency Procedures"], "correct": "Stage Lighting Overview", "explanation": "The passage describes the basic stage lighting setup in the theater."},
                {"cefr_band": "basic", "passage": "SOUND SYSTEM CHECK: Before every performance, the sound engineer tests all microphones and speakers. Wireless microphone batteries are replaced with fresh ones. Volume levels are set during rehearsal with performers on stage. A backup wired microphone is kept at the wings for emergencies.", "options": ["Audio Equipment List", "Sound Check Procedures", "Performance Rules", "Equipment Inventory"], "correct": "Sound Check Procedures", "explanation": "The passage outlines the pre-show sound system check process."},
                {"cefr_band": "intermediate", "passage": "RIGGING SAFETY STANDARDS: All rigging points above the stage are inspected monthly by a certified technician. Maximum load ratings are posted at each fly rail position. Performers using aerial equipment must wear safety harnesses rated to twice their body weight. Any rigging modification requires written approval from the technical director.", "options": ["Stage Design", "Rigging Safety Requirements", "Performer Guidelines", "Equipment Specifications"], "correct": "Rigging Safety Requirements", "explanation": "The passage details the safety standards for stage rigging."},
                {"cefr_band": "intermediate", "passage": "LED SCREEN OPERATIONS: The main stage features a 30-foot LED video wall used for show backdrops and visual effects. Content is loaded from the media server and cued by the stage manager during performances. Screen brightness is adjusted based on ambient lighting conditions. Pixel mapping must be verified after any screen panel replacement.", "options": ["Visual Effects Guide", "LED Screen Operating Procedures", "Show Production Notes", "Technical Specifications"], "correct": "LED Screen Operating Procedures", "explanation": "The passage explains the operation of the LED video wall during shows."},
                {"cefr_band": "advanced", "passage": "SHOW TECHNICAL REHEARSAL PROTOCOL: Full technical rehearsals are conducted 48 hours before opening night. The stage manager coordinates lighting, sound, video, and scenic cues in sequence. Each department head signs off on their cue list. Problems identified during tech rehearsal must be resolved within 12 hours. A final dress rehearsal with full cast confirms all systems are performance-ready.", "options": ["Rehearsal Schedule", "Technical Rehearsal Standards", "Production Timeline", "Crew Assignments"], "correct": "Technical Rehearsal Standards", "explanation": "The passage describes the full technical rehearsal protocol."},
                {"cefr_band": "advanced", "passage": "PYROTECHNICS AND SPECIAL EFFECTS COMPLIANCE: All pyrotechnic effects require a licensed operator and advance filing of a safety plan with the staff captain. Indoor pyrotechnics are limited to cold spark machines and CO2 jets. Haze machines must use water-based fluid to avoid triggering fire detection systems. Effect logs are maintained and submitted to the safety officer after each performance.", "options": ["Fire Safety Regulations", "Special Effects Compliance Standards", "Show Production Rules", "Hazard Assessment"], "correct": "Special Effects Compliance Standards", "explanation": "The passage outlines compliance requirements for special effects and pyrotechnics."}
            ],
            "Entertainment": [
                {"cefr_band": "basic", "passage": "DAILY ENTERTAINMENT SCHEDULE: Live music plays in the atrium from 5:00 PM to 7:00 PM each evening. The main theater show starts at 8:30 PM with a second seating at 10:15 PM. Trivia games are held in the lounge at 3:00 PM on sea days. A schedule is delivered to each cabin every evening.", "options": ["Event Calendar", "Daily Entertainment Schedule", "Show Times", "Activity Options"], "correct": "Daily Entertainment Schedule", "explanation": "The passage describes the daily entertainment activities and times."},
                {"cefr_band": "basic", "passage": "MAIN THEATER SEATING: The main theater seats 900 guests across two levels. Seating is open and on a first-come, first-served basis. Doors open 30 minutes before showtime. Guests are asked to silence phones and refrain from flash photography during performances.", "options": ["Venue Capacity", "Theater Seating Information", "Show Rules", "Ticket Policy"], "correct": "Theater Seating Information", "explanation": "The passage provides information about main theater seating and policies."},
                {"cefr_band": "intermediate", "passage": "GUEST PARTICIPATION EVENTS: The cruise director hosts interactive events including game shows, lip sync battles, and dance competitions. Sign-up sheets are posted at the activities desk by 10:00 AM on event days. Prizes include onboard credit, branded merchandise, and specialty dining vouchers. Events are held in the main lounge and require no additional charge.", "options": ["Activity Fees", "Guest Participation Event Details", "Prize Catalog", "Competition Rules"], "correct": "Guest Participation Event Details", "explanation": "The passage describes guest participation entertainment events."},
                {"cefr_band": "intermediate", "passage": "POOLSIDE ENTERTAINMENT: DJ music plays at the pool deck from 11:00 AM to 4:00 PM on sea days. Themed pool parties are scheduled once per voyage and include contests and giveaways. Volume levels are monitored to maintain a comfortable environment for all guests. The entertainment team coordinates with the bar staff for drink specials during events.", "options": ["Pool Rules", "Poolside Entertainment Guide", "DJ Schedule", "Event Planning"], "correct": "Poolside Entertainment Guide", "explanation": "The passage describes poolside entertainment programming."},
                {"cefr_band": "advanced", "passage": "ENTERTAINMENT BUDGET AND PROGRAMMING: The entertainment director manages a per-voyage budget covering headliner fees, production costs, and technical labor. Guest satisfaction scores from post-cruise surveys directly influence future programming decisions. Acts are contracted six months in advance through the shoreside entertainment division. Emergency replacement performers are maintained on a standby roster.", "options": ["Financial Report", "Entertainment Programming and Budget", "Talent Recruitment", "Survey Results"], "correct": "Entertainment Programming and Budget", "explanation": "The passage describes the entertainment budgeting and programming process."},
                {"cefr_band": "advanced", "passage": "PERFORMER CONTRACT AND CONDUCT STANDARDS: All entertainers sign a code of conduct prohibiting fraternization with guests and consumption of alcohol within four hours of a performance. Rehearsal attendance is mandatory and tracked. Contract violations result in written warnings; two warnings lead to disembarkation at the next port. Performance evaluations are conducted weekly by the entertainment director.", "options": ["Crew Policies", "Performer Conduct Standards", "HR Regulations", "Talent Management"], "correct": "Performer Conduct Standards", "explanation": "The passage outlines the conduct and contract standards for onboard performers."}
            ],
            "Fleet Finance": [
                {"cefr_band": "basic", "passage": "ONBOARD CURRENCY: All transactions onboard are conducted in US dollars. Currency exchange is available at Guest Services during operating hours. Credit cards are accepted at all onboard outlets. Cash withdrawals are not available from the ship.", "options": ["Payment Methods", "Onboard Currency Policy", "Guest Services Hours", "Banking Options"], "correct": "Onboard Currency Policy", "explanation": "The passage explains the onboard currency and payment options."},
                {"cefr_band": "basic", "passage": "CREW PAY SCHEDULE: Crew wages are deposited on the 15th and last day of each month. Pay stubs are available through the crew portal. Questions about deductions or overtime should be directed to the payroll office on Deck 2. Direct deposit forms must be submitted before the first pay period.", "options": ["Banking Information", "Crew Pay Schedule", "HR Contact Info", "Benefits Overview"], "correct": "Crew Pay Schedule", "explanation": "The passage describes the crew payroll schedule and procedures."},
                {"cefr_band": "intermediate", "passage": "DEPARTMENTAL BUDGET TRACKING: Each department head receives a monthly budget allocation and must submit expense reports by the 5th of the following month. Variances exceeding 10 percent require written justification. The fleet finance team conducts quarterly reviews with each department. Unspent funds do not roll over to the next period.", "options": ["Accounting Procedures", "Budget Tracking Guidelines", "Expense Policy", "Financial Planning"], "correct": "Budget Tracking Guidelines", "explanation": "The passage outlines how departmental budgets are tracked and reviewed."},
                {"cefr_band": "intermediate", "passage": "PROCUREMENT APPROVAL PROCESS: Purchase orders below $500 require department head approval. Orders between $500 and $5,000 must be approved by the hotel director. Any purchase exceeding $5,000 requires shoreside authorization from the fleet procurement office. Emergency purchases may bypass standard approval with post-facto documentation.", "options": ["Purchasing Rules", "Procurement Approval Tiers", "Vendor Management", "Order Processing"], "correct": "Procurement Approval Tiers", "explanation": "The passage explains the tiered procurement approval process."},
                {"cefr_band": "advanced", "passage": "REVENUE MANAGEMENT ANALYSIS: The fleet finance team monitors daily revenue per available cabin day across all ship-generated income streams including dining, beverage, casino, spa, and shore excursions. Yield management models adjust pricing dynamically based on booking pace and historical demand. Weekly flash reports are distributed to the captain and hotel director. Underperforming revenue centers trigger an action plan within 48 hours.", "options": ["Sales Report", "Revenue Management Practices", "Pricing Strategy", "Financial Dashboard"], "correct": "Revenue Management Practices", "explanation": "The passage describes the revenue management and analysis practices."},
                {"cefr_band": "advanced", "passage": "AUDIT AND COMPLIANCE FRAMEWORK: Internal audits are conducted semi-annually covering cash handling, inventory controls, and vendor payments. External auditors review consolidated fleet financials annually. All financial transactions must comply with Sarbanes-Oxley and maritime regulatory requirements. Audit findings are tracked in a corrective action register until resolved.", "options": ["Regulatory Requirements", "Audit and Compliance Framework", "Risk Assessment", "Internal Controls"], "correct": "Audit and Compliance Framework", "explanation": "The passage outlines the financial audit and compliance framework."}
            ],
            "Guest Technology": [
                {"cefr_band": "basic", "passage": "WIFI CONNECTIVITY: The ship offers three WiFi tiers: Basic for email and messaging, Standard for web browsing, and Premium for streaming. Packages are purchased at the internet cafe on Deck 5 or through the cruise app. Connection speeds vary based on satellite coverage and the number of users online.", "options": ["Internet Pricing", "WiFi Connectivity Guide", "App Instructions", "Network Setup"], "correct": "WiFi Connectivity Guide", "explanation": "The passage explains the available WiFi packages and how to purchase them."},
                {"cefr_band": "basic", "passage": "DIGITAL KEY CARD: Guests can use the cruise app as a digital room key after completing online check-in. The digital key works via Bluetooth and requires the phone to be unlocked. If the digital key fails, the physical key card remains active at all times. Technical support is available at Guest Services.", "options": ["App Features", "Digital Key Card Guide", "Check-in Instructions", "Troubleshooting Help"], "correct": "Digital Key Card Guide", "explanation": "The passage describes how the digital key card feature works."},
                {"cefr_band": "intermediate", "passage": "INTERACTIVE TV SYSTEM: Each stateroom television provides on-demand movies, ship information, and account review features. Guests can order room service and book excursions through the TV menu. The system updates daily with new content. Remote controls are standardized across all cabin categories.", "options": ["Entertainment Options", "Interactive TV Features", "Channel Listing", "Room Service Menu"], "correct": "Interactive TV Features", "explanation": "The passage describes the interactive TV system capabilities."},
                {"cefr_band": "intermediate", "passage": "WAYFINDING KIOSK NETWORK: Touchscreen kiosks are positioned at elevator lobbies on every guest deck. They display interactive deck maps, event schedules, and restaurant menus. Kiosks support six languages and can print directions. Usage data is collected anonymously to improve future content placement.", "options": ["Ship Maps", "Wayfinding Kiosk Information", "Guest Directory", "Digital Signage"], "correct": "Wayfinding Kiosk Information", "explanation": "The passage describes the wayfinding kiosk network and features."},
                {"cefr_band": "advanced", "passage": "NETWORK INFRASTRUCTURE: The ship's guest network operates on a dual-band satellite system providing up to 500 Mbps aggregate bandwidth. Traffic shaping prioritizes safety communications and crew operations. Guest bandwidth is dynamically allocated based on active package subscriptions. Network health is monitored by the IT team from a centralized operations center on Deck 0.", "options": ["Technical Specifications", "Network Infrastructure Overview", "Satellite Coverage Map", "IT Department Structure"], "correct": "Network Infrastructure Overview", "explanation": "The passage describes the ship's network infrastructure and management."},
                {"cefr_band": "advanced", "passage": "TECHNOLOGY ROLLOUT PLANNING: New guest-facing technology features are piloted on a single ship for two voyages before fleet-wide deployment. Feedback is collected through in-app surveys and Guest Services reports. The technology team provides training to frontline staff 72 hours before each rollout. Post-deployment metrics include adoption rate, error frequency, and guest satisfaction impact.", "options": ["Project Management", "Technology Rollout Process", "Staff Training Plan", "Feature Testing"], "correct": "Technology Rollout Process", "explanation": "The passage explains the process for deploying new guest technology."}
            ],
            "Human Resources": [
                {"cefr_band": "basic", "passage": "CREW ID BADGES: All crew members must wear their identification badge while on duty. Badges display the crew member's name, department, and photo. Lost badges must be reported to HR within 24 hours. A replacement badge costs $10 and is issued from the HR office on Deck 2.", "options": ["Uniform Policy", "Crew ID Badge Policy", "Security Requirements", "HR Contact Information"], "correct": "Crew ID Badge Policy", "explanation": "The passage describes the crew identification badge requirements."},
                {"cefr_band": "basic", "passage": "CREW DINING HOURS: The crew mess is open for breakfast from 6:00 AM to 8:00 AM, lunch from 11:30 AM to 1:30 PM, and dinner from 5:30 PM to 7:30 PM. A late-night snack is available from 10:00 PM to 11:00 PM. Crew must present their ID badge to enter the dining area.", "options": ["Meal Schedule", "Crew Dining Information", "Menu Options", "Galley Hours"], "correct": "Crew Dining Information", "explanation": "The passage provides crew dining hours and access requirements."},
                {"cefr_band": "intermediate", "passage": "PERFORMANCE REVIEW CYCLE: Crew members receive a formal performance review at the midpoint and end of each contract. Reviews are conducted by the department head using a standardized evaluation form. Ratings cover punctuality, teamwork, job knowledge, and guest interaction. Outstanding reviews may qualify the crew member for promotion or contract extension.", "options": ["Promotion Policy", "Performance Review Process", "Training Requirements", "Contract Terms"], "correct": "Performance Review Process", "explanation": "The passage explains the performance review cycle and criteria."},
                {"cefr_band": "intermediate", "passage": "GRIEVANCE PROCEDURE: Crew members with workplace concerns should first discuss the issue with their immediate supervisor. If unresolved, a written grievance may be submitted to the HR manager. Investigations are conducted within five working days. The crew member may request a union representative be present during formal hearings.", "options": ["Complaint Process", "Crew Grievance Procedure", "Disciplinary Policy", "Union Information"], "correct": "Crew Grievance Procedure", "explanation": "The passage outlines the formal grievance procedure for crew members."},
                {"cefr_band": "advanced", "passage": "MARITIME LABOR CONVENTION COMPLIANCE: The vessel complies with MLC 2006 standards regarding minimum age, employment agreements, hours of rest, and onboard living conditions. Rest hour records are maintained digitally and audited by the safety officer. Complaints under the MLC may be submitted confidentially through the onboard grievance system or directly to the flag state.", "options": ["Safety Regulations", "MLC Compliance Standards", "Employment Law", "Crew Welfare"], "correct": "MLC Compliance Standards", "explanation": "The passage describes the ship's compliance with Maritime Labor Convention requirements."},
                {"cefr_band": "advanced", "passage": "SUCCESSION PLANNING AND TALENT DEVELOPMENT: HR maintains a development pipeline for key shipboard leadership positions including hotel director, chief engineer, and staff captain. High-potential crew members are identified through performance data and manager nominations. Development plans include cross-departmental rotations, mentoring, and shoreside leadership courses. Succession readiness is reported to fleet HR quarterly.", "options": ["Training Catalog", "Succession Planning Program", "Leadership Development", "Recruitment Strategy"], "correct": "Succession Planning Program", "explanation": "The passage describes the succession planning and talent development program."}
            ],
            "Info Technology": [
                {"cefr_band": "basic", "passage": "IT HELP DESK: The IT help desk is located on Deck 2 and is open from 8:00 AM to 6:00 PM. Crew members can submit service requests in person, by phone at extension 2200, or via the crew intranet. Common requests include password resets, printer issues, and software access. Response times are within four hours for standard requests.", "options": ["Contact Directory", "IT Help Desk Information", "Crew Services", "Technical Support Hours"], "correct": "IT Help Desk Information", "explanation": "The passage provides IT help desk location, hours, and services."},
                {"cefr_band": "basic", "passage": "CREW INTERNET ACCESS: Crew members receive a limited free internet allowance each month. Additional data can be purchased through the crew portal at discounted rates. Personal devices must be registered with IT before connecting to the crew WiFi network. Streaming and large downloads are restricted during peak hours.", "options": ["WiFi Policy", "Crew Internet Access Policy", "Network Rules", "Data Pricing"], "correct": "Crew Internet Access Policy", "explanation": "The passage explains crew internet access policies and limitations."},
                {"cefr_band": "intermediate", "passage": "SHIPBOARD SOFTWARE SYSTEMS: Operational systems include the property management system for guest accounts, the point-of-sale system for retail and dining, and the inventory management platform for provisions. Each system runs on a dedicated server cluster in the IT room on Deck 0. System backups are performed automatically every six hours.", "options": ["Hardware Inventory", "Shipboard Software Systems Overview", "Server Specifications", "Backup Procedures"], "correct": "Shipboard Software Systems Overview", "explanation": "The passage describes the main software systems used onboard."},
                {"cefr_band": "intermediate", "passage": "CYBERSECURITY AWARENESS: All crew members must complete annual cybersecurity training. Phishing emails should be reported immediately to the IT security team. USB drives from external sources must not be connected to shipboard computers. Passwords must be at least 12 characters and changed every 90 days.", "options": ["Training Requirements", "Cybersecurity Awareness Guidelines", "Password Policy", "IT Security Rules"], "correct": "Cybersecurity Awareness Guidelines", "explanation": "The passage outlines cybersecurity awareness requirements for crew members."},
                {"cefr_band": "advanced", "passage": "DISASTER RECOVERY PLAN: The IT disaster recovery plan defines procedures for restoring critical systems within two hours of a major failure. Primary servers are mirrored to a secondary data center in the engine casing. Satellite uplink failover occurs automatically within 90 seconds. The plan is tested quarterly with a simulated outage drill coordinated between IT, the bridge, and the hotel director.", "options": ["Emergency Procedures", "IT Disaster Recovery Plan", "System Architecture", "Business Continuity"], "correct": "IT Disaster Recovery Plan", "explanation": "The passage describes the IT disaster recovery plan and testing procedures."},
                {"cefr_band": "advanced", "passage": "TECHNOLOGY REFRESH CYCLE: Shipboard hardware follows a three-year refresh cycle aligned with dry dock schedules. End-of-life equipment is replaced with standardized models to reduce spare parts inventory. Software updates are deployed fleet-wide through a centralized patch management system. Each refresh project includes a risk assessment and rollback plan approved by the fleet CTO.", "options": ["Procurement Schedule", "Technology Refresh Standards", "Equipment Lifecycle", "Budget Planning"], "correct": "Technology Refresh Standards", "explanation": "The passage outlines the technology refresh cycle and governance."}
            ],
            "Infotainment": [
                {"cefr_band": "basic", "passage": "IN-CABIN ENTERTAINMENT: Each stateroom television offers over 100 on-demand movies, live satellite channels, and a ship information channel. Movie selections are updated at the start of each voyage. Parental controls can be activated by contacting Guest Services. The TV remote also controls cabin lighting in suite categories.", "options": ["Movie List", "In-Cabin Entertainment Guide", "TV Instructions", "Channel Directory"], "correct": "In-Cabin Entertainment Guide", "explanation": "The passage describes the in-cabin entertainment options available to guests."},
                {"cefr_band": "basic", "passage": "DIGITAL SIGNAGE: Large display screens throughout the ship show daily schedules, restaurant menus, port information, and safety messages. Content is updated by the infotainment team three times daily. Screens in elevator lobbies display a rotating loop of upcoming events. Emergency messages override all scheduled content automatically.", "options": ["Ship Directory", "Digital Signage Overview", "Event Schedule", "Safety Displays"], "correct": "Digital Signage Overview", "explanation": "The passage describes the digital signage system and content management."},
                {"cefr_band": "intermediate", "passage": "CONTENT MANAGEMENT SYSTEM: The infotainment team uses a centralized platform to schedule and distribute media content across all guest-facing screens. New content is uploaded via the crew intranet and requires approval from the entertainment director. Scheduling conflicts are flagged automatically. Content performance is measured by screen dwell time collected from proximity sensors.", "options": ["Media Production", "Content Management Procedures", "Screen Maintenance", "Approval Workflow"], "correct": "Content Management Procedures", "explanation": "The passage describes how media content is managed and distributed."},
                {"cefr_band": "intermediate", "passage": "LIVE BROADCAST CAPABILITIES: The ship can broadcast live events to all stateroom televisions and public area screens simultaneously. The broadcast studio on Deck 6 is equipped for two-camera production. Live events include bridge tours, cooking demonstrations, and port arrival coverage. A 10-second delay is applied to all live feeds for content review.", "options": ["Studio Equipment", "Live Broadcast Capabilities", "Event Coverage Guide", "Production Schedule"], "correct": "Live Broadcast Capabilities", "explanation": "The passage explains the ship's live broadcasting setup and capabilities."},
                {"cefr_band": "advanced", "passage": "MEDIA SERVER ARCHITECTURE: The infotainment system runs on a redundant media server cluster delivering content to over 2,000 endpoints including stateroom TVs, digital signs, and kiosk displays. Content delivery uses adaptive bitrate streaming to manage bandwidth. The system supports concurrent playback of 500 unique titles. Failover to the backup server occurs within 30 seconds with no guest interruption.", "options": ["Network Specifications", "Media Server Architecture", "System Requirements", "Infrastructure Diagram"], "correct": "Media Server Architecture", "explanation": "The passage describes the technical architecture of the media server system."},
                {"cefr_band": "advanced", "passage": "GUEST ENGAGEMENT ANALYTICS: The infotainment team tracks content consumption data including most-watched movies, peak viewing hours, and channel popularity by demographic segment. Reports are generated weekly and shared with the entertainment director and marketing team. Insights inform content licensing decisions for future voyages. Privacy regulations require that all data be aggregated and anonymized before analysis.", "options": ["Viewership Report", "Guest Engagement Analytics Process", "Marketing Data", "Privacy Compliance"], "correct": "Guest Engagement Analytics Process", "explanation": "The passage describes how guest engagement data is collected and used."}
            ],
            "Musicians": [
                {"cefr_band": "basic", "passage": "PERFORMANCE SCHEDULE: Musicians perform at designated venues according to the weekly schedule posted in the crew area. Sets are typically 45 minutes with a 15-minute break between sets. The evening lounge show begins at 9:00 PM and ends at 11:30 PM. Schedule changes are communicated by the entertainment coordinator by noon.", "options": ["Event Calendar", "Musician Performance Schedule", "Venue Assignments", "Break Policy"], "correct": "Musician Performance Schedule", "explanation": "The passage describes the musician performance schedule and set structure."},
                {"cefr_band": "basic", "passage": "INSTRUMENT STORAGE: Musical instruments must be stored in the designated music storage room on Deck 3 when not in use. The room is climate-controlled to protect sensitive instruments. Each musician is assigned a locker. Personal instruments brought onboard must be listed on the crew inventory form at embarkation.", "options": ["Storage Rules", "Instrument Storage Policy", "Crew Lockers", "Equipment Inventory"], "correct": "Instrument Storage Policy", "explanation": "The passage explains instrument storage requirements and facilities."},
                {"cefr_band": "intermediate", "passage": "SOUND LEVEL GUIDELINES: Musicians must adhere to the ship's sound level policy. Volume in dining venues must not exceed 70 decibels. Outdoor deck performances are limited to 85 decibels. The entertainment technical team provides a decibel meter for each venue. Violations are documented and may result in venue reassignment.", "options": ["Noise Regulations", "Sound Level Guidelines", "Venue Rules", "Performance Standards"], "correct": "Sound Level Guidelines", "explanation": "The passage outlines volume limits for musical performances in different venues."},
                {"cefr_band": "intermediate", "passage": "REPERTOIRE AND GUEST REQUESTS: Musicians are expected to maintain a repertoire of at least 200 songs covering classic, contemporary, and genre-specific categories. Guest requests should be accommodated when possible. A request logbook is kept at each venue to track popular songs. The entertainment coordinator reviews repertoire lists monthly.", "options": ["Song Selection", "Repertoire and Request Policy", "Guest Feedback", "Music Programming"], "correct": "Repertoire and Request Policy", "explanation": "The passage describes the repertoire requirements and guest request handling."},
                {"cefr_band": "advanced", "passage": "MUSICIAN CONTRACT OBLIGATIONS: Contract musicians are engaged for the full voyage duration with no early termination without cause. Rehearsals are unpaid but mandatory when called by the entertainment director. Musicians may not perform for tips or accept private engagement offers from guests. Intellectual property created during the contract remains the property of the cruise line.", "options": ["Employment Terms", "Musician Contract Terms", "Legal Guidelines", "Compensation Policy"], "correct": "Musician Contract Terms", "explanation": "The passage details the contractual obligations of onboard musicians."},
                {"cefr_band": "advanced", "passage": "COLLABORATIVE PERFORMANCE PLANNING: The entertainment director coordinates themed music nights requiring collaboration between multiple musician groups, the DJ, and the production cast. Planning meetings are held 72 hours in advance to align set lists, transitions, and staging. Technical requirements including additional monitors, microphone assignments, and lighting cues are submitted in writing to the technical team.", "options": ["Event Coordination", "Collaborative Performance Planning", "Technical Requests", "Rehearsal Schedule"], "correct": "Collaborative Performance Planning", "explanation": "The passage describes how collaborative performances are planned and coordinated."}
            ],
            "Production Staff": [
                {"cefr_band": "basic", "passage": "COSTUME CARE: Production staff are responsible for maintaining all costumes used in onboard shows. Costumes must be inspected for damage before and after each performance. Minor repairs such as loose buttons or torn seams are handled backstage. Major repairs are logged and sent to the wardrobe supervisor.", "options": ["Wardrobe Inventory", "Costume Care Procedures", "Show Preparation", "Backstage Rules"], "correct": "Costume Care Procedures", "explanation": "The passage describes costume maintenance responsibilities."},
                {"cefr_band": "basic", "passage": "BACKSTAGE SAFETY: All production staff must attend a backstage safety briefing before the first performance of each voyage. Running backstage during scene changes is prohibited. Glow tape marks safe walkways and step-off points. Fire extinguishers are located at each wing entrance and behind the cyclorama.", "options": ["Safety Equipment", "Backstage Safety Rules", "Stage Layout", "Emergency Plan"], "correct": "Backstage Safety Rules", "explanation": "The passage outlines backstage safety requirements for production staff."},
                {"cefr_band": "intermediate", "passage": "QUICK-CHANGE PROCEDURES: Several show numbers require costume changes completed in under 60 seconds. Quick-change booths are positioned in both stage wings with dedicated dressers assigned to each performer. Costumes are pre-set in order of appearance before the show. A communication headset links dressers to the stage manager for timing cues.", "options": ["Costume Design", "Quick-Change Procedures", "Performance Timing", "Backstage Coordination"], "correct": "Quick-Change Procedures", "explanation": "The passage describes the quick-change process during shows."},
                {"cefr_band": "intermediate", "passage": "PROP MANAGEMENT: All props are cataloged in the production inventory system with photos and storage locations. Props are set on preset tables before each show according to the preset list. Missing or damaged props must be reported to the production manager immediately. Replica props are carried as spares for critical show items.", "options": ["Inventory System", "Prop Management Procedures", "Storage Guide", "Show Checklist"], "correct": "Prop Management Procedures", "explanation": "The passage explains how show props are managed and maintained."},
                {"cefr_band": "advanced", "passage": "SHOW INSTALLATION PROCESS: When a new production is loaded onto a ship, the installation team has a 48-hour window during turnaround to set scenic elements, program lighting, configure sound, and run technical rehearsals. The production manager coordinates with the chief officer for crane access to load large set pieces through the shell doors. A punch list of unresolved items is tracked and must be cleared before opening night.", "options": ["Construction Timeline", "Show Installation Process", "Load-In Schedule", "Production Planning"], "correct": "Show Installation Process", "explanation": "The passage describes the process of installing a new show onboard."},
                {"cefr_band": "advanced", "passage": "CAST WELLNESS AND INJURY PREVENTION: Production staff monitor cast physical condition through daily check-ins before rehearsals and performances. Stretching and warm-up sessions are mandatory. Injuries are documented in the production incident log and reported to the medical center. Understudies are assigned to principal roles and rehearse weekly to ensure show continuity.", "options": ["Health and Safety", "Cast Wellness Protocol", "Medical Procedures", "Rehearsal Policy"], "correct": "Cast Wellness Protocol", "explanation": "The passage describes the cast wellness and injury prevention program."}
            ],
            "Shore Excursions": [
                {"cefr_band": "basic", "passage": "EXCURSION DESK HOURS: The shore excursion desk is located on Deck 5 and is open from 8:00 AM to 8:00 PM on sea days. On port days, the desk opens two hours before arrival and closes one hour after departure. Staff can answer questions about tour options, meeting times, and cancellation policies.", "options": ["Desk Location", "Excursion Desk Information", "Tour Schedule", "Customer Service Hours"], "correct": "Excursion Desk Information", "explanation": "The passage provides shore excursion desk location and operating hours."},
                {"cefr_band": "basic", "passage": "MEETING POINT INSTRUCTIONS: Guests booked on shore excursions should meet in the main theater at the time printed on their ticket. Tour groups are called by number. Guests must bring their room key card and a valid photo ID. Late arrivals cannot be accommodated once the group has departed.", "options": ["Tour Ticket Guide", "Meeting Point Instructions", "Departure Schedule", "Guest Requirements"], "correct": "Meeting Point Instructions", "explanation": "The passage explains where and when guests should gather for excursions."},
                {"cefr_band": "intermediate", "passage": "EXCURSION CANCELLATION POLICY: Cancellations made more than 48 hours before the port day receive a full refund to the onboard account. Cancellations within 48 hours are subject to a 50 percent penalty. No-shows receive no refund. Weather-related cancellations by the cruise line are fully refunded. Guests may transfer bookings to another tour if space permits.", "options": ["Refund Policy", "Excursion Cancellation Policy", "Booking Terms", "Weather Guidelines"], "correct": "Excursion Cancellation Policy", "explanation": "The passage explains the cancellation and refund policy for shore excursions."},
                {"cefr_band": "intermediate", "passage": "TOUR OPERATOR VETTING: All shore excursion operators are vetted annually for safety compliance, insurance coverage, and vehicle maintenance records. Operators must provide proof of liability insurance with a minimum coverage of one million dollars. Vehicles are inspected before each season. Guest feedback scores below 3.5 out of 5 trigger a performance review.", "options": ["Vendor Selection", "Tour Operator Vetting Standards", "Safety Compliance", "Insurance Requirements"], "correct": "Tour Operator Vetting Standards", "explanation": "The passage describes how tour operators are vetted and monitored."},
                {"cefr_band": "advanced", "passage": "EXCURSION REVENUE OPTIMIZATION: The shore excursion team uses historical booking data and guest demographics to curate port-specific tour portfolios. Premium experiences such as private yacht charters and helicopter tours carry margins above 40 percent. Dynamic pricing adjusts tour rates based on remaining capacity seven days before the port call. Cross-selling with spa and dining packages increases per-guest spend.", "options": ["Sales Analysis", "Excursion Revenue Optimization", "Tour Pricing Strategy", "Marketing Plan"], "correct": "Excursion Revenue Optimization", "explanation": "The passage describes the revenue optimization strategy for shore excursions."},
                {"cefr_band": "advanced", "passage": "EMERGENCY PROTOCOLS FOR TOURS ASHORE: If a guest is injured or becomes ill during a shore excursion, the tour guide contacts the ship's emergency coordinator via satellite phone. The ship's medical team is placed on standby for the guest's return. In severe cases, the local emergency services number is dialed immediately. All incidents are documented with photographs, witness statements, and a timeline filed within two hours of return.", "options": ["First Aid Procedures", "Shore Excursion Emergency Protocol", "Medical Evacuation Plan", "Incident Reporting"], "correct": "Shore Excursion Emergency Protocol", "explanation": "The passage outlines emergency procedures during shore excursions."}
            ],
            "Youth Programs": [
                {"cefr_band": "basic", "passage": "KIDS CLUB HOURS: The kids club on Deck 12 is open from 9:00 AM to noon and 2:00 PM to 5:00 PM on sea days. Evening sessions run from 7:00 PM to 10:00 PM. Children aged 3 to 11 are welcome. Parents must complete a registration form and provide emergency contact information.", "options": ["Activity Schedule", "Kids Club Information", "Age Requirements", "Registration Form"], "correct": "Kids Club Information", "explanation": "The passage provides kids club hours, location, and registration requirements."},
                {"cefr_band": "basic", "passage": "AGE GROUP DIVISIONS: Youth programs are divided into three groups: Penguins for ages 3 to 5, Stingrays for ages 6 to 8, and Sharks for ages 9 to 11. Each group has a dedicated playroom and age-appropriate activities. Teen programs for ages 12 to 17 operate separately in the teen lounge.", "options": ["Program Overview", "Age Group Divisions", "Activity Options", "Teen Club Info"], "correct": "Age Group Divisions", "explanation": "The passage describes how youth programs are divided by age group."},
                {"cefr_band": "intermediate", "passage": "CHILD CHECK-IN AND CHECK-OUT: Parents check children in and out using a secure wristband scanning system. Only adults listed on the registration form may collect a child. Photo identification is required for pick-up if the adult is not recognized by staff. Children may not leave the club unaccompanied unless written parental consent is on file for ages 8 and above.", "options": ["Security Measures", "Check-In and Check-Out Procedures", "Parental Consent", "Wristband System"], "correct": "Check-In and Check-Out Procedures", "explanation": "The passage outlines the secure check-in and check-out process for children."},
                {"cefr_band": "intermediate", "passage": "DAILY ACTIVITY PLANNING: Youth staff design daily activity schedules that include arts and crafts, scavenger hunts, movie screenings, and supervised swimming. Activities are planned around meal times and port schedules. A printed schedule is distributed to parents each morning. Rainy-day alternatives are prepared in advance for outdoor activities.", "options": ["Event Calendar", "Daily Activity Planning", "Program Curriculum", "Staff Responsibilities"], "correct": "Daily Activity Planning", "explanation": "The passage describes how daily youth activities are planned and communicated."},
                {"cefr_band": "advanced", "passage": "CHILD SAFEGUARDING POLICY: All youth program staff must hold a valid child safeguarding certification and pass a background check before employment. The staff-to-child ratio is maintained at 1:8 for ages 3 to 5 and 1:12 for ages 6 to 11. Any allegation or observation of abuse is reported immediately to the staff captain and shoreside child protection officer. Incident records are sealed and retained for a minimum of seven years.", "options": ["HR Requirements", "Child Safeguarding Policy", "Staff Training Standards", "Legal Compliance"], "correct": "Child Safeguarding Policy", "explanation": "The passage outlines the child safeguarding policy and reporting requirements."},
                {"cefr_band": "advanced", "passage": "YOUTH PROGRAM EVALUATION: Program effectiveness is measured through parent satisfaction surveys distributed on the final sea day. Participation rates and repeat attendance are tracked by age group. The youth director submits a voyage summary report to the fleet family programming manager. Insights are used to update activity kits, training materials, and staffing recommendations for future sailings.", "options": ["Survey Results", "Youth Program Evaluation Process", "Feedback Analysis", "Program Improvement"], "correct": "Youth Program Evaluation Process", "explanation": "The passage describes how youth programs are evaluated and improved."}
            ],
            "Audio Visual Media": [
                {"cefr_band": "basic", "passage": "AV EQUIPMENT CHECKOUT: Audio visual equipment is stored in the media room on Deck 4. Items available include projectors, portable speakers, wireless microphones, and presentation clickers. All equipment must be reserved through the AV request form at least 24 hours in advance. Items are signed out and must be returned within two hours of event completion.", "options": ["Equipment List", "AV Equipment Checkout Process", "Reservation System", "Media Room Location"], "correct": "AV Equipment Checkout Process", "explanation": "The passage describes the AV equipment checkout process and requirements."},
                {"cefr_band": "basic", "passage": "CONFERENCE ROOM AV SETUP: Each conference room is equipped with a ceiling-mounted projector, a retractable screen, and a table-mounted microphone. Laptops can be connected via HDMI or wirelessly through the casting device. An instruction card is posted next to the AV panel in each room. Technical support is available by calling extension 4400.", "options": ["Room Features", "Conference Room AV Setup Guide", "Meeting Room Booking", "IT Support"], "correct": "Conference Room AV Setup Guide", "explanation": "The passage explains the AV setup in conference rooms."},
                {"cefr_band": "intermediate", "passage": "VIDEO PRODUCTION WORKFLOW: The AV media team produces promotional videos, safety briefings, and event highlight reels during each voyage. Raw footage is captured using professional-grade cameras and edited in the onboard production suite. Final cuts require approval from the entertainment director before distribution. Completed videos are uploaded to the stateroom TV system and social media channels.", "options": ["Filming Schedule", "Video Production Workflow", "Content Guidelines", "Editing Software"], "correct": "Video Production Workflow", "explanation": "The passage describes the onboard video production workflow."},
                {"cefr_band": "intermediate", "passage": "LIVE EVENT STREAMING: The AV team provides live streaming capability for shipboard events including captain's welcome parties, cooking demonstrations, and port arrival coverage. A two-camera setup with a dedicated audio feed is used for most broadcasts. The signal is distributed to stateroom TVs and public area screens via the media server. A five-second broadcast delay is standard for quality control.", "options": ["Broadcasting Equipment", "Live Event Streaming Procedures", "Event Coverage Plan", "Signal Distribution"], "correct": "Live Event Streaming Procedures", "explanation": "The passage explains the live event streaming setup and procedures."},
                {"cefr_band": "advanced", "passage": "MEDIA ASSET MANAGEMENT: All video, photo, and audio content produced onboard is cataloged in a digital asset management system organized by voyage, date, and content type. Files are tagged with metadata including location, talent names, and usage rights. Assets are archived to the shoreside media library at the end of each voyage via satellite upload. Retention policies require raw footage to be stored for three years.", "options": ["Content Library", "Media Asset Management Standards", "File Organization", "Storage Policy"], "correct": "Media Asset Management Standards", "explanation": "The passage describes how media assets are managed, tagged, and archived."},
                {"cefr_band": "advanced", "passage": "POST-PRODUCTION AND BRAND COMPLIANCE: All media content distributed to guests or external channels must comply with the cruise line's brand guidelines covering logo placement, color palette, typography, and music licensing. The AV media supervisor reviews final edits against a brand compliance checklist. Unauthorized use of copyrighted music or third-party footage results in immediate content removal. Quarterly audits verify compliance across all active media assets.", "options": ["Brand Standards", "Post-Production Compliance Standards", "Editorial Guidelines", "Quality Assurance"], "correct": "Post-Production Compliance Standards", "explanation": "The passage outlines the post-production brand compliance requirements."}
            ],
            "Onboard Media": [
                {"cefr_band": "basic", "passage": "DAILY NEWSLETTER: The ship's daily newsletter is delivered to each stateroom by 6:00 AM. It includes the day's schedule of events, dining hours, port information, and weather forecasts. A digital version is available on the cruise app. Guest submissions for announcements must be approved by the media coordinator.", "options": ["Event Schedule", "Daily Newsletter Information", "App Features", "Publication Rules"], "correct": "Daily Newsletter Information", "explanation": "The passage describes the daily newsletter and its content."},
                {"cefr_band": "basic", "passage": "SHIP PHOTOGRAPHY GUIDELINES: The onboard media team photographs key events including embarkation, formal nights, and port arrivals. Photos are displayed in the photo gallery on Deck 7. Crew members appearing in guest-facing media must wear proper uniform. Guests may opt out of photography by notifying Guest Services.", "options": ["Photo Policy", "Ship Photography Guidelines", "Gallery Hours", "Privacy Options"], "correct": "Ship Photography Guidelines", "explanation": "The passage explains the ship's photography guidelines and guest opt-out option."},
                {"cefr_band": "intermediate", "passage": "SOCIAL MEDIA CONTENT CREATION: The onboard media team captures and publishes content to the cruise line's official social media accounts during each voyage. Posts include behind-the-scenes footage, guest testimonials, and destination highlights. All content must be reviewed by the media coordinator before posting. Crew members may not post ship-related content on personal accounts without authorization.", "options": ["Marketing Strategy", "Social Media Content Procedures", "Posting Schedule", "Brand Guidelines"], "correct": "Social Media Content Procedures", "explanation": "The passage describes the social media content creation and approval process."},
                {"cefr_band": "intermediate", "passage": "GUEST TESTIMONIAL COLLECTION: The media team records video testimonials from willing guests during the voyage. Guests sign a release form granting the cruise line usage rights. Interviews are conducted in the media lounge using a standardized question list. Raw footage is edited and forwarded to the shoreside marketing department within 48 hours of voyage end.", "options": ["Interview Guide", "Guest Testimonial Collection Process", "Release Form Details", "Marketing Materials"], "correct": "Guest Testimonial Collection Process", "explanation": "The passage describes how guest testimonials are collected and processed."},
                {"cefr_band": "advanced", "passage": "EDITORIAL CALENDAR AND CONTENT STRATEGY: The onboard media coordinator maintains a voyage-specific editorial calendar aligned with the cruise line's seasonal marketing themes. Content pillars include destination storytelling, culinary experiences, wellness features, and entertainment highlights. The calendar is shared with the entertainment, food and beverage, and shore excursion teams to coordinate cross-departmental coverage. Performance metrics including reach, engagement, and sentiment are reported weekly.", "options": ["Marketing Plan", "Editorial Calendar and Content Strategy", "Campaign Schedule", "Social Media Analytics"], "correct": "Editorial Calendar and Content Strategy", "explanation": "The passage outlines the editorial calendar and content strategy approach."},
                {"cefr_band": "advanced", "passage": "MEDIA CRISIS COMMUNICATION PROTOCOL: In the event of a shipboard incident requiring public communication, the onboard media team follows the fleet crisis communication playbook. All external statements must be approved by the shoreside corporate communications team before release. Social media accounts are paused until messaging is authorized. The media coordinator serves as the onboard point of contact for any press inquiries and documents all media interactions in the incident log.", "options": ["Emergency Procedures", "Media Crisis Communication Protocol", "Public Relations Guide", "Incident Response Plan"], "correct": "Media Crisis Communication Protocol", "explanation": "The passage describes the media crisis communication protocol and chain of approval."}
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
            ],
            "Spa & Wellness": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'What spa treatments do you offer today?' Describe the available services.", "context": "Spa services inquiry", "keywords": ["massage", "facial", "sauna", "appointment", "available", "menu", "today"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should list available treatments clearly."},
                {"cefr_band": "basic", "prompt": "A guest says: 'I'd like to book a massage for this afternoon.' Help them make the appointment.", "context": "Spa booking request", "keywords": ["appointment", "time", "available", "therapist", "duration", "book", "confirm"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should check availability and confirm the booking."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'I have sensitive skin. Which facial treatment would you recommend?' Advise them.", "context": "Treatment recommendation for sensitive skin", "keywords": ["sensitive", "gentle", "hypoallergenic", "recommend", "ingredients", "soothing", "consultation", "patch test"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should recommend appropriate treatments and explain why they suit sensitive skin."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The hot stone massage was too rough and I have bruises.' Handle the complaint.", "context": "Treatment complaint", "keywords": ["apologize", "sorry", "medical", "report", "manager", "compensation", "document", "follow up"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize sincerely, offer medical attention, and escalate."},
                {"cefr_band": "advanced", "prompt": "A couple wants to plan a full-day wellness package including spa, fitness, and healthy dining. Create a personalized itinerary for them.", "context": "Comprehensive wellness package planning", "keywords": ["itinerary", "couples", "treatment", "yoga", "nutrition", "schedule", "relaxation", "customized", "wellness"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should create a detailed and appealing day-long wellness plan."}
            ],
            "Entertainment Technical": [
                {"cefr_band": "basic", "prompt": "A performer says: 'The stage lights are flickering during my act.' Respond and offer to fix the issue.", "context": "Stage lighting malfunction", "keywords": ["lights", "check", "fix", "replace", "moment", "apologies", "technician", "resolve"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should acknowledge the problem and explain immediate steps."},
                {"cefr_band": "basic", "prompt": "The cruise director asks: 'Is the sound system ready for tonight's show?' Confirm the status.", "context": "Sound system readiness check", "keywords": ["ready", "tested", "microphones", "speakers", "levels", "confirmed", "set up"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should confirm readiness with specific details."},
                {"cefr_band": "intermediate", "prompt": "During a live performance, the main speaker blows out. Explain to the stage manager what happened and your backup plan.", "context": "Emergency audio failure during show", "keywords": ["speaker", "blown", "backup", "redirect", "monitor", "channel", "temporary", "replace"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain the failure and present a quick contingency solution."},
                {"cefr_band": "intermediate", "prompt": "A guest performer requests a specific lighting setup for their act. Discuss the requirements and feasibility.", "context": "Custom lighting request from performer", "keywords": ["spotlight", "color", "cue", "dimmer", "position", "feasible", "rehearsal", "program"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should discuss technical capabilities and agree on a workable plan."},
                {"cefr_band": "advanced", "prompt": "Brief your technical crew on the setup requirements for a multi-act variety show including live band, dancers, and aerial performers.", "context": "Complex show technical briefing", "keywords": ["rigging", "cues", "transitions", "safety", "lighting plot", "sound check", "aerial", "coordination", "timeline"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a comprehensive technical plan covering all acts."}
            ],
            "Entertainment": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'What shows are on tonight?' Tell them about the evening entertainment.", "context": "Entertainment schedule inquiry", "keywords": ["show", "tonight", "theater", "time", "comedy", "music", "deck", "schedule"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should describe the evening's entertainment options clearly."},
                {"cefr_band": "basic", "prompt": "A guest says: 'How do I sign up for the karaoke night?' Help them register.", "context": "Activity registration", "keywords": ["sign up", "list", "name", "song", "time", "location", "tonight", "register"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the registration process simply."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The show started late and we missed the beginning because of wrong information.' Respond professionally.", "context": "Schedule misinformation complaint", "keywords": ["apologize", "schedule", "change", "notify", "sorry", "inconvenience", "make up", "feedback"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize and explain what happened while offering a remedy."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'Can you recommend activities for a rainy sea day?' Suggest indoor entertainment options.", "context": "Rainy day activity recommendations", "keywords": ["indoor", "trivia", "movie", "spa", "game show", "workshop", "lounge", "recommend"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should suggest a variety of engaging indoor activities."},
                {"cefr_band": "advanced", "prompt": "Present to the entertainment team your proposal for a new themed deck party that combines live music, interactive games, and dining.", "context": "New event concept proposal", "keywords": ["theme", "concept", "budget", "logistics", "timeline", "music", "interactive", "catering", "promotion"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a creative and well-organized event proposal."}
            ],
            "Fleet Finance": [
                {"cefr_band": "basic", "prompt": "A crew member asks: 'How do I check my onboard account balance?' Explain the process.", "context": "Account balance inquiry", "keywords": ["account", "balance", "kiosk", "reception", "statement", "check", "card"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain how to access account information."},
                {"cefr_band": "basic", "prompt": "A guest asks: 'What currencies do you accept at the front desk?' Provide the information.", "context": "Currency acceptance inquiry", "keywords": ["US dollars", "euros", "credit card", "exchange", "accept", "currency", "cash"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should list accepted currencies and payment methods."},
                {"cefr_band": "intermediate", "prompt": "A department head asks: 'Why is our bar revenue below target this month?' Discuss possible reasons and actions.", "context": "Revenue analysis discussion", "keywords": ["revenue", "target", "variance", "occupancy", "pricing", "promotion", "analysis", "trend"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should analyze the shortfall and suggest corrective actions."},
                {"cefr_band": "intermediate", "prompt": "A vendor invoice has discrepancies. Explain to the supplier what needs to be corrected before payment.", "context": "Invoice discrepancy resolution", "keywords": ["invoice", "discrepancy", "quantity", "price", "correct", "reconcile", "purchase order", "payment"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should identify discrepancies and request corrections professionally."},
                {"cefr_band": "advanced", "prompt": "Present the monthly financial summary to the ship's senior officers, highlighting key variances and recommending budget adjustments.", "context": "Monthly financial review presentation", "keywords": ["budget", "variance", "forecast", "cost control", "revenue", "EBITDA", "savings", "recommendation", "quarter"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present financial data clearly with actionable recommendations."}
            ],
            "Guest Technology": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'How do I connect to the ship's Wi-Fi?' Walk them through the steps.", "context": "Wi-Fi connection assistance", "keywords": ["Wi-Fi", "connect", "password", "network", "settings", "device", "login"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should give simple step-by-step Wi-Fi connection instructions."},
                {"cefr_band": "basic", "prompt": "A guest says: 'The TV in my cabin is not working.' Help them troubleshoot.", "context": "In-cabin TV troubleshooting", "keywords": ["TV", "remote", "power", "channel", "reset", "working", "technician"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should suggest basic troubleshooting steps."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'Which internet package should I buy? I need to video call my family.' Recommend the right plan.", "context": "Internet package recommendation", "keywords": ["package", "streaming", "video call", "bandwidth", "premium", "basic", "speed", "upgrade"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should match the guest's needs to the appropriate package."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The internet is extremely slow and I paid for premium.' Address their concern.", "context": "Internet speed complaint", "keywords": ["apologize", "speed", "congestion", "troubleshoot", "reset", "refund", "premium", "technical team"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should acknowledge the issue and offer solutions or compensation."},
                {"cefr_band": "advanced", "prompt": "The IT manager asks you to explain to the guest services team how the new digital concierge app works so they can assist guests.", "context": "Technology training for staff", "keywords": ["app", "features", "navigation", "booking", "itinerary", "notifications", "troubleshoot", "FAQ", "demo"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should deliver a clear and comprehensive app walkthrough for non-technical staff."}
            ],
            "Human Resources": [
                {"cefr_band": "basic", "prompt": "A new crew member asks: 'Where do I go for my safety orientation?' Direct them.", "context": "New crew orientation directions", "keywords": ["orientation", "deck", "room", "time", "report", "training", "safety"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should give clear directions and timing for orientation."},
                {"cefr_band": "basic", "prompt": "A crew member asks: 'How do I apply for shore leave?' Explain the procedure.", "context": "Shore leave application", "keywords": ["form", "submit", "supervisor", "approval", "schedule", "advance", "shore leave"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the application steps simply."},
                {"cefr_band": "intermediate", "prompt": "A crew member says: 'I'm having a conflict with my cabin mate. Can HR help?' Listen and advise.", "context": "Crew conflict mediation", "keywords": ["understand", "mediation", "discuss", "solution", "respectful", "transfer", "report", "confidential"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should show empathy and explain the mediation process."},
                {"cefr_band": "intermediate", "prompt": "A department head asks: 'We need additional staff for the busy holiday season. How do we request that?' Explain the process.", "context": "Staffing request procedure", "keywords": ["request", "headcount", "approval", "budget", "justification", "recruitment", "timeline", "form"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain the staffing request procedure clearly."},
                {"cefr_band": "advanced", "prompt": "Conduct a briefing for department heads on the new crew performance evaluation system, including timelines and criteria.", "context": "Performance evaluation system rollout", "keywords": ["evaluation", "criteria", "timeline", "feedback", "KPIs", "development plan", "rating", "calibration", "deadline"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present the evaluation system comprehensively with clear expectations."}
            ],
            "Info Technology": [
                {"cefr_band": "basic", "prompt": "A crew member says: 'My work computer won't turn on.' Help them troubleshoot.", "context": "Computer power issue", "keywords": ["power", "cable", "plug", "restart", "button", "check", "IT support"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should suggest basic power troubleshooting steps."},
                {"cefr_band": "basic", "prompt": "A crew member asks: 'I forgot my login password. How do I reset it?' Explain the process.", "context": "Password reset request", "keywords": ["reset", "password", "IT desk", "email", "verify", "temporary", "new password"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the password reset procedure."},
                {"cefr_band": "intermediate", "prompt": "A department reports: 'Our point-of-sale system has been down for 30 minutes.' Explain what actions you are taking.", "context": "POS system outage response", "keywords": ["investigating", "server", "network", "restart", "backup", "ETA", "workaround", "escalate"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain current actions and provide a timeline for resolution."},
                {"cefr_band": "intermediate", "prompt": "A crew member received a suspicious phishing email. Explain to them what to do and why it matters.", "context": "Cybersecurity awareness", "keywords": ["phishing", "delete", "click", "report", "suspicious", "security", "link", "IT team"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should explain safe actions and the importance of reporting."},
                {"cefr_band": "advanced", "prompt": "Present to the ship's management team a proposal for upgrading the onboard network infrastructure, including costs, benefits, and timeline.", "context": "Network upgrade proposal", "keywords": ["bandwidth", "infrastructure", "upgrade", "ROI", "downtime", "phases", "budget", "capacity", "implementation"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a structured technical proposal with business justification."}
            ],
            "Infotainment": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'How do I use the interactive map on the cabin TV?' Show them.", "context": "Interactive TV navigation help", "keywords": ["remote", "menu", "map", "select", "screen", "channel", "navigate"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the TV navigation steps simply."},
                {"cefr_band": "basic", "prompt": "A guest says: 'I want to watch a movie on the cabin TV. How do I find the movie list?' Help them.", "context": "On-demand movie access", "keywords": ["movie", "on-demand", "menu", "select", "remote", "list", "play"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain how to access the movie library."},
                {"cefr_band": "intermediate", "prompt": "A guest reports: 'The interactive screen in the atrium is frozen and not responding.' Explain what you will do.", "context": "Public display malfunction", "keywords": ["restart", "technician", "apologize", "report", "fix", "shortly", "system", "reboot"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should acknowledge the issue and explain the fix process."},
                {"cefr_band": "intermediate", "prompt": "The cruise director asks: 'Can we add a daily quiz game to the interactive TV system?' Discuss feasibility.", "context": "New content feature discussion", "keywords": ["content", "system", "programming", "schedule", "feasible", "format", "upload", "timeline"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should assess feasibility and outline implementation steps."},
                {"cefr_band": "advanced", "prompt": "Present a plan to your team for rolling out a new interactive wayfinding kiosk system across all guest decks, covering installation, testing, and crew training.", "context": "New system rollout planning", "keywords": ["kiosk", "installation", "testing", "training", "rollout", "schedule", "locations", "maintenance", "user experience"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a detailed rollout plan with clear phases and responsibilities."}
            ],
            "Musicians": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'What time does the live music start at the pool deck?' Provide the information.", "context": "Live music schedule inquiry", "keywords": ["music", "pool", "time", "today", "afternoon", "evening", "schedule"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should give the performance time and location."},
                {"cefr_band": "basic", "prompt": "A guest says: 'Can you play Happy Birthday for my wife?' Respond warmly.", "context": "Song request from guest", "keywords": ["of course", "happy to", "birthday", "congratulations", "song", "dedicate", "name"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should accept the request warmly and confirm details."},
                {"cefr_band": "intermediate", "prompt": "The entertainment manager asks: 'Can you adjust your set list for the formal night? We need more jazz and standards.' Discuss the change.", "context": "Set list adjustment request", "keywords": ["set list", "jazz", "standards", "adjust", "repertoire", "formal", "appropriate", "rehearse"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should discuss repertoire options and confirm adjustments."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The band is too loud in the lounge. We can't have a conversation.' Respond diplomatically.", "context": "Volume complaint from guest", "keywords": ["apologize", "volume", "adjust", "lower", "comfortable", "enjoy", "feedback", "balance"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should acknowledge the concern and offer to adjust the volume."},
                {"cefr_band": "advanced", "prompt": "You are rehearsing with a new band member who is unfamiliar with the ship's show format. Explain the performance protocols, cue system, and audience interaction expectations.", "context": "New musician onboarding", "keywords": ["cue", "setlist", "transitions", "audience", "interaction", "protocol", "sound check", "attire", "timing"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should explain performance expectations and logistics comprehensively."}
            ],
            "Production Staff": [
                {"cefr_band": "basic", "prompt": "A performer asks: 'Where is the costume storage room?' Direct them.", "context": "Backstage directions", "keywords": ["costume", "storage", "backstage", "deck", "room", "follow", "stairs"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should give clear directions to the costume area."},
                {"cefr_band": "basic", "prompt": "The stage manager says: 'We need the fog machine refilled before the 8 PM show.' Confirm you will handle it.", "context": "Equipment preparation request", "keywords": ["fog machine", "refill", "ready", "before", "show", "confirm", "done"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should confirm the task and timeline."},
                {"cefr_band": "intermediate", "prompt": "During rehearsal, a dancer reports that part of the stage floor is slippery. Explain how you will address the safety concern.", "context": "Stage safety issue", "keywords": ["safety", "slippery", "tape", "clean", "report", "inspect", "fix", "rehearsal"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should address the hazard immediately and explain preventive measures."},
                {"cefr_band": "intermediate", "prompt": "The production manager asks: 'Can we change the backdrop between acts in under two minutes?' Discuss logistics.", "context": "Quick scene change planning", "keywords": ["backdrop", "change", "crew", "timing", "rehearse", "positions", "smooth", "transition"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should assess feasibility and propose a crew plan for quick changes."},
                {"cefr_band": "advanced", "prompt": "Lead the pre-show production meeting for a new Broadway-style revue, covering technical cues, cast positions, safety protocols, and contingency plans.", "context": "Pre-show production meeting", "keywords": ["cues", "blocking", "safety", "contingency", "run sheet", "crew", "communication", "pyrotechnics", "timeline"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should conduct a thorough and organized pre-show briefing."}
            ],
            "Shore Excursions": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'What shore excursions are available at the next port?' Describe some options.", "context": "Excursion options inquiry", "keywords": ["tour", "beach", "city", "available", "price", "duration", "book"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should describe a few excursion options clearly."},
                {"cefr_band": "basic", "prompt": "A guest says: 'I booked a snorkeling tour but I can't swim well. Is it still safe?' Reassure and advise them.", "context": "Safety concern about excursion", "keywords": ["life jacket", "guide", "safe", "shallow", "alternative", "comfortable", "instructor"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should reassure the guest and explain safety measures or alternatives."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The tour bus left without us and we were only five minutes late.' Handle the complaint.", "context": "Missed excursion complaint", "keywords": ["apologize", "policy", "departure time", "refund", "rebook", "alternative", "understand", "sorry"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should empathize, explain policy, and offer alternatives."},
                {"cefr_band": "intermediate", "prompt": "A guest asks: 'Which excursion is best for elderly parents who cannot walk long distances?' Recommend appropriately.", "context": "Accessibility-focused recommendation", "keywords": ["accessible", "wheelchair", "gentle", "scenic", "seated", "comfortable", "recommend", "pace"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should recommend suitable low-mobility excursions with sensitivity."},
                {"cefr_band": "advanced", "prompt": "Brief the shore excursion team on a new port of call, covering available tours, local risks, emergency contacts, and guest communication plans.", "context": "New port briefing for team", "keywords": ["port", "tours", "safety", "emergency", "contacts", "communication", "logistics", "vendors", "briefing"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should deliver a comprehensive port briefing covering all operational aspects."}
            ],
            "Youth Programs": [
                {"cefr_band": "basic", "prompt": "A parent asks: 'What activities are available for my 6-year-old today?' Describe the kids' program.", "context": "Children's program inquiry", "keywords": ["kids club", "activities", "crafts", "games", "time", "age group", "fun"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should describe age-appropriate activities clearly."},
                {"cefr_band": "basic", "prompt": "A parent says: 'I need to pick up my child from the kids' club. What's the procedure?' Explain.", "context": "Child pickup procedure", "keywords": ["sign out", "ID", "wristband", "parent", "verify", "pickup", "card"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the safe pickup procedure."},
                {"cefr_band": "intermediate", "prompt": "A parent says: 'My daughter is feeling left out in the group activities. Can you help?' Address the concern.", "context": "Child inclusion concern", "keywords": ["understand", "attention", "include", "activities", "buddy", "comfortable", "check in", "support"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should show empathy and explain steps to ensure inclusion."},
                {"cefr_band": "intermediate", "prompt": "A teenager asks: 'The teen club is boring. There's nothing cool to do.' Engage them and suggest activities.", "context": "Teen engagement challenge", "keywords": ["understand", "activities", "gaming", "pool party", "DJ night", "suggestions", "interested", "try"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should engage positively and present appealing options."},
                {"cefr_band": "advanced", "prompt": "Present to the youth programs team your plan for a themed adventure day for children ages 7-12, including activities, staffing, safety measures, and schedule.", "context": "Themed event planning for children", "keywords": ["theme", "activities", "schedule", "staffing", "safety", "ratios", "materials", "backup plan", "engagement"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a detailed, safety-conscious, and engaging event plan."}
            ],
            "Audio Visual Media": [
                {"cefr_band": "basic", "prompt": "A colleague asks: 'How do I play the safety video on the main screen?' Walk them through it.", "context": "Video playback assistance", "keywords": ["screen", "play", "remote", "input", "video", "source", "start"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain the playback steps clearly."},
                {"cefr_band": "basic", "prompt": "The event coordinator says: 'We need a microphone and speaker for the pool deck announcement.' Confirm availability.", "context": "AV equipment request", "keywords": ["microphone", "speaker", "available", "pool deck", "setup", "portable", "ready"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should confirm equipment availability and setup timing."},
                {"cefr_band": "intermediate", "prompt": "During a conference at sea, the presenter's laptop won't connect to the projector. Troubleshoot and explain the steps to the presenter.", "context": "Projector connectivity troubleshooting", "keywords": ["HDMI", "adapter", "resolution", "input", "display", "settings", "cable", "restart"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should troubleshoot methodically and communicate clearly."},
                {"cefr_band": "intermediate", "prompt": "The cruise director wants to livestream the deck party to cabin TVs. Discuss what equipment and setup you need.", "context": "Live streaming setup discussion", "keywords": ["camera", "encoder", "stream", "bandwidth", "channel", "feed", "test", "monitor"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should outline the technical requirements for the livestream."},
                {"cefr_band": "advanced", "prompt": "Propose a complete AV upgrade plan for the ship's main theater, including new projection, sound, and lighting systems with budget estimates and installation timeline.", "context": "Theater AV upgrade proposal", "keywords": ["projection", "surround sound", "LED", "budget", "installation", "downtime", "phases", "specifications", "ROI"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present a comprehensive and well-justified upgrade proposal."}
            ],
            "Onboard Media": [
                {"cefr_band": "basic", "prompt": "A guest asks: 'Where can I find the daily newsletter with today's activities?' Help them.", "context": "Daily program inquiry", "keywords": ["newsletter", "daily", "cabin", "app", "activities", "schedule", "copy"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should explain where to find the daily program."},
                {"cefr_band": "basic", "prompt": "A guest says: 'I'd like a printed copy of my cruise photos. Where do I go?' Direct them.", "context": "Photo printing request", "keywords": ["photo", "gallery", "print", "deck", "digital", "order", "pick up"], "rubric": {"fluency": 2, "vocabulary": 2, "grammar": 2, "content": 4}, "explanation": "Should direct the guest to the appropriate location."},
                {"cefr_band": "intermediate", "prompt": "The marketing manager asks: 'Can you create a short promotional video for the spa's new treatment?' Discuss the plan.", "context": "Promotional content creation", "keywords": ["video", "script", "footage", "editing", "deadline", "approval", "format", "channels"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should outline the video production steps and timeline."},
                {"cefr_band": "intermediate", "prompt": "A guest complains: 'The digital signage near the restaurant shows the wrong menu times.' Report and fix the issue.", "context": "Digital signage error", "keywords": ["signage", "update", "correct", "apologize", "content management", "fix", "verify", "menu"], "rubric": {"fluency": 3, "vocabulary": 3, "grammar": 2, "content": 2}, "explanation": "Should apologize, fix the content, and verify the correction."},
                {"cefr_band": "advanced", "prompt": "Present a content strategy for all onboard media channels—cabin TV, digital signage, app notifications, and printed materials—for an upcoming themed cruise week.", "context": "Multi-channel content strategy", "keywords": ["strategy", "channels", "content calendar", "branding", "messaging", "coordination", "assets", "approval", "distribution"], "rubric": {"fluency": 3, "vocabulary": 2, "grammar": 2, "content": 3}, "explanation": "Should present an integrated, multi-channel content plan with clear timelines."}
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
