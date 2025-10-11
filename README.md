# 🚀 Rankzen Automated SEO Outreach Tool

**Simple, lightweight tool that finds under-optimized local business websites, runs quick SEO audits, generates plain-English reports, and submits outreach via contact forms.**

## 🎯 **QUICK START**

```bash
# Run everything automatically (Phase 1 + Phase 2)
python run_rankzen.py

# Or run the automated agent directly
python automated_agent.py

# Or use the web control panel
python start_control_panel.py
```

That's it! The tool runs both Phase 1 and Phase 2 automatically.

## 🌐 **WEB CONTROL PANEL**

The web control panel provides a user-friendly interface to manage the bot:

- **Dashboard**: Monitor bot status, progress, and statistics
- **Start/Stop Bot**: Control bot operations remotely
- **Leads Management**: View contacted businesses and their status
- **Settings**: Configure API keys, industries, regions, and templates
- **Activity Logs**: Monitor bot activity and errors

```bash
# Start the web control panel
python start_control_panel.py

# Access the control panel at:
# Dashboard: http://localhost:8000/admin
# Landing Page: http://localhost:8000/

# Default admin password: admin123
# Change this in the settings after first login!
```

## 🧪 **TESTING & OPTIONS**

```bash
# Quick test mode (single site audit)
python run_rankzen.py test

# Run single cycle
python automated_agent.py single

# Run continuously (every 6 minutes)
python automated_agent.py continuous

# Show help
python run_rankzen.py help
```

## 📋 **SETUP (One-time)**

1. **Create `.env` file** with your API keys:
```env
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
RANKZEN_API_KEY=your_rankzen_key_here
CAPTCHA_API_KEY=your_captcha_key_here (optional)
STRIPE_SECRET_KEY=your_stripe_secret_key_here (optional)
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here (optional)
STRIPE_PRODUCT_KEY=your_stripe_product_key_here (optional)
RESEND_API_KEY=your_resend_api_key_here (optional)
```

2. **Run the tool:**
```bash
python run_rankzen.py
```

## 🎯 **PHASE 1: DISCOVERY & OUTREACH**

**What it does automatically:**
- **Discovers** local business websites (landscaping, real estate, plumbers, HVAC, roofers, lawyers)
- **Audits** their SEO performance with technical analysis
- **Generates** plain-English reports with 2-3 key issues
- **Submits** outreach via contact forms using Playwright
- **Runs every 6 minutes** continuously
- **Logs everything** to CSV files

**How to run Phase 1 only:**
```bash
# Run single discovery/audit/outreach cycle
python automated_agent.py single

# Run continuously (every 6 minutes)
python automated_agent.py continuous
```

## 📧 **EMAIL OUTREACH FUNCTIONALITY**

When contact form submission is not possible or as a supplement to form submissions, the tool can send emails using the Resend API. This feature:

- Automatically discovers email addresses on target websites
- Sends personalized outreach emails using Resend API
- Works as a fallback when contact forms are not available
- Can be used in addition to form submissions for increased reach

To enable email outreach:
1. Add `RESEND_API_KEY=your_resend_api_key` to your `.env` file
2. The system will automatically send emails when contact forms are not found
3. Emails are only sent when valid email addresses are discovered

## 🎯 **PHASE 2: CLIENT FULFILLMENT** *(Automatically Integrated)*

**What happens automatically after successful outreach:**
- **Engagement Message** - Asks "Would you like help fixing this?" 
- **Payment Link** - Sends Stripe $100 payment link when client agrees
- **Credential Collection** - Securely collects CMS login details after payment
- **SEO Implementation** - Applies the identified fixes automatically
- **Human QA** - Triggers manual verification system
- **Owner Notification** - Sends final confirmation & feedback request

**Phase 2 is automatically triggered** when Phase 1 successfully submits outreach. No separate command needed!

## 📊 **OUTPUT FILES**

- `data/seo_outreach_log.csv` - Main comprehensive log of all activities
- `data/blacklist.json` - Prevents duplicate contacts
- `logs/audit-YYYYMMDD.jsonl` - Daily detailed logs
- `data/phase2_interactions.jsonl` - Phase 2 client interactions
- `data/seo_implementations.jsonl` - SEO fixes applied
- `data/qa_reviews.jsonl` - Human QA reviews
- `data/encrypted_credentials.jsonl` - Securely stored client credentials

## 🩺 Service Health

- API health: `GET /health/email` returns Resend connectivity status
- Webhooks: configure Resend to post delivery/bounce/complaint events to `/admin/email/webhook`

## 🎯 **TARGET INDUSTRIES**

- Landscaping
- Real Estate Agents/Brokerages
- Plumbers
- HVAC
- Roofers
- Lawyers (PI/Immigration)

## 🎯 **TARGET REGIONS**

- **Tier 1:** New York City, Miami-Dade, Austin, Los Angeles, Phoenix
- **Tier 2:** Dallas-Fort Worth, Chicago, Atlanta, Denver, Seattle

## 🚀 **FEATURES**

### **Phase 1: Discovery & Outreach**
- **Automated Discovery** - Finds local businesses via Serper API
- **SEO Auditing** - Technical analysis with scoring (0-100)
- **AI Reports** - Plain-English recommendations (2-3 issues max)
- **Form Submission** - Playwright-powered automation with CAPTCHA handling
- **Email Outreach** - Sends emails via Resend API as fallback or supplement
- **Blacklist Management** - Never contacts the same site twice
- **Rate Limiting** - Respects website politeness and daily limits
- **Intelligent Filtering** - Skips sites with good SEO scores (>80)

### **Phase 2: Client Fulfillment** *(Fully Integrated)*
- **Engagement Focus** - Asks "Would you like help?" instead of just pitching
- **Payment Integration** - Automatically sends Stripe $100 payment links
- **Credential Collection** - Securely stores CMS login details (encrypted)
- **SEO Implementation** - Applies the identified fixes automatically
- **Human QA** - Triggers manual verification system for quality control
- **Owner Notification** - Sends final confirmation & feedback request

### **System Features**
- **Lightweight** - No web interface, pure automation
- **Intelligent** - Skips sites with good SEO scores
- **Resilient** - Handles errors gracefully and continues
- **CAPTCHA-ready** - Handles form protection automatically
- **Fully Autonomous** - Runs continuously without manual intervention

## ⚡ **PERFORMANCE**

- **30 sites per cycle** (configurable)
- **150 daily audits** maximum
- **25 daily outreach** maximum
- **6-minute cycles** (configurable)
- **Real-time monitoring** of Phase 2 responses

## 🎯 **CLIENT INSTRUCTIONS**

### **For Non-Technical Users:**

1. **Setup** (one-time):
   - Create `.env` file with your API keys
   - Run `python run_rankzen.py`

2. **Daily Operation**:
   - The tool runs automatically every 6 minutes
   - No manual intervention required
   - Monitor results in `data/seo_outreach_log.csv`

3. **Phase 2 Management**:
   - Check `data/phase2_interactions.jsonl` for client responses
   - Review `data/qa_reviews.jsonl` for sites needing human verification
   - Monitor `data/seo_implementations.jsonl` for completed fixes

### **For Technical Users:**

```bash
# Run single cycle (testing)
python automated_agent.py single

# Run continuously (production)
python automated_agent.py continuous

# Monitor logs
tail -f data/seo_outreach_log.csv

# Check Phase 2 status
cat data/phase2_interactions.jsonl
```

---

**🎯 That's it! Just run `python run_rankzen.py` and both Phase 1 and Phase 2 run automatically!**
