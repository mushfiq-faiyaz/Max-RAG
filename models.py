import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, ForeignKey, Boolean, DateTime, Integer, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class Client(Base):
    __tablename__ = "clients"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), index=True)
    domain: Mapped[str] = mapped_column(String(100), unique=True)
    branding_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    locations: Mapped[List["Location"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    leads: Mapped[List["Lead"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    analytics: Mapped[List["AnalyticsEvent"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    caches: Mapped[List["CacheEntry"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    feedbacks: Mapped[List["Feedback"]] = relationship(back_populates="client", cascade="all, delete-orphan")

class Location(Base):
    __tablename__ = "locations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"))
    branch_name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text)
    phone: Mapped[str] = mapped_column(String(50))
    hours_json: Mapped[str] = mapped_column(Text, default="{}")
    client: Mapped["Client"] = relationship(back_populates="locations")

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"))
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # NEW FIELDS FROM ADDENDUM
    treatment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    preferred_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    patient_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="new") # new, contacted, booked, lost
    
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_text: Mapped[str] = mapped_column(Text)
    ip_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    client: Mapped["Client"] = relationship(back_populates="leads")

class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    query: Mapped[str] = mapped_column(Text)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    client: Mapped["Client"] = relationship(back_populates="analytics")

class CacheEntry(Base):
    __tablename__ = "cache_entries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"))
    query_text: Mapped[str] = mapped_column(Text)
    query_embedding: Mapped[List[float]] = mapped_column(Vector(384))
    response_text: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    client: Mapped["Client"] = relationship(back_populates="caches")

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"))
    query: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    client: Mapped["Client"] = relationship(back_populates="feedbacks")

class AbuseBlock(Base):
    __tablename__ = "abuse_blocks"
    ip_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    blocked_until: Mapped[datetime] = mapped_column(DateTime)
    strike_count: Mapped[int] = mapped_column(Integer, default=1)
    last_block_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)