#!/usr/bin/env python3
"""Generate HTML report from existing metrics"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Add eval to path
sys.path.insert(0, str(Path(__file__).parent / 'eval'))

from evaluate import generate_html_report

output_dir = Path(__file__).parent / 'results'
generate_html_report(output_dir)
print(f"✓ HTML report generated at {output_dir}/results/evaluation_report.html")
