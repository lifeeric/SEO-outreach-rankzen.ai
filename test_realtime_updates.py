#!/usr/bin/env python3
"""
Test script to verify real-time dashboard updates
"""

import csv
import time
import random
from datetime import datetime
from pathlib import Path

def add_test_lead_to_csv():
    """Add a test lead to the CSV file"""
    csv_path = Path("data/seo_outreach_log.csv")
    
    # Create test data
    domain = f"test{random.randint(1000, 9999)}.com"
    business_name = f"Test Business {random.randint(1000, 9999)}"
    seo_score = random.randint(30, 80)
    
    # Check if file exists to determine if we need to write header
    file_exists = csv_path.exists()
    
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
    
    # Get current timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Prepare the row data
    row = {
        # Site Information
        'Domain': domain,
        'Business Name': business_name,
        'URL': f"https://{domain}",
        'Business Type': 'Test Business',
        'Region': 'Test Region',
        
        # SEO Audit Results
        'Overall SEO Score': seo_score,
        'Title Score': random.randint(50, 100),
        'Description Score': random.randint(50, 100),
        'Speed Score': random.randint(50, 100),
        'Mobile Score': random.randint(50, 100),
        'Accessibility Score': random.randint(50, 100),
        
        # SEO Issues & Recommendations
        'SEO Issues': 'Test issue 1; Test issue 2',
        'SEO Recommendations': 'Test recommendation 1; Test recommendation 2',
        'Load Time (seconds)': random.uniform(1.0, 5.0),
        
        # AI Report
        'AI Report Subject': 'Test SEO Report',
        'AI Report Message': 'This is a test SEO report message.',
        'Report Generated': 'Yes',
        
        # Contact Form Results
        'Contact Form Found': 'Yes',
        'Form URL': f"https://{domain}/contact",
        'Submission Status': 'SUCCESS',
        'Submission Error': '',
        
        # CAPTCHA Information
        'CAPTCHA Detected': 'No',
        'CAPTCHA Type': '',
        'CAPTCHA Solved': 'No',
        
        # Campaign Data
        'Discovery Date': current_time,
        'Audit Date': current_time,
        'Outreach Date': current_time,
        'Blacklisted': 'No',
        
        # Additional Metrics
        'Page Size (KB)': random.randint(100, 1000),
        'Images Count': random.randint(5, 50),
        'Images With Alt': random.randint(3, 40),
        'Links Count': random.randint(10, 100),
        'Broken Links Count': random.randint(0, 5),
        'H1 Count': random.randint(1, 3),
        'Meta Description Length': random.randint(100, 160)
    }
    
    # Write to CSV file
    with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header only if file is new
        if not file_exists:
            writer.writeheader()
            print(f"📊 Created new CSV log file: {csv_path}")
        
        # Write the row
        writer.writerow(row)
    
    print(f"✅ Added test lead to CSV: {domain}")
    return domain

def main():
    """Main function to add test leads periodically"""
    print("🚀 Starting real-time update test...")
    print("Adding a new test lead to CSV every 10 seconds...")
    print("Check the dashboard to see real-time updates!")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            add_test_lead_to_csv()
            time.sleep(10)  # Wait 10 seconds before adding another lead
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")

if __name__ == "__main__":
    main()