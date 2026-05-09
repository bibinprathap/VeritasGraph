import unittest
from datetime import datetime
from veritasreason.normalize.data_cleaner import (
    DataCleaner,
    DuplicateDetector,
    DataValidator,
    MissingValueHandler,
    DuplicateGroup,
    ValidationResult,
)


class TestDataCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = DataCleaner()
        self.dataset = [
            {"id": 1, "name": "John Doe", "age": 30, "email": "john@example.com"},
            {"id": 2, "name": "Jane Smith", "age": 25, "email": "jane@example.com"},
            {"id": 3, "name": "John Doe", "age": 30, "email": "john@example.com"},  # Duplicate
            {"id": 4, "name": "Bob", "age": None, "email": "bob@example.com"},  # Missing age
        ]

    def test_clean_data_comprehensive(self):
        # Test full cleaning pipeline
        cleaned = self.cleaner.clean_data(
            self.dataset,
            remove_duplicates=True,
            duplicate_criteria={"key_fields": ["name", "age", "email"]},
            validate=False,  # Skip validation for this simple test
            handle_missing=True,
            missing_strategy="remove"
        )
        
        # Expecting:
        # id 3 removed (duplicate of 1)
        # id 4 removed (missing age)
        # Remaining: id 1 and id 2
        self.assertEqual(len(cleaned), 2)
        ids = [r["id"] for r in cleaned]
        self.assertIn(1, ids)
        self.assertIn(2, ids)
        self.assertNotIn(3, ids)
        self.assertNotIn(4, ids)

    def test_clean_data_fill_missing(self):
        cleaned = self.cleaner.clean_data(
            self.dataset,
            remove_duplicates=True,
            duplicate_criteria={"key_fields": ["name", "age", "email"]},
            validate=False,
            handle_missing=True,
            missing_strategy="fill",
            fill_value=0
        )
        
        # Expecting:
        # id 3 removed (duplicate)
        # id 4 kept (age filled with 0)
        self.assertEqual(len(cleaned), 3)
        ids = [r["id"] for r in cleaned]
        self.assertIn(1, ids)
        self.assertIn(2, ids)
        self.assertIn(4, ids)
        
        # Check filled value
        bob = next(r for r in cleaned if r["id"] == 4)
        self.assertEqual(bob["age"], 0)


class TestDuplicateDetector(unittest.TestCase):
    def setUp(self):
        self.detector = DuplicateDetector(similarity_threshold=0.8)
        self.dataset = [
            {"id": 1, "name": "John Doe", "city": "New York"},
            {"id": 2, "name": "Jane Smith", "city": "Los Angeles"},
            {"id": 3, "name": "John Doe", "city": "New York"},  # Exact duplicate of 1
            {"id": 4, "name": "Jon Doe", "city": "New York"},   # Similar to 1
            {"id": 5, "name": "Alice", "city": "Chicago"},
        ]

    def test_detect_exact_duplicates(self):
        duplicates = self.detector.detect_duplicates(
            self.dataset, 
            threshold=1.0,
            key_fields=["name", "city"]
        )
        # Should find group [id 1, id 3]
        self.assertEqual(len(duplicates), 1)
        group = duplicates[0]
        self.assertEqual(len(group.records), 2)
        ids = {r["id"] for r in group.records}
        self.assertEqual(ids, {1, 3})
        self.assertEqual(group.similarity_score, 1.0)

    def test_detect_fuzzy_duplicates(self):
        # "John Doe" vs "Jon Doe" similarity
        # "New York" vs "New York" is 1.0
        # Average similarity should be high
        duplicates = self.detector.detect_duplicates(
            self.dataset, 
            threshold=0.8,
            key_fields=["name", "city"]
        )
        
        # Expecting group for John Doe variants
        # Depending on string similarity implementation, 1, 3, and 4 might be grouped
        # id 1 and 3 are identical. id 4 is similar.
        
        # Let's check groups
        # We might get one big group or multiple.
        # Since the detector groups greedily:
        # 1 matches 3 (score 1.0) -> group [1, 3]
        # 1 matches 4?
        # Similarity("John Doe", "Jon Doe") -> "john doe" vs "jon doe"
        # Intersection: j,o,n, ,d,e (6 chars). Union: j,o,h,n, ,d,e (7 chars). 6/7 = 0.857
        # Similarity("New York", "New York") = 1.0
        # Avg = (0.857 + 1.0) / 2 = 0.928 > 0.8
        # So 4 should be in the group too.
        
        self.assertTrue(len(duplicates) >= 1)
        # Find group containing id 1
        group = next((g for g in duplicates if any(r["id"] == 1 for r in g.records)), None)
        self.assertIsNotNone(group)
        ids = {r["id"] for r in group.records}
        self.assertIn(1, ids)
        self.assertIn(3, ids)
        self.assertIn(4, ids)

    def test_calculate_similarity(self):
        r1 = {"a": "hello", "b": 10}
        r2 = {"a": "hello", "b": 10}
        self.assertEqual(self.detector.calculate_similarity(r1, r2), 1.0)
        
        r3 = {"a": "hallo", "b": 10}
        # "hello" vs "hallo": intersect(h,l,o) union(h,e,l,a,o).
        # h,e,l,l,o -> set(h,e,l,o)
        # h,a,l,l,o -> set(h,a,l,o)
        # inter: h,l,o (3). union: h,e,l,o,a (5). 3/5 = 0.6
        # b: 10 vs 10 = 1.0
        # avg = (0.6 + 1.0) / 2 = 0.8
        self.assertAlmostEqual(self.detector.calculate_similarity(r1, r3), 0.8)

    def test_resolve_duplicates_keep_first(self):
        group = DuplicateGroup(
            records=[
                {"id": 1, "val": "A", "extra": None},
                {"id": 2, "val": "A", "extra": "data"}
            ],
            similarity_score=1.0,
            canonical_record={"id": 1, "val": "A", "extra": None}
        )
        resolved = self.detector.resolve_duplicates([group], strategy="keep_first")
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["id"], 1)

    def test_resolve_duplicates_merge(self):
        group = DuplicateGroup(
            records=[
                {"id": 1, "val": "A", "extra": None},
                {"id": 2, "val": "A", "extra": "data"}
            ],
            similarity_score=1.0,
            canonical_record={"id": 1, "val": "A", "extra": None}
        )
        resolved = self.detector.resolve_duplicates([group], strategy="merge")
        self.assertEqual(len(resolved), 1)
        # Should have taken 'extra' from second record since first was None
        self.assertEqual(resolved[0]["extra"], "data")
        self.assertEqual(resolved[0]["val"], "A")


class TestDataValidator(unittest.TestCase):
    def setUp(self):
        self.validator = DataValidator()
        self.schema = {
            "fields": {
                "name": {"type": "str", "required": True},
                "age": {"type": "int", "required": False},
                "tags": {"type": "list", "required": False}
            }
        }

    def test_validate_valid_record(self):
        record = {"name": "Test", "age": 20, "tags": ["a", "b"]}
        result = self.validator.validate_record(record, self.schema)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)

    def test_validate_missing_required(self):
        record = {"age": 20} # Missing name
        result = self.validator.validate_record(record, self.schema)
        self.assertFalse(result.valid)
        self.assertTrue(any(e["field"] == "name" for e in result.errors))

    def test_validate_wrong_type(self):
        record = {"name": "Test", "age": "twenty"} # age should be int
        result = self.validator.validate_record(record, self.schema)
        self.assertFalse(result.valid)
        self.assertTrue(any(e["field"] == "age" for e in result.errors))

    def test_check_data_types(self):
        self.assertTrue(self.validator.check_data_types("test", str))
        self.assertTrue(self.validator.check_data_types(123, int))
        self.assertTrue(self.validator.check_data_types(123, [str, int]))
        self.assertTrue(self.validator.check_data_types("123", ["str", "int"]))
        self.assertFalse(self.validator.check_data_types(123, str))


class TestMissingValueHandler(unittest.TestCase):
    def setUp(self):
        self.handler = MissingValueHandler()
        self.dataset = [
            {"a": 1, "b": 2},
            {"a": None, "b": 2},
            {"a": 3, "b": None},
            {"a": 10, "b": 20},
        ]

    def test_identify_missing_values(self):
        info = self.handler.identify_missing_values(self.dataset)
        self.assertEqual(info["total_records"], 4)
        self.assertEqual(info["missing_counts"]["a"], 1)
        self.assertEqual(info["missing_counts"]["b"], 1)

    def test_handle_missing_remove(self):
        cleaned = self.handler.handle_missing_values(self.dataset, strategy="remove")
        self.assertEqual(len(cleaned), 2)
        # Should keep only records with no missing values
        for r in cleaned:
            self.assertIsNotNone(r["a"])
            self.assertIsNotNone(r["b"])

    def test_handle_missing_fill(self):
        cleaned = self.handler.handle_missing_values(
            self.dataset, strategy="fill", fill_value=0
        )
        self.assertEqual(len(cleaned), 4)
        # Check filled values
        self.assertEqual(cleaned[1]["a"], 0)
        self.assertEqual(cleaned[2]["b"], 0)

    def test_handle_missing_impute_mean(self):
        # a: 1, 3, 10. Mean = 14/3 = 4.66
        # b: 2, 2, 20. Mean = 24/3 = 8.0
        cleaned = self.handler.handle_missing_values(
            self.dataset, strategy="impute", method="mean"
        )
        self.assertEqual(len(cleaned), 4)
        
        # Check imputed 'a' in record 1
        self.assertAlmostEqual(cleaned[1]["a"], 4.6666666, places=5)
        # Check imputed 'b' in record 2
        self.assertEqual(cleaned[2]["b"], 8.0)

    def test_handle_missing_impute_median(self):
        dataset = [
            {"a": 1}, {"a": 3}, {"a": 10}, {"a": None}
        ]
        # 1, 3, 10. Median = 3
        cleaned = self.handler.handle_missing_values(
            dataset, strategy="impute", method="median"
        )
        self.assertEqual(cleaned[3]["a"], 3)

    def test_handle_missing_impute_zero(self):
        dataset = [
            {"a": 1}, {"a": None}
        ]
        cleaned = self.handler.handle_missing_values(
            dataset, strategy="impute", method="zero"
        )
        self.assertEqual(cleaned[1]["a"], 0)


if __name__ == "__main__":
    unittest.main()
