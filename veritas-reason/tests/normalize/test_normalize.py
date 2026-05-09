import unittest
from veritasreason.normalize.text_normalizer import TextNormalizer
from veritasreason.normalize.text_cleaner import TextCleaner

class TestTextNormalizer(unittest.TestCase):

    def setUp(self):
        self.normalizer = TextNormalizer()

    def test_normalize_text_case(self):
        text = "Hello World"
        self.assertEqual(self.normalizer.normalize_text(text, case="lower"), "hello world")
        self.assertEqual(self.normalizer.normalize_text(text, case="upper"), "HELLO WORLD")
        self.assertEqual(self.normalizer.normalize_text(text, case="preserve"), "Hello World")
        self.assertEqual(self.normalizer.normalize_text(text, case="title"), "Hello World")

    def test_normalize_unicode_integration(self):
        # e + combining acute accent
        text = "e\u0301" 
        # normalized via normalize_text (defaults to NFC)
        normalized = self.normalizer.normalize_text(text, unicode_form="NFC")
        self.assertEqual(normalized, "\u00e9")

    def test_process_special_chars_integration(self):
        text = "Hello\u2013World" # En dash
        # normalize_text calls process_special_chars internally
        processed = self.normalizer.normalize_text(text)
        self.assertEqual(processed, "Hello-World")

    def test_component_access(self):
        # Test components directly if needed
        text = "e\u0301"
        normalized = self.normalizer.unicode_normalizer.normalize_unicode(text, form="NFC")
        self.assertEqual(normalized, "\u00e9")

class TestTextCleaner(unittest.TestCase):

    def setUp(self):
        self.cleaner = TextCleaner()

    def test_clean_html(self):
        text = "<p>Hello <b>World</b></p>"
        cleaned = self.cleaner.clean(text, remove_html=True)
        self.assertEqual(cleaned.strip(), "Hello World")

    def test_clean_whitespace(self):
        text = "Hello    World\n\n"
        cleaned = self.cleaner.clean(text, normalize_whitespace=True, remove_html=False)
        self.assertEqual(cleaned, "Hello World")

    def test_clean_unicode(self):
        text = "e\u0301"
        cleaned = self.cleaner.clean(text, normalize_unicode=True)
        self.assertEqual(cleaned, "\u00e9")

if __name__ == "__main__":
    unittest.main()
