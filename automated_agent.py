#!/usr/bin/env python3
"""
Rankzen Automated SEO Outreach Agent
Runs independently to find, audit, and outreach to under-optimized local businesses
"""

import logging
import time
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

from app.config import config
from app.discovery import BusinessDiscovery
from app.seo_audit import SEOAuditor
from app.ai_reporter import AIReporter
from app.form_submitter import FormSubmitter
from app.playwright_form_submitter import playwright_submitter
import asyncio
from app.csv_reporter import csv_reporter
from app.utils import data_manager
from app.phase2_orchestrator import Phase2Orchestrator
import json

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomatedOutreachAgent:
    """Automated agent for SEO outreach to under-optimized local businesses"""
    
    def __init__(self):
        self.discovery = BusinessDiscovery()
        self.seo_auditor = SEOAuditor()
        self.ai_reporter = AIReporter()
        self.form_submitter = FormSubmitter()
        self.phase2_orchestrator = Phase2Orchestrator()
        
        # Daily limits and tracking
        self.daily_audit_count = 0
        self.daily_outreach_count = 0
        self.last_reset_date = datetime.now().date()
        
        # Performance tracking
        self.stats = {
            'total_sites_discovered': 0,
            'total_sites_audited': 0,
            'total_outreach_sent': 0,
            'total_contact_forms_found': 0,
            'total_blacklisted': 0,
            'start_time': datetime.now()
        }
    
    def reset_daily_limits(self):
        """Reset daily counters"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            logger.info("🔄 Resetting daily limits")
            self.daily_audit_count = 0
            self.daily_outreach_count = 0
            self.last_reset_date = current_date
    
    def check_daily_limits(self) -> bool:
        """Check if we've hit daily limits"""
        self.reset_daily_limits()
        
        if self.daily_audit_count >= config.DAILY_AUDITS:
            logger.warning(f"⚠️ Daily audit limit reached ({config.DAILY_AUDITS})")
            return False
        
        return True
    
    def run_discovery_cycle(self, max_sites: int = 30) -> List[Dict[str, Any]]:
        """Run a discovery cycle to find new business sites"""
        logger.info(f"🔍 Starting discovery cycle for {max_sites} sites")
        
        try:
            # Discover new business sites
            discovered_sites = self.discovery.discover_businesses(max_sites=max_sites)
            
            # Filter out already blacklisted sites
            new_sites = []
            for site in discovered_sites:
                if not data_manager.is_blacklisted(site.domain):
                    new_sites.append(site)
                else:
                    logger.info(f"⏭️ Skipping blacklisted site: {site.domain}")
            
            logger.info(f"✅ Discovery cycle complete: {len(new_sites)} new sites found")
            self.stats['total_sites_discovered'] += len(new_sites)
            
            return new_sites
            
        except Exception as e:
            logger.error(f"❌ Discovery cycle failed: {e}")
            return []
    
    async def audit_site(self, site) -> Dict[str, Any]:
        """Audit a single site and generate outreach message"""
        try:
            logger.info(f"🔍 Auditing site: {site.domain}")
            
            # Perform SEO audit
            seo_score = self.seo_auditor.audit_site(site)
            
            # Only proceed if site needs improvement (score < 70)
            if seo_score.overall_score >= 70:
                logger.info(f"⏭️ Skipping {site.domain} - score too high ({seo_score.overall_score}/100)")
                return {
                    'domain': site.domain,
                    'audited': False,  # Changed from True to False
                    'score': seo_score.overall_score,
                    'outreach_sent': False,
                    'reason': 'score_too_high'
                }
            
            # Generate outreach message
            outreach_message = self.ai_reporter.generate_outreach_message(site, seo_score)
            
            # Find contact forms
            contact_forms = self.discovery.find_contact_forms(str(site.url))
            contact_form_found = len(contact_forms) > 0
            
            # Find email addresses
            emails = self.discovery.find_email_addresses(str(site.url))
            if emails:
                site.email = emails[0]  # Use the first found email
            
            # Submit outreach if contact form found
            outreach_sent = False
            if contact_form_found:
                try:
                    # Try Playwright first (for JavaScript forms)
                    logger.info(f"🌐 Attempting Playwright form submission for {site.domain}")
                    
                    # Initialize Playwright if not already done
                    if not playwright_submitter.page:
                        await playwright_submitter.initialize()
                    
                    # Set the contact form URL
                    site.contact_form_url = contact_forms[0] if contact_forms else None
                    
                    # Submit using Playwright
                    contact_form = await playwright_submitter.submit_contact_form(site, outreach_message)
                    outreach_sent = contact_form.submitted
                    
                    if outreach_sent:
                        logger.info(f"✅ Playwright outreach sent successfully to {site.domain}")
                        self.daily_outreach_count += 1
                        self.stats['total_outreach_sent'] += 1
                        
                        # Start Phase 2 workflow
                        await self.start_phase2_workflow(site, seo_score, outreach_message)
                    else:
                        logger.warning(f"⚠️ Playwright failed, trying traditional method for {site.domain}")
                        # Fallback to traditional method
                        contact_form = self.form_submitter.submit_contact_form(site, outreach_message)
                        outreach_sent = contact_form.submitted
                        
                        if outreach_sent:
                            logger.info(f"✅ Traditional outreach sent successfully to {site.domain}")
                            self.daily_outreach_count += 1
                            self.stats['total_outreach_sent'] += 1
                            
                            # Start Phase 2 workflow
                            await self.start_phase2_workflow(site, seo_score, outreach_message)
                        else:
                            logger.warning(f"⚠️ Both methods failed for {site.domain}: {contact_form.error_message}")
                        
                except Exception as e:
                    logger.error(f"❌ Error submitting outreach to {site.domain}: {e}")
            else:
                logger.info(f"⚠️ No contact form found for {site.domain}")
            
            # Add to CSV log
            csv_reporter.add_site_log(site, seo_score, outreach_message, 
                                     contact_form if contact_form_found else None)
            
            # Add to blacklist to prevent duplicate outreach
            data_manager.add_to_blacklist(site.domain)
            self.stats['total_blacklisted'] += 1
            
            # Update stats
            self.daily_audit_count += 1
            self.stats['total_sites_audited'] += 1
            if contact_form_found:
                self.stats['total_contact_forms_found'] += 1
            
            return {
                'domain': site.domain,
                'audited': True,
                'score': seo_score.overall_score,
                'outreach_sent': outreach_sent,
                'contact_form_found': contact_form_found,
                'issues': seo_score.issues,
                'recommendations': seo_score.recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Error auditing {site.domain}: {e}")
            return {
                'domain': site.domain,
                'audited': False,
                'error': str(e)
            }
    
    async def run_audit_cycle(self, sites: List) -> List[Dict[str, Any]]:
        """Run audit cycle on discovered sites"""
        logger.info(f"🔍 Starting audit cycle for {len(sites)} sites")
        
        results = []
        
        for site in sites:
            # Check daily limits
            if not self.check_daily_limits():
                logger.warning("⚠️ Daily limits reached, stopping audit cycle")
                break
            
            # Add delay between audits to respect rate limits
            time.sleep(1)  # 1 second delay between audits
            
            # Audit the site
            result = await self.audit_site(site)
            results.append(result)
            
            # Log progress
            logger.info(f"📊 Progress: {len(results)}/{len(sites)} sites audited")
        
        logger.info(f"✅ Audit cycle complete: {len(results)} sites processed")
        return results
    
    async def run_full_cycle(self, max_sites: int = 30) -> Dict[str, Any]:
        """Run a complete discovery and audit cycle"""
        logger.info("🚀 Starting full automated outreach cycle")
        
        start_time = datetime.now()
        
        # Step 1: Discovery
        discovered_sites = self.run_discovery_cycle(max_sites)
        
        if not discovered_sites:
            logger.warning("⚠️ No new sites discovered, cycle complete")
            return {
                'cycle_complete': True,
                'sites_discovered': 0,
                'sites_audited': 0,
                'outreach_sent': 0,
                'discovered_domains': [],
                'duration_seconds': (datetime.now() - start_time).total_seconds()
            }
        
        # Log discovered sites
        discovered_domains = [site.domain for site in discovered_sites]
        logger.info(f"🔍 Discovered sites: {discovered_domains}")
        
        # Step 2: Audit and Outreach
        audit_results = await self.run_audit_cycle(discovered_sites)
        
        # Calculate statistics
        audited_sites = [r for r in audit_results if r.get('audited', False)]
        outreach_sent = [r for r in audit_results if r.get('outreach_sent', False)]
        
        cycle_stats = {
            'cycle_complete': True,
            'sites_discovered': len(discovered_sites),
            'sites_audited': len(audited_sites),
            'outreach_sent': len(outreach_sent),
            'discovered_domains': discovered_domains,
            'audited_domains': [r['domain'] for r in audited_sites],
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'daily_audits_remaining': config.DAILY_AUDITS - self.daily_audit_count,
            'daily_outreach_remaining': 25 - self.daily_outreach_count  # Assuming 25/day limit
        }
        
        # Log final statistics
        logger.info(f"✅ Full cycle complete: {cycle_stats}")
        
        # Generate final report
        self._generate_final_report(cycle_stats)
        
        return cycle_stats
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics"""
        uptime = datetime.now() - self.stats['start_time']
        
        return {
            'agent_status': 'running',
            'uptime_hours': uptime.total_seconds() / 3600,
            'daily_audits': self.daily_audit_count,
            'daily_outreach': self.daily_outreach_count,
            'total_sites_discovered': self.stats['total_sites_discovered'],
            'total_sites_audited': self.stats['total_sites_audited'],
            'total_outreach_sent': self.stats['total_outreach_sent'],
            'total_contact_forms_found': self.stats['total_contact_forms_found'],
            'total_blacklisted': self.stats['total_blacklisted'],
            'csv_log_path': csv_reporter.get_csv_path(),
            'last_reset_date': self.last_reset_date.isoformat()
        }
    
    async def monitor_phase2_responses(self):
        """Monitor and process Phase 2 client responses"""
        try:
            # Check for pending client interactions that need processing
            pending_interactions = self.phase2_orchestrator.get_pending_interactions()
            
            if pending_interactions:
                logger.info(f"📧 Found {len(pending_interactions)} pending Phase 2 interactions")
                
                for interaction in pending_interactions:
                    try:
                        # Simulate checking for responses (in real implementation, this would check email/form responses)
                        # For now, we'll just log the monitoring
                        logger.debug(f"🔍 Monitoring interaction {interaction.get('business_site_id', 'unknown')}")
                        
                        # In a real implementation, you would:
                        # 1. Check email for responses
                        # 2. Check contact form submissions
                        # 3. Check webhook responses
                        # 4. Process positive responses automatically
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing Phase 2 interaction: {e}")
                        
        except Exception as e:
            logger.error(f"❌ Error monitoring Phase 2 responses: {e}")
    
    async def start_phase2_workflow(self, site, seo_score, outreach_message):
        """Start Phase 2 workflow when outreach is sent"""
        try:
            business_site_id = f"site_{site.domain.replace('.', '_')}_{int(time.time())}"
            
            # Start Phase 2 workflow
            result = self.phase2_orchestrator.run_phase2_workflow(
                business_site_id=business_site_id,
                domain=site.domain,
                business_name=site.business_name or site.domain,
                seo_score=seo_score.overall_score,
                seo_issues=seo_score.issues[:3],  # Top 3 issues
                seo_recommendations=seo_score.recommendations[:3]  # Top 3 recommendations
            )
            
            logger.info(f"🎯 Phase 2 workflow started for {site.domain}: {result.get('status', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error starting Phase 2 workflow for {site.domain}: {e}")
            return {'status': 'failed', 'error': str(e)}

    def _generate_final_report(self, stats: Dict[str, Any]):
        """Generate final report for the cycle"""
        try:
            logger.info("📊 Generating final cycle report...")
            
            # Get Phase 2 summary
            phase2_summary = self.phase2_orchestrator.get_workflow_summary()
            
            # Create comprehensive report
            report = {
                'timestamp': datetime.now().isoformat(),
                'cycle_stats': stats,
                'phase2_summary': phase2_summary,
                'agent_stats': self.get_agent_stats(),
                'daily_limits': {
                    'audits_remaining': self.daily_audit_count,
                    'outreach_remaining': self.daily_outreach_count
                }
            }
            
            # Save report to file
            report_file = Path(config.DATA_DIR) / f"cycle_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"✅ Final report saved to: {report_file}")
            
            # Print summary to console
            print("\n" + "="*60)
            print("📊 CYCLE COMPLETE - FINAL REPORT")
            print("="*60)
            print(f"🕒 Timestamp: {report['timestamp']}")
            print(f"🔍 Sites Discovered: {stats.get('sites_discovered', 0)}")
            print(f"📊 Sites Audited: {stats.get('sites_audited', 0)}")
            print(f"📤 Outreach Sent: {stats.get('outreach_sent', 0)}")
            print(f"⏱️  Duration: {stats.get('duration_seconds', 0):.1f} seconds")
            print(f"🎯 Phase 2 Workflows: {phase2_summary.get('total_interactions', 0)}")
            print(f"💰 Payments Completed: {phase2_summary.get('payment_summary', {}).get('total_payments', 0)}")
            print(f"📋 Daily Audits Remaining: {self.daily_audit_count}")
            print(f"📤 Daily Outreach Remaining: {self.daily_outreach_count}")
            print("="*60)
            
        except Exception as e:
            logger.error(f"❌ Error generating final report: {e}")

    async def run_continuous(self, cycle_interval_hours: float = 0.1, max_sites_per_cycle: int = 30):
        """Run the agent continuously with scheduled cycles"""
        logger.info(f"🤖 Starting continuous automated agent (cycles every {cycle_interval_hours} hours)")
        
        # Schedule regular cycles (we'll handle this differently for async)
        # schedule.every(cycle_interval_hours).hours.do(
        #     self.run_full_cycle, max_sites=max_sites_per_cycle
        # )
        
        # Run initial cycle
        logger.info("🚀 Running initial cycle...")
        await self.run_full_cycle(max_sites_per_cycle)
        
        # Continuous loop
        last_cycle_time = time.time()
        cycle_interval_seconds = cycle_interval_hours * 3600
        last_followup_check = time.time()  # Track when we last checked for follow-ups
        
        while True:
            try:
                current_time = time.time()
                
                # Check if it's time for next cycle
                if current_time - last_cycle_time >= cycle_interval_seconds:
                    logger.info("🔄 Running scheduled cycle...")
                    await self.run_full_cycle(max_sites_per_cycle)
                    last_cycle_time = current_time
                
                # Check for email follow-ups every 3 hours
                if current_time - last_followup_check >= 10800:  # 3 hours in seconds
                    logger.info("📧 Checking for email follow-ups...")
                    self.check_email_follow_ups()
                    last_followup_check = current_time
                
                # Phase 2: Monitor for client responses and process workflow
                await self.monitor_phase2_responses()
                
                await asyncio.sleep(60)  # Check every minute
                
                # Log status every hour
                if datetime.now().minute == 0:
                    stats = self.get_agent_stats()
                    logger.info(f"📊 Agent Status: {stats}")
                    
            except KeyboardInterrupt:
                logger.info("🛑 Agent stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Agent error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying

async def main():
    """Main function to run the automated agent"""
    print("🤖 Rankzen Automated SEO Outreach Agent")
    print("=" * 50)
    
    # Create agent
    agent = AutomatedOutreachAgent()
    
    # Check configuration
    print(f"🎯 Target Industries: {', '.join(config.TARGET_INDUSTRIES)}")
    print(f"🌍 Target Regions: {', '.join(config.TARGET_REGIONS)}")
    print(f"📊 Daily Audit Limit: {config.DAILY_AUDITS}")
    print(f"🧪 Test Sites: {', '.join(config.TEST_SITES)}")
    print("=" * 50)
    
    # Run options
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "single":
            # Run single cycle
            print("🚀 Running single cycle...")
            stats = await agent.run_full_cycle(max_sites=30)
            print(f"✅ Cycle complete: {stats}")
            
        elif command == "continuous":
            # Run continuously
            interval = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
            await agent.run_continuous(cycle_interval_hours=interval)
            
        elif command == "stats":
            # Show stats
            stats = agent.get_agent_stats()
            print("📊 Agent Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
                
        else:
            print("Usage:")
            print("  python automated_agent.py single     # Run single cycle")
            print("  python automated_agent.py continuous [hours]  # Run continuously (default: 0.1 hours = 6 minutes)")
            print("  python automated_agent.py stats      # Show statistics")
    else:
        # Default: run single cycle
        print("🚀 Running single cycle...")
        stats = await agent.run_full_cycle(max_sites=30)
        print(f"✅ Cycle complete: {stats}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
