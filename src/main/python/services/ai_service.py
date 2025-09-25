"""
AI Service for speech analysis and content generation
Integrates with OpenAI and Anthropic APIs
"""

import asyncio
import json
import librosa
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path
import openai
import anthropic
from core.config import settings


class AIService:
    """AI service for speech analysis and content generation"""

    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None

    async def analyze_speech_response(self, audio_file_path: str, expected_response: str,
                                    question_context: str) -> Dict[str, Any]:
        """Analyze speech response using AI"""

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

        except Exception as e:
            # Fallback scoring if AI analysis fails
            return {
                "transcript": "Error in transcription",
                "error": str(e),
                "total_points": 10,  # Minimum points for attempt
                "overall_score": 0.5,
                "feedback": "Technical issue with speech analysis. Manual review required."
            }

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