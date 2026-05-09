import random
import string
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Data gen


@pytest.fixture
def generate_text_data():
    """Generates various types of text data."""

    def _gen(type="clean", length=100):
        if type == "clean":
            return "".join(random.choices(string.ascii_letters + " ", k=length))
        elif type == "html":
            tags = ["<div>", "<p>", "<span>", "<a>", "<b>", "<i>"]
            content = "".join(random.choices(string.ascii_letters + " ", k=length))
            return f"{random.choice(tags)}{content}{random.choice(tags).replace('<', '</')}"
        elif type == "unicode":
            chars = string.ascii_letters + "éàèùâêîôûçñ"
            return "".join(random.choices(chars, k=length))
        elif type == "dirty":
            chars = string.ascii_letters + " \t\n\r"
            return "".join(random.choices(chars, k=length))

    return _gen


@pytest.fixture
def generate_dataset():
    """Generates dataset for data cleaner."""

    def _gen(rows=100, duplicate_rate=0.0):
        base_rows = []
        unique_count = int(rows * (1 - duplicate_rate))

        for i in range(unique_count):
            base_rows.append(
                {
                    "id": i,
                    "name": f"Entity_{i}",
                    "email": f"user{i}@yahoo.com",
                    "value": random.random() * 100,
                    "category": random.choice(["A", "B", "C"]),
                }
            )

        final_dataset = base_rows.copy()
        while len(final_dataset) < rows:
            source = random.choice(base_rows)
            dup = source.copy()
            if random.random() > 0.5:
                dup["value"] = source["value"] + 0.001
            final_dataset.append(dup)

        random.shuffle(final_dataset)
        return final_dataset

    return _gen
