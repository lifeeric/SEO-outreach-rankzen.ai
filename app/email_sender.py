import requests
import logging
from typing import List, Dict, Any, Optional
from app.config import config
from app.models import BusinessSite, OutreachMessage
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EmailSender:
    """Handles email sending using Resend API"""
    
    def __init__(self):
        self.base_url = "https://api.resend.com"
    
    @property
    def api_key(self):
        """Dynamically get the API key from config (which now comes from database)"""
        return config.RESEND_API_KEY
    
    @property
    def headers(self):
        """Dynamically generate headers with current API key"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def send_outreach_email(self, site: BusinessSite, message: OutreachMessage, recipient_email: str, campaign_type: str = "outreach") -> bool:
        """
        Send outreach email using Resend API and record in database
        
        Args:
            site: BusinessSite object
            message: OutreachMessage object
            recipient_email: Recipient email address
            campaign_type: Type of campaign - "outreach" or "follow-up"
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.api_key:
            logger.warning("Resend API key not configured")
            return False
            
        if not recipient_email:
            logger.warning(f"No email address provided for {site.domain}")
            return False
        
        try:
            # Prepare email parameters - Updated to use proper sender format: "Name <email@example.com>"
            params = {
                "from": "Rankzen <support@rankzen.ai>",  # Corrected sender email format
                "to": [recipient_email],        # recipient email
                "subject": message.subject,
                "html": message.message.replace('\n', '<br>')  # Convert plain text to HTML
            }
            
            # Send email via Resend API
            response = requests.post(
                f"{self.base_url}/emails",
                headers=self.headers,
                json=params,
                timeout=30
            )
            
            message_id = None
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('id', 'unknown')
                logger.info(f"✅ Email sent successfully to {recipient_email} for {site.domain}. Message ID: {message_id}")
                
                # Record email in database
                self._record_email_in_db(site, recipient_email, campaign_type, message_id, "sent")
                return True
            else:
                logger.error(f"❌ Failed to send email to {recipient_email} for {site.domain}. Status: {response.status_code}, Response: {response.text}")
                
                # Record failed attempt in database
                self._record_email_in_db(site, recipient_email, campaign_type, message_id, "failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending email to {recipient_email} for {site.domain}: {e}")
            
            # Record error in database
            self._record_email_in_db(site, recipient_email, campaign_type, None, "error")
            return False
    
    def _record_email_in_db(self, site: BusinessSite, recipient_email: str, campaign_type: str, message_id: str, status: str):
        """
        Record email sending attempt in database
        
        Args:
            site: BusinessSite object
            recipient_email: Recipient email address
            campaign_type: Type of campaign - "outreach" or "follow-up"
            message_id: Resend message ID
            status: Status of the email sending attempt
        """
        try:
            # Import db here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from web_control_panel import db, EmailOutreach, app
            
            # Use app context to avoid "The current Flask app is not registered" error
            with app.app_context():
                email_record = EmailOutreach(
                    message_id=message_id,
                    recipient_email=recipient_email,
                    domain=site.domain,
                    campaign_type=campaign_type,
                    status=status,
                    sent_at=datetime.utcnow()
                )
                db.session.add(email_record)
                db.session.commit()
                logger.info(f"✅ Email record added to database for {recipient_email} - {campaign_type}")
        except Exception as e:
            logger.error(f"❌ Error recording email in database: {e}")
            # Try to rollback if db session exists
            try:
                from web_control_panel import db
                db.session.rollback()
            except:
                pass
    
    def check_and_send_follow_ups(self):
        """
        Check for emails sent 3+ days ago with no reply and send follow-up emails
        This method should be called periodically to handle follow-up automation
        """
        try:
            # Import db and EmailOutreach here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from web_control_panel import db, EmailOutreach
            
            # Find outreach emails sent 3+ days ago that haven't had a follow-up sent
            three_days_ago = datetime.utcnow() - timedelta(days=3)
            
            outreach_emails = EmailOutreach.query.filter(
                EmailOutreach.campaign_type == "outreach",
                EmailOutreach.status == "sent",
                EmailOutreach.sent_at <= three_days_ago,
                EmailOutreach.follow_up_sent == False
            ).all()
            
            follow_up_count = 0
            for email_record in outreach_emails:
                # Check if there's been a reply (in a real implementation, this would check for replies)
                # For now, we'll assume no reply has been received
                has_replied = self._check_for_reply(email_record)
                
                if not has_replied:
                    # Send follow-up email
                    if self._send_follow_up_email(email_record):
                        follow_up_count += 1
            
            if follow_up_count > 0:
                logger.info(f"📧 Sent {follow_up_count} follow-up emails")
                
        except Exception as e:
            logger.error(f"❌ Error checking and sending follow-ups: {e}")
    
    def _check_for_reply(self, email_record) -> bool:
        """
        Check if a reply has been received for an email
        In a real implementation, this would integrate with email receiving/webhook functionality
        For now, we'll return False to simulate no reply received
        
        Args:
            email_record: EmailOutreach record to check
            
        Returns:
            bool: True if reply received, False otherwise
        """
        # TODO: Implement actual reply checking logic
        # This would typically involve:
        # 1. Setting up webhooks with Resend to receive inbound emails
        # 2. Checking for replies based on message thread/reference headers
        # 3. Updating the email record status when replies are received
        
        # For now, we'll assume no reply has been received
        return False
    
    def _send_follow_up_email(self, email_record) -> bool:
        """
        Send a follow-up email for an outreach email that didn't receive a reply
        
        Args:
            email_record: EmailOutreach record to send follow-up for
            
        Returns:
            bool: True if follow-up sent successfully, False otherwise
        """
        try:
            # Import db and EmailOutreach here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from web_control_panel import db, EmailOutreach
            
            # Create follow-up message content
            follow_up_subject = f"Following up on my previous message about {email_record.domain}"
            follow_up_body = f"""<p>Hi there,</p>
<p>I wanted to follow up on my previous message about SEO improvements for {email_record.domain}.</p>
<p>I understand you might be busy, but I wanted to reiterate that we can help improve your local search rankings with a quick fix for just $100.</p>
<p>Would you like us to implement these improvements this week?</p>
<p>Just reply "YES" if interested or "NO" if not.</p>
<p>Best regards,<br>The Rankzen Team</p>"""
            
            # Prepare email parameters - Updated to use proper sender format: "Name <email@example.com>"
            params = {
                "from": "Rankzen <support@rankzen.ai>",  # Corrected sender email format
                "to": [email_record.recipient_email],
                "subject": follow_up_subject,
                "html": follow_up_body
            }
            
            # Send follow-up email via Resend API
            response = requests.post(
                f"{self.base_url}/emails",
                headers=self.headers,
                json=params,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                follow_up_message_id = result.get('id', 'unknown')
                logger.info(f"✅ Follow-up email sent to {email_record.recipient_email}. Message ID: {follow_up_message_id}")
                
                # Update the original record to mark follow-up as sent
                email_record.follow_up_sent = True
                email_record.follow_up_message_id = follow_up_message_id
                db.session.commit()
                
                # Record follow-up email in database
                follow_up_record = EmailOutreach(
                    message_id=follow_up_message_id,
                    recipient_email=email_record.recipient_email,
                    domain=email_record.domain,
                    campaign_type="follow-up",
                    status="sent",
                    sent_at=datetime.utcnow(),
                    follow_up_sent=False
                )
                db.session.add(follow_up_record)
                db.session.commit()
                
                return True
            else:
                logger.error(f"❌ Failed to send follow-up email to {email_record.recipient_email}. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error sending follow-up email to {email_record.recipient_email}: {e}")
            return False
    
    def validate_email(self, email: str) -> bool:
        """
        Basic email validation
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if email is valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
            
        # Basic email format validation
        return "@" in email and "." in email.split("@")[-1]

# Create global email sender instance
email_sender = EmailSender()

# Add a function to check for follow-ups that can be called externally
def check_follow_ups():
    """Check for and send follow-up emails"""
    email_sender.check_and_send_follow_ups()