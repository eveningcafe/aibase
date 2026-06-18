# 03 · Data

A base model is frozen at a **knowledge cutoff** and has never seen your private
data. This layer supplements it with extra, fresh, or private knowledge **at
answer time** — no retraining. The headline technique is **RAG**
(Retrieval-Augmented Generation): retrieve the relevant context, then put it in
the prompt.

The line from the Models layer holds: **RAG for knowledge, fine-tune for
behaviour** ([`02-models/`](../02-models/)). If the model has the skill but lacks
the facts, you are in the right place.

## The pipeline

Data flows one way at build time, and is queried in reverse at answer time:

```
BUILD (offline, batch)                          ANSWER (online, per query)
  sources → clean → chunk → embed → vector store   query → embed → retrieve → rerank
                                          │                                      │
                                          └──────────────► vector store ◄────────┘
                                                                                 │
                                                          augment prompt → model → answer
```

The phases below follow this flow, and map onto the two hands-on
[labs](#labs-run-on-a-free-kaggle-gpu): build a RAG pipeline (Lab 1), then
measure it (Lab 2).

Two rules of thumb run through everything:

1. The model can only answer from what you **retrieve** — bad retrieval caps
   quality no matter how good the model is. *Most RAG failures are retrieval
   failures.*
2. Garbage in, garbage out — the pipeline (clean + chunk) decides what
   retrieval can even find.

---

## Phase 1 · Sources

The raw knowledge you want the model to use. It arrives in three broad shapes,
and the shape decides how much pipeline work you do before it is usable.

| Shape | Examples | Pipeline cost |
|-------|----------|---------------|
| **Unstructured** | PDFs, web pages, docs, email, chat logs, transcripts | High — parse, clean, chunk |
| **Semi-structured** | Markdown, HTML, JSON, CSV, tables | Medium — structure-aware splitting |
| **Structured** | SQL databases, APIs, spreadsheets | Low for the data; you often query it directly instead of embedding |

Two cross-cutting concerns from day one:

- **Freshness** — is this a one-time dump or a feed that changes? That decides
  whether you re-index nightly, on write, or never (Phase 8).
- **Permissions** — who is allowed to see each document? Access control must
  survive into retrieval, or RAG becomes a data-leak engine. Carry an ACL /
  tenant tag as metadata on every chunk.

Not everything belongs in a vector store. Exact lookups (an order status, a
price) belong in a SQL/API call the agent makes (Layer 4); RAG is for
*fuzzy, semantic* recall over text.

---

## Phase 2 · Pipelines — clean & chunk

Raw sources are cleaned (strip boilerplate, headers/footers, navigation, repeated
legal text) and then **chunked** — split into passages small enough to embed and
to fit in the prompt, large enough to carry meaning.

Chunking is the highest-leverage, most-overlooked choice in the whole layer. Too
big and a chunk dilutes the signal and wastes context; too small and it loses the
surrounding meaning.

| Strategy | How | When |
|----------|-----|------|
| **Fixed-size** | N tokens with an overlap (e.g. 512 / 64) | default, simple, robust |
| **Recursive** | split on paragraphs → sentences → words until it fits | good for prose |
| **Structure-aware** | split on Markdown headings, code blocks, table rows | docs/code with clear structure |
| **Semantic** | split where the topic shifts (embedding-distance) | best quality, more compute |

Two knobs matter most:

- **Chunk size** — measured in *tokens*, not characters. A common range is
  256–1024; smaller favours precise retrieval, larger favours context.
- **Overlap** — repeat the last ~10–20% of one chunk at the start of the next so
  a sentence split across the boundary isn't lost.

Each chunk is stored with **metadata**: source id, title, page/section, timestamp,
and the ACL/tenant tag from Phase 1. Metadata is what lets you filter ("only this
customer's docs", "only since 2026") and cite the answer back to a source.

---

## Phase 3 · Embeddings

An **embedding** is a vector (a list of numbers, e.g. 384–1536 of them) that
encodes the *meaning* of a chunk. Texts with similar meaning land near each other,
so "how do I reset my password" sits close to "forgot login credentials" even with
no shared words. Retrieval is then just *find the nearest vectors*.

An embedding model is its own, separate model from the LLM — usually small and
cheap (runs on CPU or a tiny slice of GPU).

| Choose on | Why it matters |
|-----------|----------------|
| **Dimensions** | bigger = more nuance but more storage + slower search (384 vs 1024 vs 1536) |
| **Max input length** | the chunk must fit the embedder's window, not just the LLM's |
| **Domain / language** | a model strong in your language/domain (e.g. Vietnamese, legal, code) wins |
| **Open vs API** | self-host (`bge`, `e5`, `gte`) keeps data private; API (OpenAI, Cohere, Voyage) is zero-ops |

Non-negotiable rule: **embed the documents and the queries with the same model.**
Two models produce incomparable vector spaces, and "near" becomes meaningless. If
you change the embedding model, you must re-embed the entire corpus.

---

## Phase 4 · Vector store

A database built to store millions of embeddings and answer *nearest-neighbour*
queries in milliseconds. A brute-force scan is exact but O(n); real stores use an
**ANN** (approximate nearest-neighbour) index that trades a sliver of recall for a
huge speed-up.

| Index | Idea | Trade-off |
|-------|------|-----------|
| **Flat** | compare against every vector | exact, but slow past ~100k |
| **HNSW** | a navigable graph of neighbours | fast + high recall; more memory (the common default) |
| **IVF** | cluster vectors, search nearest clusters | smaller memory; tune `nprobe` for recall |

| Store | Shape | Good for |
|-------|-------|----------|
| **FAISS** (lib) | in-process library | labs, prototypes, embedded use *(our labs)* |
| **Chroma** | lightweight local server | small apps, quick start |
| **pgvector** | Postgres extension | already on Postgres; SQL + vectors together |
| **Qdrant / Weaviate / Milvus** | dedicated vector DB | production scale, metadata filtering, hybrid search |

The **similarity metric** must match how the embedding model was trained — usually
**cosine** (angle) or **dot product**; some use **L2** (Euclidean). And a good
store filters on metadata *during* the search (e.g. `tenant = X AND date > Y`), so
permissions and freshness are enforced at retrieval, not after.

---

## Phase 5 · Retrieval

Answer time. The query is embedded with the same model, the store returns the
**top-k** nearest chunks, and those become the model's context.

- **top-k** — how many chunks to fetch (often 3–10). Too few starves the model;
  too many adds noise and burns context budget.
- **Similarity search alone misses keywords.** Dense (embedding) retrieval is
  great at meaning but can miss exact terms — product codes, error numbers, rare
  names. **Hybrid search** combines dense with classic keyword (**BM25**) and
  fuses the rankings, recovering both.
- **Reranking** — fetch a generous top-k (say 30) with the cheap vector search,
  then a small **cross-encoder reranker** rescores query-vs-chunk pairs and keeps
  the best 3–5. It is slower per pair but dramatically lifts precision, because it
  reads the query and the chunk *together* instead of comparing pre-computed
  vectors. This is the single biggest quality lever after chunking.

```
query → [dense top-30] ∪ [BM25 top-30] → rerank → top-5 → prompt
```

---

## Phase 6 · RAG — putting it together

Retrieval-Augmented Generation stitches the retrieved chunks into the prompt so
the model answers *from them*, with a citation back to the source:

```
SYSTEM: Answer only from the context. If it isn't there, say you don't know.
CONTEXT: <chunk 1> <chunk 2> … <chunk k>
USER: <the question>
```

This is the **open-book exam** vs memorizing: the model looks things up at answer
time instead of recalling from training. The payoffs are fresh + private knowledge
without retraining, **citations** (answers grounded in named sources), and a cheap
way to update knowledge — re-index, don't re-train.

Beyond the basic loop:

| Pattern | What it adds |
|---------|--------------|
| **Query rewriting** | clean up / expand the user's question before retrieval |
| **Multi-query** | retrieve for several rephrasings, union the results |
| **HyDE** | draft a hypothetical answer, embed *that* to retrieve |
| **Agentic RAG** | the agent decides *whether*, *what*, and *how often* to retrieve, and can search again (Layer 4) |

Agentic RAG is where Data meets [Orchestration](../04-orchestration/): retrieval
becomes a tool the agent calls in a loop, not a fixed pre-step.

---

## Phase 7 · Evaluation

"The demo answered well" is not evidence — the same trap as the Models layer. RAG
has **two** things to measure, because it has two stages that can each fail:

| Stage | Question | Metrics |
|-------|----------|---------|
| **Retrieval** | did we fetch the right chunks? | recall@k, precision@k, MRR, hit-rate |
| **Generation** | did the answer use them faithfully? | faithfulness (no hallucination), answer relevance, correctness |

The killer failure mode is **hallucination** — a fluent answer not supported by
the retrieved context. **Faithfulness** measures exactly that: is every claim in
the answer grounded in a chunk? Frameworks like **RAGAS** score faithfulness,
answer relevance, and context recall/precision, often using an LLM-as-judge.

Diagnose failures by stage:

- Wrong/empty answer but the right chunk *was* retrieved → a **generation**
  problem (prompt, model, or context too noisy).
- Right answer impossible because the chunk *wasn't* retrieved → a **retrieval**
  problem (chunking, embedding, top-k, or you need a reranker).

Knobs to sweep against a held-out question set: chunk size, overlap, top-k,
hybrid on/off, reranker on/off, embedding model. Report quality **with** latency
and cost — never a single number.

---

## Phase 8 · Data-ops — keeping it alive

A RAG corpus is not build-once. It is a pipeline that must stay fresh, correct,
and affordable — the data layer's equivalent of MLOps.

| Concern | The question |
|---------|--------------|
| **Freshness / re-indexing** | source changed — re-embed on write, nightly, or never? Stale chunks give confidently wrong answers. |
| **Versioning** | which corpus + embedding-model version produced this answer? (reproducibility, like the model registry) |
| **Cost** | embedding + storage + per-query retrieval + the extra prompt tokens RAG adds |
| **Latency** | retrieval + rerank time is added to every request |
| **Governance** | PII, ACLs enforced at retrieval, the right to delete a document (and its vectors), audit/citation trail |

The deletion case is sharp: if a user exercises "delete my data", the chunks
*and their embeddings* must go — a copy left in the vector store is still a leak.

---

## When RAG vs fine-tune vs just use the context window

- **Use the context window** — the knowledge is small and fits in the prompt
  (a few documents). Simplest; no infrastructure. As context windows grow, this
  covers more cases — but it re-pays the token cost on *every* call and can't
  scale to millions of documents.
- **RAG** — knowledge is large, changes, or is private. The default for grounding
  in your own corpus.
- **Fine-tune** ([`02-models/`](../02-models/)) — you need *behaviour*, not facts.
  Often **combined** with RAG: fine-tune the tone, retrieve the facts.

In short: **small & static → context window · large/fresh/private → RAG ·
behaviour → fine-tune.** They stack.

### RAG vs long context 

| Dimension | Long context — stuff the window | RAG — retrieve first |
|-----------|---------------------------------|----------------------|
| **Infrastructure** | the "no-stack stack" — no DB, embedder, reranker, or sync to keep | heavy: chunking + embedder + vector DB + reranker + keeping vectors in sync |
| **Retrieval reliability** | no retrieval step — the model sees everything | semantic search is probabilistic → **silent failure**: the answer was there, retrieval just didn't return it |
| **Cross-doc / global reasoning** | sees full documents → can spot what's *missing* (e.g. "which requirements were omitted from the release?") | only isolated snippets → can't reason over the *gap between* documents |
| **Cost per query** | reprocesses every token on **every** call (a 500-pg manual ≈ 250k tokens each time) | pays the processing cost **once at index time**; fetches a few chunks per query |
| **Accuracy at scale** | attention dilutes — a needle buried in a huge context is missed or hallucinated | top-k (say 5 chunks) removes the haystack → the model focuses on signal |
| **Data ceiling** | ~1M tokens is a drop against enterprise data lakes (TB–PB) | a retrieval layer filters an effectively infinite corpus down to what fits |

The decision rule that falls out:

- **Bounded data + global reasoning** — one legal contract, a single book to
  summarize → **long context** wins (simpler stack, sees the whole picture).
- **Fresh, private, or effectively infinite knowledge** — an enterprise corpus →
  **RAG** remains the only viable warehouse.

Caveat on the cost line: **prompt caching** offsets long context for *static* data,
but a *dynamic* corpus pays the full token tax on every request.

---

## Labs (run on a free Kaggle GPU)

Interactive Kaggle notebooks, so any student can reproduce them with no hardware
of their own — the same **T4 (16 GB)** and **Qwen2.5-3B-Instruct** as the Models
labs, so the layers chain. Setup is in [`labs/README.md`](labs/README.md).

| Lab | Phase | What you'll do | Time |
|-----|-------|----------------|------|
| **1 · Build RAG** | chunk → embed → retrieve → generate | chunk a small **Kubernetes/SRE runbook** corpus, embed with `bge-small`, index in FAISS, retrieve, and answer with Qwen2.5-3B — show the same ops question hallucinated vs grounded | ~50 min |
| **1b · Real data** *(bonus)* | ingest → clean → HNSW at scale | run the same pipeline over **30k real Stack Overflow k8s Q&A** ([dataset](https://huggingface.co/datasets/mcipriano/stackoverflow-kubernetes-questions), CC-BY-SA-4.0): strip HTML, chunk, index with HNSW, and see retrieval get hard at scale | ~40 min |
| **2 · Evaluate RAG** | retrieval + generation eval | score faithfulness, answer relevance, and context recall on a held-out set; sweep chunk-size / top-k / reranker and read the trade-off | ~45 min |

Same constraints as the Models labs: free GPU, fp16, Internet **On** for the
first cell (installs deps + pulls the embedding model and LLM).

---

## Aside · the data wall

The Models aside looked *up* the capability axis (superintelligence). The Data
layer's horizon question looks at its own fuel: **are we running out of training
data?**

Frontier pre-training has consumed much of the high-quality public text on the
internet. Projections (Epoch AI) put the usable public-text stock on track to be
exhausted around the **late 2020s** — the "data wall." Three responses are in
play:

- **Synthetic data** — models generate their own training data. Powerful, but
  risks **model collapse**: train on too much model output and quality degrades
  as the distribution narrows. Needs careful filtering and a human/real-data
  anchor.
- **Private & proprietary data** — the public web is tapped out, so the moat moves
  to data nobody else has: enterprise records, licensed archives, user
  interactions. This is *why* the data layer captures real money.
- **Human labeling at scale** — RLHF and high-quality annotation as a paid
  industry.

This closes the loop with the revenue pyramid in the top-level
[`README.md`](../README.md): **Scale AI ≈ $2B, and Meta paid $14.3B for a 49%
stake.** That price isn't for software — it's for the *data and the labeling
pipeline*. When public text runs low, whoever owns the data (and the means to
make more of it) holds the leverage. The model layer gets the headlines; the data
layer increasingly holds the moat.
