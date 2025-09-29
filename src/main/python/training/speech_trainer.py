#!/usr/bin/env python3
"""
Speech Analysis Model Training Pipeline
Trains ML models for speaking module assessment
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import librosa
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
from datetime import datetime


class SpeechTrainer:
    """Train and evaluate speech analysis models"""

    def __init__(self, data_dir: str = "data/processed/speech", model_dir: str = "models/speech"):
        self.data_dir = Path(data_dir)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = []

    def extract_audio_features(self, audio_path: str) -> Dict[str, float]:
        """Extract acoustic features from audio file"""
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=16000)

            # Extract features
            features = {}

            # Duration
            features['duration'] = librosa.get_duration(y=y, sr=sr)

            # Pitch features
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_values = pitches[pitches > 0]
            if len(pitch_values) > 0:
                features['pitch_mean'] = np.mean(pitch_values)
                features['pitch_std'] = np.std(pitch_values)
                features['pitch_min'] = np.min(pitch_values)
                features['pitch_max'] = np.max(pitch_values)
            else:
                features['pitch_mean'] = 0
                features['pitch_std'] = 0
                features['pitch_min'] = 0
                features['pitch_max'] = 0

            # Energy features
            energy = librosa.feature.rms(y=y)[0]
            features['energy_mean'] = np.mean(energy)
            features['energy_std'] = np.std(energy)

            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            features['spectral_centroid_mean'] = np.mean(spectral_centroids)
            features['spectral_centroid_std'] = np.std(spectral_centroids)

            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            features['spectral_rolloff_mean'] = np.mean(spectral_rolloff)

            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            features['zcr_mean'] = np.mean(zcr)
            features['zcr_std'] = np.std(zcr)

            # MFCCs (13 coefficients)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            for i in range(13):
                features[f'mfcc_{i}_mean'] = np.mean(mfccs[i])
                features[f'mfcc_{i}_std'] = np.std(mfccs[i])

            # Tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            features['tempo'] = tempo

            return features

        except Exception as e:
            print(f"Error extracting features from {audio_path}: {e}")
            return {}

    def load_training_data(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """Load and prepare training data"""
        data_list = []
        labels = []

        # Load labeled audio samples
        for score_dir in self.data_dir.glob('score_*'):
            score = int(score_dir.name.split('_')[1])

            for audio_file in score_dir.glob('*.wav'):
                features = self.extract_audio_features(str(audio_file))
                if features:
                    features['score'] = score
                    data_list.append(features)
                    labels.append(score)

        if not data_list:
            raise ValueError(f"No training data found in {self.data_dir}")

        df = pd.DataFrame(data_list)
        self.feature_names = [col for col in df.columns if col != 'score']

        X = df[self.feature_names].values
        y = np.array(labels)

        return X, y

    def train(self, test_size: float = 0.2, random_state: int = 42) -> Dict[str, float]:
        """Train the speech assessment model"""
        print("Loading training data...")
        X, y = self.load_training_data()

        print(f"Dataset: {len(X)} samples with {len(self.feature_names)} features")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Scale features
        print("Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        print("Training Random Forest model...")
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=random_state,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)

        metrics = {
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'n_samples': len(X),
            'n_features': len(self.feature_names),
            'train_size': len(X_train),
            'test_size': len(X_test)
        }

        print(f"\nTraining Results:")
        print(f"  Train Accuracy: {train_score:.3f}")
        print(f"  Test Accuracy: {test_score:.3f}")

        return metrics

    def save_model(self, version: str = None):
        """Save trained model and scaler"""
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = version or timestamp

        model_path = self.model_dir / f"speech_model_{version}.pkl"
        scaler_path = self.model_dir / f"scaler_{version}.pkl"
        features_path = self.model_dir / f"features_{version}.json"

        # Save model
        joblib.dump(self.model, model_path)
        print(f"Model saved to {model_path}")

        # Save scaler
        joblib.dump(self.scaler, scaler_path)
        print(f"Scaler saved to {scaler_path}")

        # Save feature names
        with open(features_path, 'w') as f:
            json.dump({'features': self.feature_names}, f, indent=2)
        print(f"Feature names saved to {features_path}")

        return {
            'model_path': str(model_path),
            'scaler_path': str(scaler_path),
            'features_path': str(features_path)
        }

    def load_model(self, version: str):
        """Load a trained model"""
        model_path = self.model_dir / f"speech_model_{version}.pkl"
        scaler_path = self.model_dir / f"scaler_{version}.pkl"
        features_path = self.model_dir / f"features_{version}.json"

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

        with open(features_path, 'r') as f:
            self.feature_names = json.load(f)['features']

        print(f"Model loaded from {model_path}")

    def predict(self, audio_path: str) -> Tuple[int, float]:
        """Predict score for an audio file"""
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")

        features = self.extract_audio_features(audio_path)
        if not features:
            return 0, 0.0

        # Prepare features
        X = np.array([[features.get(fname, 0) for fname in self.feature_names]])
        X_scaled = self.scaler.transform(X)

        # Predict
        score = self.model.predict(X_scaled)[0]
        confidence = np.max(self.model.predict_proba(X_scaled))

        return int(score), float(confidence)


def main():
    """Main training script"""
    print("=== Speech Analysis Model Training ===\n")

    trainer = SpeechTrainer()

    try:
        # Train model
        metrics = trainer.train()

        # Save model
        paths = trainer.save_model(version="v1")

        print("\n=== Training Complete ===")
        print(f"Model Performance:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        print(f"\nModel artifacts saved:")
        for key, path in paths.items():
            print(f"  {key}: {path}")

    except ValueError as e:
        print(f"\nError: {e}")
        print("\nTo train the model, you need to:")
        print("1. Create data/processed/speech/score_X directories (X = score 0-20)")
        print("2. Place labeled audio samples (.wav) in corresponding directories")
        print("3. Run this script again")


if __name__ == "__main__":
    main()