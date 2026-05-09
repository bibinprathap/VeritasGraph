# VeritasReason Performance Benchmark Suite

This document outlines the architecture, directory structure, and usage of the performance benchmarking suite for the VeritasReason Agentic RAG framework.

## Architecture

The suite is organized into modular layers mirroring the library's internal structure, which allows for isolated performance testing of specific components.

### High-Level Design Principles

- **Isolation:** Use of mocks to ensure benchmarks measure algorithm logic.

- **Virtualization:** A custom `conftest.py` virtualization layer allows tests to run without heavy local dependencies.

- **Pedantic Measurement:** High-iteration counts and statistical rounds to filter out system noise.

## Directory Structure

Based on the current production environment, the suite is organized as follows:

|                       |                                                                    |
| --------------------- | ------------------------------------------------------------------ |
| Folder                | Description                                                        |
| context/              | Low-level graph operations and memory storage logic.               |
| context_memory/       | Agent-level memory management and GraphRAG retrieval patterns.     |
| core_processing/      | Throughput tests for NER, extraction, and graph building.          |
| export/               | Serialization benchmarks for JSON, CSV, RDF, and GraphML.          |
| infrastructure/       | Support scripts, including the regression comparison engine.       |
| input_layer/          | Ingestion, parsing, and splitting performance.                     |
| normalize/            | Text cleaning, encoding handling, and date normalization.          |
| ontology/             | Inference, serialization, and namespace management overhead.       |
| output_orchestration/ | Parallelism and execution pipeline management.                     |
| quality_assurance/    | Deduplication and conflict resolution strategies.                  |
| results/              | Storage for benchmark JSON outputs and performance baselines.      |
| storage/              | Latency tests for Vector stores (FAISS) and Triplet stores (Jena). |
| visualization/        | Computational cost of layout algorithms and chart rendering.       |

## Usage

### Running the Suite

To run the full suite and generate a new results file:

```bash
python benchmarks/benchmark_runner.py
```

### Strict Mode (CI/CD)

The suite is designed to integrate with automated pipelines. Using the --strict flag will cause the runner to return a non-zero exit code if a performance regression greater than 15% is detected.

```bash
python benchmarks/benchmark_runner.py --strict
```



### Performance Comparison

The comparison engine (infrastructure/compare.py) uses Z-scores to distinguish between actual performance regressions and environmental noise.

- Regression: Change > 15% AND Z-score > 2.0.

- Noise: Change > 15% but Z-score < 2.0.

### Updating Baseline

When a performance change is intentional (e.g., a more complex but necessary algorithm is added), update the "gold standard" baseline:

```bash
cp benchmarks/results/run_latest.json benchmarks/results/baseline.json
```
