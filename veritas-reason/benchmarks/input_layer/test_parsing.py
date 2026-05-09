import csv
import io
import json
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from veritasreason.parse.code_parser import CodeParser
from veritasreason.parse.csv_parser import CSVParser
from veritasreason.parse.document_parser import DocumentParser
from veritasreason.parse.html_parser import HTMLParser
from veritasreason.parse.json_parser import JSONParser

# Data gens


def generate_json_string(item_count: int) -> str:
    data = [
        {
            "id": i,
            "name": f"Item:{i}",
            "tags": ["tag1", "tag2", "tag3"],
            "metadata": {"active": True, "score": 0.95},
        }
        for i in range(item_count)
    ]
    return json.dumps(data)


def generate_csv_string(row_count: int) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "description", "value", "date"])
    for i in range(row_count):
        writer.writerow([i, f"Item {i}", "Description text here", 100.50, "2024-01-01"])
    return output.getvalue()


def generate_html_string(element_count: int) -> str:
    lis = "".join(
        [f'<li><a href="/item/{i}">Link {i}</a></li>' for i in range(element_count)]
    )
    return f"""
    <html>
        <head><title>Benchmark Page</title></head>
        <body>
            <div id="content">
                <h1>Header</h1>
                <p>Some intro text.</p>
                <ul>{lis}</ul>
            </div>
        </body>
    </html>
    """


# lib mocks


class MockPDFPage:
    def __init__(self, page_num):
        self.width = 600
        self.height = 800
        self.page_number = page_num

    def extract_text(self):
        return f"This is text content for page {self.page_number}. " * 50

    def extract_tables(self):
        return [[["Header1", "Header2"], ["Row1", "Value1"]]]

    @property
    def images(self):
        return [{"x0": 10, "y0": 10, "width": 100, "height": 100}]


class MockPDF:
    def __init__(self, page_count):
        self.pages = [MockPDFPage(i) for i in range(page_count)]
        self.metadata = {"Title": "Benchmark PDF", "Author": "Noone"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def mock_pdfplumber():
    with patch("pdfplumber.open") as mock_open:
        yield mock_open


# Benchmarks


@pytest.mark.parametrize("size", [1000, 10000])
def test_json_parsing_throughput(benchmark, size):
    parser = JSONParser()
    json_str = generate_json_string(size)

    with patch("pathlib.Path.exists", return_value=False):

        def op():
            return parser.parse(json_str)

        benchmark.pedantic(op, iterations=5, rounds=10)


@pytest.mark.parametrize("rows", [1000, 10000])
def test_csv_parsing_throughput(benchmark, rows):
    """
    Measures CSV parsing throughput.
    """
    parser = CSVParser()
    csv_content = generate_csv_string(rows)

    with patch(
        "builtins.open", side_effect=lambda *args, **kwargs: io.StringIO(csv_content)
    ):
        with patch("pathlib.Path.exists", return_value=True):

            def op():
                return parser.parse("dummy.csv")

            benchmark.pedantic(op, iterations=5, rounds=5)


@pytest.mark.parametrize("elements", [100, 1000])
def test_html_scraping_speed(benchmark, elements):
    parser = HTMLParser()
    html_content = generate_html_string(elements)

    with patch("pathlib.Path.exists", return_value=False):

        def op():
            return parser.parse(html_content, extract_links=True)

        benchmark.pedantic(op, iterations=5, rounds=5)


@pytest.mark.parametrize("pages", [10, 50])
def test_pdf_extraction_overhead(benchmark, mock_pdfplumber, pages):
    parser = DocumentParser()

    mock_pdf = MockPDF(pages)
    mock_pdfplumber.return_value = mock_pdf

    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.suffix", new_callable=MagicMock(return_value=".pdf")
    ):

        def op():
            return parser.parse_document("dummy.pdf", extract_images=True)

        benchmark.pedantic(op, iterations=5, rounds=5)


def test_python_ast_parsing(benchmark):
    """
    Measures performance of Python AST analysis.
    """
    parser = CodeParser()

    code_lines = []
    for i in range(200):
        code_lines.append(f"import module_{i}")
        code_lines.append(f"def function_{i}(arg):")
        code_lines.append(f"    '''Docstring for function {i}'''")
        code_lines.append(f"    return arg + {i}")
        code_lines.append(f"class Class_{i}:")
        code_lines.append(f"    pass")

    code_content = "\n".join(code_lines)

    with patch(
        "builtins.open", side_effect=lambda *args, **kwargs: io.StringIO(code_content)
    ), patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.suffix", new_callable=MagicMock(return_value=".py")
    ):

        def op():
            return parser.parse_code("dummy.py")

        benchmark.pedantic(op, iterations=5, rounds=5)
