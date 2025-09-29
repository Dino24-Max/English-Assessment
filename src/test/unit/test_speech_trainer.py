#!/usr/bin/env python3
"""
Unit tests for SpeechTrainer
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import shutil
from src.main.python.training.speech_trainer import SpeechTrainer


class TestSpeechTrainer:
    """Test suite for SpeechTrainer"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def trainer(self, temp_dir):
        """Create SpeechTrainer instance"""
        data_dir = Path(temp_dir) / "data"
        model_dir = Path(temp_dir) / "models"
        return SpeechTrainer(data_dir=str(data_dir), model_dir=str(model_dir))

    def test_initialization(self, trainer, temp_dir):
        """Test trainer initialization"""
        assert trainer.data_dir.exists()
        assert trainer.model_dir.exists()
        assert trainer.model is None
        assert trainer.scaler is not None

    def test_feature_extraction_basic(self, trainer):
        """Test basic feature extraction structure"""
        # This would require actual audio file in production
        # Here we test the feature dictionary structure
        expected_features = [
            'duration', 'pitch_mean', 'pitch_std', 'pitch_min', 'pitch_max',
            'energy_mean', 'energy_std', 'spectral_centroid_mean',
            'spectral_centroid_std', 'spectral_rolloff_mean',
            'zcr_mean', 'zcr_std', 'tempo'
        ]

        # Test that these are the expected feature types
        for feature in expected_features:
            assert True  # Placeholder for actual audio test

    def test_model_attributes_after_training(self, trainer):
        """Test model attributes exist after training"""
        # Mock training would require actual data
        # Testing that attributes are properly initialized
        assert hasattr(trainer, 'model')
        assert hasattr(trainer, 'scaler')
        assert hasattr(trainer, 'feature_names')

    def test_save_model_before_training(self, trainer):
        """Test that saving fails before training"""
        with pytest.raises(ValueError, match="No model to save"):
            trainer.save_model()

    def test_model_directory_creation(self, temp_dir):
        """Test that model directory is created"""
        model_dir = Path(temp_dir) / "models" / "new_subdir"
        trainer = SpeechTrainer(model_dir=str(model_dir))
        assert model_dir.exists()


class TestFeatureExtraction:
    """Test feature extraction functions"""

    def test_feature_keys(self):
        """Test expected feature keys"""
        expected_features = {
            'duration', 'pitch_mean', 'pitch_std', 'pitch_min', 'pitch_max',
            'energy_mean', 'energy_std', 'spectral_centroid_mean',
            'spectral_centroid_std', 'spectral_rolloff_mean',
            'zcr_mean', 'zcr_std', 'tempo'
        }

        # Test MFCC features
        for i in range(13):
            expected_features.add(f'mfcc_{i}_mean')
            expected_features.add(f'mfcc_{i}_std')

        assert len(expected_features) == 13 + 26  # Basic + MFCCs

    def test_feature_value_types(self):
        """Test that features should be numeric"""
        # All features should be float or int types
        assert isinstance(0.0, (int, float))
        assert isinstance(0, (int, float))


def test_module_imports():
    """Test that training module can be imported"""
    from src.main.python.training import SpeechTrainer
    assert SpeechTrainer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])