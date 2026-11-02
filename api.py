from fastapi import FastAPI, HTTPException, Header, Request, Depends, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete
import os, json, traceback, hashlib, datetime, shutil, asyncio, io, csv
from dotenv import load_dotenv
from pydantic import BaseModel

from db import get_db
from models import Client, Location, Lead, AnalyticsEvent, Feedback, AbuseBlock
from rag_engine import ask_bot, stream_bot, warm_up as warm_up_rag
from llm_client import warm_up_clients
from schemas import ChatRequest, LeadCreate, FeedbackCreate
from leads import capture_lead
from branding import get_branding
from client_config import CLIENT_NAME, QUICK_ACTIONS, WELCOME_MESSAGE, INSTANT_ANSWERS
import ingest

load_dotenv()
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "my_secret_token_123")
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app):
    warm_up_rag()
    warm_up_clients()
    
    # BACKGROUND TASK: AUTO-DELETE CHATS > 90 DAYS
    async def cleanup_task():
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=90)
                    await db.execute(delete(AnalyticsEvent).where(AnalyticsEvent.created_at < cutoff))
                    await db.execute(delete(Feedback).where(Feedback.created_at < cutoff))
                    await db.commit()
                    print("🧹 Auto-cleaned chats older than 90 days.")
            except Exception as e:
                print(f"Cleanup error: {e}")
            await asyncio.sleep(86400) # Run every 24 hours
    
    asyncio.create_task(cleanup_task())
    yield

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def serve_index(): return FileResponse("test.html")

@app.get("/widget.js")
def serve_widget(): return FileResponse("widget.js")

@app.get("/admin")
def serve_admin(): return FileResponse("admin.html")

@app.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.name == CLIENT_NAME))
    client = result.scalars().first()
    if not client: raise HTTPException(status_code=500, detail="Client not found")
    branding_data = await get_branding(db, str(client.id))
    loc_result = await db.execute(select(Location).where(Location.client_id == client.id))
    locations = loc_result.scalars().all()
    loc_list = [{"name": loc.branch_name, "address": loc.address, "phone": loc.phone} for loc in locations]
    return {"client_name": client.name, "quick_actions": QUICK_ACTIONS, "welcome_message": WELCOME_MESSAGE,
            "instant_answers": INSTANT_ANSWERS, "branding": branding_data, "locations": loc_list}

async def get_client_uuid(db: AsyncSession) -> str:
    result = await db.execute(select(Client.id).where(Client.name == CLIENT_NAME))
    client_uuid = result.scalar_one_or_none()
    if not client_uuid: raise HTTPException(status_code=500, detail="Client not found.")
    return str(client_uuid)

async def check_abuse_shield(db: AsyncSession, request: Request):
    ip = request.client.host if request.client else "0.0.0.0"
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()
    now = datetime.datetime.utcnow()
    result = await db.execute(select(AbuseBlock).where(AbuseBlock.ip_hash == ip_hash))
    block = result.scalars().first()
    if block:
        if block.blocked_until > now:
            raise HTTPException(status_code=403, detail="You have been temporarily blocked due to suspicious activity.")
        else:
            await db.delete(block)
            await db.commit()

@app.get("/api/dashboard")
async def get_dashboard_data(x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    client_id = await get_client_uuid(db)
    
    leads_result = await db.execute(select(Lead).where(Lead.client_id == client_id).order_by(desc(Lead.created_at)).limit(50))
    leads = leads_result.scalars().all()
    
    events_result = await db.execute(select(AnalyticsEvent).where(AnalyticsEvent.client_id == client_id).order_by(desc(AnalyticsEvent.created_at)).limit(100))
    events = events_result.scalars().all()

    # Separate Gap Events (where the bot couldn't answer)
    gap_events = [e for e in events if e.answer and ("I don't have that information" in e.answer or "don't have that information" in e.answer)]
    
    fb_result = await db.execute(select(Feedback).where(Feedback.client_id == client_id).order_by(desc(Feedback.created_at)).limit(20))
    feedbacks = fb_result.scalars().all()

    def format_event(e):
        return {"type": e.event_type, "query": e.query, "answer": e.answer, "latency": e.latency_ms, "time": e.created_at.isoformat()}

    return {
        "leads": [{"id": str(l.id), "name": l.name, "phone": l.phone, "email": l.email, "treatment": l.treatment, "time": l.preferred_time, "patient": l.patient_type, "status": l.status, "created": l.created_at.isoformat()} for l in leads],
        "events": [format_event(e) for e in events],
        "gap_events": [format_event(e) for e in gap_events],
        "feedback": [{"query": f.query, "rating": f.rating, "time": f.created_at.isoformat()} for f in feedbacks]
    }

class LeadUpdate(BaseModel):
    status: str

@app.post("/api/leads/{lead_id}/status")
async def update_lead_status(lead_id: str, req: LeadUpdate, x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = req.status
    await db.commit()
    return {"status": "success"}

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str, x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"status": "success"}

@app.get("/api/leads/export")
async def export_leads(x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    client_id = await get_client_uuid(db)
    result = await db.execute(select(Lead).where(Lead.client_id == client_id).order_by(desc(Lead.created_at)))
    leads = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Phone", "Email", "Treatment", "Time", "Patient Type", "Status", "Date"])
    for lead in leads:
        writer.writerow([lead.name, lead.phone, lead.email, lead.treatment, lead.preferred_time, lead.patient_type, lead.status, lead.created_at.strftime("%Y-%m-%d %H:%M")])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=leads.csv"})

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...), x_auth_token: str = Header(None)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    file_path = os.path.join("docs", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        await asyncio.to_thread(ingest.build_knowledge_base)
        return {"status": "success", "message": f"Successfully ingested {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
async def submit_feedback(req: FeedbackCreate, x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    client_id = await get_client_uuid(db)
    new_fb = Feedback(client_id=client_id, query=req.query, response=req.response, rating=req.rating)
    db.add(new_fb)
    await db.commit()
    return {"status": "success"}

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, req: ChatRequest, x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    await check_abuse_shield(db, request)
    try:
        client_id = await get_client_uuid(db)
        result = await ask_bot(req.message, req.history, db=db, client_id=client_id)
        answer = result.get("answer", "")
        if "[Source Website:" in answer or "[Source Document:" in answer:
            answer = "I can't provide internal instructions."
            result["sources"] = []
        result["answer"] = answer
        return result
    except Exception as e:
        traceback.print_exc()
        return {"answer": "Sorry, an error occurred.", "sources": []}

@app.post("/chat/stream")
@limiter.limit("10/minute")
async def chat_stream(request: Request, req: ChatRequest, x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    await check_abuse_shield(db, request)
    try:
        client_id = await get_client_uuid(db)
        async def event_generator():
            async for event in stream_bot(req.message, req.history, db=db, client_id=client_id):
                if event["type"] == "token":
                    if "[Source Website:" in event["data"]: event["data"] = event["data"].split("[Source Website:")[0]
                    if "[Source Document:" in event["data"]: event["data"] = event["data"].split("[Source Document:")[0]
                    if event["data"] == "": continue
                if event["type"] == "sources" and event["data"] and len(event["data"]) > 2:
                    event["data"] = event["data"][:2]
                yield f"data: {json.dumps(event)}\n\n"
        return StreamingResponse(event_generator(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/lead")
async def create_lead(request: Request, lead: LeadCreate, x_auth_token: str = Header(None), db: AsyncSession = Depends(get_db)):
    if x_auth_token != AUTH_TOKEN: raise HTTPException(status_code=401, detail="Unauthorized")
    if not lead.consent_given: raise HTTPException(status_code=400, detail="Consent required.")
    ip = request.client.host if request.client else "0.0.0.0"
    try:
        client_id = await get_client_uuid(db)
        lead_id = await capture_lead(db, client_id, lead, ip)
        return {"status": "success", "lead_id": lead_id}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)