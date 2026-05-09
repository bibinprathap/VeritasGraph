import unittest
from datetime import datetime, date, timedelta, timezone
from veritasreason.normalize.date_normalizer import (
    DateNormalizer,
    TimeZoneNormalizer,
    RelativeDateProcessor,
    TemporalExpressionParser
)

class TestDateNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = DateNormalizer()

    def test_normalize_date_iso(self):
        # Test ISO8601 parsing
        self.assertEqual(
            self.normalizer.normalize_date("2023-01-01", format="date"),
            "2023-01-01"
        )
        self.assertEqual(
            self.normalizer.normalize_date("2023-01-01T12:00:00", format="ISO8601"),
            "2023-01-01T12:00:00+00:00"
        )

    def test_normalize_date_relative(self):
        # Test relative date parsing (e.g., "today", "yesterday")
        # Note: These depend on current date, so we might need to mock datetime if strictly testing logic,
        # but for now we'll assume the relative processor uses current time.
        # We can check if it returns a valid ISO date string.
        today = datetime.now(timezone.utc).date().isoformat()
        self.assertEqual(
            self.normalizer.normalize_date("today", format="date"),
            today
        )

    def test_normalize_timezone(self):
        # Test timezone conversion
        # "2023-01-01T12:00:00+01:00" -> UTC should be "2023-01-01T11:00:00+00:00"
        normalized = self.normalizer.normalize_date(
            "2023-01-01T12:00:00+01:00", 
            timezone="UTC"
        )
        self.assertEqual(normalized, "2023-01-01T11:00:00+00:00")

    def test_parse_temporal_expression(self):
        # Test range parsing
        result = self.normalizer.parse_temporal_expression("from 2023-01-01 to 2023-01-31")
        self.assertIsNotNone(result.get("range"))

class TestTimeZoneNormalizer(unittest.TestCase):
    def setUp(self):
        self.tz_normalizer = TimeZoneNormalizer()

    def test_normalize_timezone_obj(self):
        dt = datetime(2023, 1, 1, 12, 0, 0)
        # Assuming default is UTC if not specified or naive
        normalized = self.tz_normalizer.normalize_timezone(dt, "UTC")
        # Check offset instead of object identity
        self.assertEqual(normalized.tzinfo.utcoffset(normalized), timezone.utc.utcoffset(None))

class TestRelativeDateProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = RelativeDateProcessor()

    def test_process_relative_expression(self):
        # "3 days ago"
        dt = self.processor.process_relative_expression("3 days ago")
        self.assertIsInstance(dt, datetime)
        # Roughly check delta
        # Use datetime.now() since result is naive
        diff = datetime.now() - dt
        self.assertTrue(timedelta(days=2, hours=23) < diff < timedelta(days=3, hours=1))

if __name__ == "__main__":
    unittest.main()
