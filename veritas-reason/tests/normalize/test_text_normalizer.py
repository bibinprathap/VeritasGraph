import unittest
from unittest.mock import MagicMock, patch

from veritasreason.normalize.text_normalizer import (
    SpecialCharacterProcessor,
    TextNormalizer,
    UnicodeNormalizer,
    WhitespaceNormalizer,
)


class TestTextNormalizer(unittest.TestCase):
    """
    Test suite for the TextNormalizer class.
    """

    def setUp(self):
        """Set up mocks"""

        self.logger_patcher = patch("veritasreason.normalize.text_normalizer.get_logger")
        self.tracker_patcher = patch(
            "veritasreason.normalize.text_normalizer.get_progress_tracker"
        )
        self.cleaner_patcher = patch("veritasreason.normalize.text_normalizer.TextCleaner")

        self.mock_logger = self.logger_patcher.start()
        self.mock_tracker = self.tracker_patcher.start()
        self.mock_cleaner_cls = self.cleaner_patcher.start()

        # config mocks
        self.mock_tracker_instance = MagicMock()
        self.mock_tracker_instance.enabled = True
        self.mock_tracker.return_value = self.mock_tracker_instance

        self.mock_cleaner_instance = MagicMock()
        self.mock_cleaner_cls.return_value = self.mock_cleaner_instance

        # init normalization

        self.normalizer = TextNormalizer()

    def tearDown(self):
        """Stop all patches."""
        self.logger_patcher.stop()
        self.tracker_patcher.stop()
        self.cleaner_patcher.stop()

    def test_init(self):
        """Test initialization"""
        self.mock_cleaner_cls.assert_called_once()
        self.assertTrue(hasattr(self.normalizer, "unicode_normalizer"))
        self.assertTrue(hasattr(self.normalizer, "whitespace_normalizer"))
        self.assertTrue(hasattr(self.normalizer, "special_char_processor"))

        self.assertTrue(self.normalizer.progress_tracker.enabled)

    def test_normalize_text_basic(self):
        """Test basic text normalization"""
        text = "Hello World"
        result = self.normalizer.normalize_text(text)
        self.assertEqual(result, "Hello World")

        # progress bar insurance

        self.mock_tracker_instance.start_tracking.assert_called()
        self.mock_tracker_instance.stop_tracking.assert_called_with(
            self.mock_tracker_instance.start_tracking.return_value, status="completed"
        )

    def test_normalize_empty_string(self):
        """Test 'nothingness'"""
        self.assertEqual(self.normalizer.normalize_text(""), "")
        self.assertEqual(self.normalizer.normalize_text(None), "")

    def test_normalize_case_options(self):
        """Test case normalization"""
        text = "HeLLo WoRLd"

        self.assertEqual(
            self.normalizer.normalize_text(text, case="lower"), "hello world"
        )

        self.assertEqual(
            self.normalizer.normalize_text(text, case="upper"), "HELLO WORLD"
        )
        self.assertEqual(
            self.normalizer.normalize_text(text, case="title"), "Hello World"
        )

        # preserve test ---- default

        self.assertEqual(
            self.normalizer.normalize_text(text, case="preserve"), "HeLLo WoRLd"
        )

    def test_normalize_delegation(self):
        """Verify that normalize_text correctly delegates to subcomponents."""

        self.normalizer.unicode_normalizer.normalize_unicode = MagicMock(
            return_value="U"
        )
        self.normalizer.whitespace_normalizer.normalize_whitespace = MagicMock(
            return_value="W"
        )
        self.normalizer.special_char_processor.process_special_chars = MagicMock(
            return_value="S"
        )

        result = self.normalizer.normalize_text(
            "input",
            unicode_form="NFD",
            line_break_type="windows",
            normalize_diacritics=True,
        )

        self.normalizer.unicode_normalizer.normalize_unicode.assert_called_with(
            "input", form="NFD"
        )
        self.normalizer.whitespace_normalizer.normalize_whitespace.assert_called_with(
            "U", line_break_type="windows"
        )
        self.normalizer.special_char_processor.process_special_chars.assert_called_with(
            "W", normalize_diacritics=True
        )

        self.assertEqual(result, "S")

    def test_clean_text(self):
        """Test delegation to TextCleaner"""
        text = "<html>body</html>"
        self.mock_cleaner_instance.clean.return_value = "body"
        result = self.normalizer.clean_text(text, remove_html=True)

        self.mock_cleaner_instance.clean.assert_called_with(text, remove_html=True)
        self.assertEqual(result, "body")

    def test_standardize_format(self):
        """Test format standardization option"""
        text = "  one   two  "

        self.assertEqual(
            self.normalizer.standardize_format(text, format_type="compact"), "one two"
        )

        self.assertEqual(
            self.normalizer.standardize_format(text, format_type="preserve"),
            "one   two",
        )

    def test_process_batch(self):
        """Test batch processing"""
        texts = ["TEST 1", "Test 2"]
        results = self.normalizer.process_batch(texts, case="lower")
        self.assertEqual(results, ["test 1", "test 2"])

    def test_normalize_overloaded_method(self):
        """Test generic normalize method"""
        self.assertEqual(self.normalizer.normalize("TEST", case="lower"), "test")

        # dict

        docs = [
            {"id": 1, "content": "DOC 1"},
            {"id": 2, "content": "DOC 2", "other": "meta"},
            {"id": 3, "nocontent": "skip"},
        ]

        results = self.normalizer.normalize(docs, case="lower")

        self.assertEqual(results[0]["content"], "doc 1")
        self.assertEqual(results[1]["content"], "doc 2")
        self.assertEqual(results[1]["other"], "meta")

        self.assertIn("skip", results[2])

    def test_normalize_error_handling(self):
        """Test error handling"""

        self.normalizer.unicode_normalizer.normalize_unicode = MagicMock(
            side_effect=Exception("Test Error")
        )

        with self.assertRaises(Exception):
            self.normalizer.normalize_text("input")
        self.mock_tracker_instance.stop_tracking.assert_called_with(
            self.mock_tracker_instance.start_tracking.return_value,
            status="failed",
            message="Test Error",
        )


class TestUnicodeNormalizer(unittest.TestCase):
    """Test suite for UniCodeNormalizer class"""

    def setUp(self):
        self.normalizer = UnicodeNormalizer()

    def test_normalize_unicode_forms(self):
        """Test diff unicode normalization forms"""

        text_nfc = "\u00e9"
        text_nfd = "\u0065\u0301"

        self.assertEqual(self.normalizer.normalize_unicode(text_nfd, "NFC"), text_nfc)
        self.assertEqual(self.normalizer.normalize_unicode(text_nfc, "NFD"), text_nfd)

    def test_normalize_none(self):
        """Test empty input"""

        self.assertEqual(self.normalizer.normalize_unicode(None), "")
        self.assertEqual(self.normalizer.normalize_unicode(""), "")

    def test_normalize_failure_fallback(self):
        """Test that it returns og text if unicode fails"""

        with patch("unicodedata.normalize", side_effect=Exception("Boom")):
            result = self.normalizer.normalize_unicode("test")
            self.assertEqual(result, "test")

    def test_handle_encoding(self):
        """Test encoding handling"""
        self.assertEqual(self.normalizer.handle_encoding("test", "utf-8"), "test")

        # bytes in

        byte_data = "test".encode("utf-8")
        self.assertEqual(self.normalizer.handle_encoding(byte_data, "utf-8"), "test")

        # cross encoding

        latin_bytes = "café".encode("latin-1")
        result = self.normalizer.handle_encoding(latin_bytes, "latin-1", "utf-8")
        self.assertEqual(result, "café")

        # broken bites

        bad_bytes = b"\xff"
        self.assertIsInstance(self.normalizer.handle_encoding(bad_bytes, "utf-8"), str)

    def test_process_special_chars_replacement(self):
        """Test unicode character replacement"""
        input_text = "\u2018single\u2019 \u201Cdouble\u201D \u2013 \u2014 \u2026"
        expected = "'single' \"double\" - -- ..."
        self.assertEqual(self.normalizer.process_special_chars(input_text), expected)


class TestWhitespaceNormalizer(unittest.TestCase):
    """Test suite for WhitespaceNormalizer class"""

    def setUp(self):
        self.normalizer = WhitespaceNormalizer()

    def test_normalize_whitespace_basic(self):
        """Test basic whitespace cleanup"""
        text = "Hello   World\tTest"

        self.assertEqual(self.normalizer.normalize_whitespace(text), "Hello World Test")

    def test_handle_line_breaks(self):
        """Test line break conversion"""
        text = "Row1\r\nRow2\rRow3\n"

        self.assertEqual(
            self.normalizer.handle_line_breaks(text, "unix"), "Row1\nRow2\nRow3\n"
        )

        res_windows = self.normalizer.handle_line_breaks("Row1\nRow2", "windows")
        self.assertEqual(res_windows, "Row1\r\nRow2")

    def test_process_indentation(self):
        """Test indentation conversion"""

        spaces = "    Code"
        self.assertEqual(self.normalizer.process_indentation(spaces, "tabs"), "\tCode")

        tabs = "\tCode"
        self.assertEqual(
            self.normalizer.process_indentation(tabs, "spaces"), "    Code"
        )


class TestSpecialCharacterProcessor(unittest.TestCase):
    """Test suite for SpecialCharacterProcessor class."""

    def setUp(self):
        self.processor = SpecialCharacterProcessor()

    def test_normalize_punctuation(self):
        """Test punctuation cleanup"""

        text = "“Hello” ‘World’ – …"
        expected = "\"Hello\" 'World' - ..."

        self.assertEqual(self.processor.normalize_punctuation(text), expected)

    def test_process_diacritics_remove(self):
        """Test removing diacritics"""

        text = "Crème Brûlée"
        expected = "Creme Brulee"
        result = self.processor.process_diacritics(text, remove_diacritics=True)

        self.assertEqual(result, expected)

    def test_process_diacritics_normalize(self):
        """Test normalizing diacritics"""

        text = "e\u0301"  # NFD ~~ this wastes memory

        expected = "\u00e9"  # should become NFC which is uh precomposed single char
        result = self.processor.process_diacritics(text, remove_diacritics=False)
        self.assertEqual(result, expected)

    def test_process_special_chars_integration(self):
        """Test the main processing method integration"""
        text = "“Crème”"

        result = self.processor.process_special_chars(
            text, normalize_diacritics=True, remove_diacritics=True
        )
        self.assertEqual(result, '"Creme"')


if __name__ == "__main__":
    unittest.main()
