from pydantic import BaseModel, HttpUrl, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class InteractionStatus(str, Enum):
    """Status of client interaction"""
    INITIAL_OUTREACH = "initial_outreach"
    ENGAGEMENT_SENT = "engagement_sent"
    CLIENT_RESPONDED = "client_responded"
    AGREED_TO_HELP = "agreed_to_help"
    PAYMENT_LINK_SENT = "payment_link_sent"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_COMPLETED = "payment_completed"
    CREDENTIALS_REQUESTED = "credentials_requested"
    CREDENTIALS_PENDING = "credentials_pending"
    CREDENTIALS_COLLECTED = "credentials_collected"
    SEO_FIXES_STARTED = "seo_fixes_started"
    IMPLEMENTATION_IN_PROGRESS = "implementation_in_progress"
    SEO_FIXES_COMPLETED = "seo_fixes_completed"
    QA_REQUESTED = "qa_requested"
    QA_PENDING = "qa_pending"
    QA_APPROVED = "qa_approved"
    QA_REJECTED = "qa_rejected"
    OWNER_NOTIFIED = "owner_notified"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentStatus(str, Enum):
    """Payment processing status"""
    PENDING = "pending"
    LINK_SENT = "link_sent"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class QAResult(str, Enum):
    """QA review result"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"

class ClientInteraction(BaseModel):
    """Tracks the full client interaction flow"""
    business_site_id: str
    domain: str
    business_name: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    
    # Initial audit data
    initial_seo_score: Optional[int] = None
    initial_seo_issues: List[str] = Field(default_factory=list)
    initial_seo_recommendations: List[str] = Field(default_factory=list)
    
    # Interaction flow
    status: InteractionStatus = InteractionStatus.INITIAL_OUTREACH
    initial_outreach_date: Optional[datetime] = None
    engagement_sent_date: Optional[datetime] = None
    client_response_date: Optional[datetime] = None
    client_response_text: Optional[str] = None
    agreement_date: Optional[datetime] = None
    
    # Payment details
    payment_link: Optional[str] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payment_amount: int = 10000  # $100 in cents
    payment_completed_date: Optional[datetime] = None
    stripe_payment_id: Optional[str] = None
    stripe_session_id: Optional[str] = None
    
    # Credentials collection
    credentials_requested_date: Optional[datetime] = None
    website_url: Optional[str] = None
    cms_login_url: Optional[str] = None
    username: Optional[str] = None
    password_encrypted: Optional[str] = None
    credentials_collected_date: Optional[datetime] = None
    credentials_notes: Optional[str] = None
    
    # SEO Implementation
    seo_fixes_started_date: Optional[datetime] = None
    seo_fixes_completed_date: Optional[datetime] = None
    changes_made: List[str] = Field(default_factory=list)
    implementation_notes: Optional[str] = None
    implementation_success: Optional[bool] = None
    
    # QA Process
    qa_requested_date: Optional[datetime] = None
    qa_reviewer: Optional[str] = None
    qa_result: QAResult = QAResult.PENDING
    qa_notes: Optional[str] = None
    qa_completed_date: Optional[datetime] = None
    qa_review_url: Optional[str] = None
    
    # Final notification
    owner_notified_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    final_message_sent: Optional[str] = None
    
    # Communication history
    communication_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    last_retry_date: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v)
        }

class PaymentRequest(BaseModel):
    """Payment request for Stripe"""
    business_site_id: str
    amount: int = Field(..., ge=1000)  # Minimum $10
    currency: str = "usd"
    description: str
    success_url: Optional[HttpUrl] = None
    cancel_url: Optional[HttpUrl] = None
    metadata: Optional[Dict[str, str]] = None

class PaymentResponse(BaseModel):
    """Payment response from Stripe"""
    success: bool
    payment_link: Optional[str] = None
    session_id: Optional[str] = None
    error_message: Optional[str] = None

class CredentialsRequest(BaseModel):
    """Credentials collection request"""
    business_site_id: str
    website_url: HttpUrl
    cms_login_url: Optional[HttpUrl] = None
    username: str
    password: str
    additional_notes: Optional[str] = None

class CredentialsResponse(BaseModel):
    """Credentials collection response"""
    success: bool
    credentials_stored: bool
    error_message: Optional[str] = None

class SEOImplementation(BaseModel):
    """SEO implementation request"""
    business_site_id: str
    changes_to_implement: List[str]
    implementation_notes: Optional[str] = None

class SEOImplementationResponse(BaseModel):
    """SEO implementation response"""
    success: bool
    changes_implemented: List[str]
    implementation_notes: Optional[str] = None
    error_message: Optional[str] = None

class QARequest(BaseModel):
    """QA review request"""
    business_site_id: str
    reviewer_email: Optional[str] = None
    review_url: Optional[HttpUrl] = None
    qa_notes: Optional[str] = None

class QAResponse(BaseModel):
    """QA review response"""
    business_site_id: str
    qa_result: QAResult
    reviewer: str
    qa_notes: Optional[str] = None
    review_date: datetime = Field(default_factory=datetime.now)

class OwnerNotification(BaseModel):
    """Owner notification request"""
    business_site_id: str
    notification_type: str = "completion"  # completion, qa_approved, etc.
    message: Optional[str] = None
    include_review_link: bool = True

class EngagementMessage(BaseModel):
    """Engagement message for client interaction"""
    business_site_id: str
    message_type: str = "engagement"  # engagement, payment, credentials, completion
    subject: Optional[str] = None
    body: str
    include_payment_link: bool = False
    include_credentials_form: bool = False
