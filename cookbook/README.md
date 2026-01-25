# 📚 VeritasGraph Cookbook

Interactive notebooks demonstrating VeritasGraph features and testing.

## Notebooks

| Notebook | Description |
|----------|-------------|
| [test_hierarchical_tree_accuracy.ipynb](test_hierarchical_tree_accuracy.ipynb) | Test the accuracy of hierarchical tree extraction |

## 🌳 Hierarchical Tree Accuracy Testing

The `test_hierarchical_tree_accuracy.ipynb` notebook provides comprehensive accuracy testing for VeritasGraph's tree extraction feature:

### What It Tests

1. **TOC Detection** - Can we correctly identify Table of Contents pages?
2. **Structure Extraction** - Are section numbers (1, 1.1, 1.1.2) correctly parsed?
3. **Parent-Child Relationships** - Are hierarchical links accurate?
4. **Page Range Inference** - Do sections span the correct pages?
5. **Tree Navigation** - Can we navigate the tree structure?

### Metrics Measured

| Metric | Description | Target |
|--------|-------------|--------|
| Section Recall | % of expected sections found | >90% |
| Structure Accuracy | Correct hierarchical numbers | >95% |
| Parent-Child Accuracy | Correct relationships | >90% |
| Page Range Accuracy | Correct page assignments | >85% |

### Running the Tests

```bash
# From the VeritasGraph directory
cd cookbook
jupyter notebook test_hierarchical_tree_accuracy.ipynb
```

Or run in VS Code:
1. Open the notebook
2. Select a Python kernel with VeritasGraph installed
3. Run all cells

### Adding Custom Test Cases

You can add your own test cases by modifying the `TEST_CASES` list:

```python
TestCase(
    name="Your Document Type",
    description="Description of the document structure",
    expected_toc_pages=[2, 3],  # Pages containing TOC
    total_pages=30,
    expected_sections=[
        {"structure": "1", "title": "First Chapter", "level": 1, "parent_structure": "root", "start_page": 4},
        {"structure": "1.1", "title": "First Section", "level": 2, "parent_structure": "1", "start_page": 5},
        # ... more sections
    ],
)
```

### Testing with Real PDFs

The notebook includes an optional section for testing with real PDF documents:

```python
from veritasgraph import VisionRAGPipeline

pipeline = VisionRAGPipeline(extract_tree=True)
doc = pipeline.ingest_pdf("your_document.pdf")

# View extracted tree
print(pipeline.get_document_tree(doc.document_id))
```

## Requirements

```bash
pip install veritasgraph pillow jupyter
```

## Output

The notebook exports results to `tree_extraction_accuracy_results.json` for tracking accuracy over time.

---

**VeritasGraph v0.2.0** | The Power of PageIndex's Tree + The Flexibility of a Graph
