import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import config

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data storage and retrieval for the SEO outreach tool"""
    
    def __init__(self):
        self.data_dir = Path(config.DATA_DIR)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.blacklist_file = self.data_dir / "blacklist.json"
        self.logs_file = self.data_dir / "logs.json"
        
        # Initialize files if they don't exist
        self._initialize_files()
    
    def _initialize_files(self):
        """Initialize data files if they don't exist"""
        if not self.blacklist_file.exists():
            self.save_blacklist([])
        
        if not self.logs_file.exists():
            self.save_logs([])
    
    def add_to_blacklist(self, domain: str):
        """Add a domain to the blacklist"""
        try:
            blacklist = self.load_blacklist()
            if domain not in blacklist:
                blacklist.append(domain)
                self.save_blacklist(blacklist)
                logger.info(f"✅ Added {domain} to blacklist")
        except Exception as e:
            logger.error(f"❌ Error adding to blacklist: {e}")
    
    def is_blacklisted(self, domain: str) -> bool:
        """Check if a domain is blacklisted"""
        try:
            blacklist = self.load_blacklist()
            return domain in blacklist
        except Exception as e:
            logger.error(f"❌ Error checking blacklist: {e}")
            return False
    
    def load_blacklist(self) -> List[str]:
        """Load the blacklist from file"""
        try:
            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"❌ Error loading blacklist: {e}")
            return []
    
    def save_blacklist(self, blacklist: List[str]):
        """Save the blacklist to file"""
        try:
            with open(self.blacklist_file, 'w') as f:
                json.dump(blacklist, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving blacklist: {e}")
    
    def add_log_entry(self, action: str, domain: str, status: str, details: Dict[str, Any] = None):
        """Add a log entry"""
        try:
            logs = self.load_logs()
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'domain': domain,
                'status': status,
                'details': details or {}
            }
            
            logs.append(log_entry)
            self.save_logs(logs)
            
        except Exception as e:
            logger.error(f"❌ Error adding log entry: {e}")
    
    def add_log(self, action: str, domain: str, status: str, details: str = None):
        """Add a log entry (alias for add_log_entry for compatibility)"""
        self.add_log_entry(action, domain, status, {'details': details} if details else {})
    
    def load_logs(self) -> List[Dict[str, Any]]:
        """Load logs from file"""
        try:
            if self.logs_file.exists():
                with open(self.logs_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"❌ Error loading logs: {e}")
            return []
    
    def save_logs(self, logs: List[Dict[str, Any]]):
        """Save logs to file"""
        try:
            with open(self.logs_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving logs: {e}")

# Utility functions
def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except Exception:
        return url.lower()

def clean_url(url: str) -> str:
    """Clean and normalize URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url.rstrip('/')

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    from urllib.parse import urlparse
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

# Create global data manager instance
data_manager = DataManager()
