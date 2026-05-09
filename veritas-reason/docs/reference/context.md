# Context Module Reference

> **The intelligent brain for AI agents, providing memory, decision tracking, and knowledge organization with easy-to-use interfaces that make building smart agents simple and effective.**

---

## 🎯 Overview

The **Context Module** gives your AI agents the ability to **remember**, **learn**, and **make smarter decisions** through intelligent memory management and knowledge organization. It's designed to be both powerful for production use and simple enough for rapid development.

### Key Capabilities

<div class="grid cards" markdown>

-   :material-brain:{ .lg .middle } **Smart Memory**

    ---

    Human-like memory that stores conversations, learns from experience, and retrieves relevant information when needed.

-   :material-graph-outline:{ .lg .middle } **Decision Intelligence**

    ---

    Track decisions, learn from past choices, and make consistent, improving decisions over time.

-   :material-lightbulb:{ .lg .middle } **Easy-to-Use API**

    ---

    Simple methods that make complex features accessible without overwhelming complexity.

-   :material-search:{ .lg .middle } **Smart Retrieval**

    ---

    Find relevant information quickly using hybrid search that understands context and relationships.

-   :material-account-tree:{ .lg .middle } **Knowledge Organization**

    ---

    Build intelligent knowledge graphs that understand relationships and context.

-   :material-trending-up:{ .lg .middle } **Learning & Analytics**

    ---

    Get insights about agent performance, decision patterns, and knowledge growth.

-   :material-security:{ .lg .middle } **Production Ready**

    ---

    Scalable, reliable, and tested for real-world applications.

</div>

!!! tip "Perfect For"
    - **AI Agents** that need to remember conversations and learn from decisions
    - **Chatbots** that become smarter with every interaction
    - **Decision Systems** that need to track choices and learn from patterns
    - **Knowledge Management** that organizes information intelligently
    - **Production Applications** that require reliable, scalable solutions

---

## 🤖 AgentContext - Your Agent's Brain

The main interface that makes your agent intelligent. It handles memory, decisions, and knowledge organization automatically.

### Quick Start
```python
from veritasreason.context import AgentContext
from veritasreason.vector_store import VectorStore

# Create your intelligent agent
agent = AgentContext(vector_store=VectorStore(backend="inmemory", dimension=384))

# Your agent can now remember things
memory_id = agent.store("User asked about Python programming")
print(f"Agent remembered: {memory_id}")

# And find information when needed
results = agent.retrieve("Python tutorials")
print(f"Agent found {len(results)} relevant memories")
```

### Easy Decision Learning
```python
# Your agent learns from its decisions
decision_id = agent.record_decision(
    category="content_recommendation",
    scenario="User wants Python tutorial",
    reasoning="User mentioned being a beginner",
    outcome="recommended_basics",
    confidence=0.85
)

# Your agent can now find similar past decisions
similar_decisions = agent.find_precedents("Python tutorial", limit=3)
print(f"Agent found {len(similar_decisions)} similar past decisions")
```

### Getting Smarter Over Time
```python
# Enable all learning features
smart_agent = AgentContext(
    vector_store=vector_store,
    decision_tracking=True,    # Learn from decisions
    graph_expansion=True,      # Find related information
    advanced_analytics=True,   # Understand patterns
    kg_algorithms=True,        # Advanced analysis
    vector_store_features=True
)

# Get insights about your agent's learning
insights = smart_agent.get_context_insights()
print(f"Total decisions learned: {insights.get('total_decisions', 0)}")
print(f"Decision categories: {list(insights.get('categories', {}).keys())}")
```

### Core Methods

| Method | What It Does | When to Use |
|--------|-------------|------------|
| `store(content, ...)` | Remember information | Store conversations, facts, user preferences |
| `retrieve(query, ...)` | Find relevant memories | Search for information when needed |
| `record_decision(category, scenario, reasoning, outcome, confidence, ...)` | Learn from decisions | Track choices and improve over time |
| `find_precedents(scenario, category, ...)` | Find similar decisions | Make consistent choices based on experience |
| `get_context_insights()` | Understand performance | Get analytics about your agent |

### Advanced Features
```python
# Enable all features for maximum intelligence
agent = AgentContext(
    vector_store=vector_store,
    knowledge_graph=ContextGraph(advanced_analytics=True),
    decision_tracking=True,
    graph_expansion=True,
    advanced_analytics=True,
    kg_algorithms=True,
    vector_store_features=True
)

# Query with multi-hop reasoning (GraphRAG)
from veritasreason.llms import Groq
import os

llm = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))

result = agent.query_with_reasoning(
    query="What technologies work well together?",
    llm_provider=llm,
    max_hops=2
)

print(f"Response: {result['response']}")
print(f"Reasoning: {result['reasoning_path']}")
```

---

## 🏗️ ContextGraph - Knowledge Organization

When you need to organize complex information and understand relationships, ContextGraph helps you build intelligent knowledge networks.

### Easy Knowledge Graph Building
```python
from veritasreason.context import ContextGraph

# Create a knowledge graph
knowledge = ContextGraph(advanced_analytics=True)

# Add things you want to remember (nodes)
knowledge.add_node("Python", "language", properties={"popularity": "high"})
knowledge.add_node("Programming", "concept", properties={"type": "skill"})
knowledge.add_node("FastAPI", "framework", properties={"language": "Python"})

# Connect related things (edges)
knowledge.add_edge("Python", "Programming", "related_to")
knowledge.add_edge("Python", "FastAPI", "supports")
knowledge.add_edge("FastAPI", "Programming", "used_for")
```

### Easy Decision Management
```python
# Record decisions in your knowledge graph
from veritasreason.context.decision_models import Decision
from datetime import datetime

decision = Decision(
    decision_id="tech_choice_001",
    category="technology_choice",
    scenario="Framework selection for web API",
    reasoning="FastAPI provides better performance for Python APIs",
    outcome="selected_fastapi",
    confidence=0.92,
    timestamp=datetime.now(),
    decision_maker="system",
    metadata={"entities": ["Python", "FastAPI", "web_project"]}
)
knowledge.add_decision(decision)

# Or use the convenience method for quick decisions
decision_id = knowledge.add_decision_simple(
    category="technology_choice",
    scenario="Framework selection for web API",
    reasoning="FastAPI provides better performance for Python APIs",
    outcome="selected_fastapi",
    confidence=0.92,
    entities=["Python", "FastAPI", "web_project"]
)

# Find similar decisions easily
similar = knowledge.find_precedents_by_scenario(
    scenario="web framework",
    category="technology_choice",
    limit=3
)

print(f"Found {len(similar)} similar decisions")
```

### Smart Analytics
```python
# Understand decision impact
impact = knowledge.analyze_decision_impact(decision_id)
print(f"This decision influenced {impact.get('total_influenced', 0)} other decisions")

# Get decision summary
summary = knowledge.get_decision_summary()
print(f"Total decisions: {summary.get('total_decisions', 0)}")
print(f"Categories: {list(summary.get('categories', {}).keys())}")

# Trace decision chains
chains = knowledge.trace_decision_chain(decision_id)
print(f"Decision chain has {len(chains)} connections")

# Check if decisions follow rules
compliance = knowledge.check_decision_rules({
    "category": "loan_approval",
    "scenario": "Mortgage application",
    "reasoning": "Good credit score, stable income",
    "outcome": "approved",
    "confidence": 0.95
})

if compliance.get("compliant", False):
    print("✅ Decision follows all rules")
else:
    print(f"❌ Rule violations: {compliance.get('violations', [])}")
```

### Graph Analytics Made Simple
```python
# Get overview of your knowledge graph
summary = knowledge.get_graph_summary()
print(f"Knowledge graph has {summary.get('nodes', 0)} concepts")
print(f"And {summary.get('edges', 0)} relationships")

# Find related concepts
related = knowledge.find_related_nodes("Python", how_many=5)
for concept_id, similarity in related:
    print(f"Related to {concept_id}: {similarity:.2f}")

# Understand which concepts are most important
importance = knowledge.get_node_importance("Python")
print(f"Python importance score: {importance.get('degree', 0)}")
```

### Core Methods

| Method | What It Does | When to Use |
|--------|-------------|------------|
| `add_node(node_id, node_type, properties)` | Add concepts to remember | Build knowledge base |
| `add_edge(source, target, relation)` | Connect related concepts | Show relationships |
| `add_decision(decision)` or `add_decision(category, scenario, reasoning, outcome, ...)` | Record decisions | Track choices and learn |
| `add_decision_simple(category, scenario, reasoning, outcome, confidence, ...)` | Easy decision recording | Quick decision tracking |
| `find_precedents(decision_id, limit)` | Find precedents by ID | Get connected decisions |
| `find_precedents_by_scenario(scenario, category, ...)` | Find similar decisions | Make consistent choices |
| `analyze_decision_impact(decision_id)` | Understand decision influence | See how decisions affect others |
| `get_decision_summary()` | Get decision statistics | Understand decision patterns |
| `trace_decision_chain(decision_id)` | Trace decision connections | Understand decision relationships |
| `check_decision_rules(decision_data)` | Validate decisions | Ensure compliance |
| `get_graph_summary()` | Get graph overview | Understand knowledge structure |
| `find_related_nodes(node_id, how_many)` | Find related concepts | Discover connections |
| `get_node_importance(node_id)` | Measure concept importance | Identify key concepts |

---

## 🔄 Using Both Together - Complete Intelligence

### Your Smart Agent System
```python
from veritasreason.context import AgentContext, ContextGraph
from veritasreason.vector_store import VectorStore

# Create the components
vector_store = VectorStore(backend="inmemory", dimension=384)
knowledge = ContextGraph(advanced_analytics=True)

# Create your intelligent agent
agent = AgentContext(
    vector_store=vector_store,
    knowledge_graph=knowledge,  # Add knowledge graph
    decision_tracking=True,
    graph_expansion=True,
    advanced_analytics=True
)

# Your agent works like this:
# 1. Store information in memory
agent.store("User wants to learn web development with Python")
agent.store("User is a beginner programmer")
agent.store("User prefers hands-on tutorials")

# 2. Find relevant information
results = agent.retrieve("Python web development tutorials")
print(f"Found {len(results)} relevant memories")

# 3. Make smart decisions
decision_id = agent.record_decision(
    category="content_recommendation",
    scenario="Python web development learning path",
    reasoning="Beginner needs hands-on Python web tutorial",
    outcome="recommended_flask_tutorial",
    confidence=0.89
)

# 4. Learn and improve over time
insights = agent.get_context_insights()
print(f"Agent insights: {insights}")

# 5. Access advanced features when needed
graph_summary = agent.graph_builder.get_graph_summary()
node_importance = agent.graph_builder.get_node_importance("Python")
```

---

## 🎯 Real-World Applications

### 🏦 Banking - Smart Loan Decisions
```python
# Track loan decisions and learn from patterns
bank_agent = AgentContext(vector_store=bank_vector_store, decision_tracking=True)

# Store customer information
bank_agent.store("Customer has credit score 750, stable employment")
bank_agent.store("Customer is first-time homebuyer")

# Make loan decision
loan_decision = bank_agent.record_decision(
    category="loan_approval",
    scenario="First-time homebuyer mortgage",
    reasoning="Good credit score, stable income, 20% down payment",
    outcome="approved",
    confidence=0.94
)

# Find similar loan decisions for consistency
similar_loans = bank_agent.find_precedents("homebuyer", category="loan_approval")
print(f"Found {len(similar_loans)} similar loan decisions")
```

### 🏥 Healthcare - Patient Care Decisions
```python
# Track patient care decisions
health_agent = AgentContext(vector_store=medical_vector_store, decision_tracking=True)

# Store patient information
health_agent.store("Patient has hypertension, type 2 diabetes")
health_agent.store("Patient allergic to penicillin")

# Make treatment decision
treatment_decision = health_agent.record_decision(
    category="treatment_plan",
    scenario="Hypertension with diabetes",
    reasoning="ACE inhibitors safe for diabetic patients",
    outcome="prescribed_ace_inhibitor",
    confidence=0.91
)

# Find similar treatment cases
similar_cases = health_agent.find_precedents("hypertension", category="treatment_plan")
```

### 🛒 E-commerce - Smart Recommendations
```python
# Track recommendation decisions
ecommerce_graph = ContextGraph()

# Build user-product knowledge
ecommerce_graph.add_node("user_123", "user", {"segment": "premium"})
ecommerce_graph.add_node("laptop_xyz", "product", {"category": "electronics"})
ecommerce_graph.add_edge("user_123", "laptop_xyz", "viewed")

# Make recommendation decision
from veritasreason.context.decision_models import Decision
from datetime import datetime

rec_decision = Decision(
    decision_id="rec_001",
    category="product_recommendation",
    scenario="Laptop recommendation for premium user",
    reasoning="User prefers high-performance electronics",
    outcome="recommended_gaming_laptop",
    confidence=0.87,
    timestamp=datetime.now(),
    decision_maker="recommendation_system",
    metadata={"entities": ["user_123", "laptop_xyz"]}
)
ecommerce_graph.add_decision(rec_decision)

# Or use the convenience method
rec_decision_id = ecommerce_graph.add_decision_simple(
    category="product_recommendation",
    scenario="Laptop recommendation for premium user",
    reasoning="User prefers high-performance electronics",
    outcome="recommended_gaming_laptop",
    confidence=0.87,
    entities=["user_123", "laptop_xyz"]
)

# Find similar recommendations
similar_recs = ecommerce_graph.find_precedents_by_scenario(
    scenario="laptop recommendation",
    limit=5
)
```

---

## ⚙️ Configuration Options

### Simple Setup (Most Common)
```python
# Just memory and basic learning
agent = AgentContext(vector_store=vector_store)
```

### Smart Setup (Recommended)
```python
# Memory + decision learning
agent = AgentContext(
    vector_store=vector_store,
    decision_tracking=True,
    graph_expansion=True
)
```

### Complete Setup (Maximum Power)
```python
# Everything enabled
agent = AgentContext(
    vector_store=vector_store,
    knowledge_graph=ContextGraph(advanced_analytics=True),
    decision_tracking=True,
    graph_expansion=True,
    advanced_analytics=True,
    kg_algorithms=True,
    vector_store_features=True
)
```

### ContextGraph Options
```python
# Basic knowledge graph
graph = ContextGraph()

# Advanced knowledge graph
graph = ContextGraph(
    advanced_analytics=True,      # Enable smart algorithms
    centrality_analysis=True,     # Find important concepts
    community_detection=True,     # Find groups of related concepts
    node_embeddings=True          # Understand concept similarity
)
```

---

## 📊 Data Structures

### MemoryItem - The Basic Memory Unit
```python
@dataclass
class MemoryItem:
    content: str              # The actual text content
    timestamp: datetime       # When it was created
    metadata: Dict            # Tags like user_id, conversation_id
    embedding: List[float]    # Vector representation
    entities: List[Dict]      # Entities found in content
```

### Decision - The Decision Unit
```python
@dataclass
class Decision:
    decision_id: str         # Unique decision identifier
    category: str            # Decision category (approval, rejection, etc.)
    scenario: str            # Decision scenario description
    reasoning: str           # Decision reasoning and explanation
    outcome: str             # Decision outcome
    confidence: float        # Confidence score (0-1)
    decision_maker: str      # Decision maker identifier
    timestamp: datetime      # When decision was made
    entities: List[str]      # Related entities
    metadata: Dict           # Additional decision metadata
```

### Graph Node - Knowledge Concept
```python
{
    "id": "node_unique_id",
    "type": "concept",
    "properties": {
        "content": "Description of the node",
        "weight": 1.0,
        "importance": 0.85
    }
}
```

### Graph Edge - Knowledge Relationship
```python
{
    "source_id": "origin_node",
    "target_id": "destination_node",
    "type": "related_to",
    "weight": 0.8,
    "properties": {
        "similarity": 0.75,
        "confidence": 0.9
    }
}
```

---

## 🚀 Advanced Features

### GraphRAG with Multi-Hop Reasoning
```python
# Query with reasoning and LLM integration
result = agent.query_with_reasoning(
    query="What technologies work well together?",
    llm_provider=llm_provider,
    max_hops=2,
    max_results=10
)

print(f"Response: {result['response']}")
print(f"Reasoning Path: {result['reasoning_path']}")
print(f"Confidence: {result['confidence']:.3f}")
```

### Production Integration
```python
# Use with persistent graph stores
from veritasreason.graph_store import GraphStore

# Neo4j integration
neo4j_store = GraphStore(
    backend="neo4j",
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Production agent with persistent storage
production_agent = AgentContext(
    vector_store=vector_store,
    knowledge_graph=neo4j_store,
    decision_tracking=True,
    advanced_analytics=True
)
```

### Analytics and Insights
```python
# Get comprehensive insights
insights = agent.get_context_insights()
print(f"Total decisions: {insights.get('total_decisions', 0)}")
print(f"Decision categories: {list(insights.get('categories', {}).keys())}")
print(f"Most common outcome: {insights.get('most_common_outcome', 'N/A')}")

# Graph analytics
graph_insights = agent.graph_builder.get_graph_summary()
node_importance = agent.graph_builder.get_node_importance("key_concept")
```

---

## 📚 Need More Help?

### For Beginners
- Start with **AgentContext** for most applications
- Use basic **store/retrieve** for memory management
- Add **decision tracking** to enable learning
- Enable features gradually as needed

### For Advanced Users
- Add **ContextGraph** for knowledge organization
- Use **analytics** to understand patterns
- Implement **policies** for consistent decisions
- Use **persistence** for state management

### For Production
- Enable **all features** for maximum intelligence
- Use **save/load** for state persistence
- **Monitor performance** with insights and health checks
- **Test thoroughly** before deployment

### Examples and Tutorials
- Look at the **real-world examples** above for your specific use case
- Check **configuration options** to customize your agent
- Start simple and add power as needed

---

**Happy building intelligent agents!** 🎯

---

## 📚 See Also

- [Vector Store](vector_store.md) - The long-term storage backend
- [Graph Store](graph_store.md) - The knowledge graph backend
- [KG Algorithms](kg.md) - Knowledge graph algorithms and analytics
- [Reasoning](reasoning.md) - Uses context for logic

## Cookbook

Interactive tutorials to learn context management, GraphRAG, and decision tracking:

- **[Context Module](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/introduction/19_Context_Module.ipynb)**: Practical guide to the context module for AI agents
  - **Topics**: Agent memory, context graph, hybrid retrieval, entity linking, decision tracking
  - **Difficulty**: Intermediate
  - **Use Cases**: Building stateful AI agents, persistent memory systems, decision management

- **[Advanced Context Engineering](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/11_Advanced_Context_Engineering.ipynb)**: Build a production-grade memory system for AI agents
  - **Topics**: Agent memory, GraphRAG, entity injection, lifecycle management, persistent stores, decision analytics
  - **Difficulty**: Advanced
  - **Use Cases**: Production agent systems, advanced memory management, decision analysis

- **[Decision Tracking with KG Algorithms](https://github.com/Hawksight-AI/veritas-reason/blob/main/cookbook/advanced/12_Decision_Tracking_KG.ipynb)**: Advanced decision tracking and analytics
  - **Topics**: Decision lifecycle, precedent search, causal analysis, KG algorithms, policy compliance
  - **Difficulty**: Advanced
  - **Use Cases**: Banking decisions, healthcare decisions, legal precedent analysis
