"""
rag.py -- Task 2 retrieval layer (Modular Spec Summarization, LAsset Input Pre-processing).
Knowledge source: NEORV32 datasheet AsciiDoc sources pinned to the RTL-matching commit.
Paper params: 1000-char chunks, 200 overlap, top-20 retrieval (arXiv:2601.02624 SIV).
Deviations (logged): corpus = .adoc sources in lieu of rendered PDF; embeddings =
bge-small-en-v1.5 in lieu of text-embedding-ada-002 (dev-tier substitution).
Query construction: name + units + Stage-A header (v1, adopted via R4 A/B eval:
v0 11/22 hit@1 -> v1 22/22, mean rank 1.0).
"""

from pathlib import Path
import json, hashlib
import numpy as np

CHUNK_SIZE = 1000
CHUNK_OVLP = 200
TOP_K      = 20
EMB_MODEL  = "text-embedding-ada-002"
CACHE_DIR  = Path("stage_a_out/rag_cache")

# module-level state, set by build_index()
_chunks, _embs, _search, _qmodel = None, None, None, None


def _load_corpus(spec_dir: Path):
    docs = [(p.name, p.read_text(encoding="utf-8", errors="ignore"))
            for p in sorted(spec_dir.glob("*.adoc"))]
    if not docs:
        raise FileNotFoundError(f"no .adoc files under {spec_dir.resolve()}")
    return docs


def _chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVLP):
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text) - overlap, 1), step)]


def _build_chunks(docs):
    # chunk per source file, never across file boundaries (attribution integrity)
    return [{"id": f"{src}#{j}", "source": src, "text": c}
            for src, text in docs for j, c in enumerate(_chunk_text(text))]


def build_index(spec_dir):
    """Chunk + embed (cached) + index. Returns (chunks, embeddings)."""
    global _chunks, _embs, _search
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    _chunks = _build_chunks(_load_corpus(Path(spec_dir)))
    tag = EMB_MODEL.replace("/", "_")
    fp  = hashlib.sha256((tag + "".join(c["text"] for c in _chunks)).encode()).hexdigest()[:16]
    emb_f = CACHE_DIR / f"emb_{fp}.npy"

    if emb_f.exists():
        _embs = np.load(emb_f)
    else:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(EMB_MODEL)
        _embs = np.asarray(m.encode([c["text"] for c in _chunks], batch_size=64,
                                    show_progress_bar=True, normalize_embeddings=True),
                           dtype=np.float32)
        np.save(emb_f, _embs)
        (CACHE_DIR / f"chunks_{fp}.jsonl").write_text(
            "\n".join(json.dumps(c) for c in _chunks), encoding="utf-8")

    try:
        import faiss
        index = faiss.IndexFlatIP(_embs.shape[1]); index.add(_embs)
        def _s(qv, k):
            s, i = index.search(qv[None, :], k); return s[0], i[0]
    except ImportError:
        def _s(qv, k):
            sims = _embs @ qv; idx = np.argsort(-sims)[:k]; return sims[idx], idx
    _search = _s

    print(f"rag: {len(_chunks)} chunks | emb {_embs.shape} | cache {fp}")
    return _chunks, _embs


def embed_query(q):
    global _qmodel
    if _qmodel is None:
        from sentence_transformers import SentenceTransformer
        _qmodel = SentenceTransformer(EMB_MODEL)
    return np.asarray(_qmodel.encode([q], normalize_embeddings=True), dtype=np.float32)[0]


def retrieve(query, k=TOP_K):
    if _search is None:
        raise RuntimeError("call build_index() first")
    scores, idx = _search(embed_query(query), k)
    return [{"score": float(s), **_chunks[i]} for s, i in zip(scores, idx)]


def build_rag_query(mod):
    h = f" -- {mod.header}" if mod.header else ""
    return f"{mod.name} {' '.join(mod.units)}{h}"