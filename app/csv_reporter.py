import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from app.models import BusinessSite, SEOScore, OutreachMessage, ContactForm
from app.config import config

logger = logging.getLogger(__name__)

class CSVReporter:
    """Generates and maintains a single comprehensive CSV report for SEO outreach campaigns"""
    
    def __init__(self):
        self.data_dir = Path(config.DATA_DIR)
        self.data_dir.mkdir(exist_ok=True)
        self.csv_file = self.data_dir / "seo_outreach_log.csv"
        
    def add_site_log(self, 
                    site: BusinessSite,
                    seo_score: Optional[SEOScore] = None,
                    outreach_message: Optional[OutreachMessage] = None,
                    contact_form: Optional[ContactForm] = None) -> str:
        """
        Add a single site log to the CSV file (creates file if it doesn't exist)
        """
        # Define fieldnames for the CSV
        fieldnames = [
            # Site Information
            'Domain', 'Business Name', 'URL', 'Business Type', 'Region',
            
            # SEO Audit Results
            'Overall SEO Score', 'Title Score', 'Description Score', 'Speed Score', 
            'Mobile Score', 'Accessibility Score',
            
            # SEO Issues & Recommendations
            'SEO Issues', 'SEO Recommendations', 'Load Time (seconds)',
            
            # AI Report
            'AI Report Subject', 'AI Report Message', 'Report Generated',
            
            # Contact Form Results
            'Contact Form Found', 'Form URL', 'Submission Status', 'Submission Error',
            
            # CAPTCHA Information
            'CAPTCHA Detected', 'CAPTCHA Type', 'CAPTCHA Solved',
            
            # Campaign Data
            'Discovery Date', 'Audit Date', 'Outreach Date', 'Blacklisted',
            
            # Additional Metrics
            'Page Size (KB)', 'Images Count', 'Images With Alt', 'Links Count', 
            'Broken Links Count', 'H1 Count', 'Meta Description Length'
        ]
        
        # Check if file exists to determine if we need to write header
        file_exists = self.csv_file.exists()
        
        # Prepare data for the new row
        seo_issues = ""
        seo_recommendations = ""
        if seo_score:
            seo_issues = "; ".join(seo_score.issues) if seo_score.issues else ""
            seo_recommendations = "; ".join(seo_score.recommendations) if seo_score.recommendations else ""
        
        # Prepare AI report data
        ai_subject = ""
        ai_message = ""
        report_generated = "No"
        if outreach_message:
            ai_subject = outreach_message.subject or ""
            ai_message = outreach_message.message or ""
            report_generated = "Yes"
        
        # Prepare contact form data
        contact_form_found = "No"
        form_url = ""
        submission_status = "Not Attempted"
        submission_error = ""
        if contact_form:
            contact_form_found = "Yes"
            form_url = str(contact_form.url) if contact_form.url else ""
            submission_status = "SUCCESS" if contact_form.submitted else "FAILED"
            submission_error = contact_form.error_message or ""
        
        # Prepare CAPTCHA data
        captcha_detected = "No"
        captcha_type = ""
        captcha_solved = "No"
        if contact_form and contact_form.has_captcha:
            captcha_detected = "Yes"
            captcha_type = contact_form.captcha_type or ""
            captcha_solved = "Unknown"
        
        # Get current timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare the row data
        row = {
            # Site Information
            'Domain': site.domain,
            'Business Name': site.business_name or 'Unknown',
            'URL': site.url,
            'Business Type': site.business_type or 'Unknown',
            'Region': site.region or 'Unknown',
            
            # SEO Audit Results
            'Overall SEO Score': seo_score.overall_score if seo_score else 0,
            'Title Score': seo_score.title_score if seo_score else 0,
            'Description Score': seo_score.description_score if seo_score else 0,
            'Speed Score': seo_score.speed_score if seo_score else 0,
            'Mobile Score': seo_score.mobile_score if seo_score else 0,
            'Accessibility Score': seo_score.accessibility_score if seo_score else 0,
            
            # SEO Issues & Recommendations
            'SEO Issues': seo_issues,
            'SEO Recommendations': seo_recommendations,
            'Load Time (seconds)': seo_score.load_time if seo_score else 0,
            
            # AI Report
            'AI Report Subject': ai_subject,
            'AI Report Message': ai_message,
            'Report Generated': report_generated,
            
            # Contact Form Results
            'Contact Form Found': contact_form_found,
            'Form URL': form_url,
            'Submission Status': submission_status,
            'Submission Error': submission_error,
            
            # CAPTCHA Information
            'CAPTCHA Detected': captcha_detected,
            'CAPTCHA Type': captcha_type,
            'CAPTCHA Solved': captcha_solved,
            
            # Campaign Data
            'Discovery Date': current_time,
            'Audit Date': current_time,
            'Outreach Date': current_time,
            'Blacklisted': 'Yes' if getattr(site, 'blacklisted', False) else 'No',
            
            # Additional Metrics
            'Page Size (KB)': seo_score.page_size_kb if seo_score else 0,
            'Images Count': seo_score.images_count if seo_score else 0,
            'Images With Alt': seo_score.images_with_alt if seo_score else 0,
            'Links Count': seo_score.links_count if seo_score else 0,
            'Broken Links Count': seo_score.broken_links_count if seo_score else 0,
            'H1 Count': seo_score.h1_count if seo_score else 0,
            'Meta Description Length': seo_score.meta_description_length if seo_score else 0
        }
        
        # Write to CSV file
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header only if file is new
            if not file_exists:
                writer.writeheader()
                logger.info(f"📊 Created new CSV log file: {self.csv_file}")
            
            # Write the row
            writer.writerow(row)
        
        logger.info(f"✅ Added site log to CSV: {site.domain}")
        return str(self.csv_file)
    
    def get_csv_path(self) -> str:
        """Get the path to the CSV log file"""
        return str(self.csv_file)
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from the CSV log"""
        if not self.csv_file.exists():
            return {
                'total_sites': 0,
                'successful_submissions': 0,
                'failed_submissions': 0,
                'sites_with_contact_forms': 0,
                'sites_with_captcha': 0,
                'average_seo_score': 0
            }
        
        total_sites = 0
        successful_submissions = 0
        failed_submissions = 0
        sites_with_contact_forms = 0
        sites_with_captcha = 0
        seo_scores = []
        
        with open(self.csv_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total_sites += 1
                
                # Count contact form submissions
                if row['Contact Form Found'] == 'Yes':
                    sites_with_contact_forms += 1
                    if row['Submission Status'] == 'SUCCESS':
                        successful_submissions += 1
                    elif row['Submission Status'] == 'FAILED':
                        failed_submissions += 1
                
                # Count CAPTCHA
                if row['CAPTCHA Detected'] == 'Yes':
                    sites_with_captcha += 1
                
                # Collect SEO scores
                try:
                    seo_score = float(row['Overall SEO Score'])
                    seo_scores.append(seo_score)
                except (ValueError, KeyError):
                    pass
        
        average_seo_score = sum(seo_scores) / len(seo_scores) if seo_scores else 0
        
        return {
            'total_sites': total_sites,
            'successful_submissions': successful_submissions,
            'failed_submissions': failed_submissions,
            'sites_with_contact_forms': sites_with_contact_forms,
            'sites_with_captcha': sites_with_captcha,
            'average_seo_score': round(average_seo_score, 2)
        }
    
    def export_filtered_report(self, 
                             filters: Dict[str, Any] = None,
                             output_filename: str = None) -> str:
        """
        Export a filtered version of the log (for specific date ranges, regions, etc.)
        """
        if not self.csv_file.exists():
            logger.warning("No CSV log file exists to export")
            return ""
        
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"filtered_report_{timestamp}.csv"
        
        output_path = self.data_dir / output_filename
        
        # Read all data and apply filters
        filtered_rows = []
        with open(self.csv_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Apply filters if provided
                if filters:
                    include_row = True
                    for key, value in filters.items():
                        if key in row and row[key] != str(value):
                            include_row = False
                            break
                    if include_row:
                        filtered_rows.append(row)
                else:
                    filtered_rows.append(row)
        
        # Write filtered data to new file
        if filtered_rows:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = filtered_rows[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(filtered_rows)
            
            logger.info(f"✅ Exported filtered report: {output_path}")
            return str(output_path)
        else:
            logger.warning("No data matches the specified filters")
            return ""

# Create a global instance
csv_reporter = CSVReporter()
