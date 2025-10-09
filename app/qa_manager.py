import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from app.config import config
from app.phase2_models import QARequest, QAResponse, QAResult

logger = logging.getLogger(__name__)

class QAManager:
    """Manages human QA review process for SEO implementations"""
    
    def __init__(self):
        self.qa_log_file = Path("data/qa_reviews.jsonl")
        self.qa_log_file.parent.mkdir(exist_ok=True)
        self.qa_reviews: Dict[str, Dict[str, Any]] = {}
        self._load_qa_reviews()
    
    def _load_qa_reviews(self):
        """Load existing QA reviews from file"""
        if self.qa_log_file.exists():
            try:
                with open(self.qa_log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            self.qa_reviews[data['business_site_id']] = data
                logger.info(f"Loaded {len(self.qa_reviews)} existing QA reviews")
            except Exception as e:
                logger.error(f"Error loading QA reviews: {e}")
    
    def _save_qa_review(self, qa_data: Dict[str, Any]):
        """Save QA review to file"""
        try:
            with open(self.qa_log_file, 'a') as f:
                f.write(json.dumps(qa_data) + '\n')
        except Exception as e:
            logger.error(f"Error saving QA review: {e}")
    
    def request_qa_review(self, business_site_id: str, website_url: str,
                         changes_made: List[str], reviewer_email: str = None) -> Dict[str, Any]:
        """Request human QA review for SEO implementation"""
        logger.info(f"🔍 Requesting QA review for {business_site_id}")
        
        # Use default reviewer if none specified
        if not reviewer_email:
            reviewer_email = config.QA_REVIEWER_EMAIL
        
        qa_data = {
            "business_site_id": business_site_id,
            "website_url": website_url,
            "reviewer_email": reviewer_email,
            "request_date": datetime.now().isoformat(),
            "changes_made": changes_made,
            "status": "pending",
            "qa_result": "pending",
            "reviewer_notes": None,
            "review_date": None,
            "review_url": None
        }
        
        self.qa_reviews[business_site_id] = qa_data
        self._save_qa_review(qa_data)
        
        # Send notification to reviewer
        notification_sent = self._send_qa_notification(qa_data)
        
        if notification_sent:
            logger.info(f"✅ QA review requested for {business_site_id}")
            return {
                "success": True,
                "qa_request_id": business_site_id,
                "reviewer_email": reviewer_email,
                "notification_sent": True
            }
        else:
            logger.warning(f"⚠️ QA review requested but notification failed for {business_site_id}")
            return {
                "success": True,
                "qa_request_id": business_site_id,
                "reviewer_email": reviewer_email,
                "notification_sent": False
            }
    
    def _send_qa_notification(self, qa_data: Dict[str, Any]) -> bool:
        """Send notification to QA reviewer"""
        try:
            reviewer_email = qa_data.get('reviewer_email')
            website_url = qa_data.get('website_url')
            changes_made = qa_data.get('changes_made', [])
            
            # Create notification message
            changes_text = "\n• ".join(changes_made)
            
            notification_message = f"""🔍 QA Review Request

A new SEO implementation requires your review:

Website: {website_url}
Business ID: {qa_data.get('business_site_id')}

Changes Made:
• {changes_text}

Please review the website and approve or reject the implementation.

Review URL: {website_url}

Reply with:
- APPROVED: If the implementation looks good
- REJECTED: If changes are needed
- NEEDS_REVISION: If minor adjustments are required

Thank you!"""

            # In production, this would send an email or Slack notification
            logger.info(f"📧 QA notification would be sent to {reviewer_email}")
            logger.info(f"Notification content: {notification_message}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending QA notification: {e}")
            return False
    
    def submit_qa_response(self, business_site_id: str, reviewer: str,
                          qa_result: str, notes: str = None) -> Dict[str, Any]:
        """Submit QA review response"""
        logger.info(f"📝 Submitting QA response for {business_site_id}")
        
        if business_site_id not in self.qa_reviews:
            return {
                "success": False,
                "error": "QA review not found for this business"
            }
        
        qa_data = self.qa_reviews[business_site_id]
        
        # Update QA data
        qa_data["status"] = "completed"
        qa_data["qa_result"] = qa_result.lower()
        qa_data["reviewer"] = reviewer
        qa_data["reviewer_notes"] = notes
        qa_data["review_date"] = datetime.now().isoformat()
        
        # Save updated QA data
        self._save_qa_review(qa_data)
        
        logger.info(f"✅ QA response submitted for {business_site_id}: {qa_result}")
        
        return {
            "success": True,
            "qa_result": qa_result,
            "reviewer": reviewer,
            "review_date": qa_data["review_date"]
        }
    
    def get_qa_status(self, business_site_id: str) -> Optional[Dict[str, Any]]:
        """Get QA status for a business"""
        return self.qa_reviews.get(business_site_id)
    
    def get_pending_qa_reviews(self) -> List[Dict[str, Any]]:
        """Get all pending QA reviews"""
        return [
            qa_data for qa_data in self.qa_reviews.values() 
            if qa_data.get('status') == 'pending'
        ]
    
    def get_completed_qa_reviews(self) -> List[Dict[str, Any]]:
        """Get all completed QA reviews"""
        return [
            qa_data for qa_data in self.qa_reviews.values() 
            if qa_data.get('status') == 'completed'
        ]
    
    def get_qa_reviews_by_result(self, result: str) -> List[Dict[str, Any]]:
        """Get QA reviews by result"""
        return [
            qa_data for qa_data in self.qa_reviews.values() 
            if qa_data.get('qa_result') == result.lower()
        ]
    
    def get_qa_summary(self) -> Dict[str, Any]:
        """Get summary of QA reviews"""
        try:
            all_reviews = list(self.qa_reviews.values())
            
            total_reviews = len(all_reviews)
            pending_reviews = len([r for r in all_reviews if r.get('status') == 'pending'])
            completed_reviews = len([r for r in all_reviews if r.get('status') == 'completed'])
            
            approved_reviews = len([r for r in all_reviews if r.get('qa_result') == 'approved'])
            rejected_reviews = len([r for r in all_reviews if r.get('qa_result') == 'rejected'])
            needs_revision = len([r for r in all_reviews if r.get('qa_result') == 'needs_revision'])
            
            approval_rate = (approved_reviews / completed_reviews * 100) if completed_reviews > 0 else 0
            
            return {
                "total_reviews": total_reviews,
                "pending_reviews": pending_reviews,
                "completed_reviews": completed_reviews,
                "approved_reviews": approved_reviews,
                "rejected_reviews": rejected_reviews,
                "needs_revision": needs_revision,
                "approval_rate": round(approval_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting QA summary: {e}")
            return {
                "total_reviews": 0,
                "pending_reviews": 0,
                "completed_reviews": 0,
                "approved_reviews": 0,
                "rejected_reviews": 0,
                "needs_revision": 0,
                "approval_rate": 0
            }
    
    def approve_implementation(self, business_site_id: str, reviewer: str = "System") -> Dict[str, Any]:
        """Approve an implementation (for testing/demo purposes)"""
        return self.submit_qa_response(
            business_site_id=business_site_id,
            reviewer=reviewer,
            qa_result="approved",
            notes="Auto-approved for testing purposes"
        )
    
    def reject_implementation(self, business_site_id: str, reviewer: str = "System", 
                            notes: str = "Implementation needs improvement") -> Dict[str, Any]:
        """Reject an implementation (for testing/demo purposes)"""
        return self.submit_qa_response(
            business_site_id=business_site_id,
            reviewer=reviewer,
            qa_result="rejected",
            notes=notes
        )
    
    def request_revision(self, business_site_id: str, reviewer: str = "System",
                        notes: str = "Minor adjustments needed") -> Dict[str, Any]:
        """Request revision for an implementation (for testing/demo purposes)"""
        return self.submit_qa_response(
            business_site_id=business_site_id,
            reviewer=reviewer,
            qa_result="needs_revision",
            notes=notes
        )

# Global instance
qa_manager = QAManager()
