import importlib.abc
import importlib.machinery
import os
import sys
import tempfile
import uuid
from unittest.mock import patch

import numpy as np
import pytest

# Import interception

HEAVY_LIBS = {
    "pdfplumber",
    "docx",
    "pptx",
    "openpyxl",
    "pandas",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "lxml",
    "pytesseract",
    "networkx",
    "chardet",
    "langdetect",
    "neo4j",
    "weaviate",
    "qdrant_client",
    "sentence_transformers",
    "transformers",
    "fastembed",
    "spacy",
    "thinc",
    "torch",
    "matplotlib",
    "umap",
    "pynndescent",
    "fireworks",
    "fireworks.client",
    "docling",
    "docling.document_converter",
    "docling.backend",
    "docling_core",
    "docling_core.types",
    "instructor",
    "instructor.processing",
    "instructor.core",
    "instructor.providers",
    "instructor.providers.fireworks",
    "pyarrow",
    "arrow",
    "pa",
}


class MockMeta(type):
    """Metaclass that only claims RobustMocks as instances."""

    def __instancecheck__(cls, instance):
        return hasattr(instance, "_is_robust_mock")

    def __subclasscheck__(cls, subclass):
        return True


def create_mock_class(full_name: str):
    return MockMeta(
        full_name.split(".")[-1],
        (object,),
        {
            "__module__": ".".join(full_name.split(".")[:-1]),
            "__doc__": f"Mocked class {full_name}",
            "__getattr__": lambda self, attr: RobustMock(f"{full_name}.{attr}"),
            "__call__": lambda self, *args, **kwargs: RobustMock(full_name),
            "__init__": lambda self, *args, **kwargs: None,
            "__repr__": lambda self: f"<MockClass {full_name}>",
        },
    )


class RobustMock:
    def __init__(self, name: str = "mock"):
        self.__name__ = name
        self.__version__ = "9.9.9"
        self._is_robust_mock = True
        self.__path__ = []
        self.__file__ = "mock_file.py"
        self.__all__ = []

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        full_name = f"{self.__name__}.{name}"
        
        # Special handling for common PIL patterns
        if self.__name__.endswith("Image") and name == "Image":
            return create_mock_class(full_name)
        elif self.__name__.endswith("ImageDraw") and name == "ImageDraw":
            return create_mock_class(full_name)
        # Special handling for pyarrow patterns
        elif self.__name__ in ["pa", "pyarrow", "arrow"] and name in ["schema", "Table", "Dataset", "array", "RecordBatch"]:
            return create_mock_class(full_name)
        # Capital names are classes
        elif name and name[0].isupper():
            return create_mock_class(full_name)
        return RobustMock(full_name)

    def __call__(self, *args, **kwargs):
        return RobustMock(self.__name__)

    def __iter__(self):
        return iter([])

    def __getitem__(self, item):
        return RobustMock(f"{self.__name__}[{item}]")

    def __len__(self):
        return 0

    def __bool__(self):
        return True

    def __hash__(self):
        return id(self)

    def __repr__(self):
        return f"<RobustMock {self.__name__}>"


class MockLoader(importlib.abc.Loader):
    def create_module(self, spec):
        mock_module = RobustMock(spec.name)
        mock_module.__spec__ = spec
        mock_module.__loader__ = self
        mock_module.__package__ = spec.parent
        return mock_module

    def exec_module(self, module):
        pass


class MockFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        # Check for exact matches first
        if fullname in HEAVY_LIBS:
            return importlib.machinery.ModuleSpec(fullname, MockLoader())
        
        # Check for prefix matches (e.g., PIL.Image, PIL.ImageDraw)
        for lib in HEAVY_LIBS:
            if fullname.startswith(lib + "."):
                return importlib.machinery.ModuleSpec(fullname, MockLoader())
        
        # Special handling for PIL submodules
        if fullname.startswith("PIL."):
            return importlib.machinery.ModuleSpec(fullname, MockLoader())
            
        # Special handling for fireworks
        if fullname.startswith("fireworks."):
            return importlib.machinery.ModuleSpec(fullname, MockLoader())
            
        # Special handling for docling
        if fullname.startswith("docling"):
            return importlib.machinery.ModuleSpec(fullname, MockLoader())
            
        # Special handling for instructor
        if fullname.startswith("instructor"):
            return importlib.machinery.ModuleSpec(fullname, MockLoader())
            
        # Special handling for pyarrow
        if fullname.startswith("pyarrow") or fullname.startswith("arrow"):
            return importlib.machinery.ModuleSpec(fullname, MockLoader())
            
        return None


if os.getenv("BENCHMARK_REAL_LIBS") != "1":
    if not any(isinstance(f, MockFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, MockFinder())
    
    # Special handling for 'pa' alias that's commonly used for pyarrow
    if "pa" not in sys.modules:
        sys.modules["pa"] = RobustMock("pa")
    
    # Pre-emptively create a mock arrow_exporter module to prevent import errors
    # This must happen BEFORE any veritasreason.export imports
    import types
    mock_arrow_module = types.ModuleType('veritasreason.export.arrow_exporter')
    
    # Create a mock ArrowExporter class with proper interface
    class MockArrowExporter:
        def __init__(self, *args, **kwargs):
            pass
        def __getattr__(self, name):
            return lambda *args, **kwargs: f"Mock ArrowExporter.{name}"
    
    mock_arrow_module.ArrowExporter = MockArrowExporter
    mock_arrow_module.ENTITY_SCHEMA = RobustMock("ENTITY_SCHEMA")
    mock_arrow_module.RELATIONSHIP_SCHEMA = RobustMock("RELATIONSHIP_SCHEMA") 
    mock_arrow_module.METADATA_SCHEMA = RobustMock("METADATA_SCHEMA")
    mock_arrow_module.pa = RobustMock("pa")
    
    # Inject the mock module into sys.modules
    sys.modules["veritasreason.export.arrow_exporter"] = mock_arrow_module

# Infrastructure and Data Fixtures


class NullTracker:
    def start_tracking(self, *args, **kwargs):
        return "dummy_id"

    def update_tracking(self, *args, **kwargs):
        pass

    def stop_tracking(self, *args, **kwargs):
        pass

    def register_pipeline_modules(self, *args, **kwargs):
        pass

    def clear_pipeline_context(self, *args, **kwargs):
        pass

    def update_progress(self, *args, **kwargs):
        pass

    def update_progress_batch(self, *args, **kwargs):
        pass

    @property
    def enabled(self):
        return False

    @enabled.setter
    def enabled(self, value):
        pass


@pytest.fixture(autouse=True)
def kill_io_overhead():
    tracker = NullTracker()
    with patch("veritasreason.utils.logging.get_logger"), patch(
        "veritasreason.utils.progress_tracker.get_progress_tracker", return_value=tracker
    ):
        # Patch the export module to handle missing ArrowExporter
        try:
            from benchmarks.export.arrow_exporter import ArrowExporter, ENTITY_SCHEMA, RELATIONSHIP_SCHEMA, METADATA_SCHEMA
            mock_arrow_module = RobustMock("veritasreason.export.arrow_exporter")
            mock_arrow_module.ArrowExporter = ArrowExporter
            mock_arrow_module.ENTITY_SCHEMA = ENTITY_SCHEMA
            mock_arrow_module.RELATIONSHIP_SCHEMA = RELATIONSHIP_SCHEMA
            mock_arrow_module.METADATA_SCHEMA = METADATA_SCHEMA
        except ImportError:
            mock_arrow_module = RobustMock("veritasreason.export.arrow_exporter")
        
        with patch.dict('sys.modules', {
            'veritasreason.export.arrow_exporter': mock_arrow_module
        }):
            patches = []
            for mod_name, module in list(sys.modules.items()):
                if mod_name.startswith("veritasreason.") and hasattr(
                    module, "get_progress_tracker"
                ):
                    p = patch.object(module, "get_progress_tracker", return_value=tracker)
                    patches.append(p)
            for p in patches:
                p.start()
            yield
            for p in patches:
                p.stop()


class MockVectorStore:
    def __init__(self, dim=384):
        self.dim = dim

    def embed(self, text: str):
        return np.random.rand(self.dim).astype(np.float32)

    def store_vectors(self, vectors, metadata):
        pass

    def search(self, query, limit=5):
        return [
            {"id": str(uuid.uuid4()), "score": 0.9, "content": "test", "metadata": {}}
            for _ in range(limit)
        ]


@pytest.fixture
def mock_vector_store():
    return MockVectorStore()


@pytest.fixture
def generate_graph_data():
    BASE_NS = "http://veritasreason.example.org/resource/"
    PRED_NS = "http://veritasreason.example.org/predicate/"

    def _gen(n_nodes: int = 100, avg_degree: int = 4):
        nodes = [
            {
                "id": f"{BASE_NS}node/{i}",
                "type": "Entity",
                "properties": {"label": f"Node {i}"},
            }
            for i in range(n_nodes)
        ]
        edges = [
            {
                "source_id": f"{BASE_NS}node/{i}",
                "target_id": f"{BASE_NS}node/{(i+1)%n_nodes}",
                "type": f"{PRED_NS}conn",
                "properties": {"w": 1.0},
            }
            for i in range(n_nodes)
        ]
        return nodes, edges

    return _gen


@pytest.fixture
def populated_context_graph(generate_graph_data):
    from veritasreason.context.context_graph import ContextGraph

    def _create(n_nodes=1000):
        g = ContextGraph()
        nodes, edges = generate_graph_data(n_nodes)
        g.add_nodes(nodes)
        g.add_edges(edges)
        return g

    return _create


@pytest.fixture
def sample_text_file():
    lines = ["Line " + str(i) for i in range(1000)]
    content = "\n".join(lines)
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".txt", encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    yield tmp_path
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


@pytest.fixture
def long_text_string():
    return "benchmark " * 5000
