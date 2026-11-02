import hashlib
import uuid
import os
import aiosmtplib
from email.message import EmailMessage
from sqlalchemy.ext.asyncio import AsyncSession
from models import Lead
from schemas import LeadCreate

async def send_owner_email(lead_data: LeadCreate):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT", 587)
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    owner_email = os.getenv("OWNER_EMAIL", "info@pallmalldental.co.uk")

    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"\n📧 [MOCK EMAIL] New Lead: {lead_data.name} | Phone: {lead_data.phone} | Treatment: {lead_data.treatment}")
        return

    message = EmailMessage()
    message["From"] = smtp_user
    message["To"] = owner_email
    message["Subject"] = f"🚨 New Lead: {lead_data.name} ({lead_data.treatment})"
    
    body = f"""
    New Patient Lead Captured!
    
    Name: {lead_data.name}
    Phone: {lead_data.phone or 'Not provided'}
    Email: {lead_data.email or 'Not provided'}
    Treatment Interest: {lead_data.treatment or 'Not specified'}
    Preferred Time: {lead_data.preferred_time or 'Any'}
    Patient Type: {lead_data.patient_type or 'Unknown'}
    
    Consent Given: Yes (GDPR Compliant)
    """
    message.set_content(body)

    try:
        await aiosmtplib.send(message, hostname=smtp_host, port=int(smtp_port), username=smtp_user, password=smtp_pass, use_tls=True if int(smtp_port) == 465 else False, start_tls=True if int(smtp_port) == 587 else False)
        print(f"✅ Email alert sent to {owner_email}")
    except Exception as e:
        print(f"❌ Failed to send email alert: {e}")

async def capture_lead(db: AsyncSession, client_id: str, lead_data: LeadCreate, ip_address: str) -> uuid.UUID:
    if not lead_data.consent_given:
        raise ValueError("Cannot capture lead without explicit consent.")

    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()

    new_lead = Lead(
        client_id=client_id,
        name=lead_data.name,
        phone=lead_data.phone,
        email=lead_data.email,
        treatment=lead_data.treatment,
        preferred_time=lead_data.preferred_time,
        patient_type=lead_data.patient_type,
        status="new",
        consent_given=True,
        consent_text="I agree to be contacted about my enquiry.",
        ip_hash=ip_hash
    )
    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)
    
    import asyncio
    asyncio.create_task(send_owner_email(lead_data))
    
    return new_lead.id