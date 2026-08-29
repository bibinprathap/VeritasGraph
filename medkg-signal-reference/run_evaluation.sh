#!/bin/bash
# Complete Evaluation Pipeline for MedKG-Signal
# Runs all experiments and generates results for ICSPIS 2026 paper

set -e  # Exit on error

echo "========================================="
echo "MedKG-Signal Evaluation Pipeline"
echo "ICSPIS 2026 Submission"
echo "========================================="
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
DATA_DIR="$PROJECT_DIR/data"
RESULTS_DIR="$PROJECT_DIR/results"
EVAL_DIR="$PROJECT_DIR/eval"
SRC_DIR="$PROJECT_DIR/src"

# Create directories
mkdir -p "$DATA_DIR/graphs"
mkdir -p "$RESULTS_DIR/images"
mkdir -p "$RESULTS_DIR/metrics"
mkdir -p "$RESULTS_DIR/reports"

echo "✓ Directories created"
echo ""

# Step 1: Generate sample medical knowledge graph
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Generating Medical Knowledge Graph"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd "$SRC_DIR"
python3 kg_construction.py \
    --generate-sample-data \
    --num-encounters 100 \
    --visualize \
    --output-dir "$DATA_DIR/graphs"
echo ""
echo "✓ Knowledge graph generated and visualized"
echo ""

# Step 2: Run evaluations for all tasks
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Running Evaluation Pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd "$EVAL_DIR"
python3 evaluate.py \
    --task all \
    --n-samples 1000 \
    --output-dir "$RESULTS_DIR" \
    --generate-images \
    --generate-report
echo ""
echo "✓ Evaluation complete"
echo ""

# Step 3: Copy KG images to results
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Collecting Result Images"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Copy KG visualizations if they exist
if [ -f "$RESULTS_DIR/images/kg_static.png" ]; then
    echo "✓ Knowledge graph visualizations ready"
else
    echo "⚠ Warning: KG visualizations not found"
fi

# Check for evaluation images
if [ -f "$RESULTS_DIR/images/model_comparison.png" ]; then
    echo "✓ Model comparison charts ready"
else
    echo "⚠ Warning: Comparison charts not found"
fi

echo ""

# Step 4: Generate summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Generating Summary Report"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Count files
NUM_METRICS=$(find "$RESULTS_DIR/metrics" -name "*.json" | wc -l)
NUM_IMAGES=$(find "$RESULTS_DIR/images" -type f | wc -l)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "EVALUATION PIPELINE COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Results Summary:"
echo "   - Metric files: $NUM_METRICS"
echo "   - Visualizations: $NUM_IMAGES"
echo ""
echo "📁 Output Locations:"
echo "   📈 Metrics:     $RESULTS_DIR/metrics/"
echo "   🖼️  Images:      $RESULTS_DIR/images/"
echo "   📄 HTML Report: $RESULTS_DIR/results/evaluation_report.html"
echo ""
echo "🔗 Quick Access:"
echo "   View HTML report:"
echo "     firefox $RESULTS_DIR/results/evaluation_report.html"
echo ""
echo "   View knowledge graph:"
echo "     eog $RESULTS_DIR/images/kg_static.png"
echo ""
echo "   View comparisons:"
echo "     eog $RESULTS_DIR/images/model_comparison.png"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ All evaluations complete!"
echo "Ready for ICSPIS 2026 paper submission"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
