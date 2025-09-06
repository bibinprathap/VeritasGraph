# VeritasGraph  
**Enterprise-Grade Graph RAG for Secure, On-Premise AI with Verifiable Attribution**

VeritasGraph is a production-ready, end-to-end framework for building advanced question-answering and summarization systems that operate entirely within your private infrastructure.  

It is architected to overcome the fundamental limitations of traditional vector-search-based Retrieval-Augmented Generation (RAG) by leveraging a knowledge graph to perform complex, multi-hop reasoning.  

Baseline RAG systems excel at finding direct answers but falter when faced with questions that require connecting disparate information or understanding a topic holistically. **VeritasGraph addresses this challenge directly, providing not just answers, but transparent, auditable reasoning paths with full source attribution for every generated claim, establishing a new standard for trust and reliability in enterprise AI.**

---

## 🚀 Demo  

### Video Walkthrough  
A brief video demonstrating the core functionality of VeritasGraph, from data ingestion to multi-hop querying with full source attribution.  

[![Video Walkthrough](https://github.com/bibinprathap/VeritasGraph/blob/master/assets/graphrag.JPG)](https://drive.google.com/file/d/1lEmAOUCLV0h98kY-ars96SNf5O6lVmiY/view?usp=sharing)  

> 📌 To make the video thumbnail appear, take a screenshot of your video, name it `video_thumbnail.png`, upload it to an `assets` folder in your repository, and update the placeholder path above.

---

### System Architecture Screenshot  
The following diagram illustrates the end-to-end pipeline of the VeritasGraph system:  
 

```mermaid 
graph TD
    subgraph "Indexing Pipeline (One-Time Process)"
        A --> B{Document Chunking};
        B --> C{LLM-Powered Extraction<br/>(Entities & Relationships)};
        C --> D;
        C --> E[Knowledge Graph];
    end

    subgraph "Query Pipeline (Real-Time)"
        F[User Query] --> G{Hybrid Retrieval Engine};
        G -- "1. Vector Search for Entry Points" --> D;
        G -- "2. Multi-Hop Graph Traversal" --> E;
        G --> H{Pruning & Re-ranking};
        H -- "Rich Reasoning Context" --> I{LoRA-Tuned LLM Core};
        I -- "Generated Answer + Provenance" --> J{Attribution & Provenance Layer};
        J --> K[Attributed Answer];
    end

    style A fill:#f2f2f2,stroke:#333,stroke-width:2px
    style F fill:#e6f7ff,stroke:#333,stroke-width:2px
    style K fill:#e6ffe6,stroke:#333,stroke-width:2pxgraph TD
    subgraph "Indexing Pipeline (One-Time Process)"
        A --> B{Document Chunking};
        B --> C{LLM-Powered Extraction<br/>(Entities & Relationships)};
        C --> D[Vector Index];
        C --> E[Knowledge Graph];
    end

    subgraph "Query Pipeline (Real-Time)"
        F[User Query] --> G{Hybrid Retrieval Engine};
        G -- "1. Vector Search for Entry Points" --> D;
        G -- "2. Multi-Hop Graph Traversal" --> E;
        G --> H{Pruning & Re-ranking};
        H -- "Rich Reasoning Context" --> I{LoRA-Tuned LLM Core};
        I -- "Generated Answer + Provenance" --> J{Attribution & Provenance Layer};
        J --> K[Attributed Answer];
    end

    style A fill:#f2f2f2,stroke:#333,stroke-width:2px
    style F fill:#e6f7ff,stroke:#333,stroke-width:2px
    style K fill:#e6ffe6,stroke:#333,stroke-width:2px
```
> 📌 Please upload your diagram to the `assets` folder in your repository and replace the path above.

---

## 📑 Table of Contents  

- [Core Capabilities](#1-core-capabilities)  
- [The Architectural Blueprint](#2-the-architectural-blueprint-from-unstructured-data-to-attributed-insights)  
- [Beyond Semantic Search](#3-beyond-semantic-search-solving-the-multi-hop-challenge)  
- [Secure On-Premise Deployment Guide](#4-secure-on-premise-deployment-guide)  
- [API Usage & Examples](#5-api-usage--examples)  
- [Project Philosophy & Future Roadmap](#6-project-philosophy--future-roadmap)  
- [Acknowledgments & Citations](#7-acknowledgments--citations)  

---

## 1. Core Capabilities  

VeritasGraph integrates four critical components into a cohesive, powerful, and secure system:  

- **Multi-Hop Graph Reasoning** – Move beyond semantic similarity to traverse complex relationships within your data.  
- **Efficient LoRA-Tuned LLM** – Fine-tuned using Low-Rank Adaptation for efficient, powerful on-premise deployment.  
- **End-to-End Source Attribution** – Every statement is linked back to specific source documents and reasoning paths.  
- **Secure & Private On-Premise Architecture** – Fully deployable within your infrastructure, ensuring data sovereignty.  

---

## 2. The Architectural Blueprint: From Unstructured Data to Attributed Insights  

The VeritasGraph pipeline transforms unstructured documents into a structured knowledge graph for attributable reasoning.  

### **Stage 1: Automated Knowledge Graph Construction**  
- **Document Chunking** – Segment input docs into granular `TextUnits`.  
- **Entity & Relationship Extraction** – LLM extracts structured triplets `(head, relation, tail)`.  
- **Graph Assembly** – Nodes + edges stored in a graph database (e.g., Neo4j).  

### **Stage 2: The Hybrid Retrieval Engine**  
- **Query Analysis & Entry-Point Identification** – Vector search finds relevant entry nodes.  
- **Contextual Expansion via Multi-Hop Traversal** – Graph traversal uncovers hidden relationships.  
- **Pruning & Re-Ranking** – Removes noise, keeps most relevant facts for reasoning.  

### **Stage 3: The LoRA-Tuned Reasoning Core**  
- **Augmented Prompting** – Context formatted with query, sources, and instructions.  
- **LLM Generation** – Locally hosted, LoRA-tuned open-source model generates attributed answers.  
- **LoRA Fine-Tuning** – Specialization for reasoning + attribution with efficiency.  

### **Stage 4: The Attribution & Provenance Layer**  
- **Metadata Propagation** – Track source IDs, chunks, and graph nodes.  
- **Traceable Generation** – Model explicitly cites sources.  
- **Structured Attribution Output** – JSON object with provenance + reasoning trail.  

---

## 3. Beyond Semantic Search: Solving the Multi-Hop Challenge  

Traditional RAG fails at complex reasoning (e.g., linking an engineer across projects and patents).  
VeritasGraph succeeds by combining:  

- **Semantic search** → finds entry points.  
- **Graph traversal** → connects the dots.  
- **LLM reasoning** → synthesizes final answer with citations.  

---

## 4. Secure On-Premise Deployment Guide  

### **Prerequisites**  

**Hardware**  
- CPU: 16+ cores  
- RAM: 64GB+ (128GB recommended)  
- GPU: NVIDIA GPU with 24GB+ VRAM (A100, H100, RTX 4090)  

**Software**  
- Docker & Docker Compose  
- Python 3.10+  
- NVIDIA Container Toolkit  

### **Configuration**  
- Copy `.env.example` → `.env`  
- Populate with environment-specific values  

### **Data Ingestion**  
```bash
docker-compose run ingest
