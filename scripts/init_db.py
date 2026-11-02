import sys
import os

# 🔥 BULLETPROOF PATH FIX
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import asyncio
import json
from sqlalchemy import text, select
from db import engine, AsyncSessionLocal
from models import Base, Client, Location
from client_config import CLIENT_NAME, WIDGET_COLORS, BOOKING_URL, CLINIC_ADDRESS, CLINIC_PHONE

async def init_db():
    print("⏳ Connecting to PostgreSQL and creating tables...")
    
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created.")
    print("🌱 Seeding initial client from client_config.py...")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Client).where(Client.name == CLIENT_NAME))
        existing_client = result.scalars().first()

        if not existing_client:
            # Create Client
            new_client = Client(
                name=CLIENT_NAME,
                domain="pallmalldental.local",
                branding_json=json.dumps({
                    "primary_color": WIDGET_COLORS["primary"],
                    "accent_color": "#C0A060",
                    "booking_url": BOOKING_URL,
                    "logo_url": None
                })
            )
            session.add(new_client)
            await session.flush()

            # Location 1
            loc1 = Location(
                client_id=new_client.id,
                branch_name="Pall Mall (Main Branch)",
                address=CLINIC_ADDRESS,
                phone=CLINIC_PHONE,
                hours_json=json.dumps({"mon_fri": "8:30 am - 5:30 pm", "wed": "Late opening", "sat_sun": "Closed"})
            )
            # Location 2 (For testing Multi-Location Routing)
            loc2 = Location(
                client_id=new_client.id,
                branch_name="Canary Wharf Branch",
                address="25 Canada Square, London E14 5LQ",
                phone="020 7111 2233",
                hours_json=json.dumps({"mon_fri": "9:00 am - 6:00 pm", "sat": "10:00 am - 2:00 pm", "sun": "Closed"})
            )
            
            session.add(loc1)
            session.add(loc2)
            await session.commit()
            print(f"✅ Seeded Client: {CLIENT_NAME} & 2 Locations.")
        else:
            print(f"ℹ️ Client {CLIENT_NAME} already exists in DB. (If you don't see 2 locations, run `python scripts/init_db.py` again after deleting the docker volume).")

    print("🎉 Database initialization complete!")

if __name__ == "__main__":
    asyncio.run(init_db())