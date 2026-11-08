"""VeritasGraph core: shared graph store, ontology, compile pipeline and governance.

The GraphRAG engine itself lives in :mod:`studio_api.graphrag_engine` (kept there
for API compatibility); everything it needs to be durable, shared between the
Studio and MCP processes, and governed lives in this package.
"""

__version__ = "0.2.0"
