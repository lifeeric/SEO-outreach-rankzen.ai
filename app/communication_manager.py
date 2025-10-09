import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from app.config import config
from app.phase2_models import (
    ClientInteraction, InteractionStatus, EngagementMessage,
    CredentialsRequest, OwnerNotification
)
from app.utils import data_manager

logger = logging.getLogger(__name__)

class CommunicationManager:
    """Manages all client communication for Phase 2 workflow"""
    
    def __init__(self):
        self.interactions_file = Path("data/phase2_interactions.jsonl")
        self.interactions_file.parent.mkdir(exist_ok=True)
        self.interactions: Dict[str, ClientInteraction] = {}
        self._load_interactions()
    
    def _load_interactions(self):
        """Load existing interactions from file"""
        if self.interactions_file.exists():
            try:
                with open(self.interactions_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            interaction = ClientInteraction(**data)
                            self.interactions[interaction.business_site_id] = interaction
                logger.info(f"Loaded {len(self.interactions)} existing interactions")
            except Exception as e:
                logger.error(f"Error loading interactions: {e}")
    
    def _save_interaction(self, interaction: ClientInteraction):
        """Save interaction to file"""
        try:
            with open(self.interactions_file, 'a') as f:
                f.write(interaction.json() + '\n')
        except Exception as e:
            logger.error(f"Error saving interaction: {e}")
    
    def _update_interaction(self, interaction: ClientInteraction):
        """Update existing interaction"""
        self.interactions[interaction.business_site_id] = interaction
        self._save_interaction(interaction)
    
    def start_interaction(self, business_site_id: str, domain: str, 
                         business_name: str, seo_score: int = None,
                         seo_issues: List[str] = None, 
                         seo_recommendations: List[str] = None) -> ClientInteraction:
        """Start a new client interaction"""
        logger.info(f"Starting interaction for {domain}")
        
        interaction = ClientInteraction(
            business_site_id=business_site_id,
            domain=domain,
            business_name=business_name,
            initial_seo_score=seo_score,
            initial_seo_issues=seo_issues or [],
            initial_seo_recommendations=seo_recommendations or [],
            status=InteractionStatus.INITIAL_OUTREACH,
            initial_outreach_date=datetime.now()
        )
        
        self.interactions[business_site_id] = interaction
        self._save_interaction(interaction)
        
        logger.info(f"✅ Interaction started for {domain}")
        return interaction
    
    def send_engagement_message(self, business_site_id: str, 
                               seo_issues: List[str] = None) -> bool:
        """Send engagement message instead of pitch"""
        interaction = self.interactions.get(business_site_id)
        if not interaction:
            logger.error(f"Interaction not found for {business_site_id}")
            return False
        
        # Create engagement message
        issues_text = "; ".join(seo_issues or interaction.initial_seo_issues[:3])
        score = interaction.initial_seo_score or 50
        
        engagement_body = f"""Hi there! 👋

We just ran a quick audit on {interaction.business_name or interaction.domain} and found some opportunities to improve your local search visibility.

Current score: {score}/100

Main issues we spotted:
• {issues_text}

Would you like help fixing these? We can implement the improvements and show you results within 7 days.

Just reply "YES" if you're interested, or let me know if you have any questions!

Best regards,
The Rankzen Team"""

        # Log the engagement message
        interaction.communication_log.append({
            "date": datetime.now().isoformat(),
            "type": "engagement_sent",
            "message": engagement_body
        })
        
        interaction.status = InteractionStatus.ENGAGEMENT_SENT
        interaction.engagement_sent_date = datetime.now()
        self._update_interaction(interaction)
        
        logger.info(f"✅ Engagement message sent to {interaction.domain}")
        return True
    
    def process_client_response(self, business_site_id: str, response_text: str) -> Dict[str, Any]:
        """Process client response and determine next step"""
        interaction = self.interactions.get(business_site_id)
        if not interaction:
            return {"success": False, "error": "Interaction not found"}
        
        # Log the response
        interaction.communication_log.append({
            "date": datetime.now().isoformat(),
            "type": "client_response",
            "message": response_text
        })
        
        interaction.client_response_date = datetime.now()
        interaction.client_response_text = response_text
        
        # Analyze response for positive intent
        positive_keywords = ["yes", "interested", "help", "fix", "improve", "sure", "ok", "go"]
        response_lower = response_text.lower()
        
        is_positive = any(keyword in response_lower for keyword in positive_keywords)
        
        if is_positive:
            interaction.status = InteractionStatus.AGREED_TO_HELP
            interaction.agreement_date = datetime.now()
            self._update_interaction(interaction)
            
            logger.info(f"✅ Client agreed to help for {interaction.domain}")
            return {
                "success": True,
                "agreed": True,
                "next_step": "send_payment_link",
                "message": "Client agreed to proceed with SEO improvements"
            }
        else:
            interaction.status = InteractionStatus.CLIENT_RESPONDED
            self._update_interaction(interaction)
            
            logger.info(f"📝 Client responded but didn't agree for {interaction.domain}")
            return {
                "success": True,
                "agreed": False,
                "next_step": "follow_up",
                "message": "Client responded but didn't express interest"
            }
    
    def send_payment_link(self, business_site_id: str, payment_link: str) -> bool:
        """Send payment link to client"""
        interaction = self.interactions.get(business_site_id)
        if not interaction:
            return False
        
        payment_message = f"""Great! We're excited to help improve your SEO. 

Here's your secure payment link for the $100 SEO improvement package:
{payment_link}

Once payment is completed, we'll need your website credentials to implement the improvements.

What's included:
• Fix all identified SEO issues
• Improve local search rankings
• 7-day results guarantee
• Human QA review

Let us know when you've completed the payment!"""

        interaction.communication_log.append({
            "date": datetime.now().isoformat(),
            "type": "payment_link_sent",
            "message": payment_message
        })
        
        interaction.payment_link = payment_link
        interaction.status = InteractionStatus.PAYMENT_LINK_SENT
        self._update_interaction(interaction)
        
        logger.info(f"✅ Payment link sent to {interaction.domain}")
        return True
    
    def request_credentials(self, business_site_id: str) -> bool:
        """Request website credentials from client"""
        interaction = self.interactions.get(business_site_id)
        if not interaction:
            return False
        
        credentials_message = f"""Perfect! Payment received. 

Now we need your website credentials to implement the SEO improvements:

Please provide:
• Website URL: {interaction.domain}
• CMS login URL (if different)
• Username
• Password

We'll securely store these and use them only for implementing your SEO fixes.

You can reply with the details or let us know if you need help finding them."""

        interaction.communication_log.append({
            "date": datetime.now().isoformat(),
            "type": "credentials_requested",
            "message": credentials_message
        })
        
        interaction.status = InteractionStatus.CREDENTIALS_REQUESTED
        interaction.credentials_requested_date = datetime.now()
        self._update_interaction(interaction)
        
        logger.info(f"✅ Credentials requested from {interaction.domain}")
        return True
    
    def collect_credentials(self, business_site_id: str, 
                          website_url: str, username: str, password: str,
                          cms_login_url: str = None, notes: str = None) -> bool:
        """Collect and store client credentials"""
        interaction = self.interactions.get(business_site_id)
        if not interaction:
            return False
        
        # Store credentials (in production, this should be encrypted)
        interaction.website_url = website_url
        interaction.cms_login_url = cms_login_url
        interaction.username = username
        interaction.password_encrypted = password  # In production, encrypt this
        interaction.credentials_notes = notes
        interaction.credentials_collected_date = datetime.now()
        interaction.status = InteractionStatus.CREDENTIALS_COLLECTED
        
        # Log credential collection (without sensitive data)
        interaction.communication_log.append({
            "date": datetime.now().isoformat(),
            "type": "credentials_collected",
            "message": f"Credentials collected for {website_url}"
        })
        
        self._update_interaction(interaction)
        
        logger.info(f"✅ Credentials collected for {interaction.domain}")
        return True
    
    def notify_owner_completion(self, business_site_id: str, 
                               changes_made: List[str], qa_approved: bool = True) -> bool:
        """Send final notification to business owner"""
        interaction = self.interactions.get(business_site_id)
        if not interaction:
            return False
        
        changes_text = "\n• ".join(changes_made)
        
        if qa_approved:
            completion_message = f"""🎉 Your SEO improvements are complete!

We've successfully implemented the following changes:
• {changes_text}

Your site has been reviewed and approved by our QA team.

Please review your website and let us know how it looks! We'd love to hear your feedback.

If you're happy with the results, please consider leaving us a review.

Thank you for choosing Rankzen!"""
        else:
            completion_message = f"""Your SEO improvements are ready for review!

We've implemented the following changes:
• {changes_text}

Please review your website and let us know if any adjustments are needed.

We're here to make sure you're completely satisfied!"""

        interaction.communication_log.append({
            "date": datetime.now().isoformat(),
            "type": "completion_notification",
            "message": completion_message
        })
        
        interaction.status = InteractionStatus.OWNER_NOTIFIED
        interaction.owner_notified_date = datetime.now()
        interaction.final_message_sent = completion_message
        
        if qa_approved:
            interaction.completion_date = datetime.now()
            interaction.status = InteractionStatus.COMPLETED
        
        self._update_interaction(interaction)
        
        logger.info(f"✅ Completion notification sent to {interaction.domain}")
        return True
    
    def get_interaction(self, business_site_id: str) -> Optional[ClientInteraction]:
        """Get interaction by ID"""
        return self.interactions.get(business_site_id)
    
    def get_all_interactions(self) -> List[ClientInteraction]:
        """Get all interactions"""
        return list(self.interactions.values())
    
    def get_interactions_by_status(self, status: InteractionStatus) -> List[ClientInteraction]:
        """Get interactions by status"""
        return [i for i in self.interactions.values() if i.status == status]

# Global instance
communication_manager = CommunicationManager()
