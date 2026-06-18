---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 26px; }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; }
  code { font-size: 0.8em; }
  pre { font-size: 0.7em; line-height: 1.25; }
  table { font-size: 0.78em; }
  section.lead h1 { font-size: 52px; }
  section.lead { text-align: center; }
  footer, header { color: #888; font-size: 14px; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# Data — deep dive

<!--
The Data layer (Layer 3). Labs run on the same free Kaggle T4 (16 GB) and the same
Qwen2.5-3B as the Models labs, so the layers chain. Maps 1:1 to 03-data/README.md.
Pace: a few slides of concept, then the notebook.
-->

---

## Why this layer

A base model is frozen at a **knowledge cutoff** and has never seen your **private
data**. This layer supplements it — fresh & private knowledge **at answer time**,
no retraining.

The headline technique is **RAG** (Retrieval-Augmented Generation): retrieve the
right context, put it in the prompt.

The Models-layer line holds: **RAG for knowledge, fine-tune for behaviour.**

<!--
If the model has the skill but lacks the facts, you're in the right layer. This is
the line students forget — knowledge vs behaviour.
-->

---

## The pipeline

```
BUILD (offline)                         ANSWER (per query)
 sources → clean → chunk → embed →        query → embed → retrieve → rerank
                          vector store ◄──────────────────────────────┘
                                          augment prompt → model → answer
```

Two rules of thumb:

- The model answers only from what you **retrieve** — *most RAG failures are
  retrieval failures.*
- Garbage in, garbage out — **clean + chunk** decide what retrieval can find.

<!--
This is the agenda. Build = Lab 1; measure = Lab 2. Built one way, queried in
reverse. Burn in the two rules now — they explain every later phase.
-->

---

## Sources — three shapes

The shape decides how much pipeline work before it's usable.

| Shape | Examples | Pipeline cost |
|-------|----------|---------------|
| **Unstructured** | PDFs, web, docs, email, transcripts | high — parse, clean, chunk |
| **Semi-structured** | Markdown, HTML, JSON, CSV | medium — structure-aware split |
| **Structured** | SQL, APIs, sheets | low — often query it directly |

From day one: **freshness** (one-time dump or a feed?) and **permissions** (carry
an ACL/tenant tag on every chunk).

<!--
Not everything belongs in a vector store — exact lookups (order status, price) are
a SQL/API call the agent makes (Layer 4). RAG is for fuzzy, semantic recall. ACLs
must survive into retrieval or RAG becomes a data-leak engine.
-->

---

## Chunking — the highest-leverage knob

Split sources into passages: small enough to embed + fit the prompt, large enough
to carry meaning. Too big dilutes; too small loses context.

| Strategy | When |
|----------|------|
| **Fixed-size** (N tokens + overlap) | default, robust |
| **Recursive** (para → sentence → word) | prose |
| **Structure-aware** (headings, code, rows) | docs/code |
| **Semantic** (split where topic shifts) | best, more compute |

**Size** 256–1024 *tokens* · **overlap** ~10–20% · **metadata** (source, page, date,
ACL) for filtering + citations.

<!--
Most-overlooked choice in the layer. Tokens, not characters. Overlap stops a
sentence split across a boundary from being lost. Metadata = how you filter and
cite.
-->

---

## Embeddings — meaning as a vector

A chunk → a vector (384–1536 numbers) encoding **meaning**. Similar meaning lands
near → retrieval is *find the nearest vectors*. "reset password" ≈ "forgot login"
with no shared words.

A separate, small, cheap model (CPU-friendly). Choose on: **dimensions**, **max
input length**, **domain/language**, **open vs API**.

**Rule: embed documents and queries with the *same* model.** Change it → re-embed
everything.

<!--
The embedder is NOT the LLM. Two models → incomparable spaces, "near" is
meaningless. The chunk must fit the embedder's window, not just the LLM's. bge/e5/
gte self-host; OpenAI/Cohere/Voyage are zero-ops.
-->

---

## Vector store + ANN index

A DB for millions of embeddings, nearest-neighbour in ms. Brute force is exact but
O(n); **ANN** trades a sliver of recall for big speed.

| Index | Idea | Trade-off |
|-------|------|-----------|
| **Flat** | compare all | exact, slow past ~100k |
| **HNSW** | neighbour graph | fast + high recall, more memory (default) |
| **IVF** | cluster + search nearest | smaller memory, tune `nprobe` |

Stores: **FAISS** (labs) · Chroma · **pgvector** · Qdrant/Weaviate/Milvus. Match
the **metric** (cosine / dot / L2) to the embedder; filter metadata *during*
search.

<!--
FAISS in our labs. Metric must match how the embedder was trained — usually
cosine. Filtering during search is how tenant + freshness get enforced at
retrieval, not after.
-->

---

## Retrieval — dense isn't enough

Query embedded with the same model → store returns **top-k** (often 3–10).

- **Dense alone misses keywords** — product codes, error numbers, rare names.
  **Hybrid** = dense + **BM25** keyword, fuse the rankings.
- **Reranking** — fetch ~30 cheap, a **cross-encoder** rescores query+chunk
  *together*, keep best 3–5. Biggest quality lever after chunking.

```
query → [dense top-30] ∪ [BM25 top-30] → rerank → top-5 → prompt
```

<!--
top-k too low starves the model; too high adds noise + burns context. The
cross-encoder reads query and chunk together instead of comparing pre-computed
vectors — slower per pair, much higher precision.
-->

---

## RAG — the open-book exam

Stitch retrieved chunks into the prompt; the model answers *from them*, with a
citation.

```
SYSTEM: Answer only from the context. If it's not there, say you don't know.
CONTEXT: <chunk 1> … <chunk k>
USER:    <question>
```

Look it up at answer time vs recall from training. Payoff: **fresh + private**
knowledge, **citations**, update by **re-index not re-train**.

Beyond basic: **query rewriting · multi-query · HyDE · agentic RAG** (retrieval
becomes a tool the agent loops on → Layer 4).

<!--
The framing students remember: open-book vs memorizing. Agentic RAG is the bridge
to orchestration — the agent decides whether/what/how-often to retrieve, not a
fixed pre-step.
-->

---

## Evaluation — two stages, two failures

"It demoed well" isn't evidence. RAG has **two** stages that each fail:

| Stage | Question | Metrics |
|-------|----------|---------|
| **Retrieval** | right chunks fetched? | recall@k, precision@k, MRR |
| **Generation** | answer faithful to them? | faithfulness, answer relevance |

**Hallucination** = fluent answer not in the context. **Faithfulness** measures it.
**RAGAS** scores these (often LLM-as-judge).

Diagnose: right chunk retrieved but bad answer → **generation**. Answer impossible
because chunk missing → **retrieval**.

<!--
Sweep chunk size / overlap / top-k / hybrid / reranker / embedder against a
held-out set. Report quality WITH latency + cost. This is Lab 2.
-->

---

## Data-ops — keep the corpus alive

Build-once is a trap. The data layer's MLOps:

| Concern | The question |
|---------|--------------|
| **Freshness** | re-embed on write / nightly / never? stale = confidently wrong |
| **Versioning** | which corpus + embedder made this answer? |
| **Cost** | embedding + storage + retrieval + extra prompt tokens |
| **Latency** | retrieval + rerank added to every request |
| **Governance** | PII, ACLs at retrieval, **right to delete** |

Deletion is sharp: delete a doc → its **chunks *and* embeddings** must go, or it's
still a leak.

<!--
Mirror of the Models MLOps slide. The data layer needs versioning + gates too.
Stress the deletion case — a copy left in the vector store defeats "delete my
data".
-->

---

## RAG vs fine-tune vs context window

- **Context window** — knowledge is small, fits the prompt. Simplest; but re-pays
  tokens every call, can't scale to millions of docs.
- **RAG** — large, fresh, or private. The default for grounding.
- **Fine-tune** (Layer 2) — you need *behaviour*, not facts.

**Small & static → context window · large/fresh/private → RAG · behaviour →
fine-tune.** They **stack** — fine-tune the tone, retrieve the facts.

<!--
As context windows grow this line shifts, but token cost per call and corpus scale
keep RAG alive. The "they stack" point is the nuance — it's not either/or.
-->

---

## RAG vs long context — when does the window win?

~1M-token windows (~700k words) tempt you to just paste everything. Six dimensions:

| Dimension | Long context | RAG |
|-----------|-------------|-----|
| **Infra** | no-stack stack | DB + embedder + reranker + sync |
| **Retrieval** | sees everything | probabilistic → **silent failure** |
| **Global reasoning** | spots what's *missing* | only isolated snippets |
| **Cost/query** | reprocess all tokens **every** call | process **once** at index time |
| **Accuracy at scale** | attention dilutes (needle-in-haystack) | top-k = just the needles |
| **Data ceiling** | ~1M tokens vs TB–PB lakes | filters infinite corpora |

**Bounded + global reasoning** (one contract, one book) → **long context**.
**Fresh / private / infinite** → **RAG**.

<!--
Framing from IBM Technology "Is RAG Still Needed?" (2026). The killer RAG point is
silent failure + the missing-data case (RAG can't see the gap between two docs).
The killer long-context point is cost: a 500-pg manual ≈ 250k tokens reprocessed
every query; prompt caching helps only for static data. Don't sell either as dead.
-->

---

## Lab — RAG retrieval, made visible

One focused notebook (~35 min) on a free **Kaggle T4** with **Qwen2.5-3B**, over a
**real public k8s Q&A dataset** ([`kubernetes_qa_pairs`](https://huggingface.co/datasets/ItshMoh/kubernetes_qa_pairs)).

The heart of RAG is **retrieval** — so we make it visible:

- **print the exact chunks** a question loads into the prompt
- **top-k** — how many chunks to load (watch it grow + drift)
- **chunk size** — small = precise vs large = more context
- **reranker** — a cross-encoder reorders candidates (see the right chunk jump to #1)
- then feed the top chunks to Qwen → **grounded, cited** answer + a *"I don't know"* refusal

Pick **T4**, Internet **On** for the first cell.

<!--
Star is retrieval: cell 3 prints the loaded chunks, so students can debug RAG.
Reranker demo lands: vector grabs the wrong "images" chunk, reranker promotes the
real garbage-collection answer. Public data the model often already knows, so the
lesson here is retrieval quality + citations, not blocking hallucination. One lab
fits a 120-min session: ~60-75 min lecture + ~35 min hands-on.
-->

---

## Aside · the data wall

The Models aside looked *up* (superintelligence). Data's horizon looks at its
**fuel**: are we running out of training data?

Frontier pre-training has consumed most high-quality public text — usable stock
projected to run out **~late 2020s** (Epoch AI). Three responses:

- **Synthetic data** — risks **model collapse** (train on model output → quality
  narrows). Needs a real-data anchor.
- **Private/proprietary data** — the moat moves to data nobody else has.
- **Human labeling at scale** — RLHF as an industry.

**Scale AI ≈ $2B; Meta paid $14.3B for 49%.** That price is for *data + labeling*,
not software — the data layer holds the moat.

<!--
Closes the loop with the revenue-pyramid slide. When public text runs low, whoever
owns the data (and the means to make more) holds leverage. Model layer gets
headlines; data layer increasingly holds the moat. Hold the dates lightly —
projections, not facts.
-->
