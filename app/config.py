import os
from typing import List, Optional
from dotenv import load_dotenv

# Loading environment variables
load_dotenv()

class Config:
    """Configuration settings for the SEO Outreach Tool"""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    CAPTCHA_API_KEY: str = os.getenv("CAPTCHA_API_KEY", "")
    CAPTCHA_SERVICE: str = os.getenv("CAPTCHA_SERVICE", "2captcha")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    
    # Rankzen Configuration
    RANKZEN_API_KEY: str = os.getenv("RANKZEN_API_KEY", "")
    
    # Stripe Configuration (Phase 2) - All keys must be in .env file
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_PRODUCT_KEY: str = os.getenv("STRIPE_PRODUCT_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Phase 2 Configuration (Simplified)
    QA_REVIEWER_EMAIL: str = os.getenv("QA_REVIEWER_EMAIL", "reviewer@rankzen.com")
    

    
    # Rate Limiting & Configuration
    QPS_GLOBAL: int = int(os.getenv("QPS_GLOBAL", "5"))
    QPS_PER_DOMAIN: int = int(os.getenv("QPS_PER_DOMAIN", "2"))
    DAILY_AUDITS: int = int(os.getenv("DAILY_AUDITS", "150"))
    MAX_SITES_PER_RUN: int = int(os.getenv("MAX_SITES_PER_RUN", "30"))

    # HTTP resilience
    REQUEST_CONNECT_TIMEOUT: float = float(os.getenv("REQUEST_CONNECT_TIMEOUT", "4.0"))
    REQUEST_READ_TIMEOUT: float = float(os.getenv("REQUEST_READ_TIMEOUT", "12.0"))
    HTTP_MAX_RETRIES: int = int(os.getenv("HTTP_MAX_RETRIES", "2"))
    HTTP_BACKOFF_FACTOR: float = float(os.getenv("HTTP_BACKOFF_FACTOR", "0.5"))
    DEAD_HOST_CACHE_SECONDS: int = int(os.getenv("DEAD_HOST_CACHE_SECONDS", "1800"))
    AUDIT_MAX_URL_VARIATIONS: int = int(os.getenv("AUDIT_MAX_URL_VARIATIONS", "4"))

    # Target Industries (Rankzen focus)
    TARGET_INDUSTRIES: List[str] = os.getenv("TARGET_INDUSTRIES", "landscaping,real_estate,plumbers,hvac,roofers,lawyers").split(",")
    
    # Target Locations (Tier 1 - Rankzen focus)
    TARGET_REGIONS: List[str] = ["New York City", "Miami-Dade", "Austin", "Los Angeles", "Phoenix", "Brooklyn", "Queens", "Bronx", "Manhattan", "Staten Island"]
    
    # Target Locations (Tier 2)
    TARGET_REGIONS_TIER2: List[str] = os.getenv("TARGET_REGIONS_TIER2", "Dallas-Fort Worth,Chicago,Atlanta,Denver,Seattle").split(",")
    
    # Test Sites (live)
    TEST_SITES: List[str] = os.getenv("TEST_SITES", "sentra.one,hyperpool.io").split(",")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")
    
    # Industry-specific search terms (Rankzen targeting)
    INDUSTRY_SEARCH_TERMS = {
        "landscaping": ["landscaping services", "lawn care", "garden maintenance", "landscape design", "landscaping company"],
        "real_estate": ["real estate agent", "real estate broker", "property management", "real estate agency", "realtor"],
        "plumbers": ["plumbing services", "emergency plumber", "plumbing repair", "plumber near me", "plumbing company"],
        "hvac": ["HVAC services", "air conditioning repair", "heating and cooling", "HVAC contractor", "HVAC company"],
        "roofers": ["roofing services", "roof repair", "roofing contractor", "roof installation", "roofing company"],
        "lawyers": ["personal injury lawyer", "immigration lawyer", "law firm", "attorney", "personal injury attorney"]
    }
    
    # Outreach Templates - Phase 2: Engagement Focus
    # Default templates (will be overridden by database settings if available)
    OUTREACH_TEMPLATES = {
        "cold_email_1": {
            "subject": "Quick fixes to lift {{BusinessName}}'s local rankings",
            "body": """Hi {{FirstName}}, we ran a 60-second audit on {{BusinessName}} and found {{Issue}} hurting visibility.

Score: {{Score}}/100. Main issues: {{IssueListShort}}.

Fixing {{TopFix}} could get you more customers from Google.

Would you like help fixing this? We can implement these improvements this week for $100 and show results in 7 days.

Just reply "YES" if interested or "NO" if not.

— {{SenderName}}, Rankzen"""
        },
        "cold_email_2": {
            "subject": "{{City}} competitors outrank you for \"{{Keyword}}\"",
            "body": """Hey {{FirstName}}, competitors are beating {{BusinessName}} for \"{{Keyword}}.\"

We found: {{IssueListShort}}.

Fixing these issues could help you outrank competitors and get more local customers.

Would you like us to fix these for $100? We can complete the work in {{ETA}}.

Reply "YES" if you want help or "NO" if not interested."""
        },
        "sms": {
            "body": "Hi {{FirstName}}, Rankzen here. Your {{BusinessName}} audit score: {{Score}}/100. Main fix needed: {{TopFix}}. Would you like help fixing this for $100? Reply YES or NO."
        },
        "linkedin_dm": {
            "body": "{{FirstName}}, quick audit on {{BusinessName}} shows {{Issue}} blocking local leads. Score {{Score}}/100. Would you like help fixing this for $100? Can implement {{TopFix}} in 48h. Reply YES/NO."
        },
        "cold_call": {
            "opener": "\"{{FirstName}}? {{YourName}} from Rankzen. Your {{Channel}} profile is missing {{KeyGap}}, likely costing {{EstImpact}}. Would you like help fixing this for $100? I can implement {{TopFix}} this week. Interested?\""
        }
    }
    
    # Directory listings to check in audits (MVP)
    DIRECTORY_LISTINGS = ["Google Business Profile", "Yelp", "Facebook Page"]
    
    # Phase 2 directories (future)
    PHASE2_DIRECTORIES = ["Apple Maps", "Bing Places", "Nextdoor", "Angi", "Thumbtack"]
    
    # SEO audit criteria
    SEO_CRITERIA = {
        "title_max_length": 60,
        "description_max_length": 160,
        "max_load_time": 3.0,  # seconds
        "min_images_with_alt": 0.8,  # 80% of images should have alt text
    }

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required API keys are present"""
        required_keys = [
            "OPENAI_API_KEY",
            "SERPER_API_KEY", 
            "CAPTCHA_API_KEY"
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        if missing_keys:
            print(f"Missing required API keys: {', '.join(missing_keys)}")
            return False
        
        return True

# Create global config instance
config = Config()
