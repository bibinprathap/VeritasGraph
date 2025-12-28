# 🔬 Veritas-Scope

**Interactive Reasoning Trace UI for VeritasGraph**

> *Stop trusting Black Box RAG. See the reasoning.*

![Veritas-Scope Banner](../assets/veritas-scope-banner.png)

Veritas-Scope is a real-time visualization interface that displays the "brain" of VeritasGraph working. Instead of just returning text answers, you can now **see** the multi-hop reasoning process as it happens.

## ✨ Features

### 🧠 Visual Multi-Hop Reasoning
- **Interactive Force-Directed Graph** - Watch your knowledge graph come alive
- **Animated Reasoning Paths** - See exactly which nodes and relationships are being traversed
- **Color-Coded Node Types** - Instantly distinguish between entities, sources, communities, and answers

### 🔍 Click-to-Verify Source Attribution
- **Provenance Panel** - Every claim traced back to its source
- **Source Highlighting** - Click any node to see the original text
- **Relevance Scores** - Understand how confident the system is in each source

### 🎬 Reasoning Timeline
- **Step-by-Step Playback** - Replay the reasoning process at your own pace
- **Animation Controls** - Play, pause, step forward/backward through the trace
- **Visual Progress Indicator** - See where you are in the reasoning chain

### 📊 Real-Time Statistics
- **Node Count** - Total entities involved in the answer
- **Hop Count** - How many relationship jumps were made
- **Response Time** - Track query performance

## 🖼️ Screenshots

### Split-Screen Interface
```
┌─────────────────────────────────────────────────────────────────────┐
│  Header: Veritas-Scope | Query Type | Settings                      │
├──────────────┬──────────────────────────────────┬───────────────────┤
│              │                                  │                   │
│  Chat Panel  │     Interactive Graph View       │   Provenance      │
│              │                                  │   Panel           │
│  - Ask       │  [Query] ──► [Entity A]          │                   │
│    questions │       │          │               │   - Source texts  │
│              │       ▼          ▼               │   - Click to      │
│  - See       │  [Entity B] ◄── [Entity C]       │     verify        │
│    answers   │       │          │               │                   │
│              │       ▼          ▼               │   - Relevance     │
│              │  [Source 1]    [Answer]          │     scores        │
│              │                                  │                   │
├──────────────┴──────────────────────────────────┴───────────────────┤
│  Reasoning Timeline: [Query] → [Search] → [Traverse] → [Answer]     │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
cd veritas-scope
cp .env.example .env
docker compose up --build
```

Services:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/docs
- **Ollama**: http://localhost:11434

### Option 2: Development Mode

**Backend:**
```bash
cd veritas-scope/backend
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

**Frontend:**
```bash
cd veritas-scope/frontend
npm install
npm run dev
```

## 🏗️ Architecture

```
veritas-scope/
├── backend/
│   ├── api/
│   │   ├── main.py           # FastAPI application
│   │   ├── models.py         # Pydantic data models
│   │   └── trace_builder.py  # Reasoning trace constructor
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatPanel.tsx      # Query input & responses
│   │   │   ├── GraphPanel.tsx     # Force-directed graph
│   │   │   ├── ProvenancePanel.tsx # Source viewer
│   │   │   └── ReasoningSteps.tsx  # Timeline component
│   │   ├── store.ts          # Zustand state management
│   │   ├── api.ts            # API client
│   │   └── types.ts          # TypeScript definitions
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 📡 API Endpoints

### Query with Reasoning Trace
```http
POST /api/query
Content-Type: application/json

{
  "query": "How does Component A relate to Project B?",
  "query_type": "local",
  "include_graph": true,
  "animate_trace": true
}
```

**Response:**
```json
{
  "query": "How does Component A relate to Project B?",
  "answer": "Based on the knowledge graph...",
  "reasoning_graph": {
    "nodes": [...],
    "links": [...],
    "reasoning_steps": [...],
    "provenance": [...],
    "total_hops": 3
  },
  "completion_time": 2.45
}
```

### Get Available Output Folders
```http
GET /api/folders
```

### Get Full Knowledge Graph
```http
GET /api/graph/{output_folder}?community_level=2
```

### Get Node Details
```http
POST /api/node/details
{
  "node_id": "entity_abc123",
  "output_folder": "20241228-123456"
}
```

## 🎨 Node Color Legend

| Color | Type | Description |
|-------|------|-------------|
| 🔴 Red | Query | The user's question |
| 🟢 Teal | Entity | Knowledge graph entities |
| 🔵 Blue | Text Unit | Source text chunks |
| 🟢 Green | Community | High-level topic clusters |
| 🟡 Yellow | Document | Original documents |
| 🟣 Purple | Answer | Generated response |

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAPHRAG_API_KEY` | `ollama` | API key for LLM |
| `GRAPHRAG_LLM_MODEL` | `llama3.1-12k` | LLM model name |
| `GRAPHRAG_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `GRAPHRAG_LLM_API_BASE` | `http://localhost:11434/v1` | LLM API endpoint |

### UI Settings

- **Query Type**: Local (entity-based) or Global (community-based)
- **Community Level**: 1-5 (higher = more detailed communities)
- **Temperature**: 0-2 (LLM creativity)
- **Show Labels**: Toggle entity labels on graph
- **3D View**: Switch to 3D graph visualization

## 🧪 Development

### Running Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Building for Production
```bash
# Frontend
cd frontend
npm run build

# Docker
docker compose build
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📜 License

MIT License - see [LICENSE](../LICENSE) for details.

---

**Made with ❤️ for the VeritasGraph community**

*"Trust, but verify. Now you can see why."*
