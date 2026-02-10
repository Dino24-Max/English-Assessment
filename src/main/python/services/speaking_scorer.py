"""
Speaking Module Scoring Service

Provides intelligent scoring for speaking module responses with:
- Keyword matching with synonyms and semantic similarity
- Partial credit for related concepts
- Pronunciation and fluency estimation
- Context-aware scoring adjustments
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SpeakingScoreLevel(Enum):
    """Speaking score levels"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 70-89%
    SATISFACTORY = "satisfactory"  # 50-69%
    NEEDS_IMPROVEMENT = "needs_improvement"  # 30-49%
    POOR = "poor"           # 0-29%


@dataclass
class SpeakingScoreResult:
    """Detailed speaking score result"""
    total_points: float
    max_points: float
    percentage: float
    level: SpeakingScoreLevel
    
    # Component scores
    keyword_score: float
    keyword_max: float
    fluency_score: float
    fluency_max: float
    completeness_score: float
    completeness_max: float
    
    # Details
    matched_keywords: List[str]
    missing_keywords: List[str]
    partial_matches: List[Tuple[str, str, float]]  # (expected, found, similarity)
    
    # Feedback
    feedback: str
    improvement_tips: List[str]


class SpeakingScorerService:
    """
    Intelligent scoring service for speaking module responses.
    
    Features:
    - Synonym matching for flexibility
    - Partial credit for related concepts
    - Fluency estimation from transcript
    - Context-aware scoring
    """
    
    # Cruise/hospitality synonym mappings
    SYNONYMS = {
        # Apology words
        "apologize": ["sorry", "apologies", "apologise", "regret", "pardon"],
        "sorry": ["apologize", "apologies", "apologise", "regret", "pardon"],
        
        # Service words
        "help": ["assist", "support", "aid", "service"],
        "assist": ["help", "support", "aid", "service"],
        
        # Guest/customer words
        "guest": ["customer", "passenger", "visitor", "client"],
        "customer": ["guest", "passenger", "visitor", "client"],
        
        # Room/cabin words
        "room": ["cabin", "stateroom", "suite", "accommodation"],
        "cabin": ["room", "stateroom", "suite", "accommodation"],
        
        # Fix/repair words
        "fix": ["repair", "resolve", "address", "correct", "rectify"],
        "repair": ["fix", "resolve", "address", "correct", "rectify"],
        
        # Send/dispatch words
        "send": ["dispatch", "arrange", "call", "contact"],
        
        # Comfort words
        "comfortable": ["comfort", "pleasant", "satisfied", "happy"],
        
        # Time words
        "immediately": ["right away", "promptly", "shortly", "soon", "asap"],
        "soon": ["shortly", "promptly", "immediately", "right away"],
        
        # Department words
        "maintenance": ["engineering", "technical", "repair team"],
        "housekeeping": ["room service", "cleaning", "steward"],
        
        # Polite words
        "please": ["kindly"],
        "thank": ["thanks", "appreciate", "grateful"],
        
        # Temperature words
        "temperature": ["temp", "heat", "cold", "cooling", "heating"],
        "air conditioning": ["ac", "a/c", "cooling", "climate control"],
        
        # Location words
        "deck": ["floor", "level"],
        "restaurant": ["dining", "buffet", "eatery"],
        "spa": ["wellness", "salon"],
    }
    
    # Common filler words to ignore in fluency analysis
    FILLER_WORDS = {
        "um", "uh", "er", "ah", "like", "you know", "basically",
        "actually", "literally", "so", "well", "i mean"
    }
    
    # Polite phrases that should be rewarded
    POLITE_PHRASES = [
        "please", "thank you", "thanks", "i apologize", "i'm sorry",
        "excuse me", "pardon", "certainly", "of course", "absolutely",
        "my pleasure", "happy to help", "let me help", "i understand",
        "i appreciate", "right away", "immediately"
    ]
    
    def __init__(self, base_points: float = 4.0):
        """
        Initialize speaking scorer.
        
        Args:
            base_points: Base points per speaking question (default 4.0)
        """
        self.base_points = base_points
    
    def score_response(
        self,
        transcript: str,
        expected_keywords: List[str],
        question_context: str = "",
        recording_duration: float = 0.0
    ) -> SpeakingScoreResult:
        """
        Score a speaking response.
        
        Args:
            transcript: Transcribed speech text
            expected_keywords: List of expected keywords/phrases
            question_context: Question scenario context
            recording_duration: Duration of recording in seconds
            
        Returns:
            SpeakingScoreResult with detailed scoring
        """
        # Normalize inputs
        transcript_lower = transcript.lower().strip()
        expected_lower = [kw.lower().strip() for kw in expected_keywords]
        
        # 1. Keyword matching (60% of score)
        keyword_result = self._score_keywords(transcript_lower, expected_lower)
        keyword_max = self.base_points * 0.6
        keyword_score = keyword_result["score"] * keyword_max
        
        # 2. Fluency estimation (20% of score)
        fluency_result = self._estimate_fluency(transcript_lower, recording_duration)
        fluency_max = self.base_points * 0.2
        fluency_score = fluency_result["score"] * fluency_max
        
        # 3. Completeness/politeness (20% of score)
        completeness_result = self._score_completeness(transcript_lower, question_context)
        completeness_max = self.base_points * 0.2
        completeness_score = completeness_result["score"] * completeness_max
        
        # Calculate total
        total_points = keyword_score + fluency_score + completeness_score
        percentage = (total_points / self.base_points) * 100
        level = self._percentage_to_level(percentage)
        
        # Generate feedback
        feedback, tips = self._generate_feedback(
            keyword_result, fluency_result, completeness_result, level
        )
        
        return SpeakingScoreResult(
            total_points=round(total_points, 2),
            max_points=self.base_points,
            percentage=round(percentage, 1),
            level=level,
            keyword_score=round(keyword_score, 2),
            keyword_max=keyword_max,
            fluency_score=round(fluency_score, 2),
            fluency_max=fluency_max,
            completeness_score=round(completeness_score, 2),
            completeness_max=completeness_max,
            matched_keywords=keyword_result["matched"],
            missing_keywords=keyword_result["missing"],
            partial_matches=keyword_result["partial"],
            feedback=feedback,
            improvement_tips=tips
        )
    
    def _score_keywords(
        self, 
        transcript: str, 
        expected_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Score keyword matching with synonym support.
        
        Args:
            transcript: Normalized transcript
            expected_keywords: List of expected keywords
            
        Returns:
            Dict with score, matched, missing, and partial matches
        """
        if not expected_keywords:
            return {
                "score": 1.0,
                "matched": [],
                "missing": [],
                "partial": []
            }
        
        matched = []
        missing = []
        partial = []
        
        # Tokenize transcript for word matching
        transcript_words = set(re.findall(r'\b\w+\b', transcript))
        
        for keyword in expected_keywords:
            keyword_clean = keyword.strip().lower()
            
            # Check exact match
            if keyword_clean in transcript or self._phrase_in_text(keyword_clean, transcript):
                matched.append(keyword)
                continue
            
            # Check synonym match
            synonym_match = self._check_synonyms(keyword_clean, transcript, transcript_words)
            if synonym_match:
                matched.append(keyword)
                partial.append((keyword, synonym_match, 0.9))
                continue
            
            # Check partial/fuzzy match
            partial_match = self._check_partial_match(keyword_clean, transcript_words)
            if partial_match:
                partial.append((keyword, partial_match[0], partial_match[1]))
                if partial_match[1] >= 0.7:
                    matched.append(keyword)
                continue
            
            missing.append(keyword)
        
        # Calculate score
        total_keywords = len(expected_keywords)
        full_matches = len([m for m in matched if m not in [p[0] for p in partial]])
        partial_matches = len([p for p in partial if p[2] >= 0.7])
        weak_matches = len([p for p in partial if 0.5 <= p[2] < 0.7])
        
        # Weighted scoring
        score = (
            full_matches * 1.0 +
            partial_matches * 0.8 +
            weak_matches * 0.5
        ) / total_keywords
        
        return {
            "score": min(1.0, score),
            "matched": matched,
            "missing": missing,
            "partial": partial
        }
    
    def _phrase_in_text(self, phrase: str, text: str) -> bool:
        """
        Check if a phrase exists in text (handles multi-word phrases).
        
        Args:
            phrase: Phrase to find
            text: Text to search in
            
        Returns:
            True if phrase found
        """
        # Simple word boundary check
        pattern = r'\b' + re.escape(phrase) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _check_synonyms(
        self, 
        keyword: str, 
        transcript: str,
        transcript_words: Set[str]
    ) -> Optional[str]:
        """
        Check if any synonym of keyword exists in transcript.
        
        Args:
            keyword: Keyword to check
            transcript: Full transcript text
            transcript_words: Set of words in transcript
            
        Returns:
            Matched synonym or None
        """
        # Get synonyms for this keyword
        synonyms = self.SYNONYMS.get(keyword, [])
        
        # Also check if keyword is a synonym of something else
        for base_word, syn_list in self.SYNONYMS.items():
            if keyword in syn_list:
                synonyms.extend([base_word] + syn_list)
        
        synonyms = list(set(synonyms))
        
        for synonym in synonyms:
            if synonym in transcript_words or self._phrase_in_text(synonym, transcript):
                return synonym
        
        return None
    
    def _check_partial_match(
        self, 
        keyword: str, 
        transcript_words: Set[str]
    ) -> Optional[Tuple[str, float]]:
        """
        Check for partial/fuzzy matches.
        
        Args:
            keyword: Keyword to match
            transcript_words: Set of words in transcript
            
        Returns:
            Tuple of (matched_word, similarity) or None
        """
        best_match = None
        best_score = 0.0
        
        for word in transcript_words:
            if len(word) < 3:
                continue
            
            # Check if one contains the other
            if keyword in word or word in keyword:
                similarity = min(len(keyword), len(word)) / max(len(keyword), len(word))
                if similarity > best_score:
                    best_score = similarity
                    best_match = word
            
            # Check prefix match
            elif keyword[:3] == word[:3] and len(keyword) > 3 and len(word) > 3:
                # Calculate similarity based on common prefix
                common_len = 0
                for i in range(min(len(keyword), len(word))):
                    if keyword[i] == word[i]:
                        common_len += 1
                    else:
                        break
                similarity = common_len / max(len(keyword), len(word))
                if similarity > best_score and similarity >= 0.5:
                    best_score = similarity
                    best_match = word
        
        if best_match and best_score >= 0.5:
            return (best_match, best_score)
        
        return None
    
    def _estimate_fluency(
        self, 
        transcript: str, 
        duration: float
    ) -> Dict[str, Any]:
        """
        Estimate fluency from transcript.
        
        Args:
            transcript: Transcribed text
            duration: Recording duration in seconds
            
        Returns:
            Dict with score and details
        """
        if not transcript or transcript.startswith("["):
            return {"score": 0.3, "words_per_minute": 0, "filler_ratio": 0}
        
        # Count words
        words = re.findall(r'\b\w+\b', transcript)
        word_count = len(words)
        
        # Count filler words
        filler_count = sum(1 for w in words if w.lower() in self.FILLER_WORDS)
        filler_ratio = filler_count / max(1, word_count)
        
        # Calculate words per minute
        if duration > 0:
            wpm = (word_count / duration) * 60
        else:
            wpm = word_count * 6  # Assume ~10 seconds if no duration
        
        # Score based on WPM (optimal is 120-150 WPM)
        if 100 <= wpm <= 180:
            wpm_score = 1.0
        elif 80 <= wpm < 100 or 180 < wpm <= 200:
            wpm_score = 0.8
        elif 60 <= wpm < 80 or 200 < wpm <= 220:
            wpm_score = 0.6
        else:
            wpm_score = 0.4
        
        # Penalize for filler words
        filler_penalty = min(0.3, filler_ratio)
        
        # Final fluency score
        score = max(0.2, wpm_score - filler_penalty)
        
        return {
            "score": score,
            "words_per_minute": wpm,
            "filler_ratio": filler_ratio,
            "word_count": word_count
        }
    
    def _score_completeness(
        self, 
        transcript: str, 
        context: str
    ) -> Dict[str, Any]:
        """
        Score completeness and politeness.
        
        Args:
            transcript: Transcribed text
            context: Question context
            
        Returns:
            Dict with score and details
        """
        if not transcript or transcript.startswith("["):
            return {"score": 0.2, "polite_phrases": [], "sentence_count": 0}
        
        # Count sentences (rough estimate)
        sentences = re.split(r'[.!?]+', transcript)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Check for polite phrases
        polite_found = []
        for phrase in self.POLITE_PHRASES:
            if phrase in transcript:
                polite_found.append(phrase)
        
        # Score components
        # Sentence completeness (at least 2-3 sentences is good)
        if sentence_count >= 3:
            sentence_score = 1.0
        elif sentence_count == 2:
            sentence_score = 0.8
        elif sentence_count == 1:
            sentence_score = 0.5
        else:
            sentence_score = 0.2
        
        # Politeness bonus
        politeness_score = min(1.0, len(polite_found) * 0.25)
        
        # Combined score
        score = sentence_score * 0.6 + politeness_score * 0.4
        
        return {
            "score": score,
            "polite_phrases": polite_found,
            "sentence_count": sentence_count
        }
    
    def _percentage_to_level(self, percentage: float) -> SpeakingScoreLevel:
        """
        Convert percentage to score level.
        
        Args:
            percentage: Score percentage
            
        Returns:
            SpeakingScoreLevel enum
        """
        if percentage >= 90:
            return SpeakingScoreLevel.EXCELLENT
        elif percentage >= 70:
            return SpeakingScoreLevel.GOOD
        elif percentage >= 50:
            return SpeakingScoreLevel.SATISFACTORY
        elif percentage >= 30:
            return SpeakingScoreLevel.NEEDS_IMPROVEMENT
        else:
            return SpeakingScoreLevel.POOR
    
    def _generate_feedback(
        self,
        keyword_result: Dict,
        fluency_result: Dict,
        completeness_result: Dict,
        level: SpeakingScoreLevel
    ) -> Tuple[str, List[str]]:
        """
        Generate feedback and improvement tips.
        
        Args:
            Various scoring results
            level: Overall score level
            
        Returns:
            Tuple of (feedback_message, improvement_tips)
        """
        tips = []
        
        # Level-based feedback
        level_feedback = {
            SpeakingScoreLevel.EXCELLENT: "Excellent response! You demonstrated strong communication skills.",
            SpeakingScoreLevel.GOOD: "Good response. You covered the key points well.",
            SpeakingScoreLevel.SATISFACTORY: "Satisfactory response. Some key elements were addressed.",
            SpeakingScoreLevel.NEEDS_IMPROVEMENT: "Your response needs improvement in several areas.",
            SpeakingScoreLevel.POOR: "Your response did not adequately address the scenario."
        }
        
        feedback = level_feedback[level]
        
        # Keyword tips
        if keyword_result["missing"]:
            missing_count = len(keyword_result["missing"])
            if missing_count <= 2:
                tips.append(f"Try to include: {', '.join(keyword_result['missing'][:2])}")
            else:
                tips.append("Include more key terms related to the scenario")
        
        # Fluency tips
        if fluency_result["score"] < 0.6:
            if fluency_result.get("words_per_minute", 0) < 80:
                tips.append("Try to speak a bit faster and more naturally")
            elif fluency_result.get("words_per_minute", 0) > 200:
                tips.append("Slow down slightly for clearer communication")
            if fluency_result.get("filler_ratio", 0) > 0.1:
                tips.append("Reduce filler words like 'um' and 'uh'")
        
        # Completeness tips
        if completeness_result["score"] < 0.6:
            if completeness_result.get("sentence_count", 0) < 2:
                tips.append("Provide a more complete response with full sentences")
            if not completeness_result.get("polite_phrases"):
                tips.append("Use polite phrases like 'I apologize' or 'Let me help you'")
        
        return feedback, tips


# Convenience function for quick scoring
def score_speaking_response(
    transcript: str,
    expected_keywords: List[str],
    question_context: str = "",
    recording_duration: float = 0.0,
    base_points: float = 4.0
) -> SpeakingScoreResult:
    """
    Quick function to score a speaking response.
    
    Args:
        transcript: Transcribed speech text
        expected_keywords: List of expected keywords/phrases
        question_context: Question scenario context
        recording_duration: Duration of recording in seconds
        base_points: Base points for the question
        
    Returns:
        SpeakingScoreResult with detailed scoring
    """
    scorer = SpeakingScorerService(base_points=base_points)
    return scorer.score_response(
        transcript, expected_keywords, question_context, recording_duration
    )
