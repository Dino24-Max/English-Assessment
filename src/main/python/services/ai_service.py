"""
AI Service for speech analysis and content generation
Integrates with OpenAI and Anthropic APIs
Includes local Whisper model for free, high-accuracy transcription
Includes timeout, retry, and error handling
"""

import asyncio
import json
import logging
import librosa
import numpy as np
import tempfile
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import openai
import anthropic
from core.config import settings

logger = logging.getLogger(__name__)

# Thread pool for CPU-intensive tasks (Whisper transcription)
_executor = ThreadPoolExecutor(max_workers=2)

# Global Whisper model cache (load once, reuse)
_whisper_model = None
_whisper_model_size = None


def _get_whisper_model(model_size: str = None):
    """
    Get or load Whisper model (cached for reuse).
    
    Args:
        model_size: Model size (tiny, base, small, medium, large-v3)
        
    Returns:
        Loaded Whisper model
    """
    global _whisper_model, _whisper_model_size
    
    target_size = model_size or settings.WHISPER_MODEL_SIZE
    
    # Return cached model if same size
    if _whisper_model is not None and _whisper_model_size == target_size:
        return _whisper_model
    
    try:
        import whisper
        logger.info(f"Loading Whisper model: {target_size}")
        _whisper_model = whisper.load_model(target_size, device=settings.WHISPER_DEVICE)
        _whisper_model_size = target_size
        logger.info(f"Whisper model {target_size} loaded successfully")
        return _whisper_model
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        return None


def _transcribe_sync(audio_path: str, prompt: str = None) -> Tuple[str, float]:
    """
    Synchronous Whisper transcription (runs in thread pool).
    
    Args:
        audio_path: Path to audio file
        prompt: Optional prompt for context
        
    Returns:
        Tuple of (transcript, confidence)
    """
    try:
        model = _get_whisper_model()
        if model is None:
            return "[Whisper model not available]", 0.0
        
        # Build transcribe options
        options = {
            "language": settings.WHISPER_LANGUAGE,
            "temperature": 0.0,  # Deterministic for consistency
            "word_timestamps": False,
            "fp16": False if settings.WHISPER_DEVICE == "cpu" else True,
        }
        
        # Add prompt if provided (helps with domain-specific vocabulary)
        if prompt:
            options["initial_prompt"] = prompt
        
        result = model.transcribe(audio_path, **options)
        
        # Calculate average confidence from segments
        confidence = 1.0
        if result.get("segments"):
            confidences = [
                seg.get("no_speech_prob", 0) 
                for seg in result["segments"]
            ]
            # Convert no_speech_prob to confidence (1 - no_speech_prob)
            if confidences:
                confidence = 1.0 - (sum(confidences) / len(confidences))
        
        transcript = result.get("text", "").strip()
        logger.info(f"Whisper transcription completed: {len(transcript)} chars, confidence: {confidence:.2f}")
        
        return transcript, confidence
        
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}")
        return f"[Transcription error: {str(e)}]", 0.0


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
    
    async def _preprocess_audio(self, audio_file_path: str) -> str:
        """
        Preprocess audio for better transcription accuracy.
        
        Applies:
        - Format conversion to WAV (16kHz, mono)
        - Noise reduction
        - Volume normalization
        - Silence trimming
        
        Args:
            audio_file_path: Path to input audio file
            
        Returns:
            Path to preprocessed audio file (temp file)
        """
        if not settings.ENABLE_AUDIO_PREPROCESSING:
            return audio_file_path
        
        try:
            # Load audio with librosa
            y, sr = librosa.load(audio_file_path, sr=settings.AUDIO_SAMPLE_RATE, mono=True)
            
            # 1. Trim silence from beginning and end
            y_trimmed, _ = librosa.effects.trim(y, top_db=25)
            
            # 2. Noise reduction (using spectral gating)
            try:
                import noisereduce as nr
                # Estimate noise from first 0.5 seconds (or less if audio is short)
                noise_sample_len = min(int(sr * 0.5), len(y_trimmed) // 4)
                if noise_sample_len > 0:
                    y_denoised = nr.reduce_noise(
                        y=y_trimmed, 
                        sr=sr,
                        stationary=True,
                        prop_decrease=0.75
                    )
                else:
                    y_denoised = y_trimmed
            except ImportError:
                logger.warning("noisereduce not installed, skipping noise reduction")
                y_denoised = y_trimmed
            except Exception as e:
                logger.warning(f"Noise reduction failed: {e}, using original audio")
                y_denoised = y_trimmed
            
            # 3. Normalize volume
            max_val = np.max(np.abs(y_denoised))
            if max_val > 0:
                # Target amplitude (convert dB to linear scale)
                target_amplitude = 10 ** (settings.AUDIO_NORMALIZE_DB / 20)
                y_normalized = y_denoised * (target_amplitude / max_val)
            else:
                y_normalized = y_denoised
            
            # 4. Save to temporary file
            import soundfile as sf
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav", 
                delete=False,
                dir=settings.AUDIO_UPLOAD_DIR
            )
            sf.write(temp_file.name, y_normalized, sr)
            temp_file.close()
            
            logger.info(f"Audio preprocessed: {audio_file_path} -> {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            return audio_file_path  # Return original if preprocessing fails
    
    async def _transcribe_audio_local(self, audio_file_path: str, 
                                       expected_response: str = None,
                                       question_context: str = None) -> Tuple[str, float]:
        """
        Transcribe audio using local Whisper model (free, high accuracy).
        
        Args:
            audio_file_path: Path to audio file
            expected_response: Expected answer (for prompt context)
            question_context: Question context (for prompt hints)
            
        Returns:
            Tuple of (transcript, confidence_score)
        """
        # Build context prompt for better accuracy
        prompt = self._build_transcription_prompt(expected_response, question_context)
        
        # Preprocess audio for better quality
        processed_audio = await self._preprocess_audio(audio_file_path)
        
        try:
            # Run Whisper in thread pool (CPU-intensive)
            loop = asyncio.get_event_loop()
            transcript, confidence = await loop.run_in_executor(
                _executor,
                _transcribe_sync,
                processed_audio,
                prompt
            )
            
            return transcript, confidence
            
        finally:
            # Clean up temp file if different from original
            if processed_audio != audio_file_path and os.path.exists(processed_audio):
                try:
                    os.unlink(processed_audio)
                except Exception:
                    pass
    
    def _build_transcription_prompt(self, expected_response: str = None, 
                                     question_context: str = None) -> str:
        """
        Build a context prompt to improve Whisper accuracy.
        
        Uses expected keywords and question context to help Whisper
        recognize domain-specific vocabulary (cruise, hospitality).
        
        Args:
            expected_response: Expected answer text
            question_context: Question context
            
        Returns:
            Prompt string for Whisper
        """
        prompt_parts = [
            "This is a cruise ship employee speaking English in a customer service scenario."
        ]
        
        # Add question context
        if question_context:
            # Extract key terms from context
            prompt_parts.append(f"Scenario: {question_context[:200]}")
        
        # Add expected vocabulary hints
        if expected_response:
            # Extract keywords from expected response
            keywords = self._extract_keywords(expected_response)
            if keywords:
                prompt_parts.append(f"Expected vocabulary: {', '.join(keywords)}")
        
        # Domain-specific vocabulary hints
        prompt_parts.append(
            "Common terms: guest, cabin, deck, dining, reservation, "
            "apologize, assist, service, maintenance, housekeeping, "
            "captain, safety, emergency, lifeboat, muster station."
        )
        
        return " ".join(prompt_parts)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract important keywords from text for prompt hints.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keywords
        """
        if not text:
            return []
        
        # Common stop words to filter out
        stop_words = {
            'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
            'until', 'while', 'that', 'this', 'what', 'which', 'who',
            'i', 'me', 'my', 'myself', 'we', 'our', 'you', 'your',
            'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they',
            'them', 'their'
        }
        
        # Extract words (alphanumeric only)
        import re
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)
        
        return keywords[:15]  # Limit to 15 keywords

    @with_timeout_and_retry(timeout=60, retries=2)
    async def analyze_speech_response(self, audio_file_path: str, expected_response: str,
                                    question_context: str) -> Dict[str, Any]:
        """
        Analyze speech response using AI with timeout and retry.
        
        Uses local Whisper model for transcription (free, high accuracy)
        with fallback to OpenAI API if local fails.
        
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

            # Transcribe speech using local Whisper (primary) or OpenAI API (fallback)
            transcript, confidence = await self._transcribe_audio_enhanced(
                audio_file_path, 
                expected_response, 
                question_context
            )

            # Analyze content accuracy
            content_analysis = await self._analyze_speech_content(
                transcript, expected_response, question_context
            )
            
            # Adjust content analysis based on transcription confidence
            if confidence < 0.5:
                # Low confidence transcription - be more lenient
                for key in content_analysis:
                    if isinstance(content_analysis[key], (int, float)):
                        content_analysis[key] = max(content_analysis[key], 0.5)

            # Calculate final scores
            scores = self._calculate_speech_scores(audio_analysis, content_analysis)

            return {
                "transcript": transcript,
                "transcription_confidence": confidence,
                "transcription_method": "local_whisper" if settings.USE_LOCAL_WHISPER else "openai_api",
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

    async def _transcribe_audio_enhanced(self, audio_file_path: str,
                                          expected_response: str = None,
                                          question_context: str = None) -> Tuple[str, float]:
        """
        Enhanced transcription using local Whisper (primary) with OpenAI API fallback.
        
        Strategy:
        1. Try local Whisper first (free, no API costs)
        2. If local fails, fallback to OpenAI API (paid)
        3. Return best result with confidence score
        
        Args:
            audio_file_path: Path to audio file
            expected_response: Expected answer for prompt context
            question_context: Question context for prompt hints
            
        Returns:
            Tuple of (transcript, confidence_score)
        """
        transcript = ""
        confidence = 0.0
        
        # Strategy 1: Try local Whisper first (free, unlimited)
        if settings.USE_LOCAL_WHISPER:
            try:
                logger.info("Attempting transcription with local Whisper model...")
                transcript, confidence = await self._transcribe_audio_local(
                    audio_file_path, expected_response, question_context
                )
                
                # If we got a valid transcript, return it
                if transcript and not transcript.startswith("[") and confidence > 0.3:
                    logger.info(f"Local Whisper transcription successful (confidence: {confidence:.2f})")
                    return transcript, confidence
                else:
                    logger.warning(f"Local Whisper returned low quality result, trying fallback...")
                    
            except Exception as e:
                logger.warning(f"Local Whisper failed: {e}, trying OpenAI API fallback...")
        
        # Strategy 2: Fallback to OpenAI API (if local fails or disabled)
        if self.openai_client:
            try:
                logger.info("Attempting transcription with OpenAI Whisper API...")
                api_transcript = await self._transcribe_audio_api(audio_file_path)
                
                if api_transcript and not api_transcript.startswith("["):
                    logger.info("OpenAI API transcription successful")
                    return api_transcript, 0.8  # Assume good confidence for API
                    
            except Exception as e:
                logger.warning(f"OpenAI API transcription failed: {e}")
        
        # Return whatever we got (even if low quality)
        if transcript:
            return transcript, confidence
        
        return "[No transcription available]", 0.0
    
    @with_timeout_and_retry(timeout=20, retries=2)
    async def _transcribe_audio_api(self, audio_file_path: str) -> str:
        """
        Transcribe audio using OpenAI Whisper API (paid fallback).
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
        """
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
    
    async def _transcribe_audio(self, audio_file_path: str) -> str:
        """
        Legacy method for backward compatibility.
        Uses enhanced transcription with local Whisper.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        transcript, _ = await self._transcribe_audio_enhanced(audio_file_path)
        return transcript

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