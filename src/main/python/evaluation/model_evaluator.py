#!/usr/bin/env python3
"""
Model Evaluation Framework
Evaluates ML model performance with comprehensive metrics
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, mean_absolute_error,
    mean_squared_error, r2_score
)
import json
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


class ModelEvaluator:
    """Comprehensive model evaluation and reporting"""

    def __init__(self, output_dir: str = "output/evaluation"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}

    def evaluate_classification(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        labels: Optional[List] = None,
        model_name: str = "model"
    ) -> Dict:
        """Evaluate classification model performance"""

        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_macro': precision_score(y_true, y_pred, average='macro', zero_division=0),
            'precision_weighted': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall_macro': recall_score(y_true, y_pred, average='macro', zero_division=0),
            'recall_weighted': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            'f1_macro': f1_score(y_true, y_pred, average='macro', zero_division=0),
            'f1_weighted': f1_score(y_true, y_pred, average='weighted', zero_division=0),
            'mae': mean_absolute_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'n_samples': len(y_true)
        }

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()

        # Classification report
        if labels is None:
            labels = sorted(list(set(y_true) | set(y_pred)))

        report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
        metrics['classification_report'] = report

        self.results[model_name] = metrics

        return metrics

    def evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "model"
    ) -> Dict:
        """Evaluate regression model performance"""

        metrics = {
            'mae': mean_absolute_error(y_true, y_pred),
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'r2': r2_score(y_true, y_pred),
            'n_samples': len(y_true)
        }

        # Additional stats
        errors = y_pred - y_true
        metrics['mean_error'] = float(np.mean(errors))
        metrics['std_error'] = float(np.std(errors))
        metrics['median_error'] = float(np.median(errors))

        self.results[model_name] = metrics

        return metrics

    def plot_confusion_matrix(
        self,
        model_name: str,
        labels: Optional[List] = None,
        figsize: Tuple[int, int] = (10, 8)
    ) -> str:
        """Generate confusion matrix heatmap"""

        if model_name not in self.results:
            raise ValueError(f"No results found for model: {model_name}")

        cm = np.array(self.results[model_name]['confusion_matrix'])

        plt.figure(figsize=figsize)
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=labels or range(len(cm)),
            yticklabels=labels or range(len(cm))
        )
        plt.title(f'Confusion Matrix - {model_name}')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"confusion_matrix_{model_name}_{timestamp}.png"
        filepath = self.output_dir / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Confusion matrix saved to {filepath}")
        return str(filepath)

    def plot_score_distribution(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "model",
        figsize: Tuple[int, int] = (12, 6)
    ) -> str:
        """Plot true vs predicted score distributions"""

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Distribution comparison
        axes[0].hist(y_true, bins=20, alpha=0.7, label='True Scores', color='blue', edgecolor='black')
        axes[0].hist(y_pred, bins=20, alpha=0.7, label='Predicted Scores', color='orange', edgecolor='black')
        axes[0].set_xlabel('Score')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Score Distribution Comparison')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Scatter plot
        axes[1].scatter(y_true, y_pred, alpha=0.5, color='green', edgecolors='black', s=50)
        axes[1].plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()],
                     'r--', lw=2, label='Perfect Prediction')
        axes[1].set_xlabel('True Score')
        axes[1].set_ylabel('Predicted Score')
        axes[1].set_title('True vs Predicted Scores')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"score_distribution_{model_name}_{timestamp}.png"
        filepath = self.output_dir / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Score distribution plot saved to {filepath}")
        return str(filepath)

    def plot_error_analysis(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        model_name: str = "model",
        figsize: Tuple[int, int] = (12, 6)
    ) -> str:
        """Plot error analysis visualizations"""

        errors = y_pred - y_true

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Error distribution
        axes[0].hist(errors, bins=30, color='red', alpha=0.7, edgecolor='black')
        axes[0].axvline(x=0, color='blue', linestyle='--', linewidth=2, label='Zero Error')
        axes[0].set_xlabel('Prediction Error')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Error Distribution')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Error vs True Value
        axes[1].scatter(y_true, errors, alpha=0.5, color='purple', edgecolors='black', s=50)
        axes[1].axhline(y=0, color='blue', linestyle='--', linewidth=2)
        axes[1].set_xlabel('True Score')
        axes[1].set_ylabel('Prediction Error')
        axes[1].set_title('Error vs True Score')
        axes[1].grid(True, alpha=0.3)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_analysis_{model_name}_{timestamp}.png"
        filepath = self.output_dir / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Error analysis plot saved to {filepath}")
        return str(filepath)

    def generate_report(
        self,
        model_name: str,
        include_plots: bool = True,
        y_true: Optional[np.ndarray] = None,
        y_pred: Optional[np.ndarray] = None
    ) -> str:
        """Generate comprehensive evaluation report"""

        if model_name not in self.results:
            raise ValueError(f"No results found for model: {model_name}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"evaluation_report_{model_name}_{timestamp}.json"
        report_path = self.output_dir / report_filename

        report = {
            'model_name': model_name,
            'timestamp': timestamp,
            'metrics': self.results[model_name],
            'plots': {}
        }

        # Generate plots if requested
        if include_plots and y_true is not None and y_pred is not None:
            try:
                report['plots']['confusion_matrix'] = self.plot_confusion_matrix(model_name)
            except Exception as e:
                print(f"Warning: Could not generate confusion matrix: {e}")

            try:
                report['plots']['score_distribution'] = self.plot_score_distribution(
                    y_true, y_pred, model_name
                )
            except Exception as e:
                print(f"Warning: Could not generate score distribution: {e}")

            try:
                report['plots']['error_analysis'] = self.plot_error_analysis(
                    y_true, y_pred, model_name
                )
            except Exception as e:
                print(f"Warning: Could not generate error analysis: {e}")

        # Save report
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nEvaluation report saved to {report_path}")
        return str(report_path)

    def compare_models(
        self,
        metric: str = 'accuracy',
        figsize: Tuple[int, int] = (10, 6)
    ) -> str:
        """Compare multiple models on a specific metric"""

        if not self.results:
            raise ValueError("No model results to compare")

        model_names = []
        metric_values = []

        for model_name, metrics in self.results.items():
            if metric in metrics:
                model_names.append(model_name)
                metric_values.append(metrics[metric])

        if not model_names:
            raise ValueError(f"Metric '{metric}' not found in any model results")

        plt.figure(figsize=figsize)
        bars = plt.bar(model_names, metric_values, color='steelblue', edgecolor='black', alpha=0.8)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom', fontweight='bold')

        plt.xlabel('Model', fontweight='bold')
        plt.ylabel(metric.replace('_', ' ').title(), fontweight='bold')
        plt.title(f'Model Comparison - {metric.replace("_", " ").title()}', fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_comparison_{metric}_{timestamp}.png"
        filepath = self.output_dir / filename

        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Model comparison plot saved to {filepath}")
        return str(filepath)

    def print_summary(self, model_name: str):
        """Print a summary of evaluation results"""

        if model_name not in self.results:
            raise ValueError(f"No results found for model: {model_name}")

        metrics = self.results[model_name]

        print(f"\n{'='*60}")
        print(f"Evaluation Summary: {model_name}")
        print(f"{'='*60}")

        # Core metrics
        if 'accuracy' in metrics:
            print(f"\nClassification Metrics:")
            print(f"  Accuracy:           {metrics['accuracy']:.4f}")
            print(f"  Precision (macro):  {metrics['precision_macro']:.4f}")
            print(f"  Recall (macro):     {metrics['recall_macro']:.4f}")
            print(f"  F1-Score (macro):   {metrics['f1_macro']:.4f}")

        # Regression metrics
        if 'mae' in metrics:
            print(f"\nRegression Metrics:")
            print(f"  MAE:   {metrics['mae']:.4f}")
            if 'rmse' in metrics:
                print(f"  RMSE:  {metrics['rmse']:.4f}")
            if 'r2' in metrics:
                print(f"  R²:    {metrics['r2']:.4f}")

        print(f"\nDataset Size: {metrics['n_samples']} samples")
        print(f"{'='*60}\n")


def main():
    """Example usage of ModelEvaluator"""
    print("=== Model Evaluation Framework ===\n")

    # Example: Generate synthetic data for demonstration
    np.random.seed(42)
    y_true = np.random.randint(0, 21, size=100)
    y_pred = y_true + np.random.randint(-3, 4, size=100)
    y_pred = np.clip(y_pred, 0, 20)

    # Evaluate
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate_classification(y_true, y_pred, model_name="speech_model_v1")

    # Print summary
    evaluator.print_summary("speech_model_v1")

    # Generate report
    report_path = evaluator.generate_report(
        "speech_model_v1",
        include_plots=True,
        y_true=y_true,
        y_pred=y_pred
    )

    print(f"\nComplete evaluation report: {report_path}")


if __name__ == "__main__":
    main()