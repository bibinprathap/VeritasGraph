import os
import tempfile
import pandas as pd

from veritasreason.ingest.pandas_ingestor import PandasIngestor

def write_temp_csv(content: str, encoding="utf-8"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.close()
    with open(tmp.name, "w", encoding=encoding) as f:
        f.write(content)
    return tmp.name


# =======================================================
# ENCODING (5 tests)
# =======================================================

def test_encoding_latin1():
    content = "name,city\nJosé,São Paulo\n"
    path = write_temp_csv(content, encoding="latin-1")
    data = PandasIngestor().from_csv(path)
    assert data.dataframe.iloc[0]["name"] == "José"
    os.remove(path)


def test_encoding_utf8():
    content = "user,country\n李雷,China\n"
    path = write_temp_csv(content, encoding="utf-8")
    data = PandasIngestor().from_csv(path)
    assert data.dataframe.iloc[0]["user"] == "李雷"
    os.remove(path)
 
def test_from_csv_detects_tab_delimiter():
    content = (
        "user_id\trole\n"
        "1\tadmin\n"
        "2\tuser\n"
    )

    path = write_temp_csv(content)

    ingestor = PandasIngestor()
    data = ingestor.from_csv(path)

    assert data.row_count == 2
    assert data.columns == ["user_id", "role"]
    assert data.dataframe.iloc[0]["role"] == "admin"

    os.remove(path)


def test_from_csv_handles_quoted_fields_with_commas():
    content = (
        "company,revenue\n"
        '"Acme, Inc.",100\n'
        '"Widgets, LLC",200\n'
    )

    path = write_temp_csv(content)

    ingestor = PandasIngestor()
    data = ingestor.from_csv(path)

    assert data.row_count == 2
    assert data.columns == ["company", "revenue"]
    assert data.dataframe.iloc[0]["company"] == "Acme, Inc."
    assert int(data.dataframe.iloc[1]["revenue"]) == 200

    os.remove(path)


def test_from_csv_handles_multiline_quoted_fields():
    # Embed actual newlines within quoted fields
    content = "id,notes\n1,\"line1\nline2\"\n2,\"alpha\nbeta\"\n"

    path = write_temp_csv(content)

    ingestor = PandasIngestor()
    data = ingestor.from_csv(path)

    assert data.row_count == 2
    assert "\n" in data.dataframe.iloc[0]["notes"]
    assert data.dataframe.iloc[1]["notes"].split("\n")[1] == "beta"

    os.remove(path)


def test_from_csv_no_header_override():
    content = (
        "colA,colB\n"
        "x,1\n"
        "y,2\n"
    )

    path = write_temp_csv(content)

    ingestor = PandasIngestor()
    data = ingestor.from_csv(path, header=None)

    assert data.row_count == 3
    assert data.columns == [0, 1]
    assert list(data.dataframe.iloc[0]) == ["colA", "colB"]

    os.remove(path)


def test_from_csv_with_chunksize_concatenates():
    rows = ["a,b", "1,x", "2,y", "3,z", "4,w"]
    content = "\n".join(rows) + "\n"

    path = write_temp_csv(content)

    ingestor = PandasIngestor()
    data = ingestor.from_csv(path, chunksize=2)

    assert data.row_count == 4
    assert data.metadata.get("chunksize") == 2
    assert list(data.dataframe["a"]) == [1, 2, 3, 4]

    os.remove(path)


def test_from_csv_preserves_nan_values():
    content = (
        "name,score\n"
        "alice,\n"
        "bob,10\n"
    )

    path = write_temp_csv(content)

    ingestor = PandasIngestor()
    data = ingestor.from_csv(path)

    assert data.row_count == 2
    assert pd.isna(data.dataframe.iloc[0]["score"]) is True
    assert int(data.dataframe.iloc[1]["score"]) == 10

    os.remove(path)


# -------------------------------------------------------
# Test 2: Delimiter Detection (semicolon separated)
# -------------------------------------------------------


def test_encoding_accented_text():
    content = "company,city\nRenée,Zürich\n"
    path = write_temp_csv(content, encoding="latin-1")
    data = PandasIngestor().from_csv(path)
    assert data.row_count == 1
    os.remove(path)


def test_encoding_spanish():
    content = "org,country\nTelefónica,España\n"
    path = write_temp_csv(content, encoding="latin-1")
    data = PandasIngestor().from_csv(path)
    assert data.row_count == 1
    os.remove(path)


def test_encoding_ansi_cp1252():
    content = "brand,city\nPeugeot,Montréal\n"
    path = write_temp_csv(content, encoding="cp1252")   
    data = PandasIngestor().from_csv(path)
    assert data.dataframe.iloc[0]["city"] == "Montréal"
    os.remove(path)


# =======================================================
# DELIMITERS (4 tests)
# =======================================================

def test_delimiter_comma():
    content = "a,b\n1,2\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    assert list(data.columns) == ["a", "b"]
    os.remove(path)


def test_delimiter_semicolon():
    content = "a;b\n1;2\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    assert list(data.columns) == ["a", "b"]
    os.remove(path)


def test_delimiter_pipe():
    content = "a|b\n1|2\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    assert list(data.columns) == ["a", "b"]
    os.remove(path)


def test_delimiter_tab():
    content = "a\tb\n1\t2\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    assert list(data.columns) == ["a", "b"]
    os.remove(path)


# =======================================================
# BAD ROWS (3 tests)
# =======================================================

def test_bad_row_extra_columns():
    content = "x,y\n1,2\n1,2,3,4\n5,6\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    assert data.row_count == 2
    os.remove(path)

def test_bad_row_missing_column():
    content = "x,y\n1,2\n3\n4,5\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    assert data.row_count == 3
    assert data.dataframe["y"].isna().sum() == 1

def test_bad_row_unclosed_quote():
    content = "x,y\n1,2\n\"3,4\n5,6\n"
    path = write_temp_csv(content)
    data = PandasIngestor().from_csv(path)
    # The malformed quoted line consumes the following line; both are skipped.
    # Only the first valid row remains.
    assert data.row_count == 1



