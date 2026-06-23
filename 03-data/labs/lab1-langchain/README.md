# Lab 1, rebuilt with LangChain (the proof)

This folder answers one question from the layer README: *what does
[LangChain](https://python.langchain.com) actually add to RAG?*

The answer: **nothing conceptual — it productizes the seven phases.** To prove it, this
is [`lab1_simple_rag_langchain_kaggle.ipynb`](lab1_simple_rag_langchain_kaggle.ipynb) —
the **exact same Lab 1** (same `ItshMoh/kubernetes_qa_pairs` dataset, same `bge-small`
embedder, same FAISS index, same Qwen2.5-3B grounded + cited answer and refusal), but
every phase built from a LangChain component instead of by hand.

Run it side by side with [`../cloud-kaggle/lab1_simple_rag_kaggle.ipynb`](../cloud-kaggle/lab1_simple_rag_kaggle.ipynb)
and read the same numbers come out.

| Phase | Hand-built Lab 1 | This LangChain build |
|---|---|---|
| 1 · Sources | `{id, text, topic}` dicts | `Document(page_content, metadata)` |
| 2 · Chunk | hand-written `word_chunks()` | `RecursiveCharacterTextSplitter` |
| 3 · Embeddings | `SentenceTransformer(...).encode` | `HuggingFaceBgeEmbeddings` |
| 4 · Vector store | `faiss.IndexFlatIP` + `.add` | `FAISS.from_documents(...)` |
| 5 · Retrieval | hand-written `retrieve(q, k)` | `store.as_retriever(k=...)` |
| 6 · RAG prompt | manual `apply_chat_template` + `.generate` | `ChatPromptTemplate \| ChatHuggingFace` (LCEL) |

## The point

- **Same pipeline, fewer lines.** Each cell has a one-to-one twin in the hand-built
  lab. LangChain renamed each phase and made it swappable (`FAISS` → `Chroma`, `bge` →
  OpenAI, one line each).
- **The trade-off is visibility.** `rag_chain.invoke(q)` ships fast but hides Phases
  5–6 — which is *why the teaching lab builds them by hand first*. You can only debug
  what you can see, so this notebook still prints the chunks a query loads.
- **Still out of scope, framework or not:** Phase 7 evaluation (RAGAS / LangSmith) and
  Phase 8 data-ops. A framework writes the chain; it doesn't operate it.

## Running it

Same setup as the other labs — see [`../cloud-kaggle/README.md`](../cloud-kaggle/README.md).
**Accelerator = GPU T4 x2**, **Internet = On**, **Run All**. Only the final answer cell
uses the GPU; everything else is CPU and instant. First run also `pip install`s the
LangChain packages (`langchain`, `langchain-community`, `langchain-huggingface`,
`langchain-text-splitters`).
