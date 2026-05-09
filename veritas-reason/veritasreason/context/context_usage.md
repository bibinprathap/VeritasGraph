# Context Module - Usage Guide

## 🎯 What This Module Does

The context module gives your AI agents the ability to **remember**, **learn**, and **make smarter decisions** by organizing information in a way that's both powerful and easy to use.

Think of it as giving your agent a brain that can:
- **Remember conversations** (like human memory)
- **Learn from past decisions** (become smarter over time)
- **Find relevant information** quickly (when it matters most)
- **Understand relationships** between concepts
- **Make consistent decisions** based on experience

---

## 🚀 Quick Start - 5 Minutes to Your First Smart Agent

### Step 1: Basic Setup
```python
from veritasreason.context import AgentContext
from veritasreason.vector_store import VectorStore

# Create your agent with memory
vector_store = VectorStore(backend="inmemory", dimension=384)
agent = AgentContext(vector_store=vector_store)

# Your agent can now remember things
memory_id = agent.store("User asked about Python programming")
print(f"Agent remembered: {memory_id}")

# And find information when needed
results = agent.retrieve("Python tutorials")
print(f"Agent found {len(results)} relevant memories")
```

### Step 2: Add Decision Learning
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

### Step 3: Get Insights
```python
# Understand how your agent is performing
insights = agent.get_context_insights()
print(f"Agent has made {insights.get('total_decisions', 0)} decisions")
print(f"Decision categories: {list(insights.get('categories', {}).keys())}")
```

**That's it! Your agent now has memory and can learn from decisions.** 🎉

---

## 🤖 AgentContext - Your Agent's Brain

### Memory Management (Like Human Memory)
```python
# Store different types of memories
agent.store("User likes Python programming", conversation_id="chat_1")
agent.store("User is working on a web project", conversation_id="chat_2")
agent.store("User mentioned being a beginner", conversation_id="chat_3")

# Find memories when needed
results = agent.retrieve("Python programming", conversation_id="chat_1")
for result in results:
    print(f"Memory: {result['content']}")

# Search across all conversations
all_results = agent.retrieve("beginner")
print(f"Found {len(all_results)} memories about beginners")
```

### Learning from Decisions
```python
# Record important decisions
decision_id = agent.record_decision(
    category="content_recommendation",
    scenario="User wants to learn web development",
    reasoning="User is beginner, likes Python",
    outcome="recommended_python_basics",
    confidence=0.90
)

# Find similar past decisions to make better choices
similar_decisions = agent.find_precedents("web development", limit=5)
for decision in similar_decisions:
    print(f"Past decision: {decision.scenario}")
    print(f"Result: {decision.outcome}")
    print(f"Confidence: {decision.confidence}")
    print("---")
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
print(f"Most common outcome: {insights.get('most_common_outcome', 'N/A')}")
```

---

## 🏗️ ContextGraph - Knowledge Organization

When you need to organize complex information, ContextGraph helps you build knowledge networks.

### Build a Simple Knowledge Graph
```python
from veritasreason.context import ContextGraph

# Create a knowledge graph
knowledge = ContextGraph(advanced_analytics=True)

# Add things you want to remember (nodes)
knowledge.add_node("Python", "language", properties={"popularity": "high"})
knowledge.add_node("Programming", "concept", properties={"type": "skill"})
knowledge.add_node("FastAPI", "framework", properties={"language": "Python"})
knowledge.add_node("Web Development", "field", properties={"complexity": "medium"})

# Connect related things (edges)
knowledge.add_edge("Python", "Programming", "related_to")
knowledge.add_edge("Python", "FastAPI", "supports")
knowledge.add_edge("FastAPI", "Web Development", "used_for")
knowledge.add_edge("Programming", "Web Development", "requires")
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
    max_results=3
)

print(f"Found {len(similar)} similar decisions")
for decision in similar:
    print(f"  Similar scenario: {decision.get('scenario', 'N/A')}")
    print(f"  Outcome: {decision.get('outcome', 'N/A')}")
```

### Understand Decision Impact
```python
# See how decisions affect other decisions
impact = knowledge.analyze_decision_impact(decision_id)
print(f"This decision influenced {impact.get('total_influenced', 0)} other decisions")

# Get a summary of all decisions
summary = knowledge.get_decision_summary()
print(f"Total decisions: {summary.get('total_decisions', 0)}")
print(f"Categories: {list(summary.get('categories', {}).keys())}")

# Trace decision chains (how decisions connect)
chains = knowledge.trace_decision_chain(decision_id)
print(f"Decision chain has {len(chains)} connections")
```

### Smart Decision Checking
```python
# Check if decisions follow your rules
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

---

## 🔄 Using Both Together - The Complete Setup

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

## 🎯 Real-World Examples

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

## 💡 Pro Tips for Success

### 🌱 For Beginners
1. **Start with AgentContext** - It's simpler and handles most needs
2. **Use basic store/retrieve** - Like building human memory
3. **Add decision tracking** - Your agent gets smarter over time
4. **Enable features gradually** - Add complexity as you need it

### 🚀 For Advanced Users
1. **Add ContextGraph** - When you need knowledge relationships
2. **Use analytics** - Understand patterns and get insights
3. **Implement policies** - Ensure consistent decisions
4. **Use persistence** - Save and load agent state

### 🏭 For Production
1. **Enable all features** - Maximum intelligence and reliability
2. **Use save/load** - Persist agent state between sessions
3. **Monitor performance** - Use health checks and insights
4. **Test thoroughly** - Verify all functionality works

---

## 🔧 Configuration Options

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

## 🎉 You're Ready to Build Smart Agents!

With these examples, you can now:

✅ **Build Smart Agents** - That remember and learn from experience  
✅ **Track Decisions** - Make consistent, improving choices over time  
✅ **Find Information** - Quick and relevant memory retrieval  
✅ **Organize Knowledge** - Build intelligent knowledge graphs  
✅ **Make Better Decisions** - Based on past experience and patterns  
✅ **Build Real Applications** - Banking, healthcare, e-commerce, and more  

**Start simple, add power as needed! Your agents will get smarter with every decision.** 🚀

---

## 📚 Need More Help?

- **Start with AgentContext** for most applications
- **Add ContextGraph** when you need knowledge organization
- **Look at the real-world examples** for your specific use case
- **Check configuration options** to customize your agent

Happy building smart agents! 🎯
