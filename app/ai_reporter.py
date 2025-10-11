import openai
import logging
from typing import Dict, Any, Optional
from app.models import BusinessSite, SEOScore, OutreachMessage
from app.config import config
# Mock OpenAI API removed for production

logger = logging.getLogger(__name__)

class AIReporter:
    """Generates AI-powered outreach messages using Rankzen templates"""
    
    def __init__(self):
        self.default_templates = config.OUTREACH_TEMPLATES
    
    @property
    def openai_api_key(self):
        """Dynamically get the OpenAI API key from config"""
        return config.OPENAI_API_KEY
    
    def generate_outreach_message(self, site: BusinessSite, seo_score: SEOScore) -> OutreachMessage:
        """
        Generate outreach message using Rankzen templates
        """
        try:
            # Configure OpenAI with current API key
            openai.api_key = self.openai_api_key
            
            # Extract business information
            business_name = site.business_name or site.domain
            first_name = self._extract_first_name(business_name)
            city = site.region or "your area"
            
            # Get top issues and fixes (limit to 2-3 issues max as requested)
            top_issue = seo_score.issues[0] if seo_score.issues else "missing key SEO elements"
            top_fix = seo_score.recommendations[0] if seo_score.recommendations else "basic SEO optimization"
            # Limit to 2-3 issues max for plain English format
            issues_for_message = seo_score.issues[:3] if seo_score.issues else ["missing SEO elements"]
            issue_list_short = "; ".join(issues_for_message)
            
            # Generate audit link (placeholder for now)
            audit_link = f"https://rankzen.com/audit/{site.domain}"
            
            # Choose template based on score
            templates = getattr(config, 'OUTREACH_TEMPLATES', self.default_templates)

            if seo_score.overall_score < 50:
                template = "cold_email_1"  # Value-forward for low scores
            else:
                template = "cold_email_2"  # Competitor angle for medium scores

            # Get template
            template_data = templates[template]

            placeholders = {
                "FirstName": first_name,
                "BusinessName": business_name,
                "City": city,
                "Keyword": f"{site.business_type} {city}",
                "Issue": top_issue,
                "IssueListShort": issue_list_short,
                "Score": seo_score.overall_score,
                "TopFix": top_fix,
                "ETA": "48 hours",
                "AuditLink": audit_link,
                "SenderName": "Rankzen"
            }

            # Fill placeholders according to client specifications
            subject = self._fill_placeholders(template_data["subject"], {
                "BusinessName": business_name,
                "City": city,
                "Keyword": placeholders["Keyword"],
                "Issue": placeholders["Issue"],
                "Score": placeholders["Score"],
                "TopFix": placeholders["TopFix"],
                "AuditLink": placeholders["AuditLink"],
                "SenderName": placeholders["SenderName"]
            })

            body = self._fill_placeholders(template_data["body"], placeholders)

            # Generate SMS version (≤320 chars as per client spec)
            sms_body = self._fill_placeholders(templates["sms"]["body"], {
                "FirstName": placeholders["FirstName"],
                "Score": placeholders["Score"],
                "TopFix": placeholders["TopFix"],
                "AuditLink": placeholders["AuditLink"]
            })

            # Generate LinkedIn DM
            linkedin_body = self._fill_placeholders(templates["linkedin_dm"]["body"], {
                "FirstName": placeholders["FirstName"],
                "BusinessName": placeholders["BusinessName"],
                "Issue": placeholders["Issue"],
                "Score": placeholders["Score"],
                "TopFix": placeholders["TopFix"],
                "AuditLink": placeholders["AuditLink"]
            })

            # Generate cold call opener (20s as per client spec)
            call_opener = self._fill_placeholders(templates["cold_call"]["opener"], {
                "FirstName": first_name,
                "YourName": "Alex",
                "Channel": "Google Business Profile",
                "KeyGap": "business hours",
                "EstImpact": "$500-2000 monthly",
                "TopFix": top_fix
            })

            custom_template = getattr(config, 'MESSAGE_TEMPLATE', '') or ''
            if custom_template.strip():
                body = self._fill_placeholders(custom_template, placeholders)

            return OutreachMessage(
                subject=subject,
                message=body,
                sms_message=sms_body,
                linkedin_message=linkedin_body,
                call_opener=call_opener,
                template_used=template
            )
            
        except Exception as e:
            logger.error(f"Error generating outreach message for {site.domain}: {e}")
            # Fallback to simple message
            return OutreachMessage(
                subject=f"Quick SEO Review for {site.business_name or site.domain}",
                message=f"Hi there! I noticed your website could benefit from some SEO improvements. Would you like me to help you optimize it for better search rankings?",
                template_used="fallback"
            )
    
    def _extract_first_name(self, business_name: str) -> str:
        """Extract first name from business name"""
        if not business_name or business_name == "Unknown":
            return "there"
        
        # Try to extract first name from business name
        words = business_name.split()
        if words:
            # Check if first word looks like a name
            first_word = words[0].strip()
            if len(first_word) > 2 and first_word[0].isupper():
                return first_word
            elif len(words) > 1:
                # Try second word
                second_word = words[1].strip()
                if len(second_word) > 2 and second_word[0].isupper():
                    return second_word
        
        return "there"
    
    def _fill_placeholders(self, text: str, placeholders: Dict[str, str]) -> str:
        """Fill placeholders in template text"""
        result = text
        for key, value in placeholders.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result
    
    def generate_audit_report(self, site: BusinessSite, seo_score: SEOScore) -> Dict[str, Any]:
        """
        Generate a comprehensive audit report for the business
        """
        try:
            # Create audit summary
            audit_summary = {
                "business_name": site.business_name or site.domain,
                "domain": site.domain,
                "overall_score": seo_score.overall_score,
                "industry": site.business_type,
                "region": site.region,
                "audit_date": "2025-08-14",
                "issues": seo_score.issues,
                "recommendations": seo_score.recommendations,
                "directory_listings": self._check_directory_listings(site),
                "estimated_impact": self._calculate_estimated_impact(seo_score),
                "fix_eta": self._calculate_fix_eta(seo_score)
            }
            
            return audit_summary
            
        except Exception as e:
            logger.error(f"Error generating audit report for {site.domain}: {e}")
            return {
                "error": str(e),
                "business_name": site.business_name or site.domain,
                "domain": site.domain
            }
    
    def _check_directory_listings(self, site: BusinessSite) -> Dict[str, bool]:
        """Check directory listings (placeholder for now)"""
        return {
            "Google Business Profile": True,  # Assume present for now
            "Yelp": False,
            "Facebook Page": False
        }
    
    def _calculate_estimated_impact(self, seo_score: SEOScore) -> str:
        """Calculate estimated monthly impact"""
        if seo_score.overall_score < 30:
            return "$1000-3000"
        elif seo_score.overall_score < 60:
            return "$500-1500"
        else:
            return "$200-800"
    
    def _calculate_fix_eta(self, seo_score: SEOScore) -> str:
        """Calculate estimated time to fix"""
        issue_count = len(seo_score.issues)
        if issue_count <= 3:
            return "24-48 hours"
        elif issue_count <= 6:
            return "3-5 days"
        else:
            return "1-2 weeks"
