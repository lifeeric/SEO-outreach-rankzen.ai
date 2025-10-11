#!/usr/bin/env python3
"""
Rankzen Web Control Panel
Flask-based web interface for managing the automated SEO outreach bot
"""

import os
import asyncio
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length
from werkzeug.security import check_password_hash, generate_password_hash
import json
import csv
import io
from pathlib import Path
import logging
from sqlalchemy import inspect, text

# Import bot components
from app.config import config
from automated_agent import AutomatedOutreachAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'rankzen-admin-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///control_panel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Global bot instance and thread management
bot_instance = None
bot_thread = None
bot_running = False
last_csv_sync = 0  # Track last CSV sync time
csv_sync_thread = None
csv_sync_running = False

# Database Models
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    openai_api_key = db.Column(db.String(500))
    serper_api_key = db.Column(db.String(500))
    captcha_api_key = db.Column(db.String(500))
    stripe_secret_key = db.Column(db.String(500))
    stripe_publishable_key = db.Column(db.String(500))
    stripe_product_key = db.Column(db.String(500))
    resend_api_key = db.Column(db.String(500))
    target_industries = db.Column(db.Text, default='landscaping,real_estate,plumbers,hvac,roofers,lawyers')
    target_regions = db.Column(db.Text, default='New York City,Miami-Dade,Austin,Los Angeles,Phoenix')
    message_template = db.Column(db.Text)
    outreach_templates = db.Column(db.Text)  # JSON string of outreach templates
    admin_password = db.Column(db.String(500), default=generate_password_hash('admin123'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Add encryption key for API key encryption
    _encryption_key = None
    _cipher_suite = None
    
    @classmethod
    def get_cipher_suite(cls):
        """Get or create cipher suite for encryption"""
        if cls._cipher_suite is None:
            from cryptography.fernet import Fernet
            import base64
            import os
            
            # Use existing encryption key from credentials manager or create new one
            key_file = os.path.join("data", "encryption.key")
            if os.path.exists(key_file):
                try:
                    with open(key_file, 'rb') as f:
                        cls._encryption_key = f.read()
                except Exception:
                    cls._encryption_key = Fernet.generate_key()
            else:
                cls._encryption_key = Fernet.generate_key()
                # Save key for future use
                os.makedirs("data", exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(cls._encryption_key)
            
            cls._cipher_suite = Fernet(cls._encryption_key)
        
        return cls._cipher_suite
    
    def encrypt_value(self, value):
        """Encrypt a value for storage"""
        if not value:
            return value
        try:
            cipher_suite = self.get_cipher_suite()
            encrypted_data = cipher_suite.encrypt(value.encode())
            import base64
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            # Log error but return plain text as fallback
            import logging
            logging.error(f"Error encrypting value: {e}")
            return value
    
    def decrypt_value(self, encrypted_value):
        """Decrypt a stored value"""
        if not encrypted_value:
            return encrypted_value
        try:
            import base64
            cipher_suite = self.get_cipher_suite()
            decoded_data = base64.b64decode(encrypted_value.encode())
            decrypted_data = cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            # Log error but return encrypted value as fallback
            import logging
            logging.error(f"Error decrypting value: {e}")
            return encrypted_value

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(500), unique=True)
    business_name = db.Column(db.String(500))
    status = db.Column(db.String(50), default='audited')  # audited, sent, responded
    seo_score = db.Column(db.Integer)
    outreach_sent = db.Column(db.Boolean, default=False)
    contact_form_found = db.Column(db.Boolean, default=False)
    issues = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

# Add the EmailOutreach model after the Lead model
class EmailOutreach(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.String(500))  # Resend message ID
    recipient_email = db.Column(db.String(500))
    domain = db.Column(db.String(500))
    campaign_type = db.Column(db.String(50))  # outreach or follow-up
    status = db.Column(db.String(50))  # sent, pending, replied
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_sent = db.Column(db.Boolean, default=False)
    follow_up_message_id = db.Column(db.String(500))  # Resend message ID for follow-up
    subject = db.Column(db.String(500))
    body_html = db.Column(db.Text)
    body_text = db.Column(db.Text)
    context = db.Column(db.Text)  # JSON blob for additional metadata (form payload, headers, etc.)
    
    def __repr__(self):
        return f'<EmailOutreach {self.recipient_email} - {self.campaign_type}>'

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20), default='INFO')
    message = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')  # bot, audit, outreach, phase2

# Forms
class LoginForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SettingsForm(FlaskForm):
    openai_api_key = StringField('OpenAI API Key')
    serper_api_key = StringField('Serper API Key')
    captcha_api_key = StringField('Captcha API Key')
    stripe_secret_key = StringField('Stripe Secret Key')
    stripe_publishable_key = StringField('Stripe Publishable Key')
    stripe_product_key = StringField('Stripe Product Key')
    resend_api_key = StringField('Resend API Key')
    target_industries = TextAreaField('Target Industries (comma-separated)')
    target_regions = TextAreaField('Target Regions (comma-separated)')
    message_template = TextAreaField('Message Template')
    outreach_templates = TextAreaField('Outreach Templates (JSON format)')
    admin_password = PasswordField('New Admin Password (leave blank to keep current)')
    submit = SubmitField('Save Settings')

# Bot management functions
def get_bot_instance():
    """Get or create bot instance"""
    global bot_instance
    if bot_instance is None:
        bot_instance = AutomatedOutreachAgent()
    return bot_instance

def bot_worker():
    """Background worker for running the bot"""
    global bot_running
    try:
        # Ensure logging is properly configured in this thread
        import logging
        from app.config import config
        
        # Get the root logger
        root_logger = logging.getLogger()
        
        # Set the logging level
        root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # Add a stream handler if one doesn't exist
        if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            root_logger.addHandler(stream_handler)
        
        logger.info("🤖 Bot worker started")
        print("🤖 Bot worker started - Check terminal for detailed logs")
        
        bot = get_bot_instance()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.run_continuous(cycle_interval_hours=0.1, max_sites_per_cycle=30))
    except Exception as e:
        logger.error(f"Bot worker error: {e}")
        print(f"❌ Bot worker error: {e}")
        bot_running = False

def start_bot():
    """Start the bot in background thread"""
    global bot_thread, bot_running
    if not bot_running:
        bot_running = True
        bot_thread = threading.Thread(target=bot_worker, daemon=True)
        bot_thread.start()
        logger.info("Bot started")
        print("🤖 Bot started - Check terminal for detailed logs")  # Add terminal output

def stop_bot():
    """Stop the bot"""
    global bot_running
    bot_running = False
    logger.info("Bot stop signal sent")

def get_bot_stats():
    """Get current bot statistics"""
    try:
        bot = get_bot_instance()
        return bot.get_agent_stats()
    except Exception as e:
        logger.error(f"Error getting bot stats: {e}")
        return {
            'agent_status': 'error',
            'error': str(e),
            'total_sites_discovered': 0,
            'total_sites_audited': 0,
            'total_outreach_sent': 0,
            'daily_audits': 0,
            'daily_outreach': 0
        }

def load_settings_into_config():
    """Load settings from database into config - database values take precedence"""
    settings = Settings.query.first()
    if settings:
        # Always use database values (decrypted) - database takes precedence over env vars
        if settings.openai_api_key and settings.openai_api_key.strip():
            config.OPENAI_API_KEY = settings.decrypt_value(settings.openai_api_key)
        if settings.serper_api_key and settings.serper_api_key.strip():
            config.SERPER_API_KEY = settings.decrypt_value(settings.serper_api_key)
        if settings.captcha_api_key and settings.captcha_api_key.strip():
            config.CAPTCHA_API_KEY = settings.decrypt_value(settings.captcha_api_key)
        if settings.stripe_secret_key and settings.stripe_secret_key.strip():
            config.STRIPE_SECRET_KEY = settings.decrypt_value(settings.stripe_secret_key)
        if settings.stripe_publishable_key and settings.stripe_publishable_key.strip():
            config.STRIPE_PUBLISHABLE_KEY = settings.decrypt_value(settings.stripe_publishable_key)
        if settings.stripe_product_key and settings.stripe_product_key.strip():
            config.STRIPE_PRODUCT_KEY = settings.decrypt_value(settings.stripe_product_key)
        if settings.resend_api_key and settings.resend_api_key.strip():
            config.RESEND_API_KEY = settings.decrypt_value(settings.resend_api_key)
        if settings.target_industries and settings.target_industries.strip():
            config.TARGET_INDUSTRIES = [x.strip() for x in settings.target_industries.split(',')]
        if settings.target_regions and settings.target_regions.strip():
            config.TARGET_REGIONS = [x.strip() for x in settings.target_regions.split(',')]
        if settings.outreach_templates and settings.outreach_templates.strip():
            # Try to parse JSON templates
            try:
                import json
                config.OUTREACH_TEMPLATES = json.loads(settings.outreach_templates)
            except Exception as e:
                logger.error(f"Error parsing outreach templates: {e}")
        if hasattr(settings, 'message_template') and settings.message_template:
            config.MESSAGE_TEMPLATE = settings.message_template
        else:
            config.MESSAGE_TEMPLATE = ""

def log_activity(level, message, category='general'):
    """Log activity to database"""
    try:
        with app.app_context():
            log_entry = ActivityLog(level=level, message=message, category=category)
            db.session.add(log_entry)
            db.session.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

def sync_leads_from_csv():
    """Sync leads data from CSV file"""
    global last_csv_sync
    try:
        # Only sync if it's been more than 30 seconds since last sync
        import time
        current_time = time.time()
        if (current_time - last_csv_sync) < 30:
            return  # Skip sync if too recent
            
        last_csv_sync = current_time
        
        csv_path = Path("data/seo_outreach_log.csv")
        if csv_path.exists():
            import pandas as pd
            df = pd.read_csv(csv_path)

            synced_count = 0
            updated_count = 0
            for _, row in df.iterrows():
                domain = str(row.get('Domain', '')).strip()
                if domain and domain != 'Domain':  # Skip header row
                    lead = Lead.query.filter_by(domain=domain).first()
                    # Parse outreach_sent field - handle various formats
                    submission_status = str(row.get('Submission Status', '')).strip().upper()
                    submission_method = str(row.get('Submission Method', '')).strip().lower()
                    outreach_sent = submission_status == 'SUCCESS'

                    # Parse contact_form_found based on actual submission success
                    contact_form_found = outreach_sent and ('form' in submission_method)
                    
                    if lead:
                        # Update existing lead
                        lead.business_name = str(row.get('Business Name', '')).strip()
                        lead.seo_score = int(float(row.get('Overall SEO Score', 0) or 0))
                        lead.outreach_sent = outreach_sent
                        lead.contact_form_found = contact_form_found
                        lead.issues = str(row.get('SEO Issues', '')).strip()
                        lead.recommendations = str(row.get('SEO Recommendations', '')).strip()
                        lead.updated_at = datetime.utcnow()
                        # Update status based on whether outreach was sent
                        if outreach_sent and lead.status != 'sent':
                            lead.status = 'sent'
                            updated_count += 1
                        elif not outreach_sent and lead.status == 'sent':
                            # This shouldn't happen, but just in case
                            lead.status = 'audited'
                            updated_count += 1
                    else:
                        # Add new lead
                        lead = Lead(
                            domain=domain,
                            business_name=str(row.get('Business Name', '')).strip(),
                            seo_score=int(float(row.get('Overall SEO Score', 0) or 0)),
                            outreach_sent=outreach_sent,
                            contact_form_found=contact_form_found,
                            issues=str(row.get('SEO Issues', '')).strip(),
                            recommendations=str(row.get('SEO Recommendations', '')).strip(),
                            status='sent' if outreach_sent else 'audited',
                            updated_at=datetime.utcnow()
                        )
                        db.session.add(lead)
                        synced_count += 1

            db.session.commit()
            if synced_count > 0 or updated_count > 0:
                log_activity('INFO', f'Synced {synced_count} new leads and updated {updated_count} existing leads from CSV (total rows: {len(df)})', 'sync')
        else:
            log_activity('WARNING', 'CSV file not found for lead sync', 'sync')

    except Exception as e:
        logger.error(f"Error syncing leads from CSV: {e}")
        log_activity('ERROR', f'CSV sync failed: {e}', 'sync')


def ensure_email_outreach_columns():
    """Ensure the EmailOutreach table has the latest columns used by the app."""
    try:
        inspector = inspect(db.engine)
        existing_columns = {col['name'] for col in inspector.get_columns('email_outreach')}
        ddl_statements = []

        if 'subject' not in existing_columns:
            ddl_statements.append('ALTER TABLE email_outreach ADD COLUMN subject TEXT')
        if 'body_html' not in existing_columns:
            ddl_statements.append('ALTER TABLE email_outreach ADD COLUMN body_html TEXT')
        if 'body_text' not in existing_columns:
            ddl_statements.append('ALTER TABLE email_outreach ADD COLUMN body_text TEXT')
        if 'context' not in existing_columns:
            ddl_statements.append('ALTER TABLE email_outreach ADD COLUMN context TEXT')

        if ddl_statements:
            with db.engine.begin() as connection:
                for ddl in ddl_statements:
                    connection.execute(text(ddl))
            logger.info(
                "Updated email_outreach table with new columns: %s",
                ', '.join(stmt.split()[-1] for stmt in ddl_statements)
            )
    except Exception as exc:
        logger.error(f"Failed to ensure email_outreach columns: {exc}")

def csv_sync_worker():
    """Background worker for periodically syncing CSV data to database"""
    global csv_sync_running, last_csv_sync
    csv_sync_running = True
    logger.info("CSV sync worker started")
    
    while csv_sync_running:
        try:
            # Sync CSV data every 30 seconds
            with app.app_context():
                sync_leads_from_csv()
            time.sleep(30)
        except Exception as e:
            logger.error(f"Error in CSV sync worker: {e}")
            time.sleep(30)  # Continue running even if there's an error

def start_csv_sync():
    """Start the CSV sync background thread"""
    global csv_sync_thread, csv_sync_running
    if not csv_sync_running:
        csv_sync_running = True
        csv_sync_thread = threading.Thread(target=csv_sync_worker, daemon=True)
        csv_sync_thread.start()
        logger.info("CSV sync thread started")

def stop_csv_sync():
    """Stop the CSV sync background thread"""
    global csv_sync_running
    csv_sync_running = False
    logger.info("CSV sync thread stopped")

# Routes
@app.route('/')
def index():
    """Main index page"""
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin login page"""
    form = LoginForm()
    if form.validate_on_submit():
        settings = Settings.query.first()
        if settings and check_password_hash(settings.admin_password, form.password.data):
            session['admin_logged_in'] = True
            log_activity('INFO', 'Admin logged in', 'admin')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password', 'error')
            log_activity('WARNING', 'Failed admin login attempt', 'admin')

    return render_template('admin_login.html', form=form)

@app.route('/admin/dashboard')
def dashboard():
    """Main dashboard"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    # Sync leads from CSV to ensure we have the latest data
    with app.app_context():
        sync_leads_from_csv()

    # Get bot stats
    bot_stats = get_bot_stats()

    # Get lead counts
    total_leads = Lead.query.count()
    audited_leads = Lead.query.filter_by(status='audited').count()
    sent_leads = Lead.query.filter_by(status='sent').count()
    responded_leads = Lead.query.filter_by(status='responded').count()

    # Get recent activity
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()

    return render_template('dashboard.html',
                         bot_stats=bot_stats,
                         total_leads=total_leads,
                         audited_leads=audited_leads,
                         sent_leads=sent_leads,
                         responded_leads=responded_leads,
                         recent_logs=recent_logs,
                         bot_running=bot_running)

@app.route('/dashboard')
def dashboard_shortcut():
    """Convenience route so /dashboard redirects to the admin dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/admin/api/dashboard-data')
def dashboard_data():
    """API endpoint to get dashboard data in JSON format"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    # Sync leads from CSV to ensure we have the latest data
    with app.app_context():
        sync_leads_from_csv()

    # Get bot stats
    bot_stats = get_bot_stats()

    # Get lead counts
    total_leads = Lead.query.count()
    audited_leads = Lead.query.filter_by(status='audited').count()
    sent_leads = Lead.query.filter_by(status='sent').count()
    responded_leads = Lead.query.filter_by(status='responded').count()

    # Get recent activity
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    logs_data = []
    for log in recent_logs:
        logs_data.append({
            'timestamp': log.timestamp.isoformat(),
            'level': log.level,
            'message': log.message,
            'category': log.category
        })

    return jsonify({
        'bot_stats': bot_stats,
        'total_leads': total_leads,
        'audited_leads': audited_leads,
        'sent_leads': sent_leads,
        'responded_leads': responded_leads,
        'recent_logs': logs_data,
        'bot_running': bot_running
    })

@app.route('/admin/bot/start', methods=['POST'])
def bot_start():
    """Start the bot"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        start_bot()
        log_activity('INFO', 'Bot started by admin', 'bot')
        return jsonify({'status': 'started'})
    except Exception as e:
        log_activity('ERROR', f'Failed to start bot: {e}', 'bot')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/bot/stop', methods=['POST'])
def bot_stop():
    """Stop the bot"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        stop_bot()
        log_activity('INFO', 'Bot stopped by admin', 'bot')
        return jsonify({'status': 'stopped'})
    except Exception as e:
        log_activity('ERROR', f'Failed to stop bot: {e}', 'bot')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/bot/status')
def bot_status():
    """Get bot status"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'running': bot_running,
        'stats': get_bot_stats()
    })

@app.route('/admin/send-test-email', methods=['POST'])
def send_test_email():
    """Send a test email to the specified address"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get email address from request
        data = request.get_json()
        email = data.get('email', '').strip()
        
        if not email:
            return jsonify({'success': False, 'error': 'Email address is required'}), 400
        
        # Validate email format
        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            return jsonify({'success': False, 'error': 'Invalid email address format'}), 400
        
        # Import email sender
        from app.email_sender import EmailSender
        from app.models import BusinessSite, OutreachMessage
        
        # Create email sender instance
        email_sender = EmailSender()
        
        # Check if API key is configured
        if not email_sender.api_key:
            return jsonify({'success': False, 'error': 'Resend API key not configured. Please check your settings.'}), 400
        
        # Create a test business site and message
        test_site = BusinessSite(
            url="https://rankzen.ai",
            domain="rankzen.ai",
            business_name="RankZen Test",
            business_type="SEO Testing",
            region="Test Environment"
        )
        
        test_message = OutreachMessage(
            subject="RankZen Test Email",
            message=f"""
            <p>Hello,</p>
            <p>This is a test email from RankZen to verify that your email configuration is working correctly.</p>
            <p>If you received this email, it means your Resend API integration is properly configured.</p>
            <br>
            <p>Best regards,<br>
            The RankZen Team</p>
            """,
            generated_by_ai=False
        )
        
        # Send the test email
        # Using the updated sender format from the EmailSender class
        success = email_sender.send_outreach_email(test_site, test_message, email, "test")
        
        if success:
            # Log the activity
            log_activity('INFO', f'Test email sent to {email}', 'email')
            return jsonify({'success': True, 'message': 'Test email sent successfully'})
        else:
            # Log the error
            log_activity('ERROR', f'Failed to send test email to {email}', 'email')
            return jsonify({'success': False, 'error': 'Failed to send test email. Please check your Resend API configuration and try again.'}), 500
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        log_activity('ERROR', f'Error sending test email: {e}', 'email')
        return jsonify({'success': False, 'error': f'Error sending test email: {str(e)}'}), 500

@app.route('/admin/leads')
def leads():
    """Leads management page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    # Sync leads from CSV first
    with app.app_context():
        sync_leads_from_csv()

    page = request.args.get('page', 1, type=int)
    per_page = 50

    leads_query = Lead.query.order_by(Lead.created_at.desc())
    leads_pagination = leads_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('leads.html', leads=leads_pagination.items, pagination=leads_pagination)

@app.route('/admin/leads/download')
@app.route('/admin/leads/report')
def download_leads_csv():
    """Download all leads as a CSV file"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    # Fetch all leads
    leads = Lead.query.order_by(Lead.created_at.desc()).all()

    # Prepare CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Domain', 'Business Name', 'Status', 'SEO Score',
        'Outreach Sent', 'Contact Form Found', 'Created At', 'Updated At'
    ])

    # Rows
    for l in leads:
        writer.writerow([
            l.domain or '',
            l.business_name or '',
            l.status or '',
            l.seo_score if l.seo_score is not None else '',
            'Yes' if l.outreach_sent else 'No',
            'Yes' if l.contact_form_found else 'No',
            l.created_at.strftime('%Y-%m-%d %H:%M:%S') if l.created_at else '',
            l.updated_at.strftime('%Y-%m-%d %H:%M:%S') if l.updated_at else ''
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    headers = {
        'Content-Disposition': f'attachment; filename={filename}'
    }
    return Response(csv_data, mimetype='text/csv', headers=headers)

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings():
    """Settings management page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    form = SettingsForm()
    settings_obj = Settings.query.first()
    
    # Create settings object if it doesn't exist
    if not settings_obj:
        settings_obj = Settings()
        db.session.add(settings_obj)
        db.session.commit()

    if request.method == 'GET':
        # Populate form with existing settings (decrypt API keys for display)
        form.openai_api_key.data = settings_obj.decrypt_value(settings_obj.openai_api_key)
        form.serper_api_key.data = settings_obj.decrypt_value(settings_obj.serper_api_key)
        form.captcha_api_key.data = settings_obj.decrypt_value(settings_obj.captcha_api_key)
        form.stripe_secret_key.data = settings_obj.decrypt_value(settings_obj.stripe_secret_key)
        form.stripe_publishable_key.data = settings_obj.decrypt_value(settings_obj.stripe_publishable_key)
        form.stripe_product_key.data = settings_obj.decrypt_value(settings_obj.stripe_product_key)
        form.resend_api_key.data = settings_obj.decrypt_value(settings_obj.resend_api_key)
        form.target_industries.data = settings_obj.target_industries
        form.target_regions.data = settings_obj.target_regions
        form.message_template.data = settings_obj.message_template
        
        try:
            form.outreach_templates.data = settings_obj.outreach_templates
        except AttributeError:
            # Field doesn't exist yet, populate with default templates
            import json
            from app.config import config
            form.outreach_templates.data = json.dumps(config.OUTREACH_TEMPLATES, indent=2)

    if form.validate_on_submit():
        # Update settings (encrypt API keys before saving)
        settings_obj.openai_api_key = settings_obj.encrypt_value(form.openai_api_key.data)
        settings_obj.serper_api_key = settings_obj.encrypt_value(form.serper_api_key.data)
        settings_obj.captcha_api_key = settings_obj.encrypt_value(form.captcha_api_key.data)
        settings_obj.stripe_secret_key = settings_obj.encrypt_value(form.stripe_secret_key.data)
        settings_obj.stripe_publishable_key = settings_obj.encrypt_value(form.stripe_publishable_key.data)
        settings_obj.stripe_product_key = settings_obj.encrypt_value(form.stripe_product_key.data)
        settings_obj.resend_api_key = settings_obj.encrypt_value(form.resend_api_key.data)
        settings_obj.target_industries = form.target_industries.data
        settings_obj.target_regions = form.target_regions.data
        settings_obj.message_template = form.message_template.data
        settings_obj.outreach_templates = form.outreach_templates.data
            
        settings_obj.updated_at = datetime.utcnow()

        if form.admin_password.data:
            settings_obj.admin_password = generate_password_hash(form.admin_password.data)

        db.session.commit()

        # Reload config to apply changes immediately (now using database values exclusively)
        load_settings_into_config()

        flash('Settings saved successfully', 'success')
        log_activity('INFO', 'Settings updated by admin', 'admin')
        return redirect(url_for('settings'))

    return render_template('settings.html', form=form)

@app.route('/admin/logs')
def logs():
    """Logs management page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    page = request.args.get('page', 1, type=int)
    per_page = 100
    category = request.args.get('category', 'all')

    logs_query = ActivityLog.query.order_by(ActivityLog.timestamp.desc())

    if category != 'all':
        logs_query = logs_query.filter_by(category=category)

    logs_pagination = logs_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('logs.html',
                         logs=logs_pagination.items,
                         pagination=logs_pagination,
                         current_category=category)

# Add the email outreach route
@app.route('/admin/email_outreach')
def email_outreach():
    """Email outreach management page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    # Get email outreach statistics
    total_emails_sent = EmailOutreach.query.filter(EmailOutreach.campaign_type != 'form').count()
    outreach_emails = EmailOutreach.query.filter_by(campaign_type='outreach').count()
    followup_emails = EmailOutreach.query.filter_by(campaign_type='follow-up').count()
    form_submissions = EmailOutreach.query.filter_by(campaign_type='form').count()
    
    # Get pending follow-ups (outreach emails sent 3+ days ago with no follow-up sent)
    from datetime import datetime, timedelta
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    pending_followups = EmailOutreach.query.filter(
        EmailOutreach.campaign_type == "outreach",
        EmailOutreach.status == "sent",
        EmailOutreach.sent_at <= three_days_ago,
        EmailOutreach.follow_up_sent == False
    ).count()
    
    # Get recent email activity (last 20 emails)
    recent_emails = EmailOutreach.query.order_by(EmailOutreach.sent_at.desc()).limit(20).all()
    
    # Get last follow-up check time from logs
    last_followup_log = ActivityLog.query.filter_by(category='email').order_by(ActivityLog.timestamp.desc()).first()
    last_followup_check = last_followup_log.timestamp if last_followup_log else None

    return render_template('email_outreach.html',
                         total_emails_sent=total_emails_sent,
                         outreach_emails=outreach_emails,
                         followup_emails=followup_emails,
                         form_submissions=form_submissions,
                         pending_followups=pending_followups,
                         recent_emails=recent_emails,
                         last_followup_check=last_followup_check)

# Add a new route for checking follow-ups
@app.route('/admin/email/check_followups', methods=['POST'])
def check_email_followups():
    """Manually trigger follow-up email check"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from app.email_sender import check_follow_ups
        check_follow_ups()
        log_activity('INFO', 'Manual follow-up check triggered by admin', 'email')
        return jsonify({'status': 'Follow-up check completed'})
    except Exception as e:
        log_activity('ERROR', f'Failed to check follow-ups: {e}', 'email')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/settings/clear-data', methods=['POST'])
def clear_data():
    """Clear leads, logs, and CSV data while preserving settings"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Get password from request
        data = request.get_json()
        password = data.get('password', '').strip()
        
        if not password:
            return jsonify({'success': False, 'error': 'Admin password is required'}), 400
        
        # Verify admin password
        settings = Settings.query.first()
        if not settings or not check_password_hash(settings.admin_password, password):
            return jsonify({'success': False, 'error': 'Invalid admin password'}), 401
        
        # Clear leads data
        Lead.query.delete()
        
        # Clear email outreach data
        EmailOutreach.query.delete()
        
        # Clear activity logs
        ActivityLog.query.delete()
        
        # Commit changes
        db.session.commit()
        
        # Clear CSV file
        csv_path = Path("data/seo_outreach_log.csv")
        if csv_path.exists():
            # Create a new empty CSV with headers
            fieldnames = [
                'Domain', 'Business Name', 'URL', 'Business Type', 'Region',
                'Overall SEO Score', 'Title Score', 'Description Score', 'Speed Score', 
                'Mobile Score', 'Accessibility Score', 'SEO Issues', 'SEO Recommendations', 
                'Load Time (seconds)', 'AI Report Subject', 'AI Report Message', 
                'Report Generated', 'Contact Form Found', 'Form URL', 'Submission Status', 'Submission Method',
                'Submission Error', 'Email Used', 'CAPTCHA Detected', 'CAPTCHA Type', 'CAPTCHA Solved',
                'Discovery Date', 'Audit Date', 'Outreach Date', 'Blacklisted',
                'Page Size (KB)', 'Images Count', 'Images With Alt', 'Links Count', 
                'Broken Links Count', 'H1 Count', 'Meta Description Length'
            ]
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
        
        # Log the activity
        log_activity('INFO', 'Data cleared by admin (leads, logs, and CSV data)', 'admin')
        
        return jsonify({'success': True, 'message': 'Data cleared successfully. Settings preserved.'})
        
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Error clearing data: {str(e)}'}), 500

@app.route('/admin/logout')
def logout():
    """Logout admin"""
    session.pop('admin_logged_in', None)
    log_activity('INFO', 'Admin logged out', 'admin')
    return redirect(url_for('admin'))

def initialize_app():
    """Initialize the application"""
    try:
        # Create database tables
        db.create_all()
        ensure_email_outreach_columns()

        # Create default settings if they don't exist
        if not Settings.query.first():
            import json
            from app.config import config
            default_settings = Settings()
            # Set default outreach templates
            default_settings.outreach_templates = json.dumps(config.OUTREACH_TEMPLATES, indent=2)
            db.session.add(default_settings)
            db.session.commit()

        # Load settings into config
        load_settings_into_config()

        # Sync initial leads
        sync_leads_from_csv()

        log_activity('INFO', 'Web control panel initialized', 'system')
        
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        # If there's a schema mismatch, we need to recreate the database
        # In a production environment, we would implement proper migrations
        # But for development, we'll recreate the tables
        try:
            # Try to drop and recreate tables
            db.drop_all()
            db.create_all()
            
            # Create default settings
            import json
            from app.config import config
            default_settings = Settings()
            # Set default outreach templates
            default_settings.outreach_templates = json.dumps(config.OUTREACH_TEMPLATES, indent=2)
            db.session.add(default_settings)
            db.session.commit()
            
            log_activity('INFO', 'Web control panel reinitialized with new schema', 'system')
        except Exception as e2:
            logger.error(f"Error recreating database: {e2}")
            raise

# Initialize on import
with app.app_context():
    try:
        initialize_app()
        # Start CSV sync thread
        start_csv_sync()
    except Exception as e:
        logger.error(f"Error during initialization: {e}")
        # Try to recreate tables if there's a schema mismatch
        try:
            db.drop_all()
            db.create_all()
            initialize_app()
            # Start CSV sync thread
            start_csv_sync()
        except Exception as e2:
            logger.error(f"Error recreating database: {e2}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
