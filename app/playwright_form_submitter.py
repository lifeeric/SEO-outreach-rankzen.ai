import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import re

from app.config import config
from app.models import ContactForm, OutreachMessage, BusinessSite
from app.utils import extract_domain, clean_url, is_valid_url, data_manager
from app.captcha_solver import CaptchaSolver
from app.network_client import http_client, DeadHostError

logger = logging.getLogger(__name__)

class PlaywrightFormSubmitter:
    """Enhanced form submitter using Playwright for JavaScript execution"""
    
    def __init__(self):
        self.captcha_solver = CaptchaSolver()
        self.browser = None
        self.context = None
        self.page = None
        
    async def initialize(self):
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Run in background
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await self.context.new_page()
            
            # Set extra headers to appear more human-like
            await self.page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            logger.info("✅ Playwright browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Playwright: {e}")
            return False
    
    async def close(self):
        """Close Playwright browser"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("✅ Playwright browser closed")
        except Exception as e:
            logger.error(f"❌ Error closing Playwright: {e}")
    
    async def submit_contact_form(self, site: BusinessSite, message: OutreachMessage) -> ContactForm:
        """
        Submit contact form using Playwright for JavaScript execution
        """
        if not site.contact_form_url:
            logger.warning(f"No contact form URL for {site.domain}")
            return ContactForm(
                url=str(site.url),
                error_message="No contact form found",
                submission_method='form',
                email_used=getattr(site, 'email', None)
            )
        
        try:
            form_url = str(site.contact_form_url)
            logger.info(f"🌐 Navigating to {form_url} with Playwright")

            if not http_client.is_reachable(form_url):
                logger.warning(f"Contact form unreachable for {site.domain} before Playwright navigation")
                data_manager.add_log_entry(
                    "FORM_SUBMISSION",
                    site.domain,
                    "FAILED",
                    {"details": "playwright_unreachable", "form_url": form_url}
                )
                return ContactForm(
                    url=form_url,
                    submitted=False,
                    error_message="Form URL unreachable",
                    submission_method='form',
                    email_used=getattr(site, 'email', None)
                )
            
            # Navigate to the page
            await self.page.goto(form_url, wait_until='networkidle', timeout=30000)
            
            # Wait for page to load
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Check for CAPTCHA
            captcha_detected = await self._detect_captcha()
            
            if captcha_detected:
                logger.info(f"🔍 CAPTCHA detected on {site.domain}")
                captcha_solved = await self._solve_captcha()
                if not captcha_solved:
                    data_manager.add_log_entry(
                        "FORM_SUBMISSION",
                        site.domain,
                        "FAILED",
                        {"details": "playwright_captcha_failed", "form_url": form_url}
                    )
                    return ContactForm(
                        url=form_url,
                        has_captcha=True,
                        submitted=False,
                        error_message="Failed to solve CAPTCHA",
                        submission_method='form',
                        email_used=getattr(site, 'email', None)
                    )
            
            # Find and fill the contact form
            form_filled = await self._fill_contact_form(message, site)
            
            if not form_filled:
                return ContactForm(
                    url=form_url,
                    error_message="Could not find or fill contact form"
                )
            
            # Submit the form
            submission_success = await self._submit_form()
            
            if submission_success:
                logger.info(f"✅ Successfully submitted contact form for {site.domain}")
                # data_manager.add_log("FORM_SUBMISSION", site.domain, "SUCCESS")  # Commented out due to missing method
                data_manager.add_log_entry(
                    "FORM_SUBMISSION",
                    site.domain,
                    "SUCCESS",
                    {"details": "playwright_form", "form_url": form_url}
                )
                return ContactForm(
                    url=form_url,
                    submitted=True,
                    has_captcha=captcha_detected,
                    submission_method='form',
                    email_used=getattr(site, 'email', None)
                )
            else:
                logger.warning(f"⚠️ Form submission may have failed for {site.domain}")
                data_manager.add_log_entry(
                    "FORM_SUBMISSION",
                    site.domain,
                    "FAILED",
                    {"details": "playwright_submit_failed", "form_url": form_url}
                )
                return ContactForm(
                    url=form_url,
                    submitted=False,
                    error_message="Form submission failed",
                    submission_method='form',
                    email_used=getattr(site, 'email', None)
                )
                
        except DeadHostError:
            logger.warning(f"Playwright contact form host marked dead for {site.domain}")
            data_manager.add_log_entry(
                "FORM_SUBMISSION",
                site.domain,
                "FAILED",
                {"details": "playwright_dead_host", "form_url": str(site.contact_form_url)}
            )
            return ContactForm(
                url=str(site.contact_form_url) if site.contact_form_url else str(site.url),
                submitted=False,
                error_message="Host unreachable",
                submission_method='form',
                email_used=getattr(site, 'email', None)
            )
        except Exception as e:
            logger.error(f"❌ Error submitting contact form for {site.domain}: {e}")
            data_manager.add_log_entry(
                "FORM_SUBMISSION",
                site.domain,
                "ERROR",
                {"details": str(e), "form_url": str(site.contact_form_url)}
            )
            return ContactForm(
                url=str(site.contact_form_url) if site.contact_form_url else str(site.url),
                submitted=False,
                error_message=str(e),
                submission_method='form',
                email_used=getattr(site, 'email', None)
            )
    
    async def _detect_captcha(self) -> bool:
        """Detect if CAPTCHA is present on the page"""
        try:
            # Check for reCAPTCHA
            recaptcha_selectors = [
                '.g-recaptcha',
                '[data-sitekey]',
                'iframe[src*="recaptcha"]',
                '#recaptcha'
            ]
            
            for selector in recaptcha_selectors:
                if await self.page.query_selector(selector):
                    logger.info("🔍 reCAPTCHA detected")
                    return True
            
            # Check for hCaptcha
            hcaptcha_selectors = [
                '.h-captcha',
                'iframe[src*="hcaptcha"]',
                '#hcaptcha'
            ]
            
            for selector in hcaptcha_selectors:
                if await self.page.query_selector(selector):
                    logger.info("🔍 hCaptcha detected")
                    return True
            
            # Check for image CAPTCHA
            image_captcha_selectors = [
                'img[src*="captcha"]',
                '.captcha-image',
                '#captcha-image'
            ]
            
            for selector in image_captcha_selectors:
                if await self.page.query_selector(selector):
                    logger.info("🔍 Image CAPTCHA detected")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {e}")
            return False
    
    async def _solve_captcha(self) -> bool:
        """Attempt to solve CAPTCHA"""
        try:
            # Try to solve reCAPTCHA
            recaptcha_frame = await self.page.query_selector('iframe[src*="recaptcha"]')
            if recaptcha_frame:
                logger.info("🔄 Attempting to solve reCAPTCHA...")
                # Click the reCAPTCHA checkbox
                await self.page.click('.g-recaptcha')
                await self.page.wait_for_timeout(2000)
                
                # Check if solved
                if await self.page.query_selector('.g-recaptcha[data-response]'):
                    logger.info("✅ reCAPTCHA solved")
                    return True
            
            # Try to solve hCaptcha
            hcaptcha_frame = await self.page.query_selector('iframe[src*="hcaptcha"]')
            if hcaptcha_frame:
                logger.info("🔄 Attempting to solve hCaptcha...")
                await self.page.click('.h-captcha')
                await self.page.wait_for_timeout(2000)
                return True
            
            logger.warning("⚠️ Could not solve CAPTCHA automatically")
            return False
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}")
            return False
    
    async def _fill_contact_form(self, message: OutreachMessage, site: BusinessSite) -> bool:
        """Find and fill contact form fields"""
        try:
            # Common field selectors (more flexible)
            field_selectors = {
                'name': [
                    'input[name*="name" i]',
                    'input[placeholder*="name" i]',
                    'input[id*="name" i]',
                    'input[placeholder*="first" i]',
                    'input[placeholder*="last" i]',
                    'input[type="text"]'
                ],
                'email': [
                    'input[name*="email" i]',
                    'input[type="email"]',
                    'input[placeholder*="email" i]',
                    'input[id*="email" i]',
                    'input[placeholder*="e-mail" i]'
                ],
                'phone': [
                    'input[name*="phone" i]',
                    'input[name*="tel" i]',
                    'input[type="tel"]',
                    'input[placeholder*="phone" i]',
                    'input[placeholder*="telephone" i]'
                ],
                'subject': [
                    'input[name*="subject" i]',
                    'input[placeholder*="subject" i]',
                    'input[id*="subject" i]',
                    'input[placeholder*="topic" i]'
                ],
                'message': [
                    'textarea[name*="message" i]',
                    'textarea[placeholder*="message" i]',
                    'textarea[id*="message" i]',
                    'textarea',
                    'input[name*="message" i]',
                    'textarea[placeholder*="comment" i]',
                    'textarea[placeholder*="inquiry" i]',
                    'textarea[placeholder*="details" i]'
                ]
            }
            
            # Field values
            field_values = {
                'name': 'John Smith',
                'email': 'john.smith@example.com',
                'phone': '555-123-4567',
                'subject': message.subject,
                'message': message.message
            }
            
            fields_filled = 0
            
            # Debug: List all form elements on the page
            all_inputs = await self.page.query_selector_all('input')
            all_textareas = await self.page.query_selector_all('textarea')
            all_forms = await self.page.query_selector_all('form')
            all_iframes = await self.page.query_selector_all('iframe')
            logger.info(f"🔍 Found {len(all_inputs)} input fields, {len(all_textareas)} textarea fields, {len(all_forms)} forms, and {len(all_iframes)} iframes")
            
            # Wait a bit more for JavaScript to load
            await self.page.wait_for_timeout(3000)
            
            # Check again after waiting
            all_inputs_after = await self.page.query_selector_all('input')
            all_textareas_after = await self.page.query_selector_all('textarea')
            all_forms_after = await self.page.query_selector_all('form')
            logger.info(f"🔍 After waiting: {len(all_inputs_after)} input fields, {len(all_textareas_after)} textarea fields, and {len(all_forms_after)} forms")
            
            # Get page title and URL for debugging
            page_title = await self.page.title()
            current_url = self.page.url
            logger.info(f"📄 Page title: {page_title}")
            logger.info(f"🌐 Current URL: {current_url}")
            
            # Check for iframes that might contain forms
            if all_iframes:
                logger.info("🔍 Checking iframes for forms...")
                for i, iframe in enumerate(all_iframes):
                    try:
                        iframe_src = await iframe.get_attribute('src')
                        logger.info(f"   Iframe {i}: src='{iframe_src}'")
                        
                        # Try to access iframe content
                        iframe_content = await iframe.content_frame()
                        if iframe_content:
                            iframe_inputs = await iframe_content.query_selector_all('input')
                            iframe_textareas = await iframe_content.query_selector_all('textarea')
                            logger.info(f"   Iframe {i} content: {len(iframe_inputs)} inputs, {len(iframe_textareas)} textareas")
                    except Exception as e:
                        logger.debug(f"Could not access iframe {i}: {e}")
            
            # Use the updated element counts
            all_inputs = all_inputs_after
            all_textareas = all_textareas_after
            all_forms = all_forms_after
            
            # Fill each field type
            for field_type, selectors in field_selectors.items():
                for selector in selectors:
                    try:
                        field = await self.page.query_selector(selector)
                        if field:
                            # Check if field is visible and not disabled
                            is_visible = await field.is_visible()
                            is_disabled = await field.get_attribute('disabled')
                            
                            if is_visible and not is_disabled:
                                # Get field info for debugging
                                field_name = await field.get_attribute('name') or await field.get_attribute('id') or 'unknown'
                                field_placeholder = await field.get_attribute('placeholder') or 'none'
                                logger.info(f"🎯 Found {field_type} field: name='{field_name}', placeholder='{field_placeholder}'")
                                
                                # Clear the field first
                                await field.click()
                                await field.fill('')
                                
                                # Fill with appropriate value
                                value = field_values[field_type]
                                await field.fill(value)
                                
                                logger.info(f"✅ Filled {field_type} field")
                                fields_filled += 1
                                break  # Move to next field type
                                
                    except Exception as e:
                        logger.debug(f"Could not fill {field_type} field: {e}")
                        continue
            
            logger.info(f"📝 Filled {fields_filled} form fields")
            return fields_filled > 0
            
        except Exception as e:
            logger.error(f"Error filling contact form: {e}")
            return False
    
    async def _submit_form(self) -> bool:
        """Submit the filled form"""
        try:
            # Look for submit buttons
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Send")',
                'button:has-text("Submit")',
                'button:has-text("Contact")',
                'input[value*="Send" i]',
                'input[value*="Submit" i]'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.query_selector(selector)
                    if submit_button and await submit_button.is_visible():
                        logger.info(f"🚀 Clicking submit button: {selector}")
                        
                        # Click the submit button
                        await submit_button.click()
                        
                        # Wait for navigation or response
                        await self.page.wait_for_timeout(3000)
                        
                        # Check for success indicators
                        success_indicators = [
                            'thank you',
                            'success',
                            'submitted',
                            'received',
                            'sent',
                            'confirmation'
                        ]
                        
                        page_content = await self.page.content()
                        page_text = page_content.lower()
                        
                        for indicator in success_indicators:
                            if indicator in page_text:
                                logger.info(f"✅ Success indicator found: {indicator}")
                                return True
                        
                        # If no success indicator, check if we're on a different page
                        current_url = self.page.url
                        if 'thank' in current_url.lower() or 'success' in current_url.lower():
                            logger.info("✅ Redirected to success page")
                            return True
                        
                        logger.info("⚠️ No clear success indicator, but form was submitted")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Could not click submit button {selector}: {e}")
                    continue
            
            logger.warning("⚠️ No submit button found")
            return False
            
        except Exception as e:
            logger.error(f"Error submitting form: {e}")
            return False

# Global instance
playwright_submitter = PlaywrightFormSubmitter()
