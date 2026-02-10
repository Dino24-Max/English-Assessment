"""
Unit tests for Speaking Module components

Tests:
- Audio quality analyzer
- Speaking scorer with keyword matching
- Synonym matching
- Fluency estimation
"""

import sys
from pathlib import Path
import numpy as np

# Add src/main/python to path BEFORE any other imports
project_root = Path(__file__).parent.parent.parent.parent
python_src = project_root / "src" / "main" / "python"
if str(python_src) not in sys.path:
    sys.path.insert(0, str(python_src))

import pytest
from services.audio_quality import (
    AudioQualityAnalyzer, 
    AudioQualityLevel, 
    AudioQualityReport,
    get_audio_quality_feedback
)
from services.speaking_scorer import (
    SpeakingScorerService,
    SpeakingScoreLevel,
    SpeakingScoreResult,
    score_speaking_response
)


# ============================================
# Audio Quality Analyzer Tests
# ============================================

class TestAudioQualityAnalyzer:
    """Tests for AudioQualityAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return AudioQualityAnalyzer(sample_rate=16000)
    
    def test_duration_analysis_too_short(self, analyzer):
        """Test duration scoring for short recordings"""
        score = analyzer._analyze_duration(1.0)  # 1 second
        assert score < 0.5, "Short duration should have low score"
    
    def test_duration_analysis_optimal(self, analyzer):
        """Test duration scoring for optimal length"""
        score = analyzer._analyze_duration(10.0)  # 10 seconds
        assert score >= 0.9, "Optimal duration should have high score"
    
    def test_duration_analysis_too_long(self, analyzer):
        """Test duration scoring for long recordings"""
        score = analyzer._analyze_duration(150.0)  # 2.5 minutes
        assert score < 0.7, "Long duration should have reduced score"
    
    def test_volume_analysis_quiet(self, analyzer):
        """Test volume analysis for quiet audio"""
        # Create quiet audio (low amplitude)
        quiet_audio = np.random.randn(16000) * 0.001
        result = analyzer._analyze_volume(quiet_audio)
        
        assert result["average_db"] < -40, "Quiet audio should have low dB"
        assert result["score"] < 0.7, "Quiet audio should have lower score"
    
    def test_volume_analysis_normal(self, analyzer):
        """Test volume analysis for normal audio"""
        # Create normal amplitude audio
        normal_audio = np.random.randn(16000) * 0.1
        result = analyzer._analyze_volume(normal_audio)
        
        assert -30 < result["average_db"] < -10, "Normal audio should have moderate dB"
        assert result["score"] >= 0.5, "Normal audio should have decent score"
    
    def test_clipping_detection_clean(self, analyzer):
        """Test clipping detection for clean audio"""
        # Create audio without clipping (lower amplitude to ensure no clipping)
        clean_audio = np.random.randn(16000) * 0.3
        result = analyzer._detect_clipping(clean_audio)
        
        assert result["percentage"] < 5.0, "Clean audio should have minimal clipping"
        assert result["score"] >= 0.7, "Clean audio should have good clipping score"
    
    def test_clipping_detection_clipped(self, analyzer):
        """Test clipping detection for clipped audio"""
        # Create audio with clipping
        clipped_audio = np.random.randn(16000) * 2.0
        clipped_audio = np.clip(clipped_audio, -1.0, 1.0)
        result = analyzer._detect_clipping(clipped_audio)
        
        assert result["percentage"] > 0, "Clipped audio should have some clipping"
    
    def test_score_to_level_excellent(self, analyzer):
        """Test score to level conversion for excellent"""
        level = analyzer._score_to_level(0.90)
        assert level == AudioQualityLevel.EXCELLENT
    
    def test_score_to_level_good(self, analyzer):
        """Test score to level conversion for good"""
        level = analyzer._score_to_level(0.75)
        assert level == AudioQualityLevel.GOOD
    
    def test_score_to_level_acceptable(self, analyzer):
        """Test score to level conversion for acceptable"""
        level = analyzer._score_to_level(0.55)
        assert level == AudioQualityLevel.ACCEPTABLE
    
    def test_score_to_level_poor(self, analyzer):
        """Test score to level conversion for poor"""
        level = analyzer._score_to_level(0.35)
        assert level == AudioQualityLevel.POOR
    
    def test_score_to_level_unusable(self, analyzer):
        """Test score to level conversion for unusable"""
        level = analyzer._score_to_level(0.15)
        assert level == AudioQualityLevel.UNUSABLE
    
    def test_error_report_creation(self, analyzer):
        """Test error report creation"""
        report = analyzer._create_error_report("Test error")
        
        assert report.overall_level == AudioQualityLevel.ACCEPTABLE
        assert report.overall_score == 0.5
        assert "Test error" in report.issues[0]


class TestAudioQualityFeedback:
    """Tests for audio quality feedback generation"""
    
    def test_excellent_feedback(self):
        """Test feedback for excellent quality"""
        report = AudioQualityReport(
            overall_level=AudioQualityLevel.EXCELLENT,
            overall_score=0.95,
            volume_score=0.9,
            noise_score=0.9,
            clipping_score=1.0,
            duration_score=1.0,
            speech_detected=True,
            issues=[],
            recommendations=[],
            duration_seconds=10.0,
            average_volume_db=-20.0,
            peak_volume_db=-5.0,
            noise_floor_db=-50.0,
            clipping_percentage=0.0,
            speech_ratio=0.8
        )
        
        feedback = get_audio_quality_feedback(report)
        assert "Excellent" in feedback
    
    def test_poor_feedback_with_issues(self):
        """Test feedback for poor quality with issues"""
        report = AudioQualityReport(
            overall_level=AudioQualityLevel.POOR,
            overall_score=0.35,
            volume_score=0.3,
            noise_score=0.4,
            clipping_score=0.5,
            duration_score=0.4,
            speech_detected=True,
            issues=["Audio too quiet", "High background noise"],
            recommendations=["Speak louder", "Find quieter environment"],
            duration_seconds=5.0,
            average_volume_db=-45.0,
            peak_volume_db=-20.0,
            noise_floor_db=-25.0,
            clipping_percentage=0.0,
            speech_ratio=0.4
        )
        
        feedback = get_audio_quality_feedback(report)
        assert "poor" in feedback.lower()
        assert "Issues:" in feedback
        assert "Suggestions:" in feedback


# ============================================
# Speaking Scorer Tests
# ============================================

class TestSpeakingScorerService:
    """Tests for SpeakingScorerService"""
    
    @pytest.fixture
    def scorer(self):
        return SpeakingScorerService(base_points=4.0)
    
    def test_exact_keyword_match(self, scorer):
        """Test exact keyword matching"""
        transcript = "I apologize for the inconvenience. I will send maintenance to fix the air conditioning."
        keywords = ["apologize", "maintenance", "air conditioning"]
        
        result = scorer.score_response(transcript, keywords)
        
        assert len(result.matched_keywords) == 3
        assert len(result.missing_keywords) == 0
        assert result.percentage >= 70
    
    def test_synonym_matching(self, scorer):
        """Test synonym matching"""
        transcript = "I'm sorry about that. I will call someone to repair the AC."
        keywords = ["apologize", "fix", "air conditioning"]
        
        result = scorer.score_response(transcript, keywords)
        
        # "sorry" is synonym of "apologize", "repair" is synonym of "fix"
        assert len(result.matched_keywords) >= 2
        assert result.percentage >= 50
    
    def test_partial_keyword_match(self, scorer):
        """Test partial keyword matching"""
        transcript = "I apologize for the temperature issue. The technician will come."
        keywords = ["apologize", "temperature", "maintenance"]
        
        result = scorer.score_response(transcript, keywords)
        
        assert "apologize" in result.matched_keywords
        assert "temperature" in result.matched_keywords
    
    def test_missing_keywords(self, scorer):
        """Test detection of missing keywords"""
        transcript = "Okay, I will help you."
        keywords = ["apologize", "maintenance", "air conditioning", "comfortable"]
        
        result = scorer.score_response(transcript, keywords)
        
        assert len(result.missing_keywords) >= 3
        assert result.percentage < 50
    
    def test_empty_transcript(self, scorer):
        """Test handling of empty transcript"""
        transcript = ""
        keywords = ["apologize", "help"]
        
        result = scorer.score_response(transcript, keywords)
        
        assert result.total_points < 1.0
        assert result.level in [SpeakingScoreLevel.POOR, SpeakingScoreLevel.NEEDS_IMPROVEMENT]
    
    def test_error_transcript(self, scorer):
        """Test handling of error transcript"""
        transcript = "[No transcription available]"
        keywords = ["apologize", "help"]
        
        result = scorer.score_response(transcript, keywords)
        
        assert result.total_points < 2.0
    
    def test_polite_phrases_bonus(self, scorer):
        """Test bonus for polite phrases"""
        transcript = "I apologize for the inconvenience. Please let me help you. Thank you for your patience."
        keywords = ["apologize"]
        
        result = scorer.score_response(transcript, keywords)
        
        # Should have high completeness score due to polite phrases
        assert result.completeness_score > 0
        assert "apologize" in result.matched_keywords or "thank" in str(result).lower()
    
    def test_fluency_estimation_normal(self, scorer):
        """Test fluency estimation for normal speech"""
        # ~20 words in 10 seconds = 120 WPM (optimal)
        transcript = "I apologize for the inconvenience with your cabin temperature. I will immediately send someone from maintenance to fix the air conditioning and make you more comfortable."
        
        result = scorer._estimate_fluency(transcript, 10.0)
        
        assert result["score"] >= 0.6
        assert 80 <= result["words_per_minute"] <= 200
    
    def test_fluency_estimation_with_fillers(self, scorer):
        """Test fluency estimation with filler words"""
        transcript = "um I uh apologize for um the inconvenience like you know"
        
        result = scorer._estimate_fluency(transcript, 5.0)
        
        assert result["filler_ratio"] > 0.1
        # Score should be penalized for fillers
        assert result["score"] < 0.9


class TestSpeakingScoreConvenienceFunction:
    """Tests for the convenience scoring function"""
    
    def test_score_speaking_response_basic(self):
        """Test basic usage of convenience function"""
        result = score_speaking_response(
            transcript="I apologize for the problem. Let me help you.",
            expected_keywords=["apologize", "help"],
            question_context="Guest complaint scenario",
            recording_duration=8.0,
            base_points=4.0
        )
        
        assert isinstance(result, SpeakingScoreResult)
        assert result.max_points == 4.0
        assert 0 <= result.total_points <= 4.0
    
    def test_score_speaking_response_excellent(self):
        """Test excellent response scoring"""
        result = score_speaking_response(
            transcript="I sincerely apologize for the inconvenience with your air conditioning. "
                      "I will immediately send someone from maintenance to fix it and ensure "
                      "you are comfortable. Thank you for your patience.",
            expected_keywords=["apologize", "inconvenience", "maintenance", "fix", "comfortable"],
            question_context="AC complaint",
            recording_duration=12.0,
            base_points=4.0
        )
        
        assert result.level in [SpeakingScoreLevel.EXCELLENT, SpeakingScoreLevel.GOOD]
        assert result.percentage >= 70


class TestSynonymMatching:
    """Tests for synonym matching functionality"""
    
    @pytest.fixture
    def scorer(self):
        return SpeakingScorerService()
    
    def test_apology_synonyms(self, scorer):
        """Test apology word synonyms"""
        # "sorry" should match "apologize"
        result = scorer._check_synonyms("apologize", "i'm sorry about that", {"i'm", "sorry", "about", "that"})
        assert result == "sorry"
    
    def test_help_synonyms(self, scorer):
        """Test help/assist synonyms"""
        result = scorer._check_synonyms("help", "let me assist you", {"let", "me", "assist", "you"})
        assert result == "assist"
    
    def test_room_cabin_synonyms(self, scorer):
        """Test room/cabin synonyms"""
        result = scorer._check_synonyms("room", "your cabin is ready", {"your", "cabin", "is", "ready"})
        assert result == "cabin"
    
    def test_fix_repair_synonyms(self, scorer):
        """Test fix/repair synonyms"""
        result = scorer._check_synonyms("fix", "we will repair it", {"we", "will", "repair", "it"})
        assert result == "repair"
    
    def test_no_synonym_match(self, scorer):
        """Test when no synonym matches"""
        result = scorer._check_synonyms("apologize", "the weather is nice", {"the", "weather", "is", "nice"})
        assert result is None


class TestFeedbackGeneration:
    """Tests for feedback generation"""
    
    @pytest.fixture
    def scorer(self):
        return SpeakingScorerService()
    
    def test_excellent_feedback(self, scorer):
        """Test feedback for excellent score"""
        feedback, tips = scorer._generate_feedback(
            {"score": 1.0, "matched": ["a", "b"], "missing": [], "partial": []},
            {"score": 0.9, "words_per_minute": 120, "filler_ratio": 0.02},
            {"score": 0.9, "polite_phrases": ["thank you"], "sentence_count": 3},
            SpeakingScoreLevel.EXCELLENT
        )
        
        assert "Excellent" in feedback
        assert len(tips) == 0  # No tips needed for excellent
    
    def test_poor_feedback_with_tips(self, scorer):
        """Test feedback for poor score with improvement tips"""
        feedback, tips = scorer._generate_feedback(
            {"score": 0.2, "matched": [], "missing": ["apologize", "help"], "partial": []},
            {"score": 0.3, "words_per_minute": 50, "filler_ratio": 0.2},
            {"score": 0.2, "polite_phrases": [], "sentence_count": 1},
            SpeakingScoreLevel.POOR
        )
        
        assert "did not adequately" in feedback.lower() or "poor" in feedback.lower()
        assert len(tips) > 0


class TestEdgeCases:
    """Tests for edge cases in speaking scoring"""
    
    @pytest.fixture
    def scorer(self):
        return SpeakingScorerService()
    
    def test_empty_keywords_list(self, scorer):
        """Test with empty keywords list"""
        result = scorer.score_response(
            "I apologize for the inconvenience.",
            [],  # Empty keywords
            ""
        )
        
        # Should still give some score for fluency and completeness
        assert result.keyword_score == result.keyword_max  # Full keyword score when no keywords expected
    
    def test_very_long_transcript(self, scorer):
        """Test with very long transcript"""
        long_transcript = " ".join(["I apologize for the inconvenience."] * 100)
        result = scorer.score_response(
            long_transcript,
            ["apologize"],
            ""
        )
        
        assert result.total_points > 0
    
    def test_special_characters_in_transcript(self, scorer):
        """Test transcript with special characters"""
        transcript = "I'm sorry! Can I help you? The A/C is broken..."
        result = scorer.score_response(
            transcript,
            ["sorry", "help"],
            ""
        )
        
        assert "sorry" in result.matched_keywords or len(result.matched_keywords) > 0
    
    def test_case_insensitivity(self, scorer):
        """Test case insensitive matching"""
        transcript = "I APOLOGIZE for the INCONVENIENCE"
        result = scorer.score_response(
            transcript,
            ["apologize", "inconvenience"],
            ""
        )
        
        assert len(result.matched_keywords) == 2
    
    def test_zero_duration(self, scorer):
        """Test with zero recording duration"""
        result = scorer.score_response(
            "I apologize for the problem.",
            ["apologize"],
            "",
            recording_duration=0.0
        )
        
        # Should still calculate fluency with assumed duration
        assert result.fluency_score >= 0


# ============================================
# Integration Tests
# ============================================

class TestSpeakingModuleIntegration:
    """Integration tests for speaking module components"""
    
    def test_full_scoring_workflow(self):
        """Test complete scoring workflow"""
        # Simulate a real speaking response
        transcript = """
        I sincerely apologize for the inconvenience with your cabin's air conditioning.
        I understand how uncomfortable that must be. Let me immediately contact our 
        maintenance team to come and fix the issue. In the meantime, I can offer you
        a complimentary beverage while you wait. Thank you for your patience.
        """
        
        keywords = [
            "apologize", "inconvenience", "air conditioning",
            "maintenance", "fix", "comfortable"
        ]
        
        result = score_speaking_response(
            transcript=transcript,
            expected_keywords=keywords,
            question_context="Guest complains about AC not working",
            recording_duration=15.0,
            base_points=4.0
        )
        
        # Should be a good or excellent response
        assert result.level in [SpeakingScoreLevel.EXCELLENT, SpeakingScoreLevel.GOOD]
        assert result.percentage >= 60
        assert len(result.matched_keywords) >= 4
        
        # Should have positive feedback
        assert result.feedback
        assert "Excellent" in result.feedback or "Good" in result.feedback
    
    def test_poor_response_workflow(self):
        """Test scoring of a poor response"""
        transcript = "OK I will try."
        keywords = ["apologize", "maintenance", "fix", "comfortable"]
        
        result = score_speaking_response(
            transcript=transcript,
            expected_keywords=keywords,
            question_context="Guest complaint",
            recording_duration=3.0,
            base_points=4.0
        )
        
        # Should be a poor response
        assert result.level in [SpeakingScoreLevel.POOR, SpeakingScoreLevel.NEEDS_IMPROVEMENT]
        assert result.percentage < 50
        assert len(result.missing_keywords) >= 3
        
        # Should have improvement tips
        assert len(result.improvement_tips) > 0
