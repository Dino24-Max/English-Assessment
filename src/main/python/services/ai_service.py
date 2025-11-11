"""
AI Service for speech analysis and content generation
Integrates with OpenAI and Anthropic APIs
Includes timeout, retry, and error handling
"""

import asyncio
import json
import logging
import librosa
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path
from functools import wraps
import openai
import anthropic
from core.config import settings

logger = logging.getLogger(__name__)


def with_timeout_and_retry(timeout: int = None, retries: int = None):
    """
    Decorator for AI service calls with timeout and retry logic
    
    Args:
        timeout: Timeout in seconds (defaults to settings.AI_TIMEOUT_SECONDS)
        retries: Number of retry attempts (defaults to settings.AI_RETRY_ATTEMPTS)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _timeout = timeout or settings.AI_TIMEOUT_SECONDS
            _retries = retries or settings.AI_RETRY_ATTEMPTS
            last_exception = None
            
            for attempt in range(_retries):
                try:
                    # Apply timeout to the function call
                    async with asyncio.timeout(_timeout):
                        result = await func(*args, **kwargs)
                        return result
                        
                except asyncio.TimeoutError:
                    last_exception = TimeoutError(f"AI service timeout after {_timeout}s")
                    logger.warning(f"{func.__name__} timeout (attempt {attempt + 1}/{_retries})")
                    if attempt < _retries - 1:
                        await asyncio.sleep(settings.AI_RETRY_DELAY * (attempt + 1))
                    
                except (openai.APIError, anthropic.APIError) as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} API error (attempt {attempt + 1}/{_retries}): {e}")
                    if attempt < _retries - 1:
                        await asyncio.sleep(settings.AI_RETRY_DELAY * (attempt + 1))
                    
                except Exception as e:
                    last_exception = e
                    logger.error(f"{func.__name__} unexpected error: {e}")
                    break  # Don't retry on unexpected errors
            
            # All retries failed - return fallback response
            logger.error(f"{func.__name__} failed after {_retries} attempts: {last_exception}")
            raise last_exception
        
        return wrapper
    return decorator


class AIService:
    """AI service for speech analysis and content generation"""

    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None

    @with_timeout_and_retry(timeout=30, retries=3)
    async def analyze_speech_response(self, audio_file_path: str, expected_response: str,
                                    question_context: str) -> Dict[str, Any]:
        """
        Analyze speech response using AI with timeout and retry
        
        Args:
            audio_file_path: Path to audio file
            expected_response: Expected answer text
            question_context: Question context for analysis
            
        Returns:
            Dict with transcript, analysis, scores, and feedback
        """

        try:
            # Load and analyze audio file
            audio_analysis = await self._analyze_audio_quality(audio_file_path)

            # Transcribe speech (using OpenAI Whisper)
            transcript = await self._transcribe_audio(audio_file_path)

            # Analyze content accuracy
            content_analysis = await self._analyze_speech_content(
                transcript, expected_response, question_context
            )

            # Calculate final scores
            scores = self._calculate_speech_scores(audio_analysis, content_analysis)

            return {
                "transcript": transcript,
                "audio_quality": audio_analysis,
                "content_analysis": content_analysis,
                "scores": scores,
                "total_points": scores["total_score"],
                "overall_score": scores["overall_score"],
                "feedback": self._generate_speech_feedback(scores, content_analysis)
            }

        except TimeoutError as e:
            logger.error(f"Speech analysis timeout for {audio_file_path}: {e}")
            return self._get_fallback_speech_response("timeout")
            
        except (openai.APIError, anthropic.APIError) as e:
            logger.error(f"AI API error for {audio_file_path}: {e}")
            return self._get_fallback_speech_response("api_error")
            
        except Exception as e:
            logger.error(f"Unexpected error in speech analysis for {audio_file_path}: {e}")
            return self._get_fallback_speech_response("error")
    
    def _get_fallback_speech_response(self, error_type: str = "error") -> Dict[str, Any]:
        """
        Generate fallback response when AI analysis fails
        
        Args:
            error_type: Type of error ('timeout', 'api_error', 'error')
            
        Returns:
            Dict with fallback scoring and feedback
        """
        fallback_messages = {
            "timeout": "Speech analysis timed out. Manual review required.",
            "api_error": "AI service temporarily unavailable. Manual review required.",
            "error": "Technical issue with speech analysis. Manual review required."
        }
        
        return {
            "transcript": "Analysis unavailable",
            "error": error_type,
            "total_points": 10,  # Minimum points for attempt (50% of 20 points)
            "overall_score": 0.5,
            "audio_quality": {"clarity": 0.5, "fluency": 0.5, "pronunciation": 0.5},
            "content_analysis": {"accuracy": 0.5, "completeness": 0.5, "appropriateness": 0.5},
            "scores": {
                "clarity": 2,
                "fluency": 2,
                "pronunciation": 2,
                "accuracy": 2,
                "appropriateness": 2,
                "total_score": 10,
                "overall_score": 0.5
            },
            "feedback": fallback_messages.get(error_type, fallback_messages["error"])
        }

    @with_timeout_and_retry(timeout=20, retries=2)
    async def _transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio using OpenAI Whisper API"""

        if not self.openai_client:
            return "[Audio transcription unavailable - API key not configured]"

        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = await self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
            return transcript.text

        except Exception as e:
            return f"[Transcription error: {str(e)}]"

    @with_timeout_and_retry(timeout=15, retries=2)
    async def _analyze_speech_content(self, transcript: str, expected_response: str,
                                    context: str) -> Dict[str, Any]:
        """Analyze speech content for accuracy and appropriateness"""

        if not self.anthropic_client:
            # Fallback analysis without AI
            return {
                "content_accuracy": 0.7,
                "politeness": 0.8,
                "completeness": 0.7,
                "relevance": 0.8
            }

        try:
            prompt = f"""
            Analyze this cruise employee's spoken response for a customer service scenario.

            Context: {context}
            Expected type of response: {expected_response}
            Actual response: {transcript}

            Rate the response on a scale of 0.0 to 1.0 for:
            1. Content accuracy (does it address the customer's need?)
            2. Politeness (appropriate service language?)
            3. Completeness (sufficient information provided?)
            4. Relevance (stays on topic?)

            Return only a JSON object with these ratings.
            """

            message = await self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            content = message.content[0].text
            return json.loads(content)

        except Exception as e:
            # Fallback scoring
            return {
                "content_accuracy": 0.6,
                "politeness": 0.7,
                "completeness": 0.6,
                "relevance": 0.7
            }

    async def _analyze_audio_quality(self, audio_file_path: str) -> Dict[str, Any]:
        """Analyze audio quality metrics"""

        try:
            # Load audio file
            y, sr = librosa.load(audio_file_path)

            # Calculate audio metrics
            duration = librosa.get_duration(y=y, sr=sr)

            # Volume analysis
            rms_energy = librosa.feature.rms(y=y)[0]
            avg_volume = np.mean(rms_energy)

            # Basic quality metrics
            quality_score = min(1.0, avg_volume * 10)  # Simple volume-based quality

            return {
                "duration_seconds": duration,
                "average_volume": float(avg_volume),
                "quality_score": float(quality_score),
                "clarity": 0.8  # Placeholder - would need more advanced analysis
            }

        except Exception as e:
            return {
                "duration_seconds": 10.0,
                "average_volume": 0.5,
                "quality_score": 0.7,
                "clarity": 0.7,
                "error": str(e)
            }

    def _calculate_speech_scores(self, audio_analysis: Dict, content_analysis: Dict) -> Dict[str, Any]:
        """Calculate final speech module scores"""

        # Scoring breakdown (20 points total)
        content_score = content_analysis.get("content_accuracy", 0.6) * 8  # 8 points max
        fluency_score = content_analysis.get("completeness", 0.6) * 4     # 4 points max
        pronunciation_score = audio_analysis.get("clarity", 0.7) * 4       # 4 points max
        politeness_score = content_analysis.get("politeness", 0.7) * 4    # 4 points max

        total_score = content_score + fluency_score + pronunciation_score + politeness_score
        overall_score = total_score / 20.0

        return {
            "content_accuracy": content_score,
            "language_fluency": fluency_score,
            "pronunciation_clarity": pronunciation_score,
            "polite_language": politeness_score,
            "total_score": min(20.0, total_score),
            "overall_score": min(1.0, overall_score)
        }

    def _generate_speech_feedback(self, scores: Dict, content_analysis: Dict) -> str:
        """Generate feedback for speech response"""

        feedback_parts = []

        if scores["content_accuracy"] < 4:
            feedback_parts.append("Focus on directly addressing customer requests")

        if scores["language_fluency"] < 2:
            feedback_parts.append("Practice speaking more complete responses")

        if scores["pronunciation_clarity"] < 2:
            feedback_parts.append("Work on clear pronunciation and speaking pace")

        if scores["polite_language"] < 2:
            feedback_parts.append("Use more polite service language (please, thank you, etc.)")

        if not feedback_parts:
            return "Excellent response! Good job with customer service communication."

        return "Areas for improvement: " + "; ".join(feedback_parts)

    async def generate_listening_dialogue(self, division: str, scenario: str) -> Dict[str, Any]:
        """Generate listening module dialogue using AI"""

        if not self.openai_client:
            return {"error": "AI service not available"}

        try:
            # Create prompt for dialogue generation
            prompt = f"""
            Create a realistic dialogue for a cruise ship {division} employee scenario: {scenario}

            Requirements:
            - 30-40 seconds when spoken aloud
            - Professional maritime/hospitality context
            - Clear question that can be answered with multiple choice
            - Include specific details (times, numbers, locations)

            Format as JSON with 'dialogue' and 'key_information' fields.
            """

            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            return {"error": f"Dialogue generation failed: {str(e)}"}

    async def generate_speech_to_text(self, text: str, voice: str = "nova") -> str:
        """Generate speech audio from text using OpenAI TTS"""

        if not self.openai_client:
            return None

        try:
            response = await self.openai_client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )

            # Save audio file
            audio_path = f"data/audio/generated_{hash(text)}.mp3"
            Path(audio_path).parent.mkdir(parents=True, exist_ok=True)

            with open(audio_path, "wb") as f:
                f.write(response.content)

            return audio_path

        except Exception as e:
            print(f"TTS generation failed: {e}")
            return None