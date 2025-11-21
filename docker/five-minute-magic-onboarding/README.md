## Five-Minute Magic Onboarding

Zero-config Docker Compose stack that spins up the VeritasGraph app, Neo4j, and Ollama on a shared bridge network.

### Prerequisites

- Docker Engine 24+
- Docker Compose plugin 2.20+
- At least 16 GB RAM (Ollama + Neo4j + app)

### Structure

```
docker/five-minute-magic-onboarding/
├── .env                     # Credentials and shared config
├── docker-compose.yaml      # Orchestrates ollama + neo4j + app
├── app/                     # Gradio UI container build context
├── neo4j/conf/neo4j.conf    # Optional overrides
└── ollama/Modelfile         # Defines llama3.1-12k custom model
```

### Configure

1. Copy `.env` and set credentials:
	```env
	DATABASE_USER=neo4j
	DATABASE_PASSWORD=your_password_here
	NEO4J_USER=${DATABASE_USER}
	NEO4J_PASS=${DATABASE_PASSWORD}
	```
2. (Optional) adjust `ollama/Modelfile` for different LLMs.

### Run

```bash
cd docker/five-minute-magic-onboarding
docker compose up --build
```

What happens:
- **ollama** container loads `llama3.1-12k` if missing and exposes `11434`.
- **neo4j** container boots with auth from `.env` and exposes `7474/7687`.
- **app** container mounts `../graphrag-ollama-config`, injects env vars, and serves Gradio UI on `7860`.

### Verify

- Ollama tags: `curl http://localhost:11434/api/tags`
- Neo4j browser: http://localhost:7474/
- Gradio UI: http://127.0.0.1:7860/

### Stop & Cleanup

```bash
docker compose down           # stop containers
docker compose down -v        # stop and remove volumes (models/data)
```

This workflow delivers a reproducible, single-command demo for VeritasGraph onboarding.
