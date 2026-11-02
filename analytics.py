from sqlalchemy.ext.asyncio import AsyncSession
from models import AnalyticsEvent
from schemas import ChatRequest

async def log_event(db: AsyncSession, client_id: str, event_type: str, query: str, answer: str = None, latency: int = None):
    new_event = AnalyticsEvent(
        client_id=client_id,
        event_type=event_type,
        query=query,
        answer=answer,
        latency_ms=latency
    )
    db.add(new_event)
    await db.commit()