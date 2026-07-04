# VeritasGraph Agent Studio Demo

This folder contains a workspace UI for building and operating AI components.

## Primary page

- Open `demos/agent-studio/index.html`

## Included sections

- Agents
- Tools
- Knowledge
- Guardrails
- Memory
- Data
- Evaluation
- Fine-tune

## Features

- Sidebar navigation between all sections
- Interactive builders for each section
- Live inventory lists with status chips
- KPI cards on top (agents, tools, eval pass, guardrail blocks)
- Save draft to browser localStorage
- Deploy workspace action mock

## Alternate visual

An additional variant is available at:

- `demos/foundry-studio/index.html`

## Sample explorer seed script

Populate the Tools section with a broad general-purpose tool catalog and create
sample explorer agents wired to those tools:

```bash
python3 demos/agent-studio/sample_tools_explorer.py
```

Optional base URL:

```bash
python3 demos/agent-studio/sample_tools_explorer.py --base http://127.0.0.1:8200
```