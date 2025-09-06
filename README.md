VeritasGraph
(https://img.shields.io/badge/build-passing-brightgreen)](https://github.com)
(https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Enterprise-Grade Graph RAG for Secure, On-Premise AI with Verifiable Attribution

VeritasGraph is a production-ready, end-to-end framework for building advanced question-answering and summarization systems that operate entirely within your private infrastructure. It is architected to overcome the fundamental limitations of traditional vector-search-based Retrieval-Augmented Generation (RAG) by leveraging a knowledge graph to perform complex, multi-hop reasoning. Baseline RAG systems excel at finding direct answers but falter when faced with questions that require connecting disparate information or understanding a topic holistically. VeritasGraph addresses this challenge directly, providing not just answers, but transparent, auditable reasoning paths with full source attribution for every generated claim, establishing a new standard for trust and reliability in enterprise AI.

Table of Contents
Core Capabilities

(#2-the-architectural-blueprint)

(#a-stage-1-automated-knowledge-graph-construction)

(#b-stage-2-the-hybrid-retrieval-engine)

(#c-stage-3-the-lora-tuned-reasoning-core)

(#d-stage-4-the-attribution--provenance-layer)

(#3-beyond-semantic-search-solving-the-multi-hop-challenge)


(#4-secure-on-premise-deployment-guide)



(#c-data-ingestion--indexing)

(#d-system-activation)


(#6-project-philosophy--future-roadmap)


1. Core Capabilities
VeritasGraph integrates four critical components into a cohesive, powerful, and secure system.

Multi-Hop Graph Reasoning: The system moves beyond simple semantic similarity to traverse complex relationships within your data. This enables it to answer questions that require synthesizing information from multiple documents and sources, uncovering connections that are invisible to traditional search methods.

Efficient LoRA-Tuned LLM: It utilizes a powerful, open-source Large Language Model that has been fine-tuned using Low-Rank Adaptation (LoRA). This technique achieves high performance on specific reasoning and attribution tasks without the prohibitive hardware and financial costs associated with full model fine-tuning, making powerful on-premise deployment economically and operationally feasible.

End-to-End Source Attribution: VeritasGraph is designed to build trust and ensure compliance through complete transparency. Every generated statement is explicitly and automatically linked back to the specific source documents and the logical reasoning path used for its generation, creating a fully auditable and verifiable output.

Secure & Private On-Premise Architecture: The entire system is engineered for deployment within your own secure environment. By avoiding any reliance on external, third-party APIs, VeritasGraph ensures complete data privacy, security, and sovereignty, giving you full control over your most sensitive information.

2. The Architectural Blueprint
The VeritasGraph pipeline is a four-stage process that systematically transforms a corpus of raw, unstructured documents into a structured knowledge asset capable of sophisticated, attributable reasoning.

A. Stage 1: Automated Knowledge Graph Construction
This initial indexing phase is the foundation upon which all subsequent reasoning capabilities are built. It ingests a collection of unstructured documents (e.g., PDFs, technical manuals, reports, wikis) and methodically transforms them into a highly structured and interconnected knowledge graph. This process converts a static collection of documents into a dynamic, queryable "world model" of the information they contain.

The construction process proceeds as follows:

Document Chunking: Input documents are first segmented into smaller, manageable TextUnits. This granular approach is essential for both focused analysis during the extraction phase and precise attribution in the final output.

Entity & Relationship Extraction: A powerful Large Language Model processes each TextUnit to perform sophisticated natural language understanding. It identifies key entities (such as people, organizations, projects, or technical concepts) and, crucially, the semantic relationships that connect them. This information is extracted as structured triplets in the form of (head_entity, relation, tail_entity).

Graph Assembly: These extracted entities and relationships are then used to populate a graph database (e.g., Neo4j). Entities become the nodes (vertices) of the graph, and the relationships become the directed edges that connect them. The result is a rich, interconnected network that represents the deep structure of the knowledge contained within the source corpus, capturing relationships that exist both within and across documents.

This transformation from unstructured text to a structured graph model is the system's foundational act of intelligence. Unlike baseline RAG, which treats documents as an indexed "bag of chunks," VeritasGraph creates a pre-computed network of potential reasoning paths.

B. Stage 2: The Hybrid Retrieval Engine
Retrieval in VeritasGraph is a sophisticated, multi-stage process that intelligently combines the strengths of modern semantic search with the logical power of graph traversal. This hybrid strategy represents a fundamental paradigm shift from simply "retrieving answers" to "retrieving a reasoning context."

The retrieval process is orchestrated as follows:

Query Analysis & Entry-Point Identification: A vector-based semantic search is executed against an index of the document chunks to identify initial "entry point" nodes within the knowledge graph that are most semantically relevant to the query.

Contextual Expansion via Multi-Hop Traversal: Starting from these entry points, the system traverses the graph by following relationships (edges) to gather additional, contextually relevant information. This process can span multiple "hops," allowing the system to connect disparate but logically linked nodes across the entire knowledge base.

Pruning & Re-ranking: The expanded context undergoes a crucial pruning and re-ranking step. This process uses algorithms to evaluate the salience of the retrieved information relative to the original query, filtering out less relevant data to prevent the "needle in a haystack" problem.

This two-pronged approach is the core mechanism that solves the multi-hop challenge. Vector search efficiently finds the what (the relevant concepts), while graph traversal uncovers the how and why (the relationships that connect them).

C. Stage 3: The LoRA-Tuned Reasoning Core
This stage involves the Large Language Model, which acts as the synthesis and reasoning engine. The use of a locally-hosted, LoRA-tuned open-source model is a deliberate architectural choice designed for performance, efficiency, and security in an on-premise environment.

The generation process includes these steps:

Augmented Prompting: The rich, structured context retrieved from the graph is systematically formatted into a detailed augmented prompt. This prompt includes the original user query, the pruned data, and explicit instructions for the LLM to synthesize a coherent answer while maintaining strict adherence to the provided sources for attribution.

LLM Generation: The augmented prompt is passed to the locally-hosted LLM, which processes the context and generates the final, human-readable answer.

LoRA Fine-Tuning: The base open-source LLM is specifically fine-tuned using Low-Rank Adaptation (LoRA) on a curated dataset of tasks that mirror the system's function. This results in a model that is both highly specialized and computationally efficient, ideal for on-premise deployment.

D. Stage 4: The Attribution & Provenance Layer
This final stage elevates VeritasGraph from a powerful Q&A system to a trustworthy, enterprise-ready knowledge tool. It provides a complete and transparent audit trail for every piece of information the system generates.

The attribution mechanism is implemented as follows:

Metadata Propagation: Throughout the entire retrieval pipeline, metadata for each piece of information (source document ID, chunk number, etc.) is meticulously tracked and preserved.

Traceable Generation: The LLM is explicitly prompted to cite the sources for each substantive claim it makes, using the rich metadata provided in the augmented prompt.

Structured Attribution Output: The final API response contains both the natural language answer and a structured JSON object detailing the full provenance of that answer. This attribution object maps claims in the response back to the specific text chunks from the source documents, creating a verifiable and fully transparent reasoning trail.

3. Beyond Semantic Search: Solving the Multi-Hop Challenge
To crystallize the practical value of VeritasGraph, consider a query that is intractable for traditional RAG systems:

"Which engineer who worked on the 'Helios' project in our European office later contributed to a patent filed by the US division?"

Baseline RAG Failure: A system based on vector search would retrieve isolated document chunks. It might find a list of engineers on the 'Helios' project, documents about the European office, and a list of US patents. However, it would lack the structural understanding to connect an individual engineer across these disparate contexts.

VeritasGraph Success: The Graph RAG pipeline would succeed by executing a logical search:

Use semantic search to identify initial nodes in the graph for 'Helios' project, 'European office', and 'US division patents'.

Identify engineer nodes that have relationships like (engineer) --> ('Helios' project) and (engineer) --> ('European office').

From this set of candidates, traverse their outgoing relationships, looking for a path like (engineer) --> (patent) where the patent node is linked to the 'US division'.

The retrieved context would be this specific path, providing the LLM with a complete and logical chain of evidence to construct the correct answer.

Comparative Analysis
Feature	Baseline RAG (Vector Search)	VeritasGraph (Graph RAG)
Reasoning Capability	Single-hop, direct questions based on semantic similarity.	Multi-hop, complex inferential questions via graph traversal.
Contextual Understanding	
Retrieves isolated, often redundant text chunks.

Retrieves interconnected entities & their relationships.

Answer Synthesis	
Struggles to connect disparate facts across documents.

Excels at synthesizing novel insights from multiple sources.

Source Attribution	Points to the source chunk, but not the reasoning path.	
Provides a fully transparent and verifiable reasoning path.

4. Secure On-Premise Deployment Guide
This section provides instructions for deploying the VeritasGraph system within your secure infrastructure. The entire system is containerized using Docker for portability and ease of deployment.

A. Prerequisites
Hardware:

CPU: 16+ cores recommended.

RAM: 64 GB minimum, 128 GB+ recommended for large datasets.

GPU: NVIDIA GPU with CUDA support (e.g., A100, H100, RTX 4090) with at least 24 GB of VRAM.

Software:

Docker and Docker Compose (latest versions).

Python 3.10 or later.

NVIDIA Container Toolkit for GPU support within Docker.

B. Component Configuration
The system is configured via a .env file. Create a .env file by copying the provided .env.example and populate it with your environment-specific values.

C. Data Ingestion & Indexing
The first step is to ingest your source documents to build the knowledge graph and vector indices. This can be a computationally intensive process.

To start the ingestion pipeline, run the following command from the repository root:

This command starts a one-off container that reads documents from DATA_PATH, performs chunking, runs entity and relationship extraction, and populates both the graph and vector databases.

D. System Activation
Once ingestion is complete, launch the full application stack.

To launch all services in detached mode, run:

Verify that all services are running correctly by checking the Docker logs:

5. API Usage & Examples
Interaction with the deployed system is handled via a simple REST API endpoint.

Endpoint: POST /query

Request Body (Python Example)
Response Body (JSON Example)
A successful response will return a JSON object containing the answer and, if requested, a detailed attribution structure.

6. Project Philosophy & Future Roadmap
Philosophy
VeritasGraph is founded on the principle that the most powerful AI systems should also be the most transparent, secure, and controllable. We are committed to democratizing enterprise-grade AI, providing organizations with the tools to build their own sovereign knowledge assets.

Roadmap
The project is under active development. Future enhancements include:

Expanded Database Support: Integration with a wider range of graph databases and vector stores.

Advanced Graph Analytics: Incorporation of community detection and summarization techniques to answer holistic questions about the entire dataset, as pioneered by Microsoft's GraphRAG.

Agentic Framework: Development of an agentic layer that can perform more complex, multi-step reasoning tasks.

Visualization UI: A web-based user interface for visualizing the knowledge graph and interactively examining attribution paths.

7. Acknowledgments & Citations
This project builds upon the foundational research and open-source contributions of the broader AI community. We acknowledge the significant influence of the following works and projects:

The pioneering research on graph-structured RAG, such as the HopRAG framework.

Microsoft's GraphRAG project, for its comprehensive approach to knowledge graph extraction and community-based reasoning.

The robust ecosystems provided by open-source libraries such as LangChain and LlamaIndex.

The foundational role of graph database technologies like Neo4j in enabling practical, scalable implementations of Graph RAG architectures.