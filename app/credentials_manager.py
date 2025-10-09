import logging
import json
import base64
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet

from app.config import config
from app.phase2_models import CredentialsRequest, CredentialsResponse

logger = logging.getLogger(__name__)

class CredentialsManager:
    """Manages secure storage of client website credentials"""
    
    def __init__(self):
        self.credentials_file = Path("data/encrypted_credentials.jsonl")
        self.credentials_file.parent.mkdir(exist_ok=True)
        
        # Generate or load encryption key
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        logger.info("✅ Credentials manager initialized with encryption")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get existing encryption key or create new one"""
        key_file = Path("data/encryption.key")
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading encryption key: {e}")
        
        # Generate new key
        try:
            new_key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(new_key)
            logger.info("🔐 Generated new encryption key")
            return new_key
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
            # Fallback to a default key (not recommended for production)
            return Fernet.generate_key()
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return data  # Fallback to plain text
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return encrypted_data  # Return as-is if decryption fails
    
    def store_credentials(self, business_site_id: str, website_url: str, 
                         username: str, password: str, cms_login_url: str = None,
                         notes: str = None) -> bool:
        """Store encrypted credentials"""
        try:
            # Create credentials record
            credentials_record = {
                "business_site_id": business_site_id,
                "website_url": website_url,
                "cms_login_url": cms_login_url,
                "username": username,
                "password_encrypted": self._encrypt_data(password),
                "notes": notes,
                "stored_date": datetime.now().isoformat(),
                "last_accessed": None
            }
            
            # Save to file
            with open(self.credentials_file, 'a') as f:
                f.write(json.dumps(credentials_record) + '\n')
            
            logger.info(f"✅ Credentials stored for {business_site_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing credentials: {e}")
            return False
    
    def get_credentials(self, business_site_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credentials"""
        try:
            if not self.credentials_file.exists():
                return None
            
            with open(self.credentials_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get('business_site_id') == business_site_id:
                            # Decrypt password
                            record['password'] = self._decrypt_data(record['password_encrypted'])
                            
                            # Update last accessed
                            record['last_accessed'] = datetime.now().isoformat()
                            self._update_credentials_record(record)
                            
                            logger.info(f"✅ Credentials retrieved for {business_site_id}")
                            return record
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error retrieving credentials: {e}")
            return None
    
    def _update_credentials_record(self, updated_record: Dict[str, Any]):
        """Update credentials record in file"""
        try:
            # Read all records
            records = []
            with open(self.credentials_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get('business_site_id') == updated_record['business_site_id']:
                            # Update the record
                            record['last_accessed'] = updated_record['last_accessed']
                        records.append(record)
            
            # Write back all records
            with open(self.credentials_file, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
                    
        except Exception as e:
            logger.error(f"❌ Error updating credentials record: {e}")
    
    def delete_credentials(self, business_site_id: str) -> bool:
        """Delete credentials for a business"""
        try:
            if not self.credentials_file.exists():
                return True
            
            # Read all records except the one to delete
            records = []
            with open(self.credentials_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get('business_site_id') != business_site_id:
                            records.append(record)
            
            # Write back remaining records
            with open(self.credentials_file, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
            
            logger.info(f"✅ Credentials deleted for {business_site_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting credentials: {e}")
            return False
    
    def list_credentials(self) -> list:
        """List all stored credentials (without sensitive data)"""
        try:
            if not self.credentials_file.exists():
                return []
            
            credentials_list = []
            with open(self.credentials_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        # Return only non-sensitive data
                        safe_record = {
                            "business_site_id": record.get('business_site_id'),
                            "website_url": record.get('website_url'),
                            "cms_login_url": record.get('cms_login_url'),
                            "username": record.get('username'),
                            "stored_date": record.get('stored_date'),
                            "last_accessed": record.get('last_accessed'),
                            "notes": record.get('notes')
                        }
                        credentials_list.append(safe_record)
            
            return credentials_list
            
        except Exception as e:
            logger.error(f"❌ Error listing credentials: {e}")
            return []
    
    def validate_credentials(self, business_site_id: str) -> bool:
        """Check if credentials exist for a business"""
        try:
            if not self.credentials_file.exists():
                return False
            
            with open(self.credentials_file, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        if record.get('business_site_id') == business_site_id:
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error validating credentials: {e}")
            return False
    
    def get_credentials_summary(self) -> Dict[str, Any]:
        """Get summary of stored credentials"""
        try:
            credentials_list = self.list_credentials()
            
            return {
                "total_credentials": len(credentials_list),
                "recent_credentials": [
                    cred for cred in credentials_list 
                    if cred.get('stored_date') and 
                    datetime.fromisoformat(cred['stored_date'].replace('Z', '+00:00')) > 
                    datetime.now().replace(tzinfo=None) - timedelta(days=7)
                ],
                "websites": list(set(cred.get('website_url') for cred in credentials_list if cred.get('website_url')))
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting credentials summary: {e}")
            return {"total_credentials": 0, "recent_credentials": [], "websites": []}

# Global instance
credentials_manager = CredentialsManager()
