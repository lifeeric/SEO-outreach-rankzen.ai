import logging
import stripe
from typing import Dict, Any, Optional
from datetime import datetime

from app.config import config
from app.phase2_models import PaymentRequest, PaymentResponse, PaymentStatus

logger = logging.getLogger(__name__)

class PaymentHandler:
    """Handles Stripe payment processing for Phase 2"""
    
    def __init__(self):
        self.stripe = stripe
        # Stripe API key is set dynamically when needed
    
    @property
    def stripe_secret_key(self):
        """Dynamically get the Stripe secret key from config"""
        return config.STRIPE_SECRET_KEY
    
    @property
    def stripe_publishable_key(self):
        """Dynamically get the Stripe publishable key from config"""
        return config.STRIPE_PUBLISHABLE_KEY
    
    @property
    def stripe_webhook_secret(self):
        """Dynamically get the Stripe webhook secret from config"""
        return config.STRIPE_WEBHOOK_SECRET
    
    def create_payment_link(self, business_site_id: str, amount: int = 10000, 
                          description: str = None) -> Optional[str]:
        """Create a Stripe payment link for $100 SEO package"""
        try:
            # Configure Stripe with current API key
            self.stripe.api_key = self.stripe_secret_key
            
            if not self.stripe_secret_key or self.stripe_secret_key == "":
                logger.error("❌ Stripe secret key not configured")
                return None
            
            # Create payment link
            payment_link_data = {
                'line_items': [{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'SEO Improvement Package',
                            'description': description or f'SEO improvements for {business_site_id}'
                        },
                        'unit_amount': amount,  # $100 in cents
                    },
                    'quantity': 1,
                }],
                'after_completion': {
                    'type': 'redirect',
                    'redirect': {
                        'url': f'https://rankzen.com/payment-success?business_id={business_site_id}'
                    }
                },
                'metadata': {
                    'business_site_id': business_site_id,
                    'service': 'seo_improvements'
                }
            }
            
            # Note: Using product_data instead of product key for dynamic product creation
            
            payment_link = self.stripe.PaymentLink.create(**payment_link_data)
            
            logger.info(f"✅ Payment link created for {business_site_id}: {payment_link.url}")
            return payment_link.url
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ Stripe error creating payment link: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error creating payment link: {e}")
            return None
    
    def verify_payment(self, session_id: str) -> Dict[str, Any]:
        """Verify payment completion using session ID"""
        try:
            if not self.stripe_secret_key:
                return {"success": False, "error": "Stripe not configured"}
            
            session = self.stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                return {
                    "success": True,
                    "payment_status": "completed",
                    "amount": session.amount_total,
                    "currency": session.currency,
                    "customer_email": session.customer_details.email if session.customer_details else None,
                    "business_site_id": session.metadata.get('business_site_id') if session.metadata else None
                }
            else:
                return {
                    "success": False,
                    "payment_status": session.payment_status,
                    "error": "Payment not completed"
                }
                
        except stripe.error.StripeError as e:
            logger.error(f"❌ Stripe error verifying payment: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"❌ Error verifying payment: {e}")
            return {"success": False, "error": str(e)}
    
    def process_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Process Stripe webhook events"""
        try:
            if not self.stripe_webhook_secret:
                logger.warning("⚠️ Stripe webhook secret not configured")
                return {"success": False, "error": "Webhook secret not configured"}
            
            event = self.stripe.Webhook.construct_event(
                payload, sig_header, self.stripe_webhook_secret
            )
            
            # Handle different event types
            if event['type'] == 'checkout.session.completed':
                return self._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'payment_intent.succeeded':
                return self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                return self._handle_payment_failed(event['data']['object'])
            else:
                logger.info(f"📝 Unhandled webhook event: {event['type']}")
                return {"success": True, "event": event['type'], "handled": False}
                
        except ValueError as e:
            logger.error(f"❌ Invalid payload: {e}")
            return {"success": False, "error": "Invalid payload"}
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"❌ Invalid signature: {e}")
            return {"success": False, "error": "Invalid signature"}
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_checkout_completed(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle checkout.session.completed event"""
        try:
            business_site_id = session.get('metadata', {}).get('business_site_id')
            if not business_site_id:
                logger.error("❌ No business_site_id in session metadata")
                return {"success": False, "error": "No business_site_id"}
            
            logger.info(f"✅ Payment completed for {business_site_id}")
            
            return {
                "success": True,
                "event": "checkout.session.completed",
                "business_site_id": business_site_id,
                "amount": session.get('amount_total'),
                "currency": session.get('currency'),
                "customer_email": session.get('customer_details', {}).get('email')
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling checkout completed: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment_intent.succeeded event"""
        try:
            logger.info(f"✅ Payment succeeded: {payment_intent.get('id')}")
            
            return {
                "success": True,
                "event": "payment_intent.succeeded",
                "payment_intent_id": payment_intent.get('id'),
                "amount": payment_intent.get('amount'),
                "currency": payment_intent.get('currency')
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling payment succeeded: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment_intent.payment_failed event"""
        try:
            logger.warning(f"⚠️ Payment failed: {payment_intent.get('id')}")
            
            return {
                "success": True,
                "event": "payment_intent.payment_failed",
                "payment_intent_id": payment_intent.get('id'),
                "error": payment_intent.get('last_payment_error', {}).get('message')
            }
            
        except Exception as e:
            logger.error(f"❌ Error handling payment failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_payment_status(self, session_id: str) -> PaymentStatus:
        """Get payment status for a session"""
        try:
            if not self.stripe_secret_key:
                return PaymentStatus.FAILED
            
            session = self.stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                return PaymentStatus.COMPLETED
            elif session.payment_status == 'unpaid':
                return PaymentStatus.PENDING
            else:
                return PaymentStatus.FAILED
                
        except Exception as e:
            logger.error(f"❌ Error getting payment status: {e}")
            return PaymentStatus.FAILED
    
    def create_refund(self, payment_intent_id: str, amount: int = None) -> Dict[str, Any]:
        """Create a refund for a payment"""
        try:
            if not self.stripe_secret_key:
                return {"success": False, "error": "Stripe not configured"}
            
            refund_data = {'payment_intent': payment_intent_id}
            if amount:
                refund_data['amount'] = amount
            
            refund = self.stripe.Refund.create(**refund_data)
            
            logger.info(f"✅ Refund created: {refund.id}")
            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ Stripe error creating refund: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"❌ Error creating refund: {e}")
            return {"success": False, "error": str(e)}

# Global instance
payment_handler = PaymentHandler()
