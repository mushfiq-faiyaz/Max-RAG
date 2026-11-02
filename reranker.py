import asyncio
from sentence_transformers import CrossEncoder

# Load the model globally so it only loads once at startup
# ms-marco-MiniLM-L-6-v2 is lightweight (~90MB) but highly effective
try:
    print("⏳ Loading Cross-Encoder Reranker...")
    reranker_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    print("✅ Reranker loaded.")
except Exception as e:
    print(f"⚠️ Failed to load reranker: {e}")
    reranker_model = None

async def rerank_documents(query: str, documents: list[str], top_n: int = 3) -> list[str]:
    """Reranks the provided documents based on relevance to the query."""
    if not reranker_model or not documents:
        return documents[:top_n]

    # Run in a separate thread to not block the async event loop
    def _sync_rerank():
        pairs = [[query, doc] for doc in documents]
        scores = reranker_model.predict(pairs)
        # Sort by score descending
        scored_docs = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:top_n]]

    return await asyncio.to_thread(_sync_rerank)