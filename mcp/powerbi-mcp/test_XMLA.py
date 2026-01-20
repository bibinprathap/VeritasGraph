import os
import sys

# =============================================================================
# 1. CONFIG
# =============================================================================

WORKSPACE_NAME = "Data Validate"
DATASET_NAME = "Data Validation"

TOKEN = """
eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6IlBjWDk4R1g0MjBUMVg2c0JEa3poUW1xZ3dNVSIsImtpZCI6IlBjWDk4R1g0MjBUMVg2c0JEa3poUW1xZ3dNVSJ9.eyJhdWQiOiJodHRwczovL2FuYWx5c2lzLndpbmRvd3MubmV0L3Bvd2VyYmkvYXBpIiwiaXNzIjoiaHR0cHM6Ly9zdHMud2luZG93cy5uZXQvOTljZjMzNTAtNDBjOC00MjYwLWJiODQtMWRhZGE0YTAyOWMwLyIsImlhdCI6MTc2ODI4MDYzMCwibmJmIjoxNzY4MjgwNjMwLCJleHAiOjE3NjgyODUxNDUsImFjY3QiOjAsImFjciI6IjEiLCJhaW8iOiJBWFFBaS84YUFBQUFsMktZSklTSVVHSk5MYitteDdWZ0tPVlhDYUxieGNtN2ExNVF4M2tOM2FpVytERWEzQ1BWcys5aVI2OEh6NTNpSVM2SFo1MlA0SGJXcjI4VEJMaGYyRlJ3NE4zTUlIY0pMdU9FUHVJZUYyOHBwSmRFOEI5WkhLMFV3Ykh1WTN2bWYxRkRVNExKZEptcEw5N0c5TUZnekE9PSIsImFtciI6WyJwd2QiLCJtZmEiXSwiYXBwaWQiOiIxOGZiY2ExNi0yMjI0LTQ1ZjYtODViMC1mN2JmMmIzOWIzZjMiLCJhcHBpZGFjciI6IjAiLCJmYW1pbHlfbmFtZSI6IlByYXRoYXAiLCJnaXZlbl9uYW1lIjoiQmliaW4iLCJpZHR5cCI6InVzZXIiLCJpcGFkZHIiOiI4My4xMTEuODAuMjIiLCJuYW1lIjoiQmliaW4gUHJhdGhhcCIsIm9pZCI6IjRmNTY2NjJkLTZiMWQtNDQwYy1iY2VhLTU1ZTNiNTg1OTA5ZiIsIm9ucHJlbV9zaWQiOiJTLTEtNS0yMS0yMjcwOTY5NTE1LTM2MDYyMDY0LTUwNzIwMDk5NC0yOTA5NCIsInB1aWQiOiIxMDAzMjAwMTY3RUNEMjRBIiwicmgiOiIxLkFYUUFVRFBQbWNoQVlFSzdoQjJ0cEtBcHdBa0FBQUFBQUFBQXdBQUFBQUFBQUFCMEFBQjBBQS4iLCJzY3AiOiJBcHAuUmVhZC5BbGwgQ2FwYWNpdHkuUmVhZC5BbGwgQ2FwYWNpdHkuUmVhZFdyaXRlLkFsbCBDb25uZWN0aW9uLlJlYWQuQWxsIENvbm5lY3Rpb24uUmVhZFdyaXRlLkFsbCBDb250ZW50LkNyZWF0ZSBEYXNoYm9hcmQuUmVhZC5BbGwgRGFzaGJvYXJkLlJlYWRXcml0ZS5BbGwgRGF0YWZsb3cuUmVhZC5BbGwgRGF0YWZsb3cuUmVhZFdyaXRlLkFsbCBEYXRhc2V0LlJlYWQuQWxsIERhdGFzZXQuUmVhZFdyaXRlLkFsbCBHYXRld2F5LlJlYWQuQWxsIEdhdGV3YXkuUmVhZFdyaXRlLkFsbCBJdGVtLkV4ZWN1dGUuQWxsIEl0ZW0uRXh0ZXJuYWxEYXRhU2hhcmUuQWxsIEl0ZW0uUmVhZFdyaXRlLkFsbCBJdGVtLlJlc2hhcmUuQWxsIE9uZUxha2UuUmVhZC5BbGwgT25lTGFrZS5SZWFkV3JpdGUuQWxsIFBpcGVsaW5lLkRlcGxveSBQaXBlbGluZS5SZWFkLkFsbCBQaXBlbGluZS5SZWFkV3JpdGUuQWxsIFJlcG9ydC5SZWFkV3JpdGUuQWxsIFJlcHJ0LlJlYWQuQWxsIFN0b3JhZ2VBY2NvdW50LlJlYWQuQWxsIFN0b3JhZ2VBY2NvdW50LlJlYWRXcml0ZS5BbGwgVGFnLlJlYWQuQWxsIFRlbmFudC5SZWFkLkFsbCBUZW5hbnQuUmVhZFdyaXRlLkFsbCBVc2VyU3RhdGUuUmVhZFdyaXRlLkFsbCBXb3Jrc3BhY2UuR2l0Q29tbWl0LkFsbCBXb3Jrc3BhY2UuR2l0VXBkYXRlLkFsbCBXb3Jrc3BhY2UuUmVhZC5BbGwgV29ya3NwYWNlLlJlYWRXcml0ZS5BbGwiLCJzaWQiOiIwMDBmOTg0YS00Y2MyLWNiZWEtNWQzMS03MmQxYmNhZjg5OWIiLCJzaWduaW5fc3RhdGUiOlsia21zaSJdLCJzdWIiOiJ5RmFzZUI0VnBJSUxiblZ6N05FNTdUc05xZWd1ZjJpRXhBd2ZYTVBjS2djIiwidGlkIjoiOTljZjMzNTAtNDBjOC00MjYwLWJiODQtMWRhZGE0YTAyOWMwIiwidW5pcXVlX25hbWUiOiJicHJhdGhhcEBFQ09VTkNJTC5BRSIsInVwbiI6ImJwcmF0aGFwQEVDT1VOQ0lMLkFFIiwidXRpIjoiWGE0U0V1WTg4a0syMDhYcWNHVkxBQSIsInZlciI6IjEuMCIsIndpZHMiOlsiZDI0YWVmNTctMTUwMC00MDcwLTg0ZGItMjY2NmYyOWNmOTY2IiwiYjc5ZmJmNGQtM2VmOS00Njg5LTgxNDMtNzZiMTk0ZTg1NTA5Il0sInhtc19hY3RfZmN0IjoiMyA1IiwieG1zX2Z0ZCI6ImlWRk9aaGhfODVsV0pXcU9kTlkwekNONldETEk4Tk1XM0VzTllfUmdrRmNCWm5KaGJtTmxZeTFrYzIxeiIsInhtc19pZHJlbCI6IjQgMSIsInhtc19zdWJfZmN0IjoiMTQgMyJ9.ElWriwz1cm8C1wo5ejmqkxvy0e-cYh_gkMUoiQCueiEFSfpVccQgDZ7FzNAKjLE_NZAMiWOMNhqZvrupOQtcU_WDDW4ASWOnE5V4MF3ZzSR6UWoorLvgptxQO-JVszlmiKz1IBbWtuLSeVwzG1nuOffwMa4d7Wg6UQyZi5C6wwDpYC_pfqAO__cH0iOJcKAxfaRhLaIoaWWN90IAYckbOcGwwqO9tI7GpmNyGmL-hbfBqjD1beez45Oxp7OjhMtp_ICQHGCQ2OZXoQ9F1-bokHMWfiWMWYkkc8vtEUJBrOcrMRshkDKlRnGHgrfK5q6acw7538gAVW6wahepuTPfyw
""".strip()

if TOKEN.lower().startswith("bearer "):
    TOKEN = TOKEN[7:]

print("Token length:", len(TOKEN))


# =============================================================================
# 2. LOAD ADOMD.NET
# =============================================================================

ADOMD_DIR = r"C:\Program Files\Microsoft.NET\ADOMD.NET\160"

if not os.path.isdir(ADOMD_DIR):
    raise RuntimeError("ADOMD.NET not installed")

sys.path.append(ADOMD_DIR)
os.environ["PATH"] = ADOMD_DIR + os.pathsep + os.environ.get("PATH", "")

import clr
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")

print("✅ ADOMD.NET loaded")


# =============================================================================
# 3. IMPORT PYADOMD
# =============================================================================

from pyadomd import Pyadomd


# =============================================================================
# 4. XMLA CONNECTION STRING (POWER BI – CORRECT)
# =============================================================================

XMLA_ENDPOINT = f"powerbi://api.powerbi.com/v1.0/myorg/{WORKSPACE_NAME}"

CONNECTION_STRING = (
    "Provider=MSOLAP;"
    f"Data Source={XMLA_ENDPOINT};"
    f"Initial Catalog={DATASET_NAME};"
    "User ID=;"
    f"Password={TOKEN};"
)

print("Connecting to:", XMLA_ENDPOINT)


# =============================================================================
# 5. TEST + SCHEMA QUERY
# =============================================================================

# ... (your existing config and ADOMD loading code) ...

import pandas as pd # Optional: for better visualization

with Pyadomd(CONNECTION_STRING) as conn:
    # 1. Get Table Names & IDs
    with conn.cursor() as cur:
        cur.execute("SELECT [ID], [Name] FROM $SYSTEM.TMSCHEMA_TABLES")
        tables = {row[0]: row[1] for row in cur.fetchall()}

    # 2. Get Column Names & IDs (to know which columns join)
    with conn.cursor() as cur:
        cur.execute("SELECT [ID], [Name] FROM $SYSTEM.TMSCHEMA_COLUMNS")
        columns = {row[0]: row[1] for row in cur.fetchall()}

    # 3. Get Relationships
    with conn.cursor() as cur:
        # We query the internal Relationship metadata
        cur.execute("""
            SELECT [FromTableID], [FromColumnID], [ToTableID], [ToColumnID] 
            FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS
        """)
        rels_raw = cur.fetchall()

print("\n🔗 DATA MODEL RELATIONSHIPS:")
print("-" * 60)
for r in rels_raw:
    from_t = tables.get(r[0], "Unknown")
    from_c = columns.get(r[1], "Unknown")
    to_t   = tables.get(r[2], "Unknown")
    to_c   = columns.get(r[3], "Unknown")
    
    print(f"[{from_t}].[{from_c}]  --->  [{to_t}].[{to_c}]")
