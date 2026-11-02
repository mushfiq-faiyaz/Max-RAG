from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Location
import json

async def get_locations(db: AsyncSession, client_id: str) -> list[Location]:
    result = await db.execute(select(Location).where(Location.client_id == client_id))
    return result.scalars().all()

async def format_location_response(db: AsyncSession, client_id: str, query: str) -> str | None:
    locations = await get_locations(db, client_id)
    
    if not locations:
        return None

    q = query.lower()
    location_keywords = ["where", "located", "address", "postcode", "situated", "find you", "location", "branch"]
    hours_keywords = ["hours", "open", "time", "close"]
    
    is_location_query = any(k in q for k in location_keywords)
    is_hours_query = any(k in q for k in hours_keywords)

    if not is_location_query and not is_hours_query:
        return None

    # Check if user specified a branch name in their query
    matched_location = None
    for loc in locations:
        # e.g. "Canary" in "where is canary wharf branch"
        first_word = loc.branch_name.split()[0].lower()
        if first_word in q or loc.branch_name.lower() in q:
            matched_location = loc
            break

    if matched_location:
        if is_location_query:
            return f"Here are the details for our {matched_location.branch_name}:\nAddress: {matched_location.address}\nPhone: {matched_location.phone}"
        else:
            hours = json.loads(matched_location.hours_json)
            hours_text = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in hours.items()])
            return f"Opening hours for {matched_location.branch_name}:\n{hours_text}"

    # If they didn't specify a branch, and there are multiple, ask them
    if len(locations) > 1:
        branches = ", ".join([loc.branch_name for loc in locations])
        return f"We have multiple locations: {branches}. Which branch are you asking about?"

    # If only 1 location
    if is_location_query:
        return f"We are located at {locations[0].address}."
    else:
        hours = json.loads(locations[0].hours_json)
        hours_text = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in hours.items()])
        return f"Our hours are:\n{hours_text}"