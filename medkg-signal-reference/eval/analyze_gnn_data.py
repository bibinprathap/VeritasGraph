#!/usr/bin/env python3
"""
Quick analysis of GNN_for_EHR synthetic data
Compare data characteristics with MedKG-Signal
"""

import pickle
import numpy as np
from scipy.sparse import issparse

print("="*80)
print("GNN_for_EHR Synthetic Data Analysis")
print("="*80)

data_path = '/home/sijo/VeritasGraph/GNN_for_EHR/data/'

# Load all synthetic data files
print("\n📂 Loading data files...")
x = pickle.load(open(data_path + 'preprocess_x.pkl', 'rb'))
y = pickle.load(open(data_path + 'y_bin.pkl', 'rb'))
train_idx = pickle.load(open(data_path + 'train_idx.pkl', 'rb'))
val_idx = pickle.load(open(data_path + 'val_idx.pkl', 'rb'))
test_idx = pickle.load(open(data_path + 'test_idx.pkl', 'rb'))
frts_selection = pickle.load(open(data_path + 'frts_selection.pkl', 'rb'))
neg_young = pickle.load(open(data_path + 'neg_young.pkl', 'rb'))

print("✅ All files loaded successfully!\n")

# Analyze feature matrix
print("="*80)
print("Feature Matrix (X)")
print("="*80)
print(f"Type: {type(x)}")
print(f"Shape: {x.shape}")
print(f"Sparse: {issparse(x)}")
if issparse(x):
    print(f"Sparsity: {1 - (x.nnz / (x.shape[0] * x.shape[1])):.4f}")
    print(f"Non-zero elements: {x.nnz:,}")
print(f"Data type: {x.dtype}")

# Analyze labels
print("\n" + "="*80)
print("Labels (Y)")
print("="*80)
print(f"Type: {type(y)}")
print(f"Shape: {y.shape}")
print(f"Positive cases: {np.sum(y):,} ({np.mean(y)*100:.2f}%)")
print(f"Negative cases: {np.sum(~y):,} ({(1-np.mean(y))*100:.2f}%)")
print(f"Class imbalance ratio: 1:{int(np.sum(~y)/np.sum(y))}")

# Analyze splits
print("\n" + "="*80)
print("Train/Val/Test Splits")
print("="*80)
total = len(y)
print(f"Total samples: {total:,}")
print(f"Train: {len(train_idx):,} ({len(train_idx)/total*100:.1f}%)")
print(f"Val:   {len(val_idx):,} ({len(val_idx)/total*100:.1f}%)")
print(f"Test:  {len(test_idx):,} ({len(test_idx)/total*100:.1f}%)")

# Check split quality
print("\n📊 Split Quality:")
print(f"Train positives: {np.sum(y[train_idx]):,} ({np.mean(y[train_idx])*100:.2f}%)")
print(f"Val positives:   {np.sum(y[val_idx]):,} ({np.mean(y[val_idx])*100:.2f}%)")
print(f"Test positives:  {np.sum(y[test_idx]):,} ({np.mean(y[test_idx])*100:.2f}%)")

# Feature selection
print("\n" + "="*80)
print("Feature Selection")
print("="*80)
print(f"Type: {type(frts_selection)}")
print(f"Selected features: {len(frts_selection):,}")
print(f"Selection rate: {len(frts_selection)/x.shape[1]*100:.2f}%")

# Negative young indices
print("\n" + "="*80)
print("Negative Young Indices (for downsampling)")
print("="*80)
print(f"Count: {len(neg_young):,}")

# Comparison with MedKG-Signal
print("\n" + "="*80)
print("Comparison with MedKG-Signal")
print("="*80)
comparison = f"""
| Aspect                | GNN_for_EHR        | MedKG-Signal      |
|-----------------------|--------------------|-------------------|
| Total samples         | {x.shape[0]:,}              | 1,000             |
| Features              | {x.shape[1]:,}          | ~50 (graph nodes) |
| Sparsity              | {1 - (x.nnz / (x.shape[0] * x.shape[1])):.4f}              | N/A (graph)       |
| Positive rate         | {np.mean(y)*100:.2f}%              | ~10%              |
| Train/Val/Test        | {len(train_idx)}/{len(val_idx)}/{len(test_idx)}            | 700/100/200       |
| Data type             | Sparse binary      | Graph + signals   |
| Graph construction    | Data-driven        | Knowledge-based   |
| Modalities            | Structured only    | Text+struct+sig   |
"""
print(comparison)

# Statistics per sample
print("\n" + "="*80)
print("Per-Sample Statistics")
print("="*80)
if issparse(x):
    nnz_per_sample = np.array(x.sum(axis=1)).flatten()
    print(f"Non-zero features per sample:")
    print(f"  Mean:   {np.mean(nnz_per_sample):.2f}")
    print(f"  Median: {np.median(nnz_per_sample):.2f}")
    print(f"  Min:    {np.min(nnz_per_sample):.0f}")
    print(f"  Max:    {np.max(nnz_per_sample):.0f}")
    print(f"  Std:    {np.std(nnz_per_sample):.2f}")

print("\n" + "="*80)
print("✅ Analysis Complete!")
print("="*80)
print("\n💡 Next Steps:")
print("1. Adapt this data format for MedKG-Signal testing")
print("2. Convert sparse features to knowledge graph representation")
print("3. Run MedKG-Signal on this test set")
print("4. Compare AUPRC results with GNN_for_EHR baseline")
print("\n📝 See /home/sijo/VeritasGraph/docs/GNN_for_EHR_ANALYSIS.md for full analysis")
