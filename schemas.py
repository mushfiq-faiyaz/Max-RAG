from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: Optional[List[Dict[str, Any]]] = None
    client_id: Optional[UUID] = None 

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    cached: bool = False

class LeadCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    treatment: Optional[str] = None
    preferred_time: Optional[str] = None
    patient_type: Optional[str] = None
    consent_given: bool = Field(..., description="Must be true to capture lead")

class LeadResponse(BaseModel):
    status: str
    lead_id: UUID

class FeedbackCreate(BaseModel):
    query: str
    response: str
    rating: int = Field(..., ge=-1, le=1)

class BrandingResponse(BaseModel):
    client_name: str
    primary_color: str
    accent_color: str
    logo_url: Optional[str]
    booking_url: str
    locations: List[Dict[str, Any]]