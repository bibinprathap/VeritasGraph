#!/usr/bin/env python3
"""
Evaluation Metrics for MedKG-Signal
Implements all metrics from the ICSPIS 2026 paper
"""

import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_recall_curve,
    roc_curve,
    confusion_matrix,
    classification_report
)
from scipy.special import softmax
from typing import Dict, List, Tuple, Optional
import json


def compute_auroc(y_true: np.ndarray, y_pred: np.ndarray, average: str = 'macro') -> float:
    """
    Compute Area Under ROC Curve
    
    Args:
        y_true: True labels (binary or multiclass)
        y_pred: Predicted probabilities
        average: 'macro', 'micro', or 'weighted'
        
    Returns:
        AUROC score
    """
    try:
        if len(y_pred.shape) == 1 or y_pred.shape[1] == 1:
            # Binary classification
            return roc_auc_score(y_true, y_pred)
        else:
            # Multiclass
            return roc_auc_score(y_true, y_pred, multi_class='ovr', average=average)
    except ValueError:
        return 0.0


def compute_auprc(y_true: np.ndarray, y_pred: np.ndarray, average: str = 'macro') -> float:
    """
    Compute Area Under Precision-Recall Curve
    
    Args:
        y_true: True labels
        y_pred: Predicted probabilities
        average: 'macro', 'micro', or 'weighted'
        
    Returns:
        AUPRC score
    """
    try:
        if len(y_pred.shape) == 1 or y_pred.shape[1] == 1:
            # Binary
            return average_precision_score(y_true, y_pred)
        else:
            # Multiclass
            return average_precision_score(y_true, y_pred, average=average)
    except ValueError:
        return 0.0


def compute_macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute Macro F1 Score
    
    Args:
        y_true: True labels
        y_pred: Predicted labels (not probabilities)
        
    Returns:
        Macro F1 score
    """
    return f1_score(y_true, y_pred, average='macro', zero_division=0)


def compute_ece(y_true: np.ndarray, y_pred_proba: np.ndarray, n_bins: int = 10) -> float:
    """
    Compute Expected Calibration Error
    
    Measures the difference between predicted confidence and actual accuracy.
    Lower is better (0 = perfect calibration).
    
    Args:
        y_true: True labels
        y_pred_proba: Predicted probabilities
        n_bins: Number of bins for calibration
        
    Returns:
        ECE score
    """
    # Get predicted class probabilities
    if len(y_pred_proba.shape) == 1:
        confidences = y_pred_proba
        predictions = (y_pred_proba > 0.5).astype(int)
    else:
        confidences = np.max(y_pred_proba, axis=1)
        predictions = np.argmax(y_pred_proba, axis=1)
        
    # Create bins
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]
    
    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        # Find samples in this bin
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)
        
        if prop_in_bin > 0:
            # Accuracy in bin
            accuracy_in_bin = np.mean(predictions[in_bin] == y_true[in_bin])
            # Average confidence in bin
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            # Add to ECE
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
            
    return ece


def compute_explanation_metrics(
    predictions: List[Dict],
    gold_evidence: Optional[List[Dict]] = None
) -> Dict[str, float]:
    """
    Compute explanation quality metrics
    
    Args:
        predictions: List of prediction dicts with 'explanation' and 'evidence_paths'
        gold_evidence: Optional gold standard evidence
        
    Returns:
        Dict of explanation metrics
    """
    metrics = {
        'evidence_precision': 0.0,
        'unsupported_claim_rate': 0.0,
        'path_validity': 0.0,
        'avg_evidence_paths': 0.0,
        'avg_explanation_length': 0.0
    }
    
    if not predictions:
        return metrics
        
    # Evidence precision: % of claims backed by KG paths
    total_claims = 0
    supported_claims = 0
    total_paths = 0
    valid_paths = 0
    
    for pred in predictions:
        explanation = pred.get('explanation', '')
        evidence_paths = pred.get('evidence_paths', [])
        
        # Count claims (sentences)
        claims = [s.strip() for s in explanation.split('.') if s.strip()]
        total_claims += len(claims)
        
        # Each claim should have at least one evidence path
        supported_claims += min(len(claims), len(evidence_paths))
        
        # Count paths
        total_paths += len(evidence_paths)
        
        # Validate paths (check if they form valid clinical reasoning)
        for path in evidence_paths:
            if validate_clinical_path(path):
                valid_paths += 1
                
    if total_claims > 0:
        metrics['evidence_precision'] = supported_claims / total_claims
        metrics['unsupported_claim_rate'] = (total_claims - supported_claims) / total_claims
        
    if total_paths > 0:
        metrics['path_validity'] = valid_paths / total_paths
        metrics['avg_evidence_paths'] = total_paths / len(predictions)
        
    # Average explanation length
    lengths = [len(p.get('explanation', '').split()) for p in predictions]
    metrics['avg_explanation_length'] = np.mean(lengths) if lengths else 0.0
    
    return metrics


def validate_clinical_path(path: List[str]) -> bool:
    """
    Validate if a path represents valid clinical reasoning
    
    Simple heuristic: path should connect entities in a meaningful way
    (encounter -> symptom -> diagnosis, lab -> diagnosis, etc.)
    """
    if len(path) < 2:
        return False
        
    # Check for valid entity type sequences
    valid_sequences = [
        ['encounter', 'diagnosis'],
        ['encounter', 'symptom', 'diagnosis'],
        ['encounter', 'lab_marker', 'diagnosis'],
        ['encounter', 'signal_phenotype', 'diagnosis'],
        ['symptom', 'diagnosis'],
        ['lab_marker', 'diagnosis'],
        ['signal_phenotype', 'diagnosis'],
        ['medication', 'diagnosis'],
    ]
    
    # Extract entity types from path (assuming format "TYPE:ID")
    try:
        path_types = [node.split(':')[0] for node in path]
        
        # Check if path matches any valid sequence
        for valid_seq in valid_sequences:
            if all(t in path_types for t in valid_seq):
                return True
    except:
        pass
        
    return False


def compute_all_metrics(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    y_pred_labels: Optional[np.ndarray] = None,
    predictions: Optional[List[Dict]] = None,
    task_name: str = "classification"
) -> Dict[str, float]:
    """
    Compute all metrics for a prediction task
    
    Args:
        y_true: True labels
        y_pred_proba: Predicted probabilities
        y_pred_labels: Predicted labels (if None, derived from probabilities)
        predictions: List of prediction dicts with explanations
        task_name: Name of the task
        
    Returns:
        Dictionary of all metrics
    """
    # Derive labels if not provided
    if y_pred_labels is None:
        if len(y_pred_proba.shape) == 1:
            y_pred_labels = (y_pred_proba > 0.5).astype(int)
        else:
            y_pred_labels = np.argmax(y_pred_proba, axis=1)
            
    metrics = {
        'task': task_name,
        'n_samples': len(y_true),
        'n_classes': len(np.unique(y_true)),
    }
    
    # Predictive metrics
    metrics['auroc'] = compute_auroc(y_true, y_pred_proba)
    metrics['auprc'] = compute_auprc(y_true, y_pred_proba)
    metrics['macro_f1'] = compute_macro_f1(y_true, y_pred_labels)
    metrics['ece'] = compute_ece(y_true, y_pred_proba)
    
    # Additional standard metrics
    metrics['accuracy'] = np.mean(y_true == y_pred_labels)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred_labels)
    metrics['confusion_matrix'] = cm.tolist()
    
    # Per-class metrics
    if len(np.unique(y_true)) == 2:
        # Binary classification
        tn, fp, fn, tp = cm.ravel()
        metrics['precision'] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        metrics['recall'] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        
    # Explanation metrics (if predictions provided)
    if predictions:
        expl_metrics = compute_explanation_metrics(predictions)
        metrics.update(expl_metrics)
        
    return metrics


def compare_models(
    results_list: List[Dict],
    model_names: List[str],
    output_path: Optional[str] = None
) -> Dict:
    """
    Compare multiple models
    
    Args:
        results_list: List of metric dictionaries from each model
        model_names: List of model names
        output_path: Optional path to save comparison
        
    Returns:
        Comparison dictionary
    """
    comparison = {
        'models': model_names,
        'metrics': {}
    }
    
    # Collect metrics
    metric_keys = set()
    for results in results_list:
        metric_keys.update(results.keys())
        
    # Remove non-numeric keys
    metric_keys = {k for k in metric_keys if isinstance(results_list[0].get(k), (int, float))}
    
    for metric in metric_keys:
        comparison['metrics'][metric] = {
            name: results.get(metric, 0.0)
            for name, results in zip(model_names, results_list)
        }
        
        # Find best model for this metric
        values = [results.get(metric, 0.0) for results in results_list]
        
        # For ECE and unsupported_claim_rate, lower is better
        if metric in ['ece', 'unsupported_claim_rate']:
            best_idx = np.argmin(values)
        else:
            best_idx = np.argmax(values)
            
        comparison['metrics'][metric]['best_model'] = model_names[best_idx]
        
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(comparison, f, indent=2)
            
    return comparison


def print_metrics_table(metrics: Dict, model_name: str = "Model"):
    """Pretty print metrics in table format"""
    print(f"\n{'='*60}")
    print(f"{model_name} - Evaluation Metrics")
    print(f"{'='*60}")
    
    print(f"\n{' Predictive Performance ':-^60}")
    print(f"  AUROC:           {metrics.get('auroc', 0.0):.4f}")
    print(f"  AUPRC:           {metrics.get('auprc', 0.0):.4f}")
    print(f"  Macro-F1:        {metrics.get('macro_f1', 0.0):.4f}")
    print(f"  Accuracy:        {metrics.get('accuracy', 0.0):.4f}")
    print(f"  ECE:             {metrics.get('ece', 0.0):.4f}")
    
    if 'precision' in metrics:
        print(f"\n{' Binary Classification Metrics ':-^60}")
        print(f"  Precision:       {metrics.get('precision', 0.0):.4f}")
        print(f"  Recall:          {metrics.get('recall', 0.0):.4f}")
        print(f"  Specificity:     {metrics.get('specificity', 0.0):.4f}")
    
    if 'evidence_precision' in metrics:
        print(f"\n{' Explanation Quality ':-^60}")
        print(f"  Evidence Precision:        {metrics.get('evidence_precision', 0.0):.4f}")
        print(f"  Unsupported Claim Rate:    {metrics.get('unsupported_claim_rate', 0.0):.4f}")
        print(f"  Path Validity:             {metrics.get('path_validity', 0.0):.4f}")
        print(f"  Avg Evidence Paths:        {metrics.get('avg_evidence_paths', 0.0):.2f}")
        
    print(f"{'='*60}\n")


if __name__ == '__main__':
    # Example usage
    print("Metrics Module - Example Usage\n")
    
    # Simulate predictions
    np.random.seed(42)
    n_samples = 1000
    
    # Binary classification example
    y_true = np.random.randint(0, 2, n_samples)
    y_pred_proba = np.random.rand(n_samples) * 0.7 + (y_true * 0.3)  # Correlated
    
    # Simulate predictions with explanations
    predictions = [
        {
            'explanation': 'Patient has elevated troponin and chest pain. ECG shows ST elevation.',
            'evidence_paths': [
                ['encounter:E001', 'lab_marker:L003', 'diagnosis:D001'],
                ['encounter:E001', 'symptom:S002', 'diagnosis:D001'],
                ['encounter:E001', 'signal_phenotype:SP002', 'diagnosis:D001']
            ]
        }
        for _ in range(n_samples)
    ]
    
    # Compute metrics
    metrics = compute_all_metrics(
        y_true,
        y_pred_proba,
        predictions=predictions[:100],  # Only first 100 with explanations
        task_name="Mortality Prediction"
    )
    
    print_metrics_table(metrics, "MedKG-Signal")
    
    # Save to JSON
    with open('/tmp/sample_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print("Saved metrics to /tmp/sample_metrics.json")
