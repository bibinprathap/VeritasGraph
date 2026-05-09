import pytest

from veritasreason.context.agent_memory import AgentMemory
from veritasreason.context.context_retriever import ContextRetriever


@pytest.fixture
def retriever_setup(mock_vector_store, populated_context_graph):
    """
    Sets up a fully configured retriever
    """
    kg = populated_context_graph(n_nodes=1000)

    memory = AgentMemory(vector_store=mock_vector_store, knowledge_graph=kg)

    retriever = ContextRetriever(
        memory_store=memory,
        knowledge_graph=kg,
        vector_store=mock_vector_store,
        hybrid_alpha=0.5,
    )

    return retriever
