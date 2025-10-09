import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from app.config import config
from app.models import BusinessSite, SEOScore, AuditResult, ContactForm, OutreachMessage
from app.discovery import BusinessDiscovery
from app.seo_audit import SEOAuditor
from app.ai_reporter import AIReporter
from app.form_submitter import FormSubmitter
from app.utils import data_manager, extract_domain
from app.csv_reporter import csv_reporter

logger = logging.getLogger(__name__)

class SEOOutreachOrchestrator:
    """Automated SEO Outreach Agent - Finds under-optimized local business websites, audits them, and sends outreach"""
    
    def __init__(self):
        self.discovery = BusinessDiscovery()
        self.auditor = SEOAuditor()
        self.reporter = AIReporter()
        self.form_submitter = FormSubmitter()
    
    def run_phase1_outreach(self, max_sites: int = None) -> Dict[str, Any]:
        """
        Run complete Phase 1 outreach process
        This automated agent:
        1. Discovers under-optimized local business websites in NY/NJ/CT
        2. Performs SEO audits on each site
        3. Generates plain-English reports using AI
        4. Submits outreach via contact forms
        """
        if max_sites is None:
            max_sites = config.MAX_SITES_PER_RUN
        
        logger.info(f"🤖 Starting Automated SEO Outreach Agent")
        logger.info(f"🎯 Target: Find and outreach to {max_sites} under-optimized local business websites")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'target_sites': max_sites,
            'discovered_sites': 0,
            'audited_sites': 0,
            'outreach_sent': 0,
            'successful_submissions': 0,
            'failed_submissions': 0,
            'skipped_sites': 0,
            'errors': []
        }
        
        try:
            # Step 1: Automatically discover under-optimized local business websites
            logger.info("🔍 Step 1: Discovering under-optimized local business websites...")
            discovered_sites = self.discovery.discover_businesses(max_sites)
            results['discovered_sites'] = len(discovered_sites)
            
            if not discovered_sites:
                logger.warning("❌ No under-optimized local business websites discovered")
                return results
            
            # Step 2: Perform SEO audits on discovered sites
            logger.info("📊 Step 2: Performing SEO audits on discovered sites...")
            audited_sites = []
            
            for site in discovered_sites:
                try:
                    logger.info(f"🔍 Auditing {site.domain}")
                    
                    # Find contact forms and email addresses
                    contact_forms = self.discovery.find_contact_forms(str(site.url))
                    if contact_forms:
                        site.contact_form_url = contact_forms[0]
                    
                    # Find email addresses
                    emails = self.discovery.find_email_addresses(str(site.url))
                    if emails:
                        site.email = emails[0]  # Use the first found email
                    
                    seo_score = self.auditor.audit_site(site)
                    site.seo_score = seo_score
                    site.audit_status = 'completed'
                    audited_sites.append(site)
                    results['audited_sites'] += 1
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error auditing {site.domain}: {e}")
                    results['errors'].append(f"Audit error for {site.domain}: {str(e)}")
                    site.audit_status = 'failed'
            
            # Step 3: Generate AI reports and submit outreach
            logger.info("🤖 Step 3: Generating AI reports and submitting outreach...")
            
            for site in audited_sites:
                try:
                    if not site.seo_score or site.seo_score.overall_score == 0:
                        logger.warning(f"⏭️  Skipping {site.domain} - no valid SEO score")
                        results['skipped_sites'] += 1
                        continue
                    
                    # Generate AI-powered plain-English report
                    logger.info(f"🤖 Generating AI report for {site.domain}")
                    outreach_message = self.reporter.generate_outreach_message(site, site.seo_score)
                    
                    # Submit outreach via contact form or email
                    logger.info(f"📝 Submitting outreach for {site.domain}")
                    contact_form = self.form_submitter.submit_contact_form(site, outreach_message)
                    
                    if contact_form.submitted:
                        # Mark as sent and add to blacklist
                        site.outreach_sent = True
                        site.outreach_date = datetime.now()
                        data_manager.add_to_blacklist(site.domain)
                        results['successful_submissions'] += 1
                        results['outreach_sent'] += 1
                        
                        logger.info(f"✅ Successfully sent outreach to {site.domain}")
                    else:
                        results['failed_submissions'] += 1
                        logger.error(f"❌ Failed to submit form for {site.domain}: {contact_form.error_message}")
                    
                    # Rate limiting between submissions
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing {site.domain}: {e}")
                    results['errors'].append(f"Processing error for {site.domain}: {str(e)}")
                    results['failed_submissions'] += 1
            
            # Generate CSV reports
            try:
                logger.info("📊 Generating comprehensive CSV reports...")
                
                # Collect all data for CSV generation
                seo_scores = {site.domain: site.seo_score for site in audited_sites if site.seo_score}
                outreach_messages = {}
                contact_forms = {}
                
                # We'll need to collect outreach messages and contact forms from the process
                # For now, we'll create placeholder data
                for site in audited_sites:
                    if hasattr(site, 'outreach_message'):
                        outreach_messages[site.domain] = site.outreach_message
                    if hasattr(site, 'contact_form'):
                        contact_forms[site.domain] = site.contact_form
                
                # Add each site to the CSV log
                for site in audited_sites:
                    seo_score = seo_scores.get(site.domain)
                    outreach_message = outreach_messages.get(site.domain)
                    contact_form = contact_forms.get(site.domain)
                    
                    csv_reporter.add_site_log(site, seo_score, outreach_message, contact_form)
                
                # Get CSV file path and summary stats
                csv_path = csv_reporter.get_csv_path()
                summary_stats = csv_reporter.get_summary_stats()
                
                logger.info(f"✅ CSV log updated: {csv_path}")
                logger.info(f"📊 Summary stats: {summary_stats}")
                
                # Add CSV info to results
                results['csv_log'] = csv_path
                results['summary_stats'] = summary_stats
                
            except Exception as e:
                logger.error(f"❌ Error generating CSV reports: {e}")
                results['csv_error'] = str(e)
            
            results['end_time'] = datetime.now().isoformat()
            logger.info(f"🎉 Automated SEO Outreach Agent completed. Results: {results}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in automated outreach agent: {e}")
            results['errors'].append(f"Agent error: {str(e)}")
            results['end_time'] = datetime.now().isoformat()
            return results
    
    def run_single_site_outreach(self, url: str) -> Dict[str, Any]:
        """
        Run outreach for a single site (for testing or manual input)
        """
        logger.info(f"🎯 Running single site outreach for {url}")
        
        try:
            # Create business site object
            domain = extract_domain(url)
            site = BusinessSite(url=url, domain=domain)
            
            # Check if already blacklisted
            if data_manager.is_blacklisted(domain):
                return {
                    'success': False,
                    'error': 'Site already blacklisted',
                    'domain': domain
                }
            
            # Find contact form
            contact_forms = self.discovery.find_contact_forms(url)
            if contact_forms:
                site.contact_form_url = contact_forms[0]
            
            # Find email addresses
            emails = self.discovery.find_email_addresses(url)
            if emails:
                site.email = emails[0]  # Use the first found email
            
            # Audit site
            seo_score = self.auditor.audit_site(site)
            site.seo_score = seo_score
            
            if not seo_score or seo_score.overall_score == 0:
                return {
                    'success': False,
                    'error': 'Failed to audit site',
                    'domain': domain
                }
            
            # Generate outreach message
            outreach_message = self.reporter.generate_outreach_message(site, seo_score)
            
            # Submit form
            contact_form = self.form_submitter.submit_contact_form(site, outreach_message)
            
            # Add to CSV log
            csv_reporter.add_site_log(site, seo_score, outreach_message, contact_form)
            
            if contact_form.submitted:
                data_manager.add_to_blacklist(domain)
                return {
                    'success': True,
                    'domain': domain,
                    'seo_score': seo_score.overall_score,
                    'message': 'Outreach sent successfully',
                    'csv_log': csv_reporter.get_csv_path()
                }
            else:
                return {
                    'success': False,
                    'error': contact_form.error_message,
                    'domain': domain,
                    'csv_log': csv_reporter.get_csv_path()
                }
                
        except Exception as e:
            logger.error(f"❌ Error in single site outreach: {e}")
            return {
                'success': False,
                'error': str(e),
                'domain': extract_domain(url) if url else 'unknown'
            }
    
    def get_outreach_stats(self) -> Dict[str, Any]:
        """Get statistics about outreach activities"""
        logs = data_manager.load_logs()
        blacklist = data_manager.load_blacklist()
        
        stats = {
            'total_blacklisted_domains': len(blacklist),
            'total_log_entries': len(logs),
            'successful_submissions': len([log for log in logs if log.get('action') == 'FORM_SUBMISSION' and log.get('status') == 'SUCCESS']),
            'failed_submissions': len([log for log in logs if log.get('action') == 'FORM_SUBMISSION' and log.get('status') in ['FAILED', 'ERROR']]),
            'recent_activity': logs[-10:] if logs else []  # Last 10 activities
        }
        
        return stats
    
    def reset_blacklist(self) -> bool:
        """Reset the blacklist (for testing purposes)"""
        try:
            data_manager.save_blacklist([])
            logger.info("✅ Blacklist reset successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error resetting blacklist: {e}")
            return False
    
    def check_email_follow_ups(self):
        """Check for and send follow-up emails"""
        try:
            from app.email_sender import check_follow_ups
            logger.info("📧 Checking for email follow-ups...")
            check_follow_ups()
            logger.info("✅ Email follow-up check completed")
        except Exception as e:
            logger.error(f"❌ Error checking email follow-ups: {e}")
