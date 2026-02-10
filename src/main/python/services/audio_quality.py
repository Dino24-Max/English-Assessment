"""
Audio Quality Detection Service

Provides real-time audio quality analysis for speaking module recordings.
Detects issues like:
- Low volume / too quiet
- Background noise
- Clipping / distortion
- Too short duration
- No speech detected
"""

import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AudioQualityLevel(Enum):
    """Audio quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


@dataclass
class AudioQualityReport:
    """Detailed audio quality report"""
    overall_level: AudioQualityLevel
    overall_score: float  # 0.0 to 1.0
    
    # Individual metrics
    volume_score: float
    noise_score: float
    clipping_score: float
    duration_score: float
    speech_detected: bool
    
    # Issues found
    issues: List[str]
    recommendations: List[str]
    
    # Technical details
    duration_seconds: float
    average_volume_db: float
    peak_volume_db: float
    noise_floor_db: float
    clipping_percentage: float
    speech_ratio: float  # Ratio of speech to total duration


class AudioQualityAnalyzer:
    """
    Analyzes audio quality for speaking module recordings.
    
    Uses librosa for audio analysis without requiring additional ML models.
    """
    
    # Quality thresholds
    MIN_DURATION_SECONDS = 3.0
    MAX_DURATION_SECONDS = 120.0
    OPTIMAL_DURATION_MIN = 5.0
    OPTIMAL_DURATION_MAX = 30.0
    
    MIN_VOLUME_DB = -40.0  # Minimum acceptable average volume
    OPTIMAL_VOLUME_DB = -20.0  # Target volume level
    MAX_VOLUME_DB = -3.0  # Above this indicates clipping risk
    
    MAX_CLIPPING_PERCENTAGE = 1.0  # Maximum acceptable clipping
    MIN_SPEECH_RATIO = 0.3  # Minimum ratio of speech to total duration
    
    NOISE_FLOOR_THRESHOLD_DB = -50.0  # Below this is considered noise floor
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize audio quality analyzer.
        
        Args:
            sample_rate: Expected sample rate for analysis
        """
        self.sample_rate = sample_rate
    
    def analyze_audio_file(self, audio_path: str) -> AudioQualityReport:
        """
        Analyze audio file and generate quality report.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            AudioQualityReport with detailed analysis
        """
        try:
            import librosa
            
            # Load audio file
            y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
            
            return self.analyze_audio_data(y, sr)
            
        except Exception as e:
            logger.error(f"Audio analysis failed for {audio_path}: {e}")
            return self._create_error_report(str(e))
    
    def analyze_audio_data(self, audio_data: np.ndarray, sample_rate: int) -> AudioQualityReport:
        """
        Analyze raw audio data and generate quality report.
        
        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            AudioQualityReport with detailed analysis
        """
        try:
            import librosa
            
            issues = []
            recommendations = []
            
            # 1. Duration analysis
            duration = len(audio_data) / sample_rate
            duration_score = self._analyze_duration(duration)
            
            if duration < self.MIN_DURATION_SECONDS:
                issues.append(f"Recording too short ({duration:.1f}s)")
                recommendations.append(f"Record for at least {self.MIN_DURATION_SECONDS} seconds")
            elif duration > self.MAX_DURATION_SECONDS:
                issues.append(f"Recording too long ({duration:.1f}s)")
                recommendations.append(f"Keep recording under {self.MAX_DURATION_SECONDS} seconds")
            
            # 2. Volume analysis
            volume_metrics = self._analyze_volume(audio_data)
            volume_score = volume_metrics["score"]
            
            if volume_metrics["average_db"] < self.MIN_VOLUME_DB:
                issues.append("Audio too quiet")
                recommendations.append("Speak louder or move closer to the microphone")
            elif volume_metrics["peak_db"] > self.MAX_VOLUME_DB:
                issues.append("Audio may be clipping (too loud)")
                recommendations.append("Speak a bit softer or move away from the microphone")
            
            # 3. Clipping detection
            clipping_metrics = self._detect_clipping(audio_data)
            clipping_score = clipping_metrics["score"]
            
            if clipping_metrics["percentage"] > self.MAX_CLIPPING_PERCENTAGE:
                issues.append(f"Audio clipping detected ({clipping_metrics['percentage']:.1f}%)")
                recommendations.append("Reduce microphone input level or speak softer")
            
            # 4. Noise analysis
            noise_metrics = self._analyze_noise(audio_data, sample_rate)
            noise_score = noise_metrics["score"]
            
            if noise_metrics["noise_floor_db"] > -30:
                issues.append("High background noise detected")
                recommendations.append("Find a quieter environment for recording")
            
            # 5. Speech detection
            speech_metrics = self._detect_speech(audio_data, sample_rate)
            speech_detected = speech_metrics["speech_detected"]
            
            if not speech_detected:
                issues.append("No speech detected in recording")
                recommendations.append("Make sure to speak clearly into the microphone")
            elif speech_metrics["speech_ratio"] < self.MIN_SPEECH_RATIO:
                issues.append("Very little speech detected")
                recommendations.append("Speak more during the recording")
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(
                duration_score, volume_score, clipping_score, 
                noise_score, speech_detected, speech_metrics["speech_ratio"]
            )
            
            # Determine quality level
            overall_level = self._score_to_level(overall_score)
            
            # Add general recommendations if quality is poor
            if overall_level in [AudioQualityLevel.POOR, AudioQualityLevel.UNUSABLE]:
                if not recommendations:
                    recommendations.append("Consider re-recording in a quieter environment")
                    recommendations.append("Check your microphone settings")
            
            return AudioQualityReport(
                overall_level=overall_level,
                overall_score=overall_score,
                volume_score=volume_score,
                noise_score=noise_score,
                clipping_score=clipping_score,
                duration_score=duration_score,
                speech_detected=speech_detected,
                issues=issues,
                recommendations=recommendations,
                duration_seconds=duration,
                average_volume_db=volume_metrics["average_db"],
                peak_volume_db=volume_metrics["peak_db"],
                noise_floor_db=noise_metrics["noise_floor_db"],
                clipping_percentage=clipping_metrics["percentage"],
                speech_ratio=speech_metrics["speech_ratio"]
            )
            
        except Exception as e:
            logger.error(f"Audio data analysis failed: {e}")
            return self._create_error_report(str(e))
    
    def _analyze_duration(self, duration: float) -> float:
        """
        Analyze duration and return score.
        
        Args:
            duration: Duration in seconds
            
        Returns:
            Score from 0.0 to 1.0
        """
        if duration < self.MIN_DURATION_SECONDS:
            return duration / self.MIN_DURATION_SECONDS * 0.5
        elif duration > self.MAX_DURATION_SECONDS:
            return max(0.3, 1.0 - (duration - self.MAX_DURATION_SECONDS) / 60)
        elif self.OPTIMAL_DURATION_MIN <= duration <= self.OPTIMAL_DURATION_MAX:
            return 1.0
        elif duration < self.OPTIMAL_DURATION_MIN:
            return 0.7 + 0.3 * (duration - self.MIN_DURATION_SECONDS) / (self.OPTIMAL_DURATION_MIN - self.MIN_DURATION_SECONDS)
        else:
            return 0.7 + 0.3 * (self.MAX_DURATION_SECONDS - duration) / (self.MAX_DURATION_SECONDS - self.OPTIMAL_DURATION_MAX)
    
    def _analyze_volume(self, audio_data: np.ndarray) -> Dict[str, float]:
        """
        Analyze volume levels.
        
        Args:
            audio_data: Audio samples
            
        Returns:
            Dict with average_db, peak_db, and score
        """
        # Avoid log of zero
        audio_abs = np.abs(audio_data)
        audio_abs = np.where(audio_abs > 1e-10, audio_abs, 1e-10)
        
        # Calculate RMS (Root Mean Square) for average volume
        rms = np.sqrt(np.mean(audio_data ** 2))
        rms = max(rms, 1e-10)
        average_db = 20 * np.log10(rms)
        
        # Peak volume
        peak = np.max(audio_abs)
        peak_db = 20 * np.log10(peak)
        
        # Score based on how close to optimal
        if average_db < self.MIN_VOLUME_DB:
            score = max(0.0, (average_db - (-60)) / (self.MIN_VOLUME_DB - (-60)))
        elif average_db > self.MAX_VOLUME_DB:
            score = max(0.3, 1.0 - (average_db - self.MAX_VOLUME_DB) / 10)
        else:
            # Score based on distance from optimal
            distance = abs(average_db - self.OPTIMAL_VOLUME_DB)
            score = max(0.5, 1.0 - distance / 20)
        
        return {
            "average_db": average_db,
            "peak_db": peak_db,
            "score": score
        }
    
    def _detect_clipping(self, audio_data: np.ndarray) -> Dict[str, float]:
        """
        Detect audio clipping.
        
        Args:
            audio_data: Audio samples
            
        Returns:
            Dict with percentage and score
        """
        # Clipping threshold (samples near max value)
        threshold = 0.99
        clipped_samples = np.sum(np.abs(audio_data) > threshold)
        total_samples = len(audio_data)
        
        percentage = (clipped_samples / total_samples) * 100
        
        # Score: 1.0 if no clipping, decreases with more clipping
        if percentage <= 0.1:
            score = 1.0
        elif percentage <= self.MAX_CLIPPING_PERCENTAGE:
            score = 1.0 - (percentage / self.MAX_CLIPPING_PERCENTAGE) * 0.3
        else:
            score = max(0.2, 0.7 - (percentage - self.MAX_CLIPPING_PERCENTAGE) / 10)
        
        return {
            "percentage": percentage,
            "score": score
        }
    
    def _analyze_noise(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, float]:
        """
        Analyze background noise level.
        
        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            
        Returns:
            Dict with noise_floor_db and score
        """
        try:
            import librosa
            
            # Use spectral analysis to estimate noise floor
            # Get the quietest parts of the audio
            frame_length = int(sample_rate * 0.025)  # 25ms frames
            hop_length = int(sample_rate * 0.010)    # 10ms hop
            
            # Calculate RMS energy per frame
            rms = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Noise floor is estimated from the quietest 10% of frames
            sorted_rms = np.sort(rms)
            noise_percentile = int(len(sorted_rms) * 0.1)
            noise_rms = np.mean(sorted_rms[:max(1, noise_percentile)])
            
            noise_floor_db = 20 * np.log10(max(noise_rms, 1e-10))
            
            # Score based on noise floor
            if noise_floor_db < self.NOISE_FLOOR_THRESHOLD_DB:
                score = 1.0
            elif noise_floor_db < -40:
                score = 0.8
            elif noise_floor_db < -30:
                score = 0.6
            elif noise_floor_db < -20:
                score = 0.4
            else:
                score = 0.2
            
            return {
                "noise_floor_db": noise_floor_db,
                "score": score
            }
            
        except Exception as e:
            logger.warning(f"Noise analysis failed: {e}")
            return {
                "noise_floor_db": -40.0,
                "score": 0.7
            }
    
    def _detect_speech(self, audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """
        Detect presence of speech in audio.
        
        Uses energy-based voice activity detection.
        
        Args:
            audio_data: Audio samples
            sample_rate: Sample rate
            
        Returns:
            Dict with speech_detected and speech_ratio
        """
        try:
            import librosa
            
            # Frame-based analysis
            frame_length = int(sample_rate * 0.025)  # 25ms frames
            hop_length = int(sample_rate * 0.010)    # 10ms hop
            
            # Calculate RMS energy per frame
            rms = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Calculate zero crossing rate (speech has moderate ZCR)
            zcr = librosa.feature.zero_crossing_rate(audio_data, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Dynamic threshold based on audio statistics
            rms_threshold = np.percentile(rms, 30)  # 30th percentile as threshold
            
            # Frames with energy above threshold are considered speech
            speech_frames = rms > rms_threshold
            
            # Additional check: ZCR should be in speech range (not too high like noise)
            zcr_upper = np.percentile(zcr, 90)
            valid_zcr = zcr < zcr_upper
            
            # Combine criteria
            speech_frames = speech_frames & valid_zcr
            
            speech_ratio = np.mean(speech_frames)
            speech_detected = speech_ratio > 0.1  # At least 10% speech
            
            return {
                "speech_detected": speech_detected,
                "speech_ratio": speech_ratio
            }
            
        except Exception as e:
            logger.warning(f"Speech detection failed: {e}")
            return {
                "speech_detected": True,  # Assume speech present on error
                "speech_ratio": 0.5
            }
    
    def _calculate_overall_score(
        self, 
        duration_score: float,
        volume_score: float,
        clipping_score: float,
        noise_score: float,
        speech_detected: bool,
        speech_ratio: float
    ) -> float:
        """
        Calculate overall quality score.
        
        Args:
            Various component scores
            
        Returns:
            Overall score from 0.0 to 1.0
        """
        # Weights for different components
        weights = {
            "duration": 0.15,
            "volume": 0.25,
            "clipping": 0.15,
            "noise": 0.20,
            "speech": 0.25
        }
        
        # Speech score
        if not speech_detected:
            speech_score = 0.0
        else:
            speech_score = min(1.0, speech_ratio / self.MIN_SPEECH_RATIO)
        
        # Weighted average
        overall = (
            weights["duration"] * duration_score +
            weights["volume"] * volume_score +
            weights["clipping"] * clipping_score +
            weights["noise"] * noise_score +
            weights["speech"] * speech_score
        )
        
        return min(1.0, max(0.0, overall))
    
    def _score_to_level(self, score: float) -> AudioQualityLevel:
        """
        Convert numeric score to quality level.
        
        Args:
            score: Score from 0.0 to 1.0
            
        Returns:
            AudioQualityLevel enum
        """
        if score >= 0.85:
            return AudioQualityLevel.EXCELLENT
        elif score >= 0.70:
            return AudioQualityLevel.GOOD
        elif score >= 0.50:
            return AudioQualityLevel.ACCEPTABLE
        elif score >= 0.30:
            return AudioQualityLevel.POOR
        else:
            return AudioQualityLevel.UNUSABLE
    
    def _create_error_report(self, error_message: str) -> AudioQualityReport:
        """
        Create error report when analysis fails.
        
        Args:
            error_message: Error description
            
        Returns:
            AudioQualityReport with error information
        """
        return AudioQualityReport(
            overall_level=AudioQualityLevel.ACCEPTABLE,
            overall_score=0.5,
            volume_score=0.5,
            noise_score=0.5,
            clipping_score=0.5,
            duration_score=0.5,
            speech_detected=True,
            issues=[f"Analysis error: {error_message}"],
            recommendations=["Try recording again if you experience issues"],
            duration_seconds=0.0,
            average_volume_db=-30.0,
            peak_volume_db=-10.0,
            noise_floor_db=-50.0,
            clipping_percentage=0.0,
            speech_ratio=0.5
        )


def get_audio_quality_feedback(report: AudioQualityReport) -> str:
    """
    Generate user-friendly feedback message from quality report.
    
    Args:
        report: AudioQualityReport from analyzer
        
    Returns:
        User-friendly feedback string
    """
    level_messages = {
        AudioQualityLevel.EXCELLENT: "Excellent recording quality!",
        AudioQualityLevel.GOOD: "Good recording quality.",
        AudioQualityLevel.ACCEPTABLE: "Recording quality is acceptable.",
        AudioQualityLevel.POOR: "Recording quality is poor.",
        AudioQualityLevel.UNUSABLE: "Recording quality is too poor to process."
    }
    
    message = level_messages[report.overall_level]
    
    if report.issues:
        message += " Issues: " + "; ".join(report.issues[:3])
    
    if report.recommendations and report.overall_level in [AudioQualityLevel.POOR, AudioQualityLevel.UNUSABLE]:
        message += " Suggestions: " + "; ".join(report.recommendations[:2])
    
    return message
