# aibase

A full-stack AI platform — **from infrastructure to application**.

The repo is organized around the **5 layers of the AI stack**. Each choice you
make at any layer — from the hardware up to the user interface — has direct
implications on the solution's **quality, speed, cost, and safety**.

```
aibase/
├── 01-infrastructure/   # GPUs & compute: on-premise, cloud, local
├── 02-models/           # model registry, serving, evaluation
├── 03-data/             # sources, pipelines, vector store, RAG
├── 04-orchestration/    # planning, execution, review, MCP
├── 05-application/       # interfaces & integrations
├── shared/              # cross-cutting config & scripts
└── docs/                # design notes, references
```

## The 5 layers

| # | Layer | What it covers |
|---|-------|----------------|
| 1 | **Infrastructure** | AI hardware (GPUs). Deploy on-premise, in the cloud, or locally. |
| 2 | **Models** | Open vs proprietary, large vs small (LLM/SLM), specialization. |
| 3 | **Data** | Data sources, processing pipelines, vector databases, RAG. |
| 4 | **Orchestration** | Break tasks into thinking → execution → review. Protocols like MCP. |
| 5 | **Application** | Interfaces (text/image/audio…) and integrations with other tools. |

## Getting started

Each layer directory has its own `README.md` describing scope and intended
contents. Start at `01-infrastructure/` and work up, or jump to the layer you
need.
