from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AuditStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

class SEOScore(BaseModel):
    """SEO audit score and findings"""
    overall_score: int = Field(..., ge=0, le=100)
    title_score: int = Field(..., ge=0, le=100)
    description_score: int = Field(..., ge=0, le=100)
    speed_score: int = Field(..., ge=0, le=100)
    mobile_score: int = Field(..., ge=0, le=100)
    accessibility_score: int = Field(..., ge=0, le=100)
    
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Additional metrics for CSV reporting
    load_time: float = 0.0
    page_size_kb: int = 0
    images_count: int = 0
    images_with_alt: int = 0
    links_count: int = 0
    broken_links_count: int = 0
    h1_count: int = 0
    meta_description_length: int = 0

class BusinessSite(BaseModel):
    """Represents a business website for outreach"""
    url: HttpUrl
    domain: str
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    region: Optional[str] = None
    contact_form_url: Optional[HttpUrl] = None
    email: Optional[str] = None
    seo_score: Optional[SEOScore] = None
    audit_status: AuditStatus = AuditStatus.PENDING
    outreach_sent: bool = False
    outreach_date: Optional[datetime] = None
    response_received: bool = False
    payment_status: PaymentStatus = PaymentStatus.PENDING
    credentials_provided: bool = False
    seo_fixes_completed: bool = False
    qa_passed: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }

class ContactForm(BaseModel):
    """Contact form structure"""
    url: HttpUrl
    form_fields: Dict[str, str] = Field(default_factory=dict)
    has_captcha: bool = False
    captcha_type: Optional[str] = None
    submitted: bool = False
    submission_date: Optional[datetime] = None
    error_message: Optional[str] = None
    email_used: Optional[str] = None
    submission_method: str = "form"

class OutreachMessage(BaseModel):
    """Outreach message content"""
    subject: str
    message: str
    sms_message: Optional[str] = None
    linkedin_message: Optional[str] = None
    call_opener: Optional[str] = None
    template_used: Optional[str] = None
    business_name: Optional[str] = None
    seo_issues: List[str] = Field(default_factory=list)
    generated_by_ai: bool = True

class PaymentRequest(BaseModel):
    """Payment request for Phase 2"""
    business_site_id: str
    amount: int = Field(..., ge=1000)  # Minimum $10
    currency: str = "usd"
    description: str
    success_url: Optional[HttpUrl] = None
    cancel_url: Optional[HttpUrl] = None

class CredentialsRequest(BaseModel):
    """Secure credentials request"""
    business_site_id: str
    website_url: HttpUrl
    cms_login_url: Optional[HttpUrl] = None
    username: str
    password: str
    additional_notes: Optional[str] = None

class AuditResult(BaseModel):
    """Complete audit result"""
    site: BusinessSite
    seo_score: SEOScore
    contact_form: Optional[ContactForm] = None
    outreach_message: Optional[OutreachMessage] = None
    audit_date: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }
