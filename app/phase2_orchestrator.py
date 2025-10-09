import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from app.config import config
from app.phase2_models import (
    ClientInteraction, InteractionStatus, PaymentStatus, QAResult,
    QARequest, QAResponse, SEOImplementation, OwnerNotification
)
from app.communication_manager import communication_manager
from app.payment_handler import payment_handler
from app.credentials_manager import credentials_manager
from app.seo_implementer import seo_implementer
from app.qa_manager import qa_manager
from app.utils import data_manager

logger = logging.getLogger(__name__)

class Phase2Orchestrator:
    """Orchestrates the complete Phase 2 client interaction and fulfillment workflow"""
    
    def __init__(self):
        self.communication_manager = communication_manager
        self.payment_handler = payment_handler
        self.credentials_manager = credentials_manager
        self.seo_implementer = seo_implementer
        self.qa_manager = qa_manager
    
    def run_phase2_workflow(self, business_site_id: str, domain: str, 
                          business_name: str, seo_score: int, 
                          seo_issues: List[str], seo_recommendations: List[str]) -> Dict[str, Any]:
        """
        Run the complete Phase 2 workflow for a single client
        """
        logger.info(f"🚀 Starting Phase 2 workflow for {domain}")
        
        workflow_result = {
            'business_site_id': business_site_id,
            'domain': domain,
            'start_time': datetime.now().isoformat(),
            'status': 'started',
            'steps_completed': [],
            'errors': []
        }
        
        try:
            # Step 1: Start client interaction
            interaction = self.communication_manager.start_interaction(
                business_site_id=business_site_id,
                domain=domain,
                business_name=business_name,
                seo_score=seo_score,
                seo_issues=seo_issues,
                seo_recommendations=seo_recommendations
            )
            workflow_result['steps_completed'].append('interaction_started')
            
            # Step 2: Send engagement message
            if self.communication_manager.send_engagement_message(business_site_id, seo_issues):
                workflow_result['steps_completed'].append('engagement_sent')
                logger.info(f"✅ Engagement message sent to {domain}")
            else:
                raise Exception("Failed to send engagement message")
            
            workflow_result['end_time'] = datetime.now().isoformat()
            workflow_result['status'] = 'engagement_completed'
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"❌ Error in Phase 2 workflow: {e}")
            workflow_result['errors'].append(str(e))
            workflow_result['status'] = 'failed'
            workflow_result['end_time'] = datetime.now().isoformat()
            return workflow_result
    
    def process_client_response(self, business_site_id: str, response_text: str) -> Dict[str, Any]:
        """
        Process client response and continue workflow
        """
        logger.info(f"📝 Processing client response for {business_site_id}")
        
        result = {
            'business_site_id': business_site_id,
            'response_processed': False,
            'next_step': None,
            'errors': []
        }
        
        try:
            # Process the response
            response_result = self.communication_manager.process_client_response(business_site_id, response_text)
            
            if response_result['success']:
                result['response_processed'] = True
                
                if response_result['agreed']:
                    # Client agreed to help - send payment link
                    payment_link = self.payment_handler.create_payment_link(
                        business_site_id=business_site_id,
                        amount=10000,  # $100
                        description=f"SEO improvements for {business_site_id}"
                    )
                    
                    if payment_link:
                        self.communication_manager.send_payment_link(business_site_id, payment_link)
                        result['next_step'] = 'payment_link_sent'
                        logger.info(f"✅ Payment link sent to {business_site_id}")
                    else:
                        result['errors'].append("Failed to create payment link")
                else:
                    result['next_step'] = 'follow_up_needed'
                    logger.info(f"📝 Client responded but didn't agree for {business_site_id}")
            else:
                result['errors'].append(response_result.get('error', 'Unknown error'))
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing client response: {e}")
            result['errors'].append(str(e))
            return result
    
    def handle_payment_completion(self, business_site_id: str, session_id: str) -> Dict[str, Any]:
        """
        Handle payment completion and move to credentials collection
        """
        logger.info(f"💳 Handling payment completion for {business_site_id}")
        
        result = {
            'business_site_id': business_site_id,
            'payment_verified': False,
            'next_step': None,
            'errors': []
        }
        
        try:
            # Verify payment
            payment_verification = self.payment_handler.verify_payment(session_id)
            
            if payment_verification['success']:
                result['payment_verified'] = True
                
                # Update interaction status
                interaction = self.communication_manager.get_interaction(business_site_id)
                if interaction:
                    interaction.payment_status = PaymentStatus.COMPLETED
                    interaction.payment_completed_date = datetime.now()
                    interaction.stripe_session_id = session_id
                    interaction.status = InteractionStatus.PAYMENT_COMPLETED
                
                # Request credentials
                if self.communication_manager.request_credentials(business_site_id):
                    result['next_step'] = 'credentials_requested'
                    logger.info(f"✅ Credentials requested for {business_site_id}")
                else:
                    result['errors'].append("Failed to request credentials")
            else:
                result['errors'].append(payment_verification.get('error', 'Payment verification failed'))
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error handling payment completion: {e}")
            result['errors'].append(str(e))
            return result
    
    def collect_credentials(self, business_site_id: str, website_url: str, 
                          username: str, password: str, cms_login_url: str = None,
                          notes: str = None) -> Dict[str, Any]:
        """
        Collect and store client credentials
        """
        logger.info(f"🔐 Collecting credentials for {business_site_id}")
        
        result = {
            'business_site_id': business_site_id,
            'credentials_stored': False,
            'next_step': None,
            'errors': []
        }
        
        try:
            # Store credentials
            if self.credentials_manager.store_credentials(
                business_site_id=business_site_id,
                website_url=website_url,
                username=username,
                password=password,
                cms_login_url=cms_login_url,
                notes=notes
            ):
                result['credentials_stored'] = True
                
                # Update interaction
                if self.communication_manager.collect_credentials(
                    business_site_id, website_url, username, password, cms_login_url, notes
                ):
                    result['next_step'] = 'seo_implementation_ready'
                    logger.info(f"✅ Credentials collected for {business_site_id}")
                else:
                    result['errors'].append("Failed to update interaction")
            else:
                result['errors'].append("Failed to store credentials")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error collecting credentials: {e}")
            result['errors'].append(str(e))
            return result
    
    def start_seo_implementation(self, business_site_id: str, 
                               changes_to_implement: List[str]) -> Dict[str, Any]:
        """
        Start SEO implementation process
        """
        logger.info(f"🔧 Starting SEO implementation for {business_site_id}")
        
        result = {
            'business_site_id': business_site_id,
            'implementation_started': False,
            'next_step': None,
            'errors': []
        }
        
        try:
            # Start implementation
            implementation_result = self.seo_implementer.start_implementation(
                business_site_id, changes_to_implement
            )
            
            if implementation_result['success']:
                result['implementation_started'] = True
                result['changes_implemented'] = implementation_result['changes_implemented']
                
                # Update interaction
                interaction = self.communication_manager.get_interaction(business_site_id)
                if interaction:
                    interaction.status = InteractionStatus.SEO_FIXES_COMPLETED
                    interaction.seo_fixes_completed_date = datetime.now()
                    interaction.changes_made = implementation_result['changes_implemented']
                    interaction.implementation_success = True
                
                # Request QA review
                qa_result = self.qa_manager.request_qa_review(
                    business_site_id=business_site_id,
                    website_url=interaction.website_url if interaction else "",
                    changes_made=implementation_result['changes_implemented']
                )
                
                if qa_result['success']:
                    result['next_step'] = 'qa_requested'
                    logger.info(f"✅ QA review requested for {business_site_id}")
                else:
                    result['errors'].append("Failed to request QA review")
            else:
                result['errors'].extend(implementation_result.get('errors', []))
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error starting SEO implementation: {e}")
            result['errors'].append(str(e))
            return result
    
    def submit_qa_response(self, business_site_id: str, reviewer: str,
                          qa_result: str, notes: str = None) -> Dict[str, Any]:
        """
        Submit QA review response
        """
        logger.info(f"📝 Submitting QA response for {business_site_id}")
        
        result = {
            'business_site_id': business_site_id,
            'qa_response_submitted': False,
            'next_step': None,
            'errors': []
        }
        
        try:
            # Submit QA response
            qa_response = self.qa_manager.submit_qa_response(
                business_site_id, reviewer, qa_result, notes
            )
            
            if qa_response['success']:
                result['qa_response_submitted'] = True
                
                # Update interaction
                interaction = self.communication_manager.get_interaction(business_site_id)
                if interaction:
                    if qa_result.lower() == 'approved':
                        interaction.status = InteractionStatus.QA_APPROVED
                        interaction.qa_result = QAResult.APPROVED
                        
                        # Notify owner of completion
                        if self.communication_manager.notify_owner_completion(
                            business_site_id, 
                            interaction.changes_made or [],
                            qa_approved=True
                        ):
                            result['next_step'] = 'owner_notified'
                            logger.info(f"✅ Owner notified of completion for {business_site_id}")
                        else:
                            result['errors'].append("Failed to notify owner")
                    else:
                        interaction.status = InteractionStatus.QA_REJECTED
                        interaction.qa_result = QAResult.REJECTED
                        result['next_step'] = 'revision_needed'
                        logger.info(f"⚠️ QA rejected for {business_site_id}")
            else:
                result['errors'].append(qa_response.get('error', 'QA response failed'))
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error submitting QA response: {e}")
            result['errors'].append(str(e))
            return result
    
    def get_workflow_status(self, business_site_id: str) -> Dict[str, Any]:
        """
        Get current workflow status for a business
        """
        try:
            interaction = self.communication_manager.get_interaction(business_site_id)
            if not interaction:
                return {
                    'business_site_id': business_site_id,
                    'status': 'not_found',
                    'error': 'No interaction found'
                }
            
            # Get additional status information
            qa_status = self.qa_manager.get_qa_status(business_site_id)
            implementation_status = self.seo_implementer.get_implementation_status(business_site_id)
            credentials_exist = self.credentials_manager.validate_credentials(business_site_id)
            
            return {
                'business_site_id': business_site_id,
                'domain': interaction.domain,
                'business_name': interaction.business_name,
                'current_status': interaction.status.value,
                'payment_status': interaction.payment_status.value,
                'qa_status': qa_status.get('qa_result') if qa_status else None,
                'implementation_status': implementation_status.get('status') if implementation_status else None,
                'credentials_collected': credentials_exist,
                'last_updated': interaction.initial_outreach_date.isoformat() if interaction.initial_outreach_date else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting workflow status: {e}")
            return {
                'business_site_id': business_site_id,
                'status': 'error',
                'error': str(e)
            }
    
    def get_pending_interactions(self) -> List[Dict[str, Any]]:
        """
        Get list of pending interactions that need monitoring/processing
        """
        try:
            interactions = self.communication_manager.get_all_interactions()
            pending_interactions = []
            
            for interaction in interactions:
                # Check if interaction needs monitoring based on status
                if interaction.status in [
                    InteractionStatus.ENGAGEMENT_SENT,
                    InteractionStatus.PAYMENT_PENDING,
                    InteractionStatus.CREDENTIALS_PENDING,
                    InteractionStatus.IMPLEMENTATION_IN_PROGRESS,
                    InteractionStatus.QA_PENDING
                ]:
                    pending_interactions.append({
                        'business_site_id': interaction.business_site_id,
                        'domain': interaction.domain,
                        'business_name': interaction.business_name,
                        'status': interaction.status.value,
                        'payment_status': interaction.payment_status.value,
                        'last_updated': interaction.initial_outreach_date.isoformat() if interaction.initial_outreach_date else None
                    })
            
            logger.debug(f"📧 Found {len(pending_interactions)} pending interactions")
            return pending_interactions
            
        except Exception as e:
            logger.error(f"❌ Error getting pending interactions: {e}")
            return []

    def get_workflow_summary(self) -> Dict[str, Any]:
        """
        Get summary of all Phase 2 workflows
        """
        try:
            interactions = self.communication_manager.get_all_interactions()
            
            total_interactions = len(interactions)
            interactions_by_status = {}
            
            for status in InteractionStatus:
                interactions_by_status[status.value] = len([
                    i for i in interactions if i.status == status
                ])
            
            # Get additional summaries
            payment_summary = {
                'total_payments': len([i for i in interactions if i.payment_status == PaymentStatus.COMPLETED]),
                'pending_payments': len([i for i in interactions if i.payment_status == PaymentStatus.PENDING])
            }
            
            qa_summary = self.qa_manager.get_qa_summary()
            implementation_summary = self.seo_implementer.get_implementation_summary()
            credentials_summary = self.credentials_manager.get_credentials_summary()
            
            return {
                'total_interactions': total_interactions,
                'interactions_by_status': interactions_by_status,
                'payment_summary': payment_summary,
                'qa_summary': qa_summary,
                'implementation_summary': implementation_summary,
                'credentials_summary': credentials_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting workflow summary: {e}")
            return {
                'total_interactions': 0,
                'interactions_by_status': {},
                'error': str(e)
            }

# Global instance
phase2_orchestrator = Phase2Orchestrator()
