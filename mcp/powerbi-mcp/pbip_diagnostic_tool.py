"""
PBIP Diagnostic and Utility Tool

This script helps you:
1. Find PBIP files on your system
2. Analyze PBIP structure
3. Identify DAX quoting issues
4. Preview changes before applying fixes
5. Test the connector with real PBIP files
"""
import os
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from powerbi_pbip_connector import PowerBIPBIPConnector, quote_tmdl_name, needs_tmdl_quoting


def find_pbip_files(start_path: str = None, max_depth: int = 3) -> List[Path]:
    """Find all .pbip files on the system or in a specific directory"""
    if not start_path:
        # Common Power BI document locations
        common_paths = [
            Path.home() / "Documents",
            Path.home() / "OneDrive" / "Documents",
            Path(f"{os.environ.get('APPDATA', '')}\\Microsoft\\Power BI"),
            Path("C:\\Users\\Public\\Documents"),
        ]
        pbip_files = []
        for path in common_paths:
            if path.exists():
                pbip_files.extend(list(path.rglob("*.pbip")))
        return pbip_files
    else:
        start = Path(start_path)
        if start.exists():
            return list(start.rglob("*.pbip"))
        return []


def analyze_pbip_structure(pbip_path: str) -> Dict[str, Any]:
    """Analyze a PBIP file structure and report findings"""
    try:
        connector = PowerBIPBIPConnector(auto_backup=False)
        if not connector.load_project(pbip_path):
            return {"error": f"Failed to load PBIP: {pbip_path}"}

        info = connector.get_project_info()

        # Get validation errors
        errors = connector.validate_tmdl_syntax()

        # Categorize errors
        error_summary = {
            "total_errors": len(errors),
            "unquoted_names": len([e for e in errors if e.error_type == "UNQUOTED_NAME"]),
            "unquoted_references": len([e for e in errors if e.error_type == "UNQUOTED_REFERENCE"]),
            "unquoted_dax": len([e for e in errors if e.error_type == "UNQUOTED_TABLE_IN_DAX"]),
            "file_errors": len([e for e in errors if e.error_type == "FILE_ERROR"]),
        }

        return {
            "pbip_path": pbip_path,
            "project_info": info,
            "error_summary": error_summary,
            "detailed_errors": [
                {
                    "file": e.file_path,
                    "line": e.line_number,
                    "type": e.error_type,
                    "message": e.message,
                    "context": e.context[:100] + "..." if len(e.context) > 100 else e.context,
                }
                for e in errors[:10]  # Show first 10 errors
            ],
            "total_detailed": len(errors),
        }

    except Exception as e:
        return {"error": str(e), "pbip_path": pbip_path}


def test_dax_quoting_fix(pbip_path: str) -> Dict[str, Any]:
    """Test the DAX quoting fix on a PBIP file (preview mode)"""
    try:
        connector = PowerBIPBIPConnector(auto_backup=False)
        if not connector.load_project(pbip_path):
            return {"error": f"Failed to load PBIP: {pbip_path}"}

        # Run validation before fix
        errors_before = connector.validate_tmdl_syntax()
        dax_errors_before = [e for e in errors_before if e.error_type == "UNQUOTED_TABLE_IN_DAX"]

        # This does NOT modify files - just previews what would be fixed
        fix_result = connector.fix_all_dax_quoting()

        # Run validation after fix
        errors_after = connector.validate_tmdl_syntax()
        dax_errors_after = [e for e in errors_after if e.error_type == "UNQUOTED_TABLE_IN_DAX"]

        return {
            "pbip_path": pbip_path,
            "files_modified": fix_result["files_modified"],
            "references_fixed": fix_result["count"],
            "tables_fixed": fix_result["tables_fixed"],
            "errors_before": len(dax_errors_before),
            "errors_after": len(dax_errors_after),
            "improvement": len(dax_errors_before) - len(dax_errors_after),
            "sample_fixes": fix_result["count"],
        }

    except Exception as e:
        return {"error": str(e), "pbip_path": pbip_path}


def print_pbip_list(pbip_files: List[Path]):
    """Print formatted list of PBIP files found"""
    if not pbip_files:
        print("  No .pbip files found")
        return

    print(f"\nFound {len(pbip_files)} PBIP file(s):\n")
    for i, pbip in enumerate(pbip_files, 1):
        print(f"  {i}. {pbip}")
        print(f"     Size: {pbip.stat().st_size / (1024*1024):.2f} MB")
        print(f"     Modified: {Path(pbip).stat().st_mtime}")
        print()


def print_analysis(analysis: Dict[str, Any]):
    """Print formatted analysis results"""
    if "error" in analysis:
        print(f"  ERROR: {analysis['error']}")
        return

    print(f"\n  Project: {analysis['project_info'].get('pbip_file', 'Unknown')}")
    print(f"  TMDL Files: {analysis['project_info'].get('tmdl_file_count', 0)}")
    print(f"  Report: {'Yes' if analysis['project_info'].get('report_json_path') else 'No'}")
    print()
    print(f"  Validation Errors Summary:")
    print(f"    - Total errors: {analysis['error_summary']['total_errors']}")
    print(f"    - Unquoted names: {analysis['error_summary']['unquoted_names']}")
    print(f"    - Unquoted references: {analysis['error_summary']['unquoted_references']}")
    print(f"    - Unquoted DAX: {analysis['error_summary']['unquoted_dax']}")

    if analysis["detailed_errors"]:
        print(f"\n  Sample Errors (showing 1-{len(analysis['detailed_errors'])} of {analysis['total_detailed']}):")
        for err in analysis["detailed_errors"][:5]:
            print(f"    - {err['type']}: {err['message']}")
            print(f"      {err['file']}:{err['line']}")


def print_fix_preview(result: Dict[str, Any]):
    """Print formatted fix preview results"""
    if "error" in result:
        print(f"  ERROR: {result['error']}")
        return

    print(f"\n  DAX Quoting Fix Preview")
    print(f"  =====================")
    print(f"  Files to be fixed: {len(result['files_modified'])}")
    for f in result['files_modified']:
        print(f"    - {f}")

    print(f"\n  References to be fixed: {result['references_fixed']}")
    print(f"  Tables affected: {result['tables_fixed']}")

    if result['errors_before'] > 0:
        print(f"\n  Impact:")
        print(f"    - Errors before: {result['errors_before']}")
        print(f"    - Errors after: {result['errors_after']}")
        print(f"    - Improvement: {result['improvement']} errors fixed")


def main():
    print("\n" + "="*70)
    print("  PBIP DIAGNOSTIC AND UTILITY TOOL")
    print("="*70)

    # Check for command line arguments
    if len(sys.argv) > 1:
        pbip_path = sys.argv[1]
        print(f"\nAnalyzing PBIP: {pbip_path}")
        print("="*70)

        analysis = analyze_pbip_structure(pbip_path)
        print_analysis(analysis)

        print("\n" + "-"*70)
        print("Testing DAX Quoting Fix (Preview)")
        print("-"*70)
        fix_preview = test_dax_quoting_fix(pbip_path)
        print_fix_preview(fix_preview)

        return 0

    # Interactive mode - find PBIP files
    print("\nSearching for PBIP files...")
    print("-"*70)

    pbip_files = find_pbip_files()
    print_pbip_list(pbip_files)

    if pbip_files:
        print("="*70)
        print("\nUsage:")
        print("-"*70)
        print("1. Analyze a specific PBIP:")
        print(f"   python pbip_diagnostic_tool.py \"{pbip_files[0]}\"")
        print()
        print("2. Find and analyze custom location:")
        print("   python pbip_diagnostic_tool.py \"C:/path/to/your/file.pbip\"")
        print()

    print("\nTo use the PBIP Connector in your code:")
    print("-"*70)
    print("""
from powerbi_pbip_connector import PowerBIPBIPConnector

# Initialize connector
connector = PowerBIPBIPConnector(auto_backup=True)

# Load your PBIP file
pbip_path = "C:/path/to/your/Report.pbip"
connector.load_project(pbip_path)

# Check for issues
errors = connector.validate_tmdl_syntax()
print(f"Found {len(errors)} issues")

# Fix DAX quoting issues
fix_result = connector.fix_all_dax_quoting()
print(f"Fixed {fix_result['count']} references")

# Rename a table (includes proper quoting)
result = connector.rename_table_in_files("OldName", "New Table Name")
print(f"Renamed: {result.success}")
    """)

    return 0


if __name__ == "__main__":
    sys.exit(main())
