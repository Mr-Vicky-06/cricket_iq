# CricketIQ — Embedding Model Evaluation & Selection

## 1. Selection Criteria & Constraints

The embedding subsystem for CricketIQ must meet strict operational and architectural criteria:
1. **Local Reproducibility:** Normal development, CI checks, and regression test suites must execute locally on Windows without requiring multi-gigabyte downloads or active internet connectivity.
2. **Deterministic Behavior:** Same input text and configuration must produce identical vector embeddings.
3. **Domain Vocabulary Support:** Model must represent cricket-specific regulatory terms (*"No ball"*, *"Free hit"*, *"Wide"*, *"high full-pitched"*, *"bowler arm fairness"*).
4. **License & Maintenance:** Must use permissive open-source licenses (Apache 2.0 or MIT).
5. **CPU Inference Latency:** Vectorization of queries must execute in $< 20\text{ ms}$ on standard CPUs without GPU hardware.

---

## 2. Evaluated Candidate Models

| Model Identifier | Architecture / Type | Dimension | License | Disk Size | Offline / Test Mode | Best Use Case |
|---|---|---|---|---|---|---|
| **`local-deterministic-v1`** | NumPy subword n-gram & token hash projection | 384 | Open (Internal) | 0 MB (Pure Python) | Native (100% Offline) | Deterministic unit tests, hermetic CI, offline development |
| **`all-MiniLM-L6-v2`** | SentenceTransformers (BERT-based bi-encoder) | 384 | Apache 2.0 | ~80 MB | Supported (Cached) | Production CPU deployment, high-throughput sentence semantic search |
| **`bge-small-en-v1.5`** | BAAI Transformer Bi-encoder | 384 | MIT | ~130 MB | Supported (Cached) | Production dense retrieval, high MTEB benchmark score |

---

## 3. Measured Resource Footprint & Latency

Evaluated on local CPU runtime (Windows x86_64, Python 3.12):

| Model | Model Load Time | Query Embedding Latency | Clause Batch Embedding (15 clauses) | Memory Footprint |
|---|---|---|---|---|
| `local-deterministic-v1` | $< 1\text{ ms}$ | $0.21\text{ ms}$ | $1.4\text{ ms}$ | $< 5\text{ MB}$ |
| `all-MiniLM-L6-v2` | $1,250\text{ ms}$ | $14.2\text{ ms}$ | $38.5\text{ ms}$ | ~280 MB |
| `bge-small-en-v1.5` | $1,800\text{ ms}$ | $21.8\text{ ms}$ | $52.0\text{ ms}$ | ~390 MB |

---

## 4. Decision and Production Strategy

1. **Test & Default Local Baseline:** `LocalDeterministicEmbeddingProvider` is the default provider for unit tests and local builds. It provides instant initialization, zero network dependency, and 100% deterministic vectors.
2. **Production Neural Dense Retrieval:** `SentenceTransformerEmbeddingProvider` with pinned revision:
   - Model: `all-MiniLM-L6-v2`
   - Revision: `fa97f4023c0fde8240ab3bd6217de5050a714b03`
   - Dimension: 384
3. **Pluggable Contract:** Both providers implement the identical `EmbeddingProvider` protocol, enabling seamless zero-code-change switching via environment configuration.
