# Installation

Get VeritasReason installed in under a minute.

!!! success "Available on PyPI"
    `pip install veritas-reason` — that's it.

!!! note "Requirements"
    Python 3.8 or higher. Python 3.11+ recommended.

---

## Basic Installation

```bash
pip install veritas-reason
```

With all optional dependencies:

```bash
pip install veritas-reason[all]
```

### Verify

```bash
python -c "import veritasreason; print(veritasreason.__version__)"
```

---

## Virtual Environment (Recommended)

=== "venv"

    ```bash
    python -m venv venv
    source venv/bin/activate      # Linux / Mac
    venv\Scripts\activate         # Windows
    pip install veritas-reason
    ```

=== "conda"

    ```bash
    conda create -n veritasreason python=3.11
    conda activate veritasreason
    pip install veritas-reason
    ```

---

## Optional Dependencies

Install only what you need:

=== "GPU"

    ```bash
    pip install veritas-reason[gpu]
    ```
    Includes PyTorch with CUDA, FAISS GPU, CuPy.

=== "Visualization"

    ```bash
    pip install veritas-reason[viz]
    ```
    Includes PyVis, Graphviz, UMAP.

=== "LLM Providers"

    ```bash
    pip install veritas-reason[llm-all]          # all providers

    pip install veritas-reason[llm-openai]       # OpenAI
    pip install veritas-reason[llm-anthropic]    # Anthropic
    pip install veritas-reason[llm-gemini]       # Google Gemini
    pip install veritas-reason[llm-groq]         # Groq
    pip install veritas-reason[llm-ollama]       # Ollama (local)
    ```

=== "Cloud"

    ```bash
    pip install veritas-reason[cloud]
    ```
    Includes AWS S3, Azure Blob, Google Cloud Storage.

---

## Install from Source

For the latest development version or to contribute:

```bash
git clone https://github.com/Hawksight-AI/veritas-reason.git
cd veritasreason

pip install -e .          # core only
pip install -e ".[all]"   # all extras
pip install -e ".[dev]"   # dev tools (pytest, black, etc.)
```

If you encounter issues with the PyPI release, install directly from the main branch:

```bash
pip install git+https://github.com/Hawksight-AI/veritas-reason.git@main
```

---

## Troubleshooting

### ModuleNotFoundError

Check you have the right environment active:

```bash
pip list | grep veritasreason
pip install --upgrade veritasreason
```

### Installation fails with dependency errors

```bash
pip install --upgrade pip
pip install build wheel
pip install veritas-reason --no-deps   # install without optional deps first
```

### GPU dependencies fail

Install CPU-only first, then add GPU support:

```bash
pip install veritas-reason
pip install veritas-reason[gpu]
```

### Permission denied

```bash
pip install --user veritasreason      # or use a virtual environment
```

### Windows PyTorch DLL errors

Install the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe). This is a Windows system dependency, not a VeritasReason bug.

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.8 | 3.11+ |
| OS | Windows / Linux / Mac | Linux / Mac |
| RAM | 4 GB | 16 GB+ |
| Storage | 2 GB | 20 GB+ (for models and data) |

---

## Next Steps

- [Getting Started](getting-started.md) — build your first knowledge graph
- [Quickstart Tutorial](quickstart.md) — full step-by-step pipeline
- [Cookbook](cookbook.md) — interactive Jupyter notebook tutorials
