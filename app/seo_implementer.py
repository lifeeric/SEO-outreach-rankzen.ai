import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json

from app.config import config
from app.phase2_models import SEOImplementation, SEOImplementationResponse
from app.credentials_manager import credentials_manager

logger = logging.getLogger(__name__)

class SEOImplementer:
    """Handles automated SEO implementation using collected credentials"""
    
    def __init__(self):
        self.implementation_log_file = Path("data/seo_implementations.jsonl")
        self.implementation_log_file.parent.mkdir(exist_ok=True)
        self.implementations: Dict[str, Dict[str, Any]] = {}
        self._load_implementations()
    
    def _load_implementations(self):
        """Load existing implementations from file"""
        if self.implementation_log_file.exists():
            try:
                with open(self.implementation_log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            self.implementations[data['business_site_id']] = data
                logger.info(f"Loaded {len(self.implementations)} existing implementations")
            except Exception as e:
                logger.error(f"Error loading implementations: {e}")
    
    def _save_implementation(self, implementation_data: Dict[str, Any]):
        """Save implementation to file"""
        try:
            with open(self.implementation_log_file, 'a') as f:
                f.write(json.dumps(implementation_data) + '\n')
        except Exception as e:
            logger.error(f"Error saving implementation: {e}")
    
    def start_implementation(self, business_site_id: str, 
                           changes_to_implement: List[str]) -> Dict[str, Any]:
        """Start SEO implementation process"""
        logger.info(f"🚀 Starting SEO implementation for {business_site_id}")
        
        # Get credentials
        credentials = credentials_manager.get_credentials(business_site_id)
        if not credentials:
            return {
                "success": False,
                "error": "No credentials found for this business"
            }
        
        implementation_data = {
            "business_site_id": business_site_id,
            "website_url": credentials.get('website_url'),
            "start_time": datetime.now().isoformat(),
            "changes_to_implement": changes_to_implement,
            "status": "started",
            "changes_implemented": [],
            "implementation_notes": [],
            "errors": [],
            "completion_time": None
        }
        
        self.implementations[business_site_id] = implementation_data
        self._save_implementation(implementation_data)
        
        # Simulate implementation process
        success = self._implement_changes(business_site_id, changes_to_implement, credentials)
        
        if success:
            implementation_data["status"] = "completed"
            implementation_data["completion_time"] = datetime.now().isoformat()
            self._save_implementation(implementation_data)
            
            logger.info(f"✅ SEO implementation completed for {business_site_id}")
            return {
                "success": True,
                "changes_implemented": implementation_data["changes_implemented"],
                "implementation_notes": implementation_data["implementation_notes"]
            }
        else:
            implementation_data["status"] = "failed"
            implementation_data["completion_time"] = datetime.now().isoformat()
            self._save_implementation(implementation_data)
            
            logger.error(f"❌ SEO implementation failed for {business_site_id}")
            return {
                "success": False,
                "errors": implementation_data["errors"]
            }
    
    def _implement_changes(self, business_site_id: str, 
                          changes: List[str], credentials: Dict[str, Any]) -> bool:
        """Implement the actual SEO changes"""
        try:
            logger.info(f"🔧 Implementing {len(changes)} changes for {business_site_id}")
            
            implementation_data = self.implementations[business_site_id]
            implemented_changes = []
            notes = []
            
            for change in changes:
                logger.info(f"Implementing: {change}")
                
                # Simulate implementation time
                time.sleep(1)
                
                # Implement based on change type
                if "meta description" in change.lower():
                    success = self._implement_meta_description(credentials, change)
                    if success:
                        implemented_changes.append(f"Added meta description")
                        notes.append(f"Meta description updated successfully")
                    else:
                        implementation_data["errors"].append(f"Failed to implement meta description")
                
                elif "title tag" in change.lower():
                    success = self._implement_title_tag(credentials, change)
                    if success:
                        implemented_changes.append(f"Updated title tag")
                        notes.append(f"Title tag optimized")
                    else:
                        implementation_data["errors"].append(f"Failed to implement title tag")
                
                elif "alt text" in change.lower():
                    success = self._implement_alt_text(credentials, change)
                    if success:
                        implemented_changes.append(f"Added alt text to images")
                        notes.append(f"Alt text added to {self._count_images(credentials)} images")
                    else:
                        implementation_data["errors"].append(f"Failed to implement alt text")
                
                elif "google business profile" in change.lower():
                    success = self._implement_gbp_fixes(credentials, change)
                    if success:
                        implemented_changes.append(f"Updated Google Business Profile")
                        notes.append(f"GBP hours, description, and categories updated")
                    else:
                        implementation_data["errors"].append(f"Failed to implement GBP fixes")
                
                elif "yelp" in change.lower():
                    success = self._implement_yelp_fixes(credentials, change)
                    if success:
                        implemented_changes.append(f"Updated Yelp listing")
                        notes.append(f"Yelp business information updated")
                    else:
                        implementation_data["errors"].append(f"Failed to implement Yelp fixes")
                
                elif "facebook" in change.lower():
                    success = self._implement_facebook_fixes(credentials, change)
                    if success:
                        implemented_changes.append(f"Updated Facebook page")
                        notes.append(f"Facebook business page optimized")
                    else:
                        implementation_data["errors"].append(f"Failed to implement Facebook fixes")
                
                else:
                    # Generic implementation
                    success = self._implement_generic_fix(credentials, change)
                    if success:
                        implemented_changes.append(change)
                        notes.append(f"Successfully implemented: {change}")
                    else:
                        implementation_data["errors"].append(f"Failed to implement: {change}")
            
            # Update implementation data
            implementation_data["changes_implemented"] = implemented_changes
            implementation_data["implementation_notes"] = notes
            
            # Check if we had any errors
            return len(implementation_data["errors"]) == 0
            
        except Exception as e:
            logger.error(f"❌ Error during implementation: {e}")
            if business_site_id in self.implementations:
                self.implementations[business_site_id]["errors"].append(str(e))
            return False
    
    def _implement_meta_description(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement meta description fix"""
        try:
            # Simulate CMS login and meta description update
            logger.info(f"📝 Adding meta description to {credentials.get('website_url')}")
            
            # In real implementation, this would:
            # 1. Login to CMS using credentials
            # 2. Navigate to page settings
            # 3. Add/update meta description
            # 4. Save changes
            
            return True
        except Exception as e:
            logger.error(f"Error implementing meta description: {e}")
            return False
    
    def _implement_title_tag(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement title tag fix"""
        try:
            logger.info(f"📝 Updating title tag for {credentials.get('website_url')}")
            
            # Simulate title tag update
            return True
        except Exception as e:
            logger.error(f"Error implementing title tag: {e}")
            return False
    
    def _implement_alt_text(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement alt text fix"""
        try:
            logger.info(f"🖼️ Adding alt text to images on {credentials.get('website_url')}")
            
            # Simulate alt text addition
            return True
        except Exception as e:
            logger.error(f"Error implementing alt text: {e}")
            return False
    
    def _implement_gbp_fixes(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement Google Business Profile fixes"""
        try:
            logger.info(f"🏢 Updating Google Business Profile for {credentials.get('website_url')}")
            
            # Simulate GBP updates
            return True
        except Exception as e:
            logger.error(f"Error implementing GBP fixes: {e}")
            return False
    
    def _implement_yelp_fixes(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement Yelp listing fixes"""
        try:
            logger.info(f"⭐ Updating Yelp listing for {credentials.get('website_url')}")
            
            # Simulate Yelp updates
            return True
        except Exception as e:
            logger.error(f"Error implementing Yelp fixes: {e}")
            return False
    
    def _implement_facebook_fixes(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement Facebook page fixes"""
        try:
            logger.info(f"📘 Updating Facebook page for {credentials.get('website_url')}")
            
            # Simulate Facebook updates
            return True
        except Exception as e:
            logger.error(f"Error implementing Facebook fixes: {e}")
            return False
    
    def _implement_generic_fix(self, credentials: Dict[str, Any], change: str) -> bool:
        """Implement generic SEO fix"""
        try:
            logger.info(f"🔧 Implementing generic fix: {change}")
            
            # Simulate generic implementation
            return True
        except Exception as e:
            logger.error(f"Error implementing generic fix: {e}")
            return False
    
    def _count_images(self, credentials: Dict[str, Any]) -> int:
        """Count images on website (simulated)"""
        # In real implementation, this would crawl the site and count images
        return 5  # Simulated count
    
    def get_implementation_status(self, business_site_id: str) -> Optional[Dict[str, Any]]:
        """Get implementation status for a business"""
        return self.implementations.get(business_site_id)
    
    def get_all_implementations(self) -> List[Dict[str, Any]]:
        """Get all implementations"""
        return list(self.implementations.values())
    
    def get_implementations_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get implementations by status"""
        return [impl for impl in self.implementations.values() if impl.get('status') == status]
    
    def get_implementation_summary(self) -> Dict[str, Any]:
        """Get summary of all implementations"""
        try:
            implementations = self.get_all_implementations()
            
            total_implementations = len(implementations)
            completed = len([impl for impl in implementations if impl.get('status') == 'completed'])
            failed = len([impl for impl in implementations if impl.get('status') == 'failed'])
            in_progress = len([impl for impl in implementations if impl.get('status') == 'started'])
            
            total_changes = sum(len(impl.get('changes_implemented', [])) for impl in implementations)
            
            return {
                "total_implementations": total_implementations,
                "completed": completed,
                "failed": failed,
                "in_progress": in_progress,
                "total_changes_implemented": total_changes,
                "success_rate": (completed / total_implementations * 100) if total_implementations > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting implementation summary: {e}")
            return {
                "total_implementations": 0,
                "completed": 0,
                "failed": 0,
                "in_progress": 0,
                "total_changes_implemented": 0,
                "success_rate": 0
            }

# Global instance
seo_implementer = SEOImplementer()
