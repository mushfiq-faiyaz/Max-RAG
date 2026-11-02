from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Client
import json

async def get_branding(db: AsyncSession, client_id: str) -> dict:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalars().first()
    
    if client and client.branding_json:
        try:
            return json.loads(client.branding_json)
        except:
            pass
            
    return {
        "primary_color": "#1A1A1A",
        "accent_color": "#C0A060",
        "booking_url": "#",
        "logo_url": None
    }