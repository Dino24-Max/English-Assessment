"""
Inference module for production ML models
"""

from .speech_inference import SpeechInferenceService, get_inference_service

__all__ = ['SpeechInferenceService', 'get_inference_service']