#!/usr/bin/env python3
"""
Unit tests for ModelEvaluator
"""

import pytest
import numpy as np
import tempfile
import shutil
from pathlib import Path
from src.main.python.evaluation.model_evaluator import ModelEvaluator


class TestModelEvaluator:
    """Test suite for ModelEvaluator"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary output directory"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def evaluator(self, temp_dir):
        """Create ModelEvaluator instance"""
        return ModelEvaluator(output_dir=temp_dir)

    @pytest.fixture
    def sample_data(self):
        """Generate sample prediction data"""
        np.random.seed(42)
        y_true = np.random.randint(0, 21, size=100)
        y_pred = y_true + np.random.randint(-3, 4, size=100)
        y_pred = np.clip(y_pred, 0, 20)
        return y_true, y_pred

    def test_initialization(self, evaluator, temp_dir):
        """Test evaluator initialization"""
        assert evaluator.output_dir.exists()
        assert str(evaluator.output_dir) == temp_dir
        assert evaluator.results == {}

    def test_evaluate_classification(self, evaluator, sample_data):
        """Test classification evaluation"""
        y_true, y_pred = sample_data

        metrics = evaluator.evaluate_classification(
            y_true, y_pred, model_name="test_model"
        )

        assert 'accuracy' in metrics
        assert 'precision_macro' in metrics
        assert 'recall_macro' in metrics
        assert 'f1_macro' in metrics
        assert 'mae' in metrics
        assert 'rmse' in metrics
        assert 'confusion_matrix' in metrics
        assert 'classification_report' in metrics

        # Check value ranges
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['precision_macro'] <= 1
        assert 0 <= metrics['f1_macro'] <= 1
        assert metrics['mae'] >= 0
        assert metrics['rmse'] >= 0

    def test_evaluate_regression(self, evaluator, sample_data):
        """Test regression evaluation"""
        y_true, y_pred = sample_data

        metrics = evaluator.evaluate_regression(
            y_true, y_pred, model_name="test_regression"
        )

        assert 'mae' in metrics
        assert 'mse' in metrics
        assert 'rmse' in metrics
        assert 'r2' in metrics
        assert 'mean_error' in metrics
        assert 'std_error' in metrics

        # Check value types
        assert isinstance(metrics['mae'], (int, float))
        assert isinstance(metrics['r2'], (int, float))
        assert metrics['n_samples'] == 100

    def test_confusion_matrix_plot(self, evaluator, sample_data, temp_dir):
        """Test confusion matrix visualization"""
        y_true, y_pred = sample_data

        # First evaluate to store results
        evaluator.evaluate_classification(y_true, y_pred, model_name="plot_test")

        # Generate plot
        plot_path = evaluator.plot_confusion_matrix("plot_test")

        assert Path(plot_path).exists()
        assert plot_path.endswith('.png')
        assert 'confusion_matrix' in plot_path

    def test_score_distribution_plot(self, evaluator, sample_data, temp_dir):
        """Test score distribution visualization"""
        y_true, y_pred = sample_data

        plot_path = evaluator.plot_score_distribution(
            y_true, y_pred, model_name="dist_test"
        )

        assert Path(plot_path).exists()
        assert plot_path.endswith('.png')
        assert 'score_distribution' in plot_path

    def test_error_analysis_plot(self, evaluator, sample_data, temp_dir):
        """Test error analysis visualization"""
        y_true, y_pred = sample_data

        plot_path = evaluator.plot_error_analysis(
            y_true, y_pred, model_name="error_test"
        )

        assert Path(plot_path).exists()
        assert plot_path.endswith('.png')
        assert 'error_analysis' in plot_path

    def test_generate_report(self, evaluator, sample_data, temp_dir):
        """Test comprehensive report generation"""
        y_true, y_pred = sample_data

        # Evaluate first
        evaluator.evaluate_classification(y_true, y_pred, model_name="report_test")

        # Generate report
        report_path = evaluator.generate_report(
            "report_test",
            include_plots=True,
            y_true=y_true,
            y_pred=y_pred
        )

        assert Path(report_path).exists()
        assert report_path.endswith('.json')

        # Check report content
        import json
        with open(report_path, 'r') as f:
            report = json.load(f)

        assert 'model_name' in report
        assert 'timestamp' in report
        assert 'metrics' in report
        assert report['model_name'] == "report_test"

    def test_compare_models(self, evaluator, sample_data):
        """Test model comparison"""
        y_true, y_pred = sample_data

        # Evaluate multiple models
        evaluator.evaluate_classification(y_true, y_pred, model_name="model_a")

        y_pred2 = y_true + np.random.randint(-2, 3, size=100)
        y_pred2 = np.clip(y_pred2, 0, 20)
        evaluator.evaluate_classification(y_true, y_pred2, model_name="model_b")

        # Compare models
        plot_path = evaluator.compare_models(metric='accuracy')

        assert Path(plot_path).exists()
        assert 'model_comparison' in plot_path

    def test_print_summary(self, evaluator, sample_data, capsys):
        """Test summary printing"""
        y_true, y_pred = sample_data

        evaluator.evaluate_classification(y_true, y_pred, model_name="summary_test")

        evaluator.print_summary("summary_test")

        captured = capsys.readouterr()
        assert "Evaluation Summary" in captured.out
        assert "Accuracy" in captured.out
        assert "Precision" in captured.out

    def test_missing_model_error(self, evaluator):
        """Test error handling for missing model"""
        with pytest.raises(ValueError, match="No results found"):
            evaluator.plot_confusion_matrix("nonexistent_model")

    def test_metrics_storage(self, evaluator, sample_data):
        """Test that results are stored correctly"""
        y_true, y_pred = sample_data

        evaluator.evaluate_classification(y_true, y_pred, model_name="storage_test")

        assert "storage_test" in evaluator.results
        assert isinstance(evaluator.results["storage_test"], dict)

    def test_multiple_evaluations(self, evaluator, sample_data):
        """Test multiple model evaluations"""
        y_true, y_pred = sample_data

        # Evaluate multiple models
        for i in range(3):
            evaluator.evaluate_classification(
                y_true, y_pred, model_name=f"model_{i}"
            )

        assert len(evaluator.results) == 3
        assert all(f"model_{i}" in evaluator.results for i in range(3))


def test_module_imports():
    """Test that evaluation module can be imported"""
    from src.main.python.evaluation import ModelEvaluator
    assert ModelEvaluator is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])