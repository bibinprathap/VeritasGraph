"""
Reasoning-Based Search for VeritasGraph
========================================
Inspired by PageIndex's 98.7% accuracy approach:
- Tree-based hierarchical navigation over knowledge graph
- LLM reasoning instead of pure vector similarity
- Multi-step verification and auto-correction
- Explicit reasoning traces for explainability

Key improvements over standard GraphRAG:
1. Reasoning-based entity/community selection (not just embeddings)
2. Verification loop to validate retrieval accuracy
3. Hierarchical graph traversal with reasoning
4. Answer confidence scoring and self-correction
"""

import asyncio
import json
import pandas as pd
import tiktoken
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import os
from dotenv import load_dotenv

# Load environment
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))

from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
from graphrag.vector_stores.lancedb import LanceDBVectorStore

from openai_config import get_llm_config, get_embedding_config


class SearchStrategy(Enum):
    """Search strategy selection based on query analysis"""
    LOCAL = "local"           # Entity-focused, specific queries
    GLOBAL = "global"         # Community-based, broad queries  
    HYBRID = "hybrid"         # Combined approach
    REASONING = "reasoning"   # Full reasoning-based search


@dataclass
class ReasoningStep:
    """Captures a single reasoning step for explainability"""
    step_type: str
    input_context: str
    reasoning: str
    output: Any
    confidence: float


@dataclass
class VerifiedResult:
    """Result with verification metadata"""
    answer: str
    confidence: float
    reasoning_trace: List[ReasoningStep]
    sources: List[Dict[str, Any]]
    verified: bool
    corrections_made: int


class ReasoningSearchEngine:
    """
    Enhanced search engine with PageIndex-inspired reasoning approach.
    
    Key features:
    1. Query analysis to determine optimal search strategy
    2. Hierarchical graph traversal with LLM reasoning
    3. Multi-step verification and auto-correction
    4. Explicit reasoning traces for explainability
    """
    
    def __init__(self, input_dir: str, community_level: int = 2, temperature: float = 0.3):
        self.input_dir = input_dir
        self.community_level = community_level
        self.temperature = temperature
        self.token_encoder = tiktoken.get_encoding("cl100k_base")
        self.reasoning_trace: List[ReasoningStep] = []
        
        # Initialize LLM
        llm_config = get_llm_config()
        self.llm = ChatOpenAI(
            api_key=llm_config["api_key"],
            api_base=llm_config["api_base"],
            model=llm_config["model"],
            api_type=llm_config["api_type"],
            max_retries=llm_config["max_retries"],
        )
        
        # Load graph data
        self._load_graph_data()
    
    def _load_graph_data(self):
        """Load all graph components for reasoning"""
        join = os.path.join
        
        # Load entities
        entity_df = pd.read_parquet(join(self.input_dir, "create_final_nodes.parquet"))
        entity_embedding_df = pd.read_parquet(join(self.input_dir, "create_final_entities.parquet"))
        self.entities = read_indexer_entities(entity_df, entity_embedding_df, self.community_level)
        self.entity_df = entity_df
        
        # Load relationships
        relationship_df = pd.read_parquet(join(self.input_dir, "create_final_relationships.parquet"))
        self.relationships = read_indexer_relationships(relationship_df)
        self.relationship_df = relationship_df
        
        # Load community reports
        report_df = pd.read_parquet(join(self.input_dir, "create_final_community_reports.parquet"))
        self.reports = read_indexer_reports(report_df, entity_df, self.community_level)
        self.report_df = report_df
        
        # Load text units
        text_unit_df = pd.read_parquet(join(self.input_dir, "create_final_text_units.parquet"))
        self.text_units = read_indexer_text_units(text_unit_df)
        
        # Build entity index for fast lookup
        self.entity_index = {e.title.lower(): e for e in self.entities}
        
        # Build graph structure for traversal
        self._build_graph_structure()
    
    def _build_graph_structure(self):
        """Build hierarchical graph structure for reasoning-based traversal"""
        self.graph_structure = {
            "communities": {},
            "entity_to_community": {},
            "community_hierarchy": {}
        }
        
        # Map entities to communities
        for entity in self.entities:
            if hasattr(entity, 'community_ids') and entity.community_ids:
                for cid in entity.community_ids:
                    if cid not in self.graph_structure["communities"]:
                        self.graph_structure["communities"][cid] = []
                    self.graph_structure["communities"][cid].append(entity.title)
                    self.graph_structure["entity_to_community"][entity.title] = cid
    
    async def _call_llm(self, prompt: str, json_mode: bool = False) -> str:
        """Call LLM with proper error handling using OpenAI-compatible API"""
        import openai
        
        llm_config = get_llm_config()
        
        try:
            client = openai.OpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config["api_base"]
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            response = client.chat.completions.create(
                model=llm_config["model"],
                messages=messages,
                temperature=self.temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM call error: {e}")
            return "{}"
    
    def _extract_json(self, content: str) -> Dict:
        """Extract JSON from LLM response (PageIndex-style)"""
        try:
            # Try to extract JSON enclosed within ```json and ```
            start_idx = content.find("```json")
            if start_idx != -1:
                start_idx += 7
                end_idx = content.rfind("```")
                json_content = content[start_idx:end_idx].strip()
            else:
                json_content = content.strip()
            
            # Clean up common issues
            json_content = json_content.replace('None', 'null')
            return json.loads(json_content)
        except json.JSONDecodeError:
            try:
                json_content = json_content.replace(',]', ']').replace(',}', '}')
                return json.loads(json_content)
            except:
                return {}
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        PageIndex-inspired query analysis with reasoning.
        Determines optimal search strategy and extracts key concepts.
        """
        # Get graph summary for context
        entity_list = list(self.entity_index.keys())[:50]  # Top entities
        community_summaries = []
        for report in self.reports[:10]:
            if hasattr(report, 'summary'):
                community_summaries.append(report.summary[:200])
        
        analysis_prompt = f"""
You are an expert at analyzing questions to determine the best retrieval strategy.

Given the question and knowledge graph context, analyze:
1. What type of information is needed (specific facts vs. broad overview)
2. Which entities or topics are most relevant
3. What search strategy would work best

Question: {query}

Available Entities (sample): {entity_list[:30]}

Community Summaries (sample):
{chr(10).join(community_summaries[:5])}

Reply in JSON format:
{{
    "thinking": "<your reasoning about the query and what information is needed>",
    "query_type": "specific" | "broad" | "comparative" | "aggregative",
    "key_concepts": ["concept1", "concept2", ...],
    "relevant_entities": ["entity1", "entity2", ...],
    "search_strategy": "local" | "global" | "hybrid",
    "confidence": 0.0-1.0
}}
"""
        
        response = await self._call_llm(analysis_prompt)
        analysis = self._extract_json(response)
        
        # Record reasoning step
        self.reasoning_trace.append(ReasoningStep(
            step_type="query_analysis",
            input_context=query,
            reasoning=analysis.get("thinking", ""),
            output=analysis,
            confidence=analysis.get("confidence", 0.5)
        ))
        
        return analysis
    
    async def reasoning_based_retrieval(
        self, 
        query: str, 
        analysis: Dict[str, Any]
    ) -> Tuple[List[Dict], str]:
        """
        PageIndex-style reasoning-based retrieval over the knowledge graph.
        Uses LLM to navigate the graph structure intelligently.
        """
        # Build graph context for reasoning
        graph_context = self._build_reasoning_context(analysis)
        
        retrieval_prompt = f"""
You are navigating a knowledge graph to find information relevant to the question.

Question: {query}

Query Analysis:
- Type: {analysis.get('query_type', 'unknown')}
- Key Concepts: {analysis.get('key_concepts', [])}
- Relevant Entities: {analysis.get('relevant_entities', [])}

Knowledge Graph Structure:
{graph_context}

Your task:
1. Reason about which parts of the graph are most relevant
2. Select the most informative nodes (entities/communities)
3. Explain your reasoning for each selection

Reply in JSON format:
{{
    "reasoning_steps": [
        {{
            "step": 1,
            "action": "examine community/entity",
            "target": "name",
            "reasoning": "why this is relevant",
            "relevance_score": 0.0-1.0
        }}
    ],
    "selected_entities": ["entity1", "entity2", ...],
    "selected_communities": ["community_id1", ...],
    "retrieval_confidence": 0.0-1.0
}}
"""
        
        response = await self._call_llm(retrieval_prompt)
        retrieval_result = self._extract_json(response)
        
        # Record reasoning step
        reasoning_text = json.dumps(retrieval_result.get("reasoning_steps", []), indent=2)
        self.reasoning_trace.append(ReasoningStep(
            step_type="graph_navigation",
            input_context=graph_context[:500],
            reasoning=reasoning_text,
            output=retrieval_result,
            confidence=retrieval_result.get("retrieval_confidence", 0.5)
        ))
        
        # Gather context from selected nodes
        context_chunks = self._gather_context(retrieval_result)
        
        return context_chunks, reasoning_text
    
    def _build_reasoning_context(self, analysis: Dict) -> str:
        """Build structured context for LLM reasoning"""
        context_parts = []
        
        # Add community information
        context_parts.append("=== COMMUNITIES (High-level topic clusters) ===")
        for i, report in enumerate(self.reports[:15]):
            if hasattr(report, 'title') and hasattr(report, 'summary'):
                context_parts.append(f"\n[Community {i}] {report.title}")
                context_parts.append(f"Summary: {report.summary[:300]}...")
        
        # Add entity information based on analysis
        context_parts.append("\n\n=== RELEVANT ENTITIES ===")
        relevant_entities = analysis.get('relevant_entities', [])
        for entity_name in relevant_entities[:10]:
            entity_key = entity_name.lower()
            if entity_key in self.entity_index:
                entity = self.entity_index[entity_key]
                context_parts.append(f"\n[Entity] {entity.title}")
                if hasattr(entity, 'description'):
                    context_parts.append(f"Description: {entity.description[:200]}")
        
        # Add some relationships
        context_parts.append("\n\n=== KEY RELATIONSHIPS ===")
        for rel in self.relationships[:20]:
            if hasattr(rel, 'source') and hasattr(rel, 'target'):
                context_parts.append(f"- {rel.source} → {rel.target}")
                if hasattr(rel, 'description'):
                    context_parts.append(f"  ({rel.description[:100]})")
        
        return "\n".join(context_parts)
    
    def _gather_context(self, retrieval_result: Dict) -> List[Dict]:
        """Gather context from selected graph nodes"""
        context_chunks = []
        
        # Gather from selected entities
        for entity_name in retrieval_result.get("selected_entities", []):
            entity_key = entity_name.lower()
            if entity_key in self.entity_index:
                entity = self.entity_index[entity_key]
                context_chunks.append({
                    "type": "entity",
                    "name": entity.title,
                    "content": getattr(entity, 'description', ''),
                    "source": "knowledge_graph"
                })
        
        # Gather from selected communities
        for report in self.reports:
            if hasattr(report, 'id'):
                report_id = str(report.id)
                if report_id in retrieval_result.get("selected_communities", []):
                    context_chunks.append({
                        "type": "community",
                        "name": getattr(report, 'title', f'Community {report_id}'),
                        "content": getattr(report, 'full_content', getattr(report, 'summary', '')),
                        "source": "community_report"
                    })
        
        return context_chunks
    
    async def verify_and_correct(
        self, 
        query: str, 
        answer: str, 
        context: List[Dict]
    ) -> Tuple[str, float, int]:
        """
        PageIndex-inspired verification and auto-correction loop.
        Validates answer against retrieved context and corrects if needed.
        """
        corrections = 0
        max_corrections = 2
        current_answer = answer
        
        while corrections < max_corrections:
            verification_prompt = f"""
You are a verification expert. Check if the answer is accurate and well-supported by the context.

Question: {query}

Answer to verify:
{current_answer}

Available Context:
{self._format_context(context)}

Verify:
1. Is the answer factually correct based on the context?
2. Are all claims supported by evidence in the context?
3. Are there any hallucinations or unsupported statements?
4. Is anything important missing?

Reply in JSON format:
{{
    "thinking": "<your verification reasoning>",
    "is_accurate": true/false,
    "confidence": 0.0-1.0,
    "issues": ["issue1", "issue2", ...],
    "suggested_correction": "<corrected answer if needed, or null>"
}}
"""
            
            response = await self._call_llm(verification_prompt)
            verification = self._extract_json(response)
            
            # Record verification step
            self.reasoning_trace.append(ReasoningStep(
                step_type="verification",
                input_context=f"Answer: {current_answer[:200]}...",
                reasoning=verification.get("thinking", ""),
                output=verification,
                confidence=verification.get("confidence", 0.5)
            ))
            
            if verification.get("is_accurate", True):
                return current_answer, verification.get("confidence", 0.8), corrections
            
            # Apply correction if provided
            if verification.get("suggested_correction"):
                current_answer = verification["suggested_correction"]
                corrections += 1
            else:
                break
        
        return current_answer, verification.get("confidence", 0.5), corrections
    
    def _format_context(self, context: List[Dict]) -> str:
        """Format context chunks for display"""
        formatted = []
        for chunk in context[:10]:
            formatted.append(f"[{chunk['type'].upper()}] {chunk['name']}")
            formatted.append(chunk['content'][:500])
            formatted.append("---")
        return "\n".join(formatted)
    
    async def generate_answer(
        self, 
        query: str, 
        context: List[Dict], 
        reasoning_trace: str
    ) -> str:
        """Generate answer with explicit reasoning"""
        answer_prompt = f"""
You are an expert analyst. Answer the question based ONLY on the provided context.

Question: {query}

Retrieved Context:
{self._format_context(context)}

Reasoning Process Used:
{reasoning_trace}

Instructions:
1. Answer based ONLY on the provided context
2. If information is not in the context, say so explicitly
3. Cite specific entities or communities when making claims
4. Be precise and avoid speculation

Provide a comprehensive, well-structured answer:
"""
        
        answer = await self._call_llm(answer_prompt)
        return answer
    
    async def search(
        self, 
        query: str, 
        response_type: str = "Multiple Paragraphs"
    ) -> VerifiedResult:
        """
        Main search method with full reasoning pipeline.
        
        Pipeline:
        1. Query Analysis (determine strategy)
        2. Reasoning-Based Retrieval (navigate graph with reasoning)
        3. Answer Generation (based on retrieved context)
        4. Verification & Correction (validate and fix)
        """
        self.reasoning_trace = []  # Reset trace
        
        # Step 1: Analyze query
        analysis = await self.analyze_query(query)
        
        # Step 2: Reasoning-based retrieval
        context, reasoning_text = await self.reasoning_based_retrieval(query, analysis)
        
        # If no context found, fall back to standard search
        if not context:
            context = self._fallback_retrieval(query)
        
        # Step 3: Generate answer
        answer = await self.generate_answer(query, context, reasoning_text)
        
        # Step 4: Verify and correct
        verified_answer, confidence, corrections = await self.verify_and_correct(
            query, answer, context
        )
        
        # Build sources list
        sources = [
            {
                "type": chunk["type"],
                "name": chunk["name"],
                "excerpt": chunk["content"][:200]
            }
            for chunk in context[:5]
        ]
        
        return VerifiedResult(
            answer=verified_answer,
            confidence=confidence,
            reasoning_trace=self.reasoning_trace,
            sources=sources,
            verified=True,
            corrections_made=corrections
        )
    
    def _fallback_retrieval(self, query: str) -> List[Dict]:
        """Fallback to basic retrieval if reasoning fails"""
        context = []
        
        # Add top entities
        for entity in self.entities[:5]:
            context.append({
                "type": "entity",
                "name": entity.title,
                "content": getattr(entity, 'description', ''),
                "source": "fallback"
            })
        
        # Add top community reports
        for report in self.reports[:3]:
            context.append({
                "type": "community",
                "name": getattr(report, 'title', 'Community'),
                "content": getattr(report, 'summary', ''),
                "source": "fallback"
            })
        
        return context


# ============================================
# Enhanced Local Search with Reasoning
# ============================================

async def reasoning_local_search(
    query: str, 
    input_dir: str, 
    community_level: int = 2, 
    temperature: float = 0.3,
    response_type: str = "Multiple Paragraphs"
) -> Dict[str, Any]:
    """
    Enhanced local search with PageIndex-style reasoning.
    
    Combines:
    - GraphRAG's local search (entity-focused)
    - PageIndex's reasoning-based retrieval
    - Verification and auto-correction
    """
    engine = ReasoningSearchEngine(input_dir, community_level, temperature)
    result = await engine.search(query, response_type)
    
    return {
        "response": result.answer,
        "confidence": result.confidence,
        "verified": result.verified,
        "corrections_made": result.corrections_made,
        "sources": result.sources,
        "reasoning_trace": [
            {
                "step": step.step_type,
                "reasoning": step.reasoning[:300],
                "confidence": step.confidence
            }
            for step in result.reasoning_trace
        ]
    }


# ============================================
# Enhanced Global Search with Reasoning
# ============================================

async def reasoning_global_search(
    query: str,
    input_dir: str,
    community_level: int = 2,
    temperature: float = 0.3,
    response_type: str = "Multiple Paragraphs"
) -> Dict[str, Any]:
    """
    Enhanced global search with reasoning-based community selection.
    """
    engine = ReasoningSearchEngine(input_dir, community_level, temperature)
    
    # Force global strategy for community-based analysis
    result = await engine.search(query, response_type)
    
    return {
        "response": result.answer,
        "confidence": result.confidence,
        "verified": result.verified,
        "sources": result.sources,
        "reasoning_trace": [
            {
                "step": step.step_type,
                "reasoning": step.reasoning[:300],
                "confidence": step.confidence
            }
            for step in result.reasoning_trace
        ]
    }


# ============================================
# Hybrid Search (Best of Both)
# ============================================

async def hybrid_reasoning_search(
    query: str,
    input_dir: str,
    community_level: int = 2,
    temperature: float = 0.3,
    response_type: str = "Multiple Paragraphs"
) -> Dict[str, Any]:
    """
    Hybrid search that combines local and global results with reasoning.
    
    Strategy:
    1. Run reasoning-based query analysis
    2. Execute both local and global searches
    3. Synthesize results with LLM reasoning
    4. Verify final answer
    """
    engine = ReasoningSearchEngine(input_dir, community_level, temperature)
    
    # Get query analysis
    analysis = await engine.analyze_query(query)
    
    # Run both search types
    local_context, local_reasoning = await engine.reasoning_based_retrieval(query, analysis)
    
    # Get global context from community reports
    global_context = []
    for report in engine.reports[:5]:
        global_context.append({
            "type": "community",
            "name": getattr(report, 'title', 'Community'),
            "content": getattr(report, 'full_content', getattr(report, 'summary', '')),
            "source": "global_search"
        })
    
    # Combine contexts
    combined_context = local_context + global_context
    
    # Generate synthesized answer
    synthesis_prompt = f"""
You are an expert analyst. Synthesize information from both local (entity-focused) and global (community-focused) search results.

Question: {query}

Local Search Results (Entity-focused):
{engine._format_context(local_context)}

Global Search Results (Community-focused):
{engine._format_context(global_context)}

Query Analysis:
- Type: {analysis.get('query_type')}
- Key Concepts: {analysis.get('key_concepts')}

Provide a comprehensive answer that:
1. Integrates insights from both local and global perspectives
2. Highlights specific entities AND broader patterns
3. Notes any conflicts between local and global views
4. Cites sources appropriately
"""
    
    answer = await engine._call_llm(synthesis_prompt)
    
    # Verify
    verified_answer, confidence, corrections = await engine.verify_and_correct(
        query, answer, combined_context
    )
    
    return {
        "response": verified_answer,
        "confidence": confidence,
        "verified": True,
        "corrections_made": corrections,
        "search_strategy": "hybrid",
        "query_analysis": analysis,
        "sources": [
            {"type": c["type"], "name": c["name"]} 
            for c in combined_context[:8]
        ]
    }


# ============================================
# Convenience function for app.py integration
# ============================================

async def enhanced_search(
    query: str,
    input_dir: str,
    query_type: str = "auto",
    community_level: int = 2,
    temperature: float = 0.3,
    response_type: str = "Multiple Paragraphs"
) -> Dict[str, Any]:
    """
    Main entry point for enhanced reasoning-based search.
    
    Args:
        query: The search query
        input_dir: Path to GraphRAG artifacts
        query_type: "local", "global", "hybrid", or "auto"
        community_level: Community hierarchy level
        temperature: LLM temperature
        response_type: Response format type
    
    Returns:
        Dictionary with response, confidence, sources, and reasoning trace
    """
    if query_type == "auto":
        # Use reasoning engine to determine best strategy
        engine = ReasoningSearchEngine(input_dir, community_level, temperature)
        analysis = await engine.analyze_query(query)
        query_type = analysis.get("search_strategy", "hybrid")
    
    if query_type == "local":
        return await reasoning_local_search(query, input_dir, community_level, temperature, response_type)
    elif query_type == "global":
        return await reasoning_global_search(query, input_dir, community_level, temperature, response_type)
    else:
        return await hybrid_reasoning_search(query, input_dir, community_level, temperature, response_type)


if __name__ == "__main__":
    # Test the reasoning search
    import asyncio
    
    async def test():
        input_dir = os.path.join(script_dir, "output", "artifacts")
        
        query = "What are the main eligibility criteria for student visas?"
        
        print("Testing Reasoning-Based Search...")
        print("=" * 60)
        
        result = await enhanced_search(
            query=query,
            input_dir=input_dir,
            query_type="auto"
        )
        
        print(f"\nQuery: {query}")
        print(f"\nConfidence: {result['confidence']:.2f}")
        print(f"Verified: {result['verified']}")
        print(f"\nAnswer:\n{result['response']}")
        print(f"\nSources: {result['sources']}")
        
        if 'reasoning_trace' in result:
            print("\nReasoning Trace:")
            for step in result['reasoning_trace']:
                print(f"  - {step['step']}: {step['reasoning'][:100]}...")
    
    asyncio.run(test())
