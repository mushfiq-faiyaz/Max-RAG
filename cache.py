import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from models import CacheEntry
from sentence_transformers import SentenceTransformer

print("⏳ Loading Cache Embedder...")
cache_embedder = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Cache Embedder loaded.")

async def get_cached_response(db: AsyncSession, client_id: str, query_text: str, threshold: float = 0.02) -> dict | None:
    """Checks if a semantically similar question exists in the cache."""
    embedding = cache_embedder.encode(query_text).tolist()
    
    # Using raw SQL for pgvector cosine distance (<=> operator)
    # 0.02 means the meaning must be almost IDENTICAL to trigger a cache hit.
    query = text("""
        SELECT response_text, sources_json 
        FROM cache_entries 
        WHERE client_id = :client_id 
        AND query_embedding <=> :embedding <= :threshold
        ORDER BY query_embedding <=> :embedding 
        LIMIT 1
    """)
    
    embedding_str = f"[{','.join(map(str, embedding))}]"
    
    result = await db.execute(query, {
        "client_id": client_id, 
        "embedding": embedding_str,
        "threshold": threshold
    })
    row = result.fetchone()
    
    if row:
        print(f"⚡ Semantic Cache HIT! (Distance < {threshold})")
        return {"answer": row[0], "sources": json.loads(row[1])}
    return None

async def save_to_cache(db: AsyncSession, client_id: str, query_text: str, response_text: str, sources: list):
    embedding = cache_embedder.encode(query_text).tolist()
    query = text("""
        INSERT INTO cache_entries (id, client_id, query_text, query_embedding, response_text, sources_json, created_at)
        VALUES (gen_random_uuid(), :client_id, :query_text, :embedding, :response_text, :sources, NOW())
    """)
    embedding_str = f"[{','.join(map(str, embedding))}]"
    
    await db.execute(query, {
        "client_id": client_id,
        "query_text": query_text,
        "embedding": embedding_str,
        "response_text": response_text,
        "sources": json.dumps(sources)
    })
    await db.commit()