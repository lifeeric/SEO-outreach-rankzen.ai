#!/usr/bin/env python3
"""
Debug script to check database contents
"""

from web_control_panel import app, db, Settings, Lead, ActivityLog

with app.app_context():
    print("=== DATABASE DEBUG ===")

    # Check settings
    settings = Settings.query.first()
    print(f"Settings exists: {settings is not None}")
    if settings:
        print(f"Serper API key in DB: {settings.serper_api_key}")
        print(f"OpenAI API key in DB: {settings.openai_api_key}")
        print(f"Target industries: {settings.target_industries}")
        print(f"Target regions: {settings.target_regions}")

    # Check leads
    leads_count = Lead.query.count()
    print(f"Total leads in DB: {leads_count}")
    if leads_count > 0:
        recent_leads = Lead.query.order_by(Lead.created_at.desc()).limit(3).all()
        for lead in recent_leads:
            print(f"  - {lead.domain}: {lead.status} (score: {lead.seo_score})")

    # Check logs
    logs_count = ActivityLog.query.count()
    print(f"Total logs in DB: {logs_count}")
    if logs_count > 0:
        recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(3).all()
        for log in recent_logs:
            print(f"  - {log.timestamp}: {log.level} - {log.message[:50]}...")

    print("=== END DEBUG ===")
