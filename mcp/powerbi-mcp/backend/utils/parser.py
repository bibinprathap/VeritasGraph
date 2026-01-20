import re

def sanitize_dax(dax: str) -> str:
    dax = dax.strip().replace("```", "").strip()
    last_paren = dax.rfind(")")
    if last_paren != -1:
        dax = dax[: last_paren + 1]
    return dax.rstrip(" .;")

def enforce_table_quotes(dax: str, table_names: list[str]) -> str:
    """Quote table names from the provided list"""
    for table in table_names:
        dax = re.sub(
            rf'(?<!\')\b{re.escape(table)}\b(?!\')\s*\[',
            f"'{table}'[",
            dax
        )
    return dax

def fix_unquoted_table_names(dax: str) -> str:
    """
    Fix unquoted table names with spaces before column references.
    Matches patterns like: TableName With Spaces[Column] 
    And converts to: 'TableName With Spaces'[Column]
    """
    # Pattern to match unquoted multi-word table names before [column]
    # Looks for: word(s) with spaces followed by [
    # But not already quoted (no ' before)
    pattern = r"(?<!')(\b[A-Za-z_][A-Za-z0-9_]*(?:\s+[A-Za-z_][A-Za-z0-9_]*)+)\s*\["
    
    def quote_table(match):
        table_name = match.group(1).strip()
        return f"'{table_name}'["
    
    return re.sub(pattern, quote_table, dax)

def fix_distinct_in_row(dax: str) -> str:
    """
    Fix invalid pattern: ROW("label", DISTINCT(...))
    DISTINCT returns a table, not a scalar, so it can't be used inside ROW.
    Convert to: DISTINCT(...)
    """
    # Pattern: ROW("something", DISTINCT('Table'[Column]))
    pattern = r'ROW\s*\(\s*"[^"]*"\s*,\s*(DISTINCT\s*\([^)]+\))\s*\)'
    
    match = re.search(pattern, dax, re.IGNORECASE)
    if match:
        # Replace the entire ROW(...DISTINCT...) with just DISTINCT(...)
        distinct_part = match.group(1)
        dax = re.sub(pattern, distinct_part, dax, flags=re.IGNORECASE)
    
    return dax

def repair_averagex_filter(dax: str) -> str:
    """
    Repairs:
    AVERAGEX(Table, condition, expr)
    -->
    AVERAGEX(FILTER('Table', condition), expr)
    """
    pattern = re.compile(
        r'AVERAGEX\s*\(\s*(\w+)\s*,\s*([^,]+?)\s*,\s*([^)]+)\)',
        re.IGNORECASE
    )

    def repl(match):
        table, condition, expr = match.groups()
        return (
            f"AVERAGEX("
            f"FILTER('{table}', {condition}), "
            f"{expr})"
        )

    return pattern.sub(repl, dax)

def fix_bare_scalar_functions(dax: str) -> str:
    """
    Fix bare scalar aggregate functions that are not wrapped in ROW().
    EVALUATE COUNT(...) is invalid - must be EVALUATE ROW("Count", COUNT(...))
    
    This fixes:
    - EVALUATE COUNT(...) → EVALUATE ROW("Count", COUNT(...))
    - EVALUATE SUM(...) → EVALUATE ROW("Total", SUM(...))
    - EVALUATE AVERAGE(...) → EVALUATE ROW("Average", AVERAGE(...))
    - EVALUATE COUNTROWS(...) → EVALUATE ROW("Count", COUNTROWS(...))
    - EVALUATE DISTINCTCOUNT(...) → EVALUATE ROW("Count", DISTINCTCOUNT(...))
    - EVALUATE MIN(...) → EVALUATE ROW("Min", MIN(...))
    - EVALUATE MAX(...) → EVALUATE ROW("Max", MAX(...))
    """
    # Map of scalar functions to their ROW label
    scalar_funcs = {
        'COUNT': 'Count',
        'COUNTROWS': 'Count',
        'DISTINCTCOUNT': 'Count',
        'SUM': 'Total',
        'AVERAGE': 'Average',
        'MIN': 'Min',
        'MAX': 'Max',
    }
    
    for func, label in scalar_funcs.items():
        # Pattern: EVALUATE followed by scalar function (not inside ROW)
        # Match: EVALUATE COUNT(...) but not EVALUATE ROW("x", COUNT(...))
        pattern = rf'EVALUATE\s+(?!ROW\s*\()({func}\s*\([^)]+\))'
        
        def make_replacement(label):
            def replacement(match):
                func_call = match.group(1)
                return f'EVALUATE ROW("{label}", {func_call})'
            return replacement
        
        dax = re.sub(pattern, make_replacement(label), dax, flags=re.IGNORECASE)
    
    return dax


def validate_aggregatorx_usage(dax: str):
    bad_patterns = [
        r'AVERAGEX\s*\([^,]+,\s*[^,]+,\s*[^)]+\)',
        r'SUMX\s*\([^,]+,\s*[^,]+,\s*[^)]+\)',
        r'COUNTX\s*\([^,]+,\s*[^,]+,\s*[^)]+\)',
    ]
    for p in bad_patterns:
        if re.search(p, dax, re.IGNORECASE):
            raise ValueError(
                "Invalid DAX: AVERAGEX/SUMX/COUNTX must have exactly 2 arguments. "
                "Use FILTER() for conditions."
            )
