import os
import re
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi

# Hardcoded to match your existing ingest.py settings
DB_DIR = "chroma_db"
COLLECTION_NAME = "client_knowledge"
EMBED_MODEL = "all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_cached_collection = None
_cached_embed_func = None
_cached_reranker = None
_cached_bm25_index = None
_cached_doc_id_to_record = {}
_cached_all_doc_ids = []

def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())

def _load_collection_and_models():
    global _cached_collection, _cached_embed_func, _cached_reranker
    global _cached_bm25_index, _cached_doc_id_to_record, _cached_all_doc_ids

    if not os.path.exists(DB_DIR):
        raise FileNotFoundError(f"ChromaDB directory '{DB_DIR}' not found. Run ingest.py first.")

    if _cached_collection is None:
        _cached_embed_func = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        client = chromadb.PersistentClient(path=DB_DIR)
        try:
            _cached_collection = client.get_collection(name=COLLECTION_NAME, embedding_function=_cached_embed_func)
        except Exception:
            _cached_collection = client.get_collection(name=COLLECTION_NAME)
    else:
        try:
            _cached_collection.count()
        except Exception:
            _cached_collection = None
            _cached_bm25_index = None
            _cached_doc_id_to_record = {}
            _cached_all_doc_ids = []
            _load_collection_and_models()
            return

    if _cached_bm25_index is None:
        total_docs = _cached_collection.count()
        if total_docs > 0:
            all_records = _cached_collection.get(include=["documents", "metadatas"])
            _cached_all_doc_ids = all_records["ids"]
            _cached_doc_id_to_record = {}
            tokenized_corpus = []
            for doc_id, text, meta in zip(all_records["ids"], all_records["documents"], all_records["metadatas"]):
                _cached_doc_id_to_record[doc_id] = {"text": text or "", "metadata": meta or {}}
                tokenized_corpus.append(_tokenize(text or ""))
            if tokenized_corpus:
                _cached_bm25_index = BM25Okapi(tokenized_corpus)
            else:
                _cached_bm25_index = None

    if _cached_reranker is None:
        try:
            _cached_reranker = CrossEncoder(RERANK_MODEL)
        except Exception:
            _cached_reranker = None

def vector_search(query: str, k: int = 20) -> List[str]:
    _load_collection_and_models()
    if _cached_collection is None or _cached_collection.count() == 0:
        return []
    actual_k = min(k, _cached_collection.count())
    results = _cached_collection.query(query_texts=[query], n_results=actual_k)
    return results["ids"][0] if results and "ids" in results and results["ids"] else []

def bm25_search(query: str, k: int = 20) -> List[str]:
    _load_collection_and_models()
    if _cached_bm25_index is None or not _cached_all_doc_ids:
        return []
    query_tokens = _tokenize(query)
    if not query_tokens:
        return _cached_all_doc_ids[:k]
    scores = _cached_bm25_index.get_scores(query_tokens)
    ranked_indices = sorted(range(len(scores)), key=lambda idx: scores[idx], reverse=True)
    return [_cached_all_doc_ids[idx] for idx in ranked_indices[:k]]

def rrf(vector_ids: List[str], bm25_ids: List[str], k: int = 60) -> List[str]:
    scores: Dict[str, float] = {}
    for rank, doc_id in enumerate(vector_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    return sorted(scores.keys(), key=lambda doc_id: scores[doc_id], reverse=True)

def hybrid_search(query: str, k: int = 20) -> List[str]:
    vec_ids = vector_search(query, k=k)
    bm25_ids = bm25_search(query, k=k)
    return rrf(vec_ids, bm25_ids, k=60)

def rerank(query: str, doc_ids: List[str], top_n: int = 6) -> List[str]:
    _load_collection_and_models()
    if not doc_ids:
        return []
    if _cached_reranker is None:
        return doc_ids[:top_n]

    pairs, valid_ids = [], []
    for d_id in doc_ids:
        record = _cached_doc_id_to_record.get(d_id)
        if record:
            pairs.append((query, record["text"]))
            valid_ids.append(d_id)

    if not pairs:
        return []

    scores = _cached_reranker.predict(pairs)
    score_map = {doc_id: float(sc) for doc_id, sc in zip(valid_ids, scores)}
    ranked_ids = sorted(valid_ids, key=lambda d_id: score_map[d_id], reverse=True)
    return ranked_ids[:top_n]

def retrieve(query: str, top_k: int = 6) -> List[Dict[str, Any]]:
    _load_collection_and_models()
    if _cached_collection is None or _cached_collection.count() == 0:
        return []

    candidate_k = max(20, top_k * 3)
    candidate_ids = hybrid_search(query, k=candidate_k)
    if not candidate_ids:
        return []

    final_ids = rerank(query, candidate_ids, top_n=top_k)

    results = []
    for rank_idx, doc_id in enumerate(final_ids, start=1):
        record = _cached_doc_id_to_record.get(doc_id)
        if not record:
            continue
        meta = record.get("metadata", {})
        results.append({
            "text": record.get("text", ""),
            "source": meta.get("source", "Unknown PDF"),
            "page": meta.get("page", 1)
        })
    return results