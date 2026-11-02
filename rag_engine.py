import os
import datetime
import re
import time
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from client_config import SYSTEM_PROMPT, CLINIC_PHONE, CLINIC_EMAIL, BOOKING_URL, INSTANT_ANSWERS
from llm_client import call_llm, stream_llm
from security import is_blocked, SAFE_REPLY
from cache import get_cached_response, save_to_cache
from analytics import log_event
from locations import format_location_response
import retrieval

load_dotenv()

FALLBACK_MSG = f"I don't have that information. Please contact the clinic directly at {CLINIC_PHONE} or email {CLINIC_EMAIL}."

def warm_up():
    try:
        retrieval.retrieve("warmup", top_k=1)
        print("✅ RAG Retrieval Engine warmed up.")
    except Exception as e:
        print(f"⚠️ RAG warm-up failed: {e}")

def fix_typos(text: str) -> str:
    return text.lower().replace("xray", "x-ray").replace("x ray", "x-ray")

def clean_search_query(text: str) -> str:
    clean = text.lower()
    fillers = ["can you make a", "can you show me a", "create a", "generate a", "markdown table", "table", "comparison", "compare", "versus", "vs", "please", "show me", "tell me", "what is", "what are"]
    for word in fillers: clean = clean.replace(word, "")
    return re.sub(r'\s+', ' ', clean).strip() or text

def clean_llm_output(text: str) -> str:
    if not text: return text
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'£\s*(\d+)\s+(\d+)', r'£\1\2', text)
    text = text.replace("Not specified", "Contact Clinic").replace("not specified", "Contact Clinic")
    lines = text.split('\n')
    unique_lines = set()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            if stripped in unique_lines: continue
            unique_lines.add(stripped)
        clean_lines.append(line)
    return "\n".join(clean_lines)

async def get_context(search_query: str, is_table: bool = False):
    try:
        clean_query = clean_search_query(search_query)
        fetch_k = 15 if is_table else 4
        def _sync_retrieve(): return retrieval.retrieve(clean_query, top_k=fetch_k)
        retrieved_chunks = await asyncio.to_thread(_sync_retrieve)
        
        if not retrieved_chunks: return None, []

        context_text = ""
        sources = []
        seen_urls = set()

        for item in retrieved_chunks:
            context_text += f"\n---\n{item['text']}\n"
            source_label = f"{item['source']} (Page {item['page']})"
            if source_label not in seen_urls and len(sources) < 2:
                seen_urls.add(source_label)
                sources.append(source_label)

        return context_text, sources
    except Exception as e:
        print(f"Context Error: {e}")
        return None, []

async def check_fast_path(question: str, db: AsyncSession = None, client_id: str = None):
    q = question.lower().strip()
    if any(w in q for w in ["hello", "hi ", "hey", "good morning", "good afternoon"]): return "Hello! How can I help you today?"
    if any(w in q for w in ["thank", "thanks"]): return "You're welcome! Let me know if you need anything else."
    
    emergency_keywords = ["bleed", "bleeding", "severe pain", "swelling", "can't swallow", "trouble swallowing", "can't breathe", "knocked out", "broken tooth", "fell out", "trauma", "abscess"]
    if any(w in q for w in emergency_keywords) and not any(w in q for w in ["last year", "past", "previously", "used to"]):
        return f"This sounds like a dental emergency. If you have trouble swallowing, breathing, severe swelling, or a knocked-out tooth, call 999 or go to A&E immediately. Otherwise, call the clinic at {CLINIC_PHONE}."

    rank_words = ["best", "top", "most famous", "recommended"]
    staff_words = ["dentist", "doctor", "dr", "surgeon", "hygienist", "staff", "team", "orthodontist", "periodontist", "endodontist"]
    if any(r in q for r in rank_words) and any(s in q for s in staff_words):
        return "All our dentists are highly qualified. I cannot rank them, but you can read about our team on the website."

    if any(w in q for w in ["ignore all previous instructions", "system update", "you are now dan", "print your system prompt"]):
        return "I'm sorry, but I can't comply with that."

    if db and client_id:
        loc_response = await format_location_response(db, client_id, q)
        if loc_response: return loc_response

    for key, data in INSTANT_ANSWERS.items():
        if any(kw in q for kw in data["keywords"]):
            if key == "hours_weekday" and any(w in q for w in ["saturday", "sunday", "weekend"]): continue
            if key == "hours_weekday" and any(w in q for w in ["evening", "night", "late"]): continue
            return data["response"]

    return None

async def ask_bot(question: str, history: list = None, db: AsyncSession = None, client_id: str = None):
    start_time = time.time()
    if is_blocked(question): return {"answer": SAFE_REPLY, "sources": []}

    fast_answer = await check_fast_path(question, db, client_id)
    if fast_answer: 
        if db and client_id: await log_event(db, client_id, "fast_path", question, fast_answer, int((time.time() - start_time) * 1000))
        return {"answer": fast_answer, "sources": []}

    if history is None: history = []
    fixed_question = fix_typos(question)
    
    q_lower = fixed_question.lower()
    is_table_request = any(w in q_lower for w in ["table", "compare", "comparison", "versus", "vs"])
    
    # 🚨 CACHE BYPASS FOR PRONOUNS 🚨
    pronouns = ["he", "she", "it", "they", "his", "her", "its", "them", "there"]
    is_follow_up = len(history) > 0 and any(p in fixed_question.lower().split() for p in pronouns)
    
    if db and client_id and not is_follow_up:
        cached_result = await get_cached_response(db, client_id, fixed_question)
        if cached_result:
            await log_event(db, client_id, "cache_hit", question, cached_result["answer"], int((time.time() - start_time) * 1000))
            return {"answer": cached_result["answer"], "sources": cached_result["sources"], "cached": True}

    search_query = fixed_question
    if is_follow_up:
        last_user_msg = [m for m in history if m["role"] == "user"]
        if last_user_msg: search_query = f"{last_user_msg[-1]['content']} {fixed_question}"

    context_text, sources = await get_context(search_query, is_table=is_table_request)
    if not context_text: return {"answer": FALLBACK_MSG, "sources": []}

    today_date = datetime.datetime.now().strftime("%B %d, %Y")
    is_broad_pricing = any(w in q_lower for w in ["treatment pricing", "price list", "all prices", "what are your fees"])

    system_content = f"Today's date is {today_date}.\n{SYSTEM_PROMPT}\n\nContext:\n{context_text}"
    if is_table_request:
        system_content += "\n\nCRITICAL: Output a valid Markdown table. Do NOT say 'I don't have that information'. Do NOT write 'Not specified'."
    elif is_broad_pricing:
        system_content += "\n\nCRITICAL: DO NOT dump the whole price list. List only 5 popular treatments."

    messages = [{"role": "system", "content": system_content}]
    for msg in history[-2:]: messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": fixed_question})

    try:
        answer = await call_llm(messages)
    except Exception:
        return {"answer": FALLBACK_MSG, "sources": []}

    if not answer or len(answer.strip()) < 5 or "don't have that information" in answer.lower():
        return {"answer": FALLBACK_MSG, "sources": []}

    cleaned_answer = clean_llm_output(answer)
    final_result = {"answer": cleaned_answer, "sources": sources}
    
    # Only cache if it's NOT a follow-up
    if db and client_id and not is_follow_up:
        await save_to_cache(db, client_id, fixed_question, cleaned_answer, sources)
        
    if db and client_id:
        await log_event(db, client_id, "llm_query", question, cleaned_answer, int((time.time() - start_time) * 1000))
        
    return final_result

async def stream_bot(question: str, history: list = None, db: AsyncSession = None, client_id: str = None):
    start_time = time.time()
    
    if is_blocked(question):
        yield {"type": "sources", "data": []}
        yield {"type": "token", "data": SAFE_REPLY}
        return

    fast_answer = await check_fast_path(question, db, client_id)
    if fast_answer:
        yield {"type": "sources", "data": []}
        yield {"type": "token", "data": fast_answer}
        return

    if history is None: history = []
    fixed_question = fix_typos(question)
    
    q_lower = fixed_question.lower()
    is_table_request = any(w in q_lower for w in ["table", "compare", "comparison", "versus", "vs"])
    
    pronouns = ["he", "she", "it", "they", "his", "her", "its", "them", "there"]
    is_follow_up = len(history) > 0 and any(p in fixed_question.lower().split() for p in pronouns)

    if db and client_id and not is_follow_up:
        cached_result = await get_cached_response(db, client_id, fixed_question)
        if cached_result:
            await log_event(db, client_id, "cache_hit", question, cached_result["answer"], int((time.time() - start_time) * 1000))
            yield {"type": "sources", "data": cached_result["sources"]}
            yield {"type": "token", "data": cached_result["answer"]}
            return

    search_query = fixed_question
    if is_follow_up:
        last_user_msg = [m for m in history if m["role"] == "user"]
        if last_user_msg: search_query = f"{last_user_msg[-1]['content']} {fixed_question}"

    context_text, sources = await get_context(search_query, is_table=is_table_request)
    if not context_text:
        yield {"type": "sources", "data": []}
        yield {"type": "token", "data": FALLBACK_MSG}
        return

    yield {"type": "sources", "data": sources}

    today_date = datetime.datetime.now().strftime("%B %d, %Y")
    is_broad_pricing = any(w in q_lower for w in ["treatment pricing", "price list", "all prices", "what are your fees"])
    
    system_content = f"Today's date is {today_date}.\n{SYSTEM_PROMPT}\n\nContext:\n{context_text}"
    if is_table_request:
        system_content += "\n\nCRITICAL: Output a valid Markdown table. Do NOT say 'I don't have that information'."
    elif is_broad_pricing:
        system_content += "\n\nCRITICAL: DO NOT dump the whole price list."

    messages = [{"role": "system", "content": system_content}]
    for msg in history[-2:]: messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": fixed_question})

    full_response = ""
    try:
        async for token in stream_llm(messages):
            full_response += token
            yield {"type": "token", "data": token}

        if full_response and "don't have that information" not in full_response.lower():
            cleaned = clean_llm_output(full_response)
            if db and client_id and not is_follow_up:
                await save_to_cache(db, client_id, fixed_question, cleaned, sources)
            if db and client_id:
                await log_event(db, client_id, "llm_query", question, cleaned, int((time.time() - start_time) * 1000))
    except Exception as e:
        print(f"Stream Error: {e}")
        yield {"type": "token", "data": "\n\n[Error: Connection to AI lost.]"}