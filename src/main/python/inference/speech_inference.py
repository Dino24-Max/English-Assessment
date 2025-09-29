#!/usr/bin/env python3
"""
Real-time Speech Inference Service
Provides fast speech assessment scoring for production use
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import joblib
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpeechInferenceService:
    """Production-ready speech inference service"""

    def __init__(self, model_version: str = "v1", model_dir: str = "models/speech"):
        self.model_dir = Path(model_dir)
        self.model_version = model_version
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.loaded = False

        # Performance tracking
        self.inference_count = 0
        self.total_inference_time = 0.0

    def load(self):
        """Load model artifacts"""
        try:
            model_path = self.model_dir / f"speech_model_{self.model_version}.pkl"
            scaler_path = self.model_dir / f"scaler_{self.model_version}.pkl"
            features_path = self.model_dir / f"features_{self.model_version}.json"

            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")

            # Load model
            self.model = joblib.load(model_path)
            logger.info(f"Model loaded from {model_path}")

            # Load scaler
            self.scaler = joblib.load(scaler_path)
            logger.info(f"Scaler loaded from {scaler_path}")

            # Load feature names
            with open(features_path, 'r') as f:
                self.feature_names = json.load(f)['features']
            logger.info(f"Loaded {len(self.feature_names)} feature names")

            self.loaded = True
            logger.info(f"Speech inference service ready (version: {self.model_version})")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def extract_features(self, audio_data: Dict) -> Dict[str, float]:
        """Extract features from audio analysis data

        Args:
            audio_data: Dictionary containing pre-computed audio features
                       (e.g., from librosa or other audio processing)

        Returns:
            Dictionary of feature values
        """
        # This is a placeholder - in production, this would extract
        # real audio features using librosa or similar
        features = {}

        # Duration
        features['duration'] = audio_data.get('duration', 0)

        # Pitch features
        features['pitch_mean'] = audio_data.get('pitch_mean', 0)
        features['pitch_std'] = audio_data.get('pitch_std', 0)
        features['pitch_min'] = audio_data.get('pitch_min', 0)
        features['pitch_max'] = audio_data.get('pitch_max', 0)

        # Energy features
        features['energy_mean'] = audio_data.get('energy_mean', 0)
        features['energy_std'] = audio_data.get('energy_std', 0)

        # Spectral features
        features['spectral_centroid_mean'] = audio_data.get('spectral_centroid_mean', 0)
        features['spectral_centroid_std'] = audio_data.get('spectral_centroid_std', 0)
        features['spectral_rolloff_mean'] = audio_data.get('spectral_rolloff_mean', 0)

        # Zero crossing rate
        features['zcr_mean'] = audio_data.get('zcr_mean', 0)
        features['zcr_std'] = audio_data.get('zcr_std', 0)

        # MFCCs
        for i in range(13):
            features[f'mfcc_{i}_mean'] = audio_data.get(f'mfcc_{i}_mean', 0)
            features[f'mfcc_{i}_std'] = audio_data.get(f'mfcc_{i}_std', 0)

        # Tempo
        features['tempo'] = audio_data.get('tempo', 0)

        return features

    def predict(self, audio_data: Dict) -> Dict:
        """Predict speech assessment score

        Args:
            audio_data: Dictionary containing audio features

        Returns:
            Dictionary with prediction results
        """
        if not self.loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start_time = datetime.now()

        try:
            # Extract features
            features = self.extract_features(audio_data)

            # Prepare feature vector
            X = np.array([[features.get(fname, 0) for fname in self.feature_names]])

            # Scale features
            X_scaled = self.scaler.transform(X)

            # Predict
            score = self.model.predict(X_scaled)[0]
            probabilities = self.model.predict_proba(X_scaled)[0]
            confidence = float(np.max(probabilities))

            # Calculate inference time
            inference_time = (datetime.now() - start_time).total_seconds()

            # Update stats
            self.inference_count += 1
            self.total_inference_time += inference_time

            result = {
                'score': int(score),
                'confidence': confidence,
                'inference_time_ms': inference_time * 1000,
                'model_version': self.model_version,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"Prediction: score={score}, confidence={confidence:.3f}, "
                       f"time={inference_time*1000:.2f}ms")

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'error': str(e),
                'score': 0,
                'confidence': 0.0
            }

    def predict_batch(self, batch_audio_data: list) -> list:
        """Batch prediction for multiple audio samples

        Args:
            batch_audio_data: List of audio data dictionaries

        Returns:
            List of prediction results
        """
        if not self.loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        start_time = datetime.now()
        results = []

        try:
            # Extract features for all samples
            feature_vectors = []
            for audio_data in batch_audio_data:
                features = self.extract_features(audio_data)
                X = [features.get(fname, 0) for fname in self.feature_names]
                feature_vectors.append(X)

            # Convert to numpy array
            X_batch = np.array(feature_vectors)

            # Scale features
            X_scaled = self.scaler.transform(X_batch)

            # Batch predict
            scores = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)

            # Calculate inference time
            inference_time = (datetime.now() - start_time).total_seconds()

            # Prepare results
            for i, (score, probs) in enumerate(zip(scores, probabilities)):
                results.append({
                    'score': int(score),
                    'confidence': float(np.max(probs)),
                    'model_version': self.model_version
                })

            # Update stats
            self.inference_count += len(batch_audio_data)
            self.total_inference_time += inference_time

            logger.info(f"Batch prediction: {len(batch_audio_data)} samples, "
                       f"time={inference_time*1000:.2f}ms, "
                       f"avg={inference_time/len(batch_audio_data)*1000:.2f}ms/sample")

            return results

        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            return [{'error': str(e), 'score': 0, 'confidence': 0.0}] * len(batch_audio_data)

    def get_stats(self) -> Dict:
        """Get inference service statistics"""
        avg_time = (self.total_inference_time / self.inference_count
                   if self.inference_count > 0 else 0)

        return {
            'model_version': self.model_version,
            'loaded': self.loaded,
            'total_inferences': self.inference_count,
            'total_time_seconds': self.total_inference_time,
            'avg_inference_time_ms': avg_time * 1000,
            'features_count': len(self.feature_names)
        }

    def health_check(self) -> Dict:
        """Health check endpoint"""
        return {
            'status': 'healthy' if self.loaded else 'not_ready',
            'model_version': self.model_version,
            'model_loaded': self.loaded,
            'inference_count': self.inference_count
        }


# Singleton instance for production use
_inference_service: Optional[SpeechInferenceService] = None


def get_inference_service(model_version: str = "v1") -> SpeechInferenceService:
    """Get or create singleton inference service instance"""
    global _inference_service

    if _inference_service is None:
        _inference_service = SpeechInferenceService(model_version=model_version)
        _inference_service.load()

    return _inference_service


def main():
    """Example usage and testing"""
    print("=== Speech Inference Service ===\n")

    # Initialize service
    service = SpeechInferenceService(model_version="v1")

    try:
        service.load()
    except FileNotFoundError:
        print("Model not found. Please train a model first using speech_trainer.py")
        return

    # Example audio data (mock features)
    example_audio = {
        'duration': 8.5,
        'pitch_mean': 150.0,
        'pitch_std': 25.0,
        'pitch_min': 100.0,
        'pitch_max': 200.0,
        'energy_mean': 0.05,
        'energy_std': 0.01,
        'spectral_centroid_mean': 2000.0,
        'spectral_centroid_std': 500.0,
        'spectral_rolloff_mean': 3000.0,
        'zcr_mean': 0.1,
        'zcr_std': 0.02,
        'tempo': 120.0
    }

    # Add MFCC features
    for i in range(13):
        example_audio[f'mfcc_{i}_mean'] = np.random.randn()
        example_audio[f'mfcc_{i}_std'] = abs(np.random.randn())

    # Single prediction
    print("Single Prediction:")
    result = service.predict(example_audio)
    print(json.dumps(result, indent=2))

    # Batch prediction
    print("\nBatch Prediction (3 samples):")
    batch_results = service.predict_batch([example_audio] * 3)
    for i, result in enumerate(batch_results, 1):
        print(f"  Sample {i}: Score={result['score']}, Confidence={result['confidence']:.3f}")

    # Stats
    print("\nService Stats:")
    stats = service.get_stats()
    print(json.dumps(stats, indent=2))

    # Health check
    print("\nHealth Check:")
    health = service.health_check()
    print(json.dumps(health, indent=2))


if __name__ == "__main__":
    main()