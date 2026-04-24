"""
Core (universal) grammar scenarios for question bank generation.

Each item: cefr_band, grammar_type, grammar_topic, question, options, correct, explanation.
cefr_band aligns with _cefr_band() in generate_question_bank (A1/A2→basic, B1/B2→intermediate, C1/C2→advanced).
"""

from __future__ import annotations

from typing import Any, Dict, List


def _r(
    band: str,
    topic: str,
    question: str,
    options: List[str],
    correct: str,
    explanation: str,
) -> Dict[str, Any]:
    return {
        "cefr_band": band,
        "grammar_type": "Core",
        "grammar_topic": topic,
        "question": question,
        "options": options,
        "correct": correct,
        "explanation": explanation,
    }


def build_core_grammar_pool() -> List[Dict[str, Any]]:
    """Return a large core pool so blueprint sampling without replacement rarely exhausts."""
    p: List[Dict[str, Any]] = []

    # --- Present Simple (basic) ---
    ps = [
        ("The ship ___ at 6:00 PM for muster.", ["sail", "sails", "sailing", "sailed"], "sails"),
        ("The crew ___ uniforms during service hours.", ["wear", "wears", "wearing", "wore"], "wear"),
        ("The restaurant ___ dinner until 10 PM.", ["serve", "serves", "serving", "served"], "serves"),
        ("The pool deck ___ at 8 AM.", ["open", "opens", "opening", "opened"], "opens"),
        ("The safety video ___ in five languages.", ["play", "plays", "playing", "played"], "plays"),
        ("The captain ___ the welcome speech tonight.", ["give", "gives", "giving", "gave"], "gives"),
        ("The spa ___ appointments online.", ["take", "takes", "taking", "took"], "takes"),
        ("The galley ___ fresh bread daily.", ["prepare", "prepares", "preparing", "prepared"], "prepares"),
    ]
    for q, opts, c in ps:
        p.append(_r("basic", "Present Simple", q, opts, c, "Present simple with third person or plural subject."))

    # --- To Be Verb (basic) ---
    tb = [
        ("The guests ___ ready for disembarkation.", ["is", "am", "are", "be"], "are"),
        ("The luggage ___ on deck five.", ["is", "are", "am", "be"], "is"),
        ("We ___ pleased to welcome you aboard.", ["is", "am", "are", "be"], "are"),
        ("The weather ___ calm this evening.", ["is", "are", "am", "be"], "is"),
        ("The keys ___ at the front desk.", ["is", "are", "am", "be"], "are"),
        ("The itinerary ___ available on the app.", ["is", "are", "am", "be"], "is"),
    ]
    for q, opts, c in tb:
        p.append(_r("basic", "To Be Verb", q, opts, c, "Correct form of 'to be' for the subject."))

    # --- Past Simple (basic) ---
    pas = [
        ("The guest ___ late to the excursion yesterday.", ["arrive", "arrives", "arrived", "arriving"], "arrived"),
        ("We ___ the safety drill before sailing.", ["complete", "completes", "completed", "completing"], "completed"),
        ("The engineer ___ the valve last night.", ["check", "checks", "checked", "checking"], "checked"),
        ("The team ___ extra towels this morning.", ["deliver", "delivers", "delivered", "delivering"], "delivered"),
        ("I ___ my training record signed.", ["get", "gets", "got", "getting"], "got"),
        ("They ___ the inventory after midnight.", ["count", "counts", "counted", "counting"], "counted"),
        ("She ___ the guest complaint to her supervisor.", ["report", "reports", "reported", "reporting"], "reported"),
    ]
    for q, opts, c in pas:
        p.append(_r("basic", "Past Simple", q, opts, c, "Past simple for a finished past action."))

    # --- Modals Can/Must (basic) ---
    mod = [
        ("Crew ___ wear life jackets during the drill.", ["can", "must", "may", "could"], "must"),
        ("Guests ___ ask for a wake-up call at reception.", ["must", "can", "should", "might"], "can"),
        ("You ___ smoke on the balcony.", ["can", "must not", "should", "may"], "must not"),
        ("Staff ___ use gloves when plating cold items.", ["may", "must", "might", "could"], "must"),
        ("Passengers ___ request a cabin change if available.", ["must", "can", "ought", "shall"], "can"),
        ("We ___ report spills immediately.", ["can", "must", "could", "might"], "must"),
    ]
    for q, opts, c in mod:
        p.append(_r("basic", "Modals Can/Must", q, opts, c, "Modal verb for obligation or permission."))

    # --- Present Perfect (intermediate) ---
    pp = [
        ("The team ___ completed the deep clean.", ["have", "has", "had", "having"], "has"),
        ("We ___ already updated the menu boards.", ["have", "has", "had", "having"], "have"),
        ("The hotel director ___ approved the overtime.", ["have", "has", "had", "having"], "has"),
        ("They ___ not received the manifest yet.", ["have", "has", "had", "having"], "have"),
        ("She ___ just finished the audit.", ["have", "has", "had", "having"], "has"),
        ("The galley ___ prepared 200 covers tonight.", ["have", "has", "had", "having"], "has"),
        ("I ___ seen this issue before on turnaround day.", ["have", "has", "had", "having"], "have"),
    ]
    for q, opts, c in pp:
        p.append(_r("intermediate", "Present Perfect", q, opts, c, "Present perfect for recent relevance."))

    # --- Passive Voice (intermediate) ---
    pv = [
        ("The cabins ___ serviced before noon.", ["are", "is", "were", "be"], "are"),
        ("Lunch ___ served on the lido deck.", ["is", "are", "was", "were"], "is"),
        ("The incident ___ logged in the security system.", ["was", "were", "is", "are"], "was"),
        ("Tickets ___ validated at the gangway.", ["are", "is", "was", "were"], "are"),
        ("The wine ___ stored at the correct temperature.", ["is", "are", "was", "were"], "is"),
        ("All trays ___ collected after midnight.", ["are", "is", "was", "were"], "are"),
    ]
    for q, opts, c in pv:
        p.append(_r("intermediate", "Passive Voice", q, opts, c, "Passive voice for processes and procedures."))

    # --- Past Perfect (intermediate) ---
    pperf = [
        ("By the time we arrived, the ship ___ already departed.", ["had", "has", "have", "was"], "had"),
        ("She realized she ___ forgotten her badge.", ["had", "has", "have", "was"], "had"),
        ("They could not enter because the area ___ been closed.", ["had", "has", "have", "was"], "had"),
        ("Before the audit, we ___ completed the checklist.", ["had", "has", "have", "were"], "had"),
        ("The guest said he ___ reserved a balcony cabin.", ["had", "has", "have", "was"], "had"),
        ("After I ___ spoken to HR, I updated the roster.", ["had", "has", "have", "was"], "had"),
    ]
    for q, opts, c in pperf:
        p.append(_r("intermediate", "Past Perfect", q, opts, c, "Past perfect for an earlier past event."))

    # --- Reported Speech (intermediate) ---
    rs = [
        ('He said he ___ tired after the double shift.', ["was", "is", "has been", "will be"], "was"),
        ("She told me she ___ help with the luggage.", ["would", "will", "can", "must"], "would"),
        ("They announced that the show ___ start at nine.", ["would", "will", "can", "should"], "would"),
        ("The captain said we ___ remain seated.", ["should", "will", "may", "might"], "should"),
        ("Guest services said the refund ___ processed tomorrow.", ["would be", "is", "was", "has been"], "would be"),
        ("He explained that the route ___ changed due to weather.", ["had been", "was", "is", "has been"], "had been"),
    ]
    for q, opts, c in rs:
        p.append(_r("intermediate", "Reported Speech", q, opts, c, "Reported speech tense / modal backshift."))

    # --- Obligation (advanced) ---
    ob = [
        ("All contractors ___ complete safety training before boarding.", ["must", "might", "could", "may"], "must"),
        ("The chief engineer insisted that every valve ___ inspected.", ["be", "is", "was", "been"], "be"),
        ("It is essential that the manifest ___ accurate.", ["be", "is", "was", "are"], "be"),
        ("The policy requires that staff ___ identification visible.", ["keep", "keeps", "kept", "keeping"], "keep"),
        ("We recommend that the area ___ cordoned off.", ["be", "is", "was", "are"], "be"),
    ]
    for q, opts, c in ob:
        p.append(_r("advanced", "Obligation", q, opts, c, "Formal obligation / subjunctive-style patterns."))

    # --- Nuanced Modality (advanced) ---
    nm = [
        ("The findings ___ suggest a need for retraining.", ["may", "must", "will", "shall"], "may"),
        ("The delay ___ have been avoided with better planning.", ["might", "must", "should", "can"], "might"),
        ("Guests ___ reasonably expect timely service.", ["might", "can", "must", "shall"], "can"),
        ("The report ought ___ include near-miss data.", ["to", "for", "of", "with"], "to"),
    ]
    for q, opts, c in nm:
        p.append(_r("advanced", "Nuanced Modality", q, opts, c, "Nuanced modal for hedging or inference."))

    return p


CORE_GRAMMAR_POOL: List[Dict[str, Any]] = build_core_grammar_pool()
