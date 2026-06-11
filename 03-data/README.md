# 03 · Data

Base models are trained on publicly available info with a **knowledge cutoff**,
which might not be complete for your task. This layer supplements the model with
extra, fresh, or private data.

## Components

| Dir | Purpose |
|-----|---------|
| `sources/` | The data itself: documents, DBs, APIs, files that supplement model knowledge. |
| `pipelines/` | Pre-processing & post-processing: ingest, clean, chunk, transform. |
| `vector-store/` | Vector databases — external data vectorized into **embeddings**, saved for fast retrieval. |
| `rag/` | Retrieval-Augmented Generation: retrieve relevant context and augment the prompt. |

## Flow

```
sources → pipelines (clean/chunk) → embed → vector-store → rag (retrieve) → model
```

RAG lets the model pull in knowledge the base model doesn't have, without
retraining. Use this when the task needs recent or private information.
