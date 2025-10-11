import logging
import requests
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

from app.config import config
from app.models import ContactForm, OutreachMessage, BusinessSite
from app.utils import extract_domain, clean_url, is_valid_url, data_manager
from app.captcha_solver import CaptchaSolver
from app.email_sender import email_sender
from app.network_client import http_client, DeadHostError

logger = logging.getLogger(__name__)

class FormSubmitter:
    """Handles automatic form submission with CAPTCHA solving"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.captcha_solver = CaptchaSolver()
    
    def submit_contact_form(self, site: BusinessSite, message: OutreachMessage) -> ContactForm:
        """
        Submit contact form for a business site
        Returns ContactForm with submission results
        """
        if not site.contact_form_url:
            logger.warning(f"No contact form URL for {site.domain}")
            return self._fallback_to_email(site, message, reason="no_contact_form")
        
        try:
            form_url = str(site.contact_form_url)
            logger.info(f"Submitting contact form for {site.domain}")

            if not http_client.is_reachable(form_url):
                logger.warning(f"Contact form unreachable for {site.domain}, falling back to email")
                return self._fallback_to_email(site, message, reason="contact_form_unreachable")
            
            # Get the form page
            response = http_client.get(form_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the contact form
            form = self._find_contact_form(soup)
            if not form:
                logger.warning(f"No form tag discovered on {form_url}, using email fallback")
                return self._fallback_to_email(site, message, reason="no_form_on_page")
            
            # Detect CAPTCHA
            captcha_info = self.captcha_solver.detect_captcha_type(soup)
            
            # Prepare form data
            form_data = self._prepare_form_data(form, message, site)
            
            # Handle CAPTCHA if present
            if captcha_info['has_captcha']:
                captcha_solution = self._handle_captcha(captcha_info, form_url, soup)
                if captcha_solution:
                    form_data.update(captcha_solution)
                else:
                    logger.warning(f"Failed to solve CAPTCHA for {site.domain}")
                    data_manager.add_log_entry(
                        "FORM_SUBMISSION", site.domain, "FAILED",
                        {"details": "captcha_failed", "form_url": form_url}
                    )
                    return ContactForm(
                        url=form_url,
                        has_captcha=True,
                        captcha_type=captcha_info['type'],
                        submitted=False,
                        error_message="Failed to solve CAPTCHA",
                        submission_method='form',
                        email_used=getattr(site, 'email', None)
                    )
            
            # Submit the form
            submit_url = self._get_submit_url(form, form_url)
            submit_response = http_client.post(submit_url, data=form_data, headers=self.headers)
            
            # Check submission result
            success = self._check_submission_success(submit_response)
            
            contact_form = ContactForm(
                url=form_url,
                form_fields=form_data,
                has_captcha=captcha_info['has_captcha'],
                captcha_type=captcha_info.get('type'),
                submitted=success,
                error_message=None if success else "Form submission failed",
                email_used=getattr(site, 'email', None),
                submission_method='form'
            )
            
            if success:
                logger.info(f"Successfully submitted contact form for {site.domain}")
                data_manager.add_log_entry(
                    "FORM_SUBMISSION",
                    site.domain,
                    "SUCCESS",
                    {
                        "method": contact_form.submission_method,
                        "form_url": form_url,
                        "email": contact_form.email_used
                    }
                )
                
                # Also send email if email address is available
                if hasattr(site, 'email') and site.email:
                    if email_sender.send_outreach_email(site, message, site.email):
                        logger.info(f"📧 Email also sent to {site.domain}")
                        contact_form.submission_method = 'form_and_email'
                        data_manager.add_log_entry(
                            "FORM_SUBMISSION",
                            site.domain,
                            "EMAIL_SENT",
                            {
                                "method": contact_form.submission_method,
                                "form_url": form_url,
                                "email": site.email
                            }
                        )
            else:
                logger.error(f"Failed to submit contact form for {site.domain}")
                data_manager.add_log_entry(
                    "FORM_SUBMISSION",
                    site.domain,
                    "FAILED",
                    {
                        "details": "form_submission_failed",
                        "form_url": form_url,
                        "email": getattr(site, 'email', None)
                    }
                )
            
            return contact_form
            
        except DeadHostError:
            logger.warning(f"Contact form host marked dead for {site.domain}, using email fallback")
            return self._fallback_to_email(site, message, reason="host_unreachable")
        except Exception as e:
            logger.error(f"Error submitting contact form for {site.domain}: {e}")
            data_manager.add_log_entry(
                "FORM_SUBMISSION",
                site.domain,
                "ERROR",
                {
                    "details": str(e),
                    "form_url": str(site.contact_form_url) if site.contact_form_url else None,
                    "email": getattr(site, 'email', None)
                }
            )
            return self._fallback_to_email(site, message, reason="exception_during_submission")

    def _fallback_to_email(self, site: BusinessSite, message: OutreachMessage, reason: str) -> ContactForm:
        """Send outreach email as a fallback when form submission is impossible."""
        email = getattr(site, 'email', None)
        fallback_url = str(site.contact_form_url) if site.contact_form_url else str(site.url)
        details = {
            "method": "email",
            "reason": reason,
            "form_url": fallback_url,
            "email": email
        }

        if email and email_sender.send_outreach_email(site, message, email):
            logger.info(f"📧 Email fallback sent to {email} for {site.domain}")
            data_manager.add_log_entry("FORM_SUBMISSION", site.domain, "EMAIL_SENT", details)
            return ContactForm(
                url=fallback_url,
                submitted=True,
                error_message=None,
                email_used=email,
                submission_method='email'
            )

        if not email:
            details["reason"] = f"{reason}_no_email"
        data_manager.add_log_entry("FORM_SUBMISSION", site.domain, "FAILED", details)

        return ContactForm(
            url=fallback_url,
            submitted=False,
            error_message=reason if email else "No email available for fallback",
            email_used=email,
            submission_method='none'
        )

    def _find_contact_form(self, soup: BeautifulSoup) -> Optional[Any]:
        """Find the contact form on the page"""
        # Look for forms with contact-related attributes
        contact_indicators = [
            'contact', 'message', 'inquiry', 'quote', 'consultation',
            'appointment', 'booking', 'request', 'form'
        ]
        
        forms = soup.find_all('form')
        
        for form in forms:
            # Check form action
            action = form.get('action', '').lower()
            if any(indicator in action for indicator in contact_indicators):
                return form
            
            # Check form ID
            form_id = form.get('id', '').lower()
            if any(indicator in form_id for indicator in contact_indicators):
                return form
            
            # Check form class
            form_class = form.get('class', [])
            if isinstance(form_class, list):
                form_class = ' '.join(form_class).lower()
            if any(indicator in form_class for indicator in contact_indicators):
                return form
            
            # Check for contact-related input fields
            inputs = form.find_all('input')
            for input_field in inputs:
                input_name = input_field.get('name', '').lower()
                input_placeholder = input_field.get('placeholder', '').lower()
                if any(indicator in input_name or indicator in input_placeholder for indicator in contact_indicators):
                    return form
        
        # If no specific contact form found, return the first form
        if forms:
            return forms[0]
        
        return None
    
    def _prepare_form_data(self, form: Any, message: OutreachMessage, site: BusinessSite) -> Dict[str, str]:
        """Prepare form data for submission"""
        form_data = {}
        
        # Common field mappings
        field_mappings = {
            'name': 'John Smith',
            'email': 'john.smith@example.com',
            'phone': '555-123-4567',
            'subject': message.subject,
            'message': message.message,
            'comment': message.message,
            'inquiry': message.message,
            'content': message.message,
            'description': message.message,
            'details': message.message,
            'company': 'SEO Consulting',
            'website': 'https://example.com'
        }
        
        # Find all input fields
        inputs = form.find_all('input')
        textareas = form.find_all('textarea')
        selects = form.find_all('select')
        
        # Process input fields
        for input_field in inputs:
            input_type = input_field.get('type', 'text').lower()
            input_name = input_field.get('name', '')
            
            if not input_name:
                continue
            
            if input_type in ['text', 'email', 'tel']:
                # Find appropriate value for this field
                value = self._get_field_value(input_name, field_mappings)
                if value:
                    form_data[input_name] = value
            elif input_type == 'hidden':
                # Include hidden fields
                form_data[input_name] = input_field.get('value', '')
            elif input_type in ['checkbox', 'radio']:
                # Handle checkboxes and radio buttons
                if input_field.get('checked') or input_type == 'checkbox':
                    form_data[input_name] = input_field.get('value', 'on')
        
        # Process textarea fields
        for textarea in textareas:
            textarea_name = textarea.get('name', '')
            if textarea_name:
                # Assume textarea is for message
                form_data[textarea_name] = message.message
        
        # Process select fields
        for select in selects:
            select_name = select.get('name', '')
            if select_name:
                # Select first option
                first_option = select.find('option')
                if first_option:
                    form_data[select_name] = first_option.get('value', '')
        
        return form_data
    
    def _get_field_value(self, field_name: str, mappings: Dict[str, str]) -> Optional[str]:
        """Get appropriate value for a form field"""
        field_name_lower = field_name.lower()
        
        for key, value in mappings.items():
            if key in field_name_lower:
                return value
        
        # Check for common patterns
        if 'name' in field_name_lower:
            return mappings['name']
        elif 'email' in field_name_lower:
            return mappings['email']
        elif 'phone' in field_name_lower or 'tel' in field_name_lower:
            return mappings['phone']
        elif 'subject' in field_name_lower:
            return mappings['subject']
        elif any(word in field_name_lower for word in ['message', 'comment', 'inquiry', 'content']):
            return mappings['message']
        
        return None
    
    def _handle_captcha(self, captcha_info: Dict[str, Any], form_url: str, soup: BeautifulSoup) -> Optional[Dict[str, str]]:
        """Handle CAPTCHA solving"""
        try:
            if captcha_info['type'] == 'recaptcha':
                site_key = captcha_info['site_key']
                if site_key:
                    solution = self.captcha_solver.solve_recaptcha(site_key, form_url)
                    if solution:
                        return {'g-recaptcha-response': solution}
            
            elif captcha_info['type'] == 'image':
                image_src = captcha_info['image_src']
                if image_src:
                    # Download CAPTCHA image
                    image_url = urljoin(form_url, image_src)
                    image_response = self.session.get(image_url)
                    if image_response.status_code == 200:
                        solution = self.captcha_solver.solve_image_captcha(image_response.content)
                        if solution:
                            # Find the CAPTCHA input field
                            captcha_input = soup.find('input', attrs={'name': re.compile(r'captcha', re.I)})
                            if captcha_input:
                                return {captcha_input['name']: solution}
            
            logger.warning(f"Could not solve CAPTCHA of type: {captcha_info['type']}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {e}")
            return None
    
    def _get_submit_url(self, form: Any, current_url: str) -> str:
        """Get the form submission URL"""
        action = form.get('action', '')
        if action:
            if action.startswith('http'):
                return action
            else:
                return urljoin(current_url, action)
        else:
            return current_url
    
    def _check_submission_success(self, response: requests.Response) -> bool:
        """Check if form submission was successful"""
        # Check HTTP status code
        if response.status_code not in [200, 201, 302, 303]:
            return False
        
        # Check for success indicators in response
        success_indicators = [
            'thank you', 'success', 'submitted', 'received', 'sent',
            'confirmation', 'message sent', 'inquiry received'
        ]
        
        error_indicators = [
            'error', 'failed', 'invalid', 'required', 'missing',
            'incorrect', 'wrong', 'try again'
        ]
        
        response_text = response.text.lower()
        
        # Check for error indicators
        for error in error_indicators:
            if error in response_text:
                return False
        
        # Check for success indicators
        for success in success_indicators:
            if success in response_text:
                return True
        
        # If no clear indicators, assume success for 2xx status codes
        return response.status_code in [200, 201]
