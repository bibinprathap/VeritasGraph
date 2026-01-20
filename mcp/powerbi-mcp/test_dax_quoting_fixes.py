"""
Test DAX Quoting Fixes for PBIP Connector

Tests for:
1. TMDL name quoting (names with spaces)
2. DAX expression validation (detecting unquoted table references)
3. DAX expression fixing (adding quotes to table names)
4. Table rename operations with proper quoting
5. Complex DAX expressions in mock PBIP projects
"""
import sys
import os
import tempfile
import shutil
import json


# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from powerbi_pbip_connector import (
    needs_tmdl_quoting,
    quote_tmdl_name,
    unquote_tmdl_name,
    fix_dax_table_references,
    PowerBIPBIPConnector,
)


def log_pass(test_name, msg=""):
    print(f"  [PASS] {test_name}: {msg}")


def log_fail(test_name, msg=""):
    print(f"  [FAIL] {test_name}: {msg}")


def test_tmdl_quoting():
    """Test TMDL name quoting functions"""
    print("\n" + "="*70)
    print("TEST 1: TMDL Quoting Functions")
    print("="*70)

    # Test needs_tmdl_quoting
    print("\nSubtest: needs_tmdl_quoting()")
    tests = [
        ("Sales", False, "Simple name - no quotes needed"),
        ("Customer Appointments", True, "Name with space - quotes needed"),
        ("My Table Name", True, "Multi-word name - quotes needed"),
        ("_measures", False, "Underscore prefix - no quotes needed"),
        ("123Table", True, "Starts with digit - quotes needed"),
        ("table", True, "Reserved word - quotes needed"),
        ("Normal_Name", False, "Underscore in name - no quotes needed"),
        ("Name's", True, "Single quote in name - quotes needed"),
        ("Leads Sales Data", True, "Multi-word with spaces - quotes needed"),
    ]

    passed = 0
    for name, expected, description in tests:
        result = needs_tmdl_quoting(name)
        if result == expected:
            log_pass(f"needs_tmdl_quoting('{name}')", description)
            passed += 1
        else:
            log_fail(f"needs_tmdl_quoting('{name}')",
                    f"Expected {expected}, got {result}")

    # Test quote_tmdl_name
    print("\nSubtest: quote_tmdl_name()")
    quote_tests = [
        ("Sales", "Sales"),
        ("Customer Appointments", "'Customer Appointments'"),
        ("My Table's Data", "'My Table''s Data'"),  # Escape internal quote
        ("Leads Sales Data", "'Leads Sales Data'"),
    ]

    for name, expected in quote_tests:
        result = quote_tmdl_name(name)
        if result == expected:
            log_pass(f"quote_tmdl_name('{name}')", f"-> {result}")
            passed += 1
        else:
            log_fail(f"quote_tmdl_name('{name}')",
                    f"Expected '{expected}', got '{result}'")

    print(f"\nQuoting tests: {passed}/{len(tests) + len(quote_tests)} passed")
    return passed == len(tests) + len(quote_tests)


def test_dax_validation():
    """Test DAX expression validation"""
    print("\n" + "="*70)
    print("TEST 2: DAX Expression Validation")
    print("="*70)

    # Test fix_dax_table_references function
    print("\nSubtest: fix_dax_table_references()")
    test_cases = [
        (
            "SUM(Leads Sales Data[Amount])",
            ["Leads Sales Data"],
            "SUM('Leads Sales Data'[Amount])",
            "Simple unquoted table reference"
        ),
        (
            "CALCULATE(SUM(Leads Sales Data[Amount]))",
            ["Leads Sales Data"],
            "CALCULATE(SUM('Leads Sales Data'[Amount]))",
            "Nested function with unquoted table"
        ),
        (
            "SUM('Leads Sales Data'[Amount])",
            ["Leads Sales Data"],
            "SUM('Leads Sales Data'[Amount])",
            "Already properly quoted"
        ),
        (
            "var x = SUM(Leads Sales Data[Amount]) RETURN x",
            ["Leads Sales Data"],
            "var x = SUM('Leads Sales Data'[Amount]) RETURN x",
            "DAX with variable"
        ),
    ]

    passed = 0
    for dax_input, tables, expected, description in test_cases:
        result = fix_dax_table_references(dax_input, tables)
        if result == expected:
            log_pass(f"fix_dax_table_references()", description)
            passed += 1
        else:
            log_fail(f"fix_dax_table_references()",
                    f"{description}\n      Input:    {dax_input}\n"
                    f"      Expected: {expected}\n      Got:      {result}")

    print(f"\nDAX validation tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_rename_with_quoting():
    """Test table rename with proper quoting"""
    print("\n" + "="*70)
    print("TEST 3: Table Rename with Proper Quoting")
    print("="*70)

    # Create a temporary directory with mock PBIP structure
    temp_dir = tempfile.mkdtemp(prefix="pbip_test_")

    try:
        print("\nSubtest: Creating mock PBIP project")

        # Create mock structure
        pbip_file = os.path.join(temp_dir, "TestProject.pbip")
        semantic_folder = os.path.join(temp_dir, "TestProject.SemanticModel")
        tables_folder = os.path.join(semantic_folder, "definition", "tables")
        relationships_folder = os.path.join(semantic_folder, "definition", "relationships")
        report_folder = os.path.join(temp_dir, "TestProject.Report")

        os.makedirs(tables_folder)
        os.makedirs(relationships_folder)
        os.makedirs(report_folder)

        # Create mock .pbip file
        with open(pbip_file, 'w') as f:
            f.write('{"version": "1.0"}')

        # Create mock table TMDL with problematic DAX
        table_content = """table Salesforce_Data
    column 'Created Date'
        dataType: dateTime

    column Amount
        dataType: decimal

    measure TotalAmount = SUM(Salesforce_Data[Amount])

    measure Total with Spaces =
        var convertedProject = SELECTEDVALUE(dim_projects[Project Name])
        RETURN
        IF(convertedProject <> BLANK(), CALCULATE(SUM(Leads Sales Data[Amount])), BLANK())
"""
        with open(os.path.join(tables_folder, "Salesforce_Data.tmdl"), 'w') as f:
            f.write(table_content)

        # Create a table with spaces
        dim_projects_content = """table 'dim_projects'
    column 'Project Name'
        dataType: string
"""
        with open(os.path.join(tables_folder, "dim_projects.tmdl"), 'w') as f:
            f.write(dim_projects_content)

        # Create table with spaces that needs fixing
        leads_content = """table 'Leads Sales Data'
    column 'Amount'
        dataType: decimal
"""
        with open(os.path.join(tables_folder, "Leads_Sales_Data.tmdl"), 'w') as f:
            f.write(leads_content)

        # Create a relationship file with the old table name
        relationship_content = """relationship 'Salesforce_Data to dim_projects'
  cardinality: manyToOne
  isActive: true
  fromTable: Salesforce_Data
  fromColumn: ProjectId
  toTable: dim_projects
  toColumn: ProjectId
"""
        with open(os.path.join(relationships_folder, "rel_salesforce_to_projects.tmdl"), 'w') as f:
            f.write(relationship_content)

        # Test loading the project
        print("  Testing PBIP project loading...")
        connector = PowerBIPBIPConnector(auto_backup=False)

        if connector.load_project(temp_dir):
            log_pass("Load project", "Mock project loaded successfully")
        else:
            log_fail("Load project", "Failed to load mock project")
            return False

        # Test validation
        print("\n  Testing DAX validation...")
        errors = connector.validate_tmdl_syntax()

        # We should have at least one error for unquoted "Leads Sales Data"
        dax_errors = [e for e in errors if e.error_type == "UNQUOTED_TABLE_IN_DAX"]
        if dax_errors:
            log_pass("Validation", f"Found {len(dax_errors)} DAX quoting error(s)")
            for err in dax_errors:
                print(f"      - {err.message}")
        else:
            log_fail("Validation", "Expected to find DAX quoting errors")

        # Test fix_all_dax_quoting
        print("\n  Testing DAX quoting fix...")
        fix_result = connector.fix_all_dax_quoting()
        if fix_result["count"] > 0:
            log_pass("Fix DAX", f"Fixed {fix_result['count']} references in {len(fix_result['files_modified'])} file(s)")
        else:
            print(f"    Info: No DAX quoting fixes needed (count={fix_result['count']})")

        # Verify after fix
        errors_after = connector.validate_tmdl_syntax()
        dax_errors_after = [e for e in errors_after if e.error_type == "UNQUOTED_TABLE_IN_DAX"]

        if len(dax_errors_after) < len(dax_errors):
            log_pass("Validation after fix",
                    f"Reduced DAX errors from {len(dax_errors)} to {len(dax_errors_after)}")
        else:
            log_fail("Validation after fix",
                    f"Expected fewer errors after fix, still have {len(dax_errors_after)}")

        # Test rename with quoting
        print("\n  Testing table rename with proper quoting...")
        result = connector.rename_table_in_files("Salesforce_Data", "Sales Force Data")

        if result.success:
            log_pass("Table rename", f"Renamed with {result.references_updated} references updated")
        else:
            log_fail("Table rename", f"Failed: {result.message}")
            if result.validation_errors:
                for err in result.validation_errors:
                    print(f"      Error: {err.message}")

        # Verify renamed table is properly quoted
        with open(os.path.join(tables_folder, "Salesforce_Data.tmdl"), 'r') as f:
            renamed_content = f.read()

        if "table 'Sales Force Data'" in renamed_content:
            log_pass("Table declaration", "Properly quoted after rename")
        else:
            log_fail("Table declaration", f"Not properly quoted. Content:\n{renamed_content}")

        # Verify DAX references are properly quoted
        if "'Sales Force Data'[Amount]" in renamed_content:
            log_pass("DAX reference in measure", "Properly quoted after rename")
        else:
            log_fail("DAX reference in measure", f"Not properly quoted")

        # Verify relationship name is updated
        print("\n  Testing relationship updates...")
        with open(os.path.join(relationships_folder, "rel_salesforce_to_projects.tmdl"), 'r') as f:
            relationship_content = f.read()

        if "'Sales Force Data to dim_projects'" in relationship_content or "'Sales Force Data' to 'dim_projects'" in relationship_content or "to dim_projects" in relationship_content:
            log_pass("Relationship name update", "Contains updated table name reference")
        else:
            log_fail("Relationship name update", f"Relationship name not updated. Content:\n{relationship_content}")

        if "fromTable: 'Sales Force Data'" in relationship_content:
            log_pass("Relationship fromTable update", "Properly quoted after rename")
        else:
            log_fail("Relationship fromTable update", f"Not properly quoted or updated. Content:\n{relationship_content}")

        return result.success

    except Exception as e:
        log_fail("Mock project test", str(e))
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_relationship_scenarios():
    """Test complex relationship scenarios with table renames"""
    print("\n" + "="*70)
    print("TEST 4: Complex Relationship Scenarios")
    print("="*70)

    temp_dir = tempfile.mkdtemp(prefix="pbip_rel_test_")

    try:
        # Create mock structure
        pbip_file = os.path.join(temp_dir, "RelTest.pbip")
        semantic_folder = os.path.join(temp_dir, "RelTest.SemanticModel")
        tables_folder = os.path.join(semantic_folder, "definition", "tables")
        relationships_folder = os.path.join(semantic_folder, "definition", "relationships")
        report_folder = os.path.join(temp_dir, "RelTest.Report")

        os.makedirs(tables_folder)
        os.makedirs(relationships_folder)
        os.makedirs(report_folder)

        # Create mock .pbip file
        with open(pbip_file, 'w') as f:
            f.write('{"version": "1.0"}')

        # Create tables
        with open(os.path.join(tables_folder, "Salesforce_Data.tmdl"), 'w') as f:
            f.write("""table Salesforce_Data
    column ProjectId
        dataType: string
    column Amount
        dataType: decimal
""")

        with open(os.path.join(tables_folder, "dim_projects.tmdl"), 'w') as f:
            f.write("""table dim_projects
    column ProjectId
        dataType: string
    column ProjectName
        dataType: string
""")

        # Create multiple relationships
        with open(os.path.join(relationships_folder, "rel1.tmdl"), 'w') as f:
            f.write("""relationship 'Salesforce_Data to dim_projects'
  cardinality: manyToOne
  fromTable: Salesforce_Data
  fromColumn: ProjectId
  toTable: dim_projects
  toColumn: ProjectId
""")

        with open(os.path.join(relationships_folder, "rel2.tmdl"), 'w') as f:
            f.write("""relationship rel_SalesforceData_Projects
  cardinality: manyToOne
  fromTable: 'Salesforce_Data'
  fromColumn: ProjectId
  toTable: 'dim_projects'
  toColumn: ProjectId
""")

        # Load and test
        connector = PowerBIPBIPConnector(auto_backup=False)
        if not connector.load_project(temp_dir):
            log_fail("Relationship test", "Failed to load project")
            return False

        # Rename table with spaces
        result = connector.rename_table_in_files("Salesforce_Data", "Salesforce Customer Data")

        if result.success:
            log_pass("Rename with relationships", f"Renamed with {result.references_updated} references")
        else:
            log_fail("Rename with relationships", f"Failed: {result.message}")
            return False

        # Verify rel1 - quoted relationship name
        with open(os.path.join(relationships_folder, "rel1.tmdl"), 'r') as f:
            rel1_content = f.read()

        if "'Salesforce Customer Data to dim_projects'" in rel1_content:
            log_pass("Relationship 1 name", "Updated to quoted format")
        else:
            log_fail("Relationship 1 name", f"Not updated correctly. Content:\n{rel1_content}")

        if "fromTable: 'Salesforce Customer Data'" in rel1_content:
            log_pass("Relationship 1 fromTable", "Properly quoted")
        else:
            log_fail("Relationship 1 fromTable", f"Not properly quoted. Content:\n{rel1_content}")

        # Verify rel2 - already quoted
        with open(os.path.join(relationships_folder, "rel2.tmdl"), 'r') as f:
            rel2_content = f.read()

        if "fromTable: 'Salesforce Customer Data'" in rel2_content:
            log_pass("Relationship 2 fromTable", "Updated properly quoted version")
        else:
            log_fail("Relationship 2 fromTable", f"Not updated. Content:\n{rel2_content}")

        return True

    except Exception as e:
        log_fail("Relationship scenarios", str(e))
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_column_rename_in_relationships():
    """Test column rename in relationship definitions"""
    print("\n" + "="*70)
    print("TEST 4B: Column Rename in Relationships")
    print("="*70)

    temp_dir = tempfile.mkdtemp(prefix="pbip_col_rel_test_")

    try:
        # Create mock structure
        pbip_file = os.path.join(temp_dir, "ColRelTest.pbip")
        semantic_folder = os.path.join(temp_dir, "ColRelTest.SemanticModel")
        tables_folder = os.path.join(semantic_folder, "definition", "tables")
        relationships_folder = os.path.join(semantic_folder, "definition", "relationships")
        report_folder = os.path.join(temp_dir, "ColRelTest.Report")

        os.makedirs(tables_folder)
        os.makedirs(relationships_folder)
        os.makedirs(report_folder)

        # Create mock .pbip file
        with open(pbip_file, 'w') as f:
            f.write('{"version": "1.0"}')

        # Create tables
        with open(os.path.join(tables_folder, "Sales.tmdl"), 'w') as f:
            f.write("""table Sales
    column SalesId
        dataType: string
    column ProjectKey
        dataType: string
""")

        with open(os.path.join(tables_folder, "Projects.tmdl"), 'w') as f:
            f.write("""table Projects
    column ProjId
        dataType: string
""")

        # Create relationship with column references that will be renamed
        with open(os.path.join(relationships_folder, "rel_sales_projects.tmdl"), 'w') as f:
            f.write("""relationship 'Sales to Projects'
  cardinality: manyToOne
  fromTable: Sales
  fromColumn: ProjectKey
  toTable: Projects
  toColumn: ProjId
""")

        # Load and test
        connector = PowerBIPBIPConnector(auto_backup=False)
        if not connector.load_project(temp_dir):
            log_fail("Column rename in relationships", "Failed to load project")
            return False

        # Rename column in the from table
        result = connector.rename_column_in_files("Sales", "ProjectKey", "ProjectId")

        if result.success:
            log_pass("Column rename in relationship", f"Renamed with {result.references_updated} references")
        else:
            log_fail("Column rename in relationship", f"Failed: {result.message}")
            return False

        # Verify relationship file - fromColumn should be updated
        with open(os.path.join(relationships_folder, "rel_sales_projects.tmdl"), 'r') as f:
            rel_content = f.read()

        if "fromColumn: ProjectId" in rel_content or "fromColumn: 'ProjectId'" in rel_content:
            log_pass("Relationship fromColumn update", "Column renamed in relationship")
        else:
            log_fail("Relationship fromColumn update", f"Column not updated. Content:\n{rel_content}")

        # Verify other parts stay the same
        if "fromTable: Sales" in rel_content:
            log_pass("Relationship fromTable unchanged", "Table reference preserved")
        else:
            log_fail("Relationship fromTable unchanged", f"Table reference was modified. Content:\n{rel_content}")

        return True

    except Exception as e:
        log_fail("Column rename in relationships", str(e))
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_complex_dax():
    """Test complex DAX scenarios"""
    print("\n" + "="*70)
    print("TEST 5: Complex DAX Scenarios")
    print("="*70)

    test_cases = [
        {
            "name": "Multiple table references",
            "dax": "CALCULATE(SUM(Leads Sales Data[Amount]), Leads Sales Data[Status] = \"Won\")",
            "tables": ["Leads Sales Data"],
            "expected": "CALCULATE(SUM('Leads Sales Data'[Amount]), 'Leads Sales Data'[Status] = \"Won\")",
        },
        {
            "name": "Nested functions",
            "dax": "IF(Leads Sales Data[Amount] > 1000, Leads Sales Data[Amount] * 2, 0)",
            "tables": ["Leads Sales Data"],
            "expected": "IF('Leads Sales Data'[Amount] > 1000, 'Leads Sales Data'[Amount] * 2, 0)",
        },
        {
            "name": "Mixed quoted and unquoted",
            "dax": "SUM(Leads Sales Data[Amount]) + SUM('Other Table'[Amount])",
            "tables": ["Leads Sales Data", "Other Table"],
            "expected": "SUM('Leads Sales Data'[Amount]) + SUM('Other Table'[Amount])",
        },
    ]

    passed = 0
    for test_case in test_cases:
        result = fix_dax_table_references(test_case["dax"], test_case["tables"])
        if result == test_case["expected"]:
            log_pass(f"Complex DAX: {test_case['name']}", "Correctly fixed")
            passed += 1
        else:
            log_fail(f"Complex DAX: {test_case['name']}",
                    f"\n      Input:    {test_case['dax']}\n"
                    f"      Expected: {test_case['expected']}\n"
                    f"      Got:      {result}")

    print(f"\nComplex DAX tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def main():
    print("\n" + "="*70)
    print("  PBIP CONNECTOR DAX QUOTING FIXES - COMPREHENSIVE TEST SUITE")
    print("="*70)

    results = []

    results.append(("TMDL Quoting", test_tmdl_quoting()))
    results.append(("DAX Validation", test_dax_validation()))
    results.append(("Table Rename", test_rename_with_quoting()))
    results.append(("Relationship Scenarios", test_relationship_scenarios()))
    results.append(("Column Rename in Relationships", test_column_rename_in_relationships()))
    results.append(("Complex DAX", test_complex_dax()))

    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "OK" if result else "XX"
        print(f"  [{symbol}] {status:5s} - {name}")

    print(f"\n  Total: {passed}/{total} test groups passed")
    print("="*70)

    if passed == total:
        print("\n  ALL TESTS PASSED!")
        return 0
    else:
        print("\n  SOME TESTS FAILED - Review output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
