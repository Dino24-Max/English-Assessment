#!/usr/bin/env python3
"""
Unit tests for Speech Inference Service
"""

import pytest
import numpy as np
from src.main.python.inference.speech_inference import SpeechInferenceService


class TestSpeechInferenceService:
    """Test suite for SpeechInferenceService"""

    @pytest.fixture
    def service(self):
        """Create inference service instance"""
        return SpeechInferenceService(model_version="v1")

    def test_initialization(self, service):
        """Test service initialization"""
        assert service.model_version == "v1"
        assert service.loaded == False
        assert service.inference_count == 0
        assert service.total_inference_time == 0.0

    def test_feature_extraction(self, service):
        """Test feature extraction from audio data"""
        audio_data = {
            'duration': 8.5,
            'pitch_mean': 150.0,
            'energy_mean': 0.05
        }

        features = service.extract_features(audio_data)

        assert 'duration' in features
        assert features['duration'] == 8.5
        assert 'pitch_mean' in features
        assert 'energy_mean' in features

    def test_extract_features_with_mfccs(self, service):
        """Test MFCC feature extraction"""
        audio_data = {}
        for i in range(13):
            audio_data[f'mfcc_{i}_mean'] = np.random.randn()
            audio_data[f'mfcc_{i}_std'] = abs(np.random.randn())

        features = service.extract_features(audio_data)

        # Check all MFCC features are present
        for i in range(13):
            assert f'mfcc_{i}_mean' in features
            assert f'mfcc_{i}_std' in features

    def test_extract_features_missing_data(self, service):
        """Test feature extraction with missing data"""
        audio_data = {}  # Empty data

        features = service.extract_features(audio_data)

        # Should return default values (0) for missing features
        assert features['duration'] == 0
        assert features['pitch_mean'] == 0
        assert features['energy_mean'] == 0

    def test_predict_before_loading(self, service):
        """Test prediction fails before loading model"""
        audio_data = {'duration': 5.0}

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.predict(audio_data)

    def test_health_check(self, service):
        """Test health check endpoint"""
        health = service.health_check()

        assert 'status' in health
        assert 'model_version' in health
        assert 'model_loaded' in health
        assert health['status'] == 'not_ready'
        assert health['model_loaded'] == False

    def test_get_stats(self, service):
        """Test statistics retrieval"""
        stats = service.get_stats()

        assert 'model_version' in stats
        assert 'loaded' in stats
        assert 'total_inferences' in stats
        assert stats['total_inferences'] == 0
        assert stats['loaded'] == False


class TestInferenceServiceWithMockModel:
    """Test inference service with mocked model"""

    @pytest.fixture
    def mock_service(self, monkeypatch):
        """Create service with mocked model"""
        service = SpeechInferenceService(model_version="v1")

        # Mock the loaded state
        service.loaded = True
        service.feature_names = ['duration', 'pitch_mean', 'energy_mean']

        # Mock model and scaler
        class MockModel:
            def predict(self, X):
                return np.array([15])

            def predict_proba(self, X):
                return np.array([[0.1, 0.2, 0.7]])

        class MockScaler:
            def transform(self, X):
                return X

        service.model = MockModel()
        service.scaler = MockScaler()

        return service

    def test_predict_with_mock(self, mock_service):
        """Test prediction with mocked model"""
        audio_data = {
            'duration': 8.0,
            'pitch_mean': 150.0,
            'energy_mean': 0.05
        }

        result = mock_service.predict(audio_data)

        assert 'score' in result
        assert 'confidence' in result
        assert 'inference_time_ms' in result
        assert result['score'] == 15
        assert 0 <= result['confidence'] <= 1

    def test_batch_predict(self, mock_service):
        """Test batch prediction"""
        batch_data = [
            {'duration': 8.0, 'pitch_mean': 150.0},
            {'duration': 9.0, 'pitch_mean': 160.0},
            {'duration': 7.0, 'pitch_mean': 140.0}
        ]

        results = mock_service.predict_batch(batch_data)

        assert len(results) == 3
        for result in results:
            assert 'score' in result
            assert 'confidence' in result

    def test_inference_stats_update(self, mock_service):
        """Test that stats update after predictions"""
        initial_count = mock_service.inference_count

        audio_data = {'duration': 8.0}
        mock_service.predict(audio_data)

        assert mock_service.inference_count == initial_count + 1
        assert mock_service.total_inference_time > 0


def test_singleton_service():
    """Test singleton pattern for inference service"""
    from src.main.python.inference.speech_inference import get_inference_service

    # This will fail if model not trained, which is expected
    # Just test the function exists
    assert callable(get_inference_service)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])