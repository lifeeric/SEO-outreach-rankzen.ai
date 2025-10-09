import requests
import time
import logging
from typing import Optional, Dict, Any
import base64
from io import BytesIO
from PIL import Image

from app.config import config

logger = logging.getLogger(__name__)

class CaptchaSolver:
    """Handles CAPTCHA solving using 2Captcha or Anti-Captcha services"""
    
    def __init__(self):
        self.service = config.CAPTCHA_SERVICE.lower()
        
        if self.service == "2captcha":
            self.base_url = "https://2captcha.com"
        elif self.service == "anticaptcha":
            self.base_url = "https://api.anti-captcha.com"
        else:
            raise ValueError(f"Unsupported CAPTCHA service: {self.service}")
    
    @property
    def api_key(self):
        """Dynamically get the CAPTCHA API key from config"""
        return config.CAPTCHA_API_KEY
    
    def solve_image_captcha(self, image_data: bytes) -> Optional[str]:
        """
        Solve image-based CAPTCHA
        Returns the solved text or None if failed
        """
        try:
            if self.service == "2captcha":
                return self._solve_2captcha_image(image_data)
            elif self.service == "anticaptcha":
                return self._solve_anticaptcha_image(image_data)
            else:
                logger.error(f"Unsupported CAPTCHA service: {self.service}")
                return None
                
        except Exception as e:
            logger.error(f"Error solving image CAPTCHA: {e}")
            return None
    
    def solve_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """
        Solve reCAPTCHA
        Returns the solved token or None if failed
        """
        try:
            if self.service == "2captcha":
                return self._solve_2captcha_recaptcha(site_key, page_url)
            elif self.service == "anticaptcha":
                return self._solve_anticaptcha_recaptcha(site_key, page_url)
            else:
                logger.error(f"Unsupported CAPTCHA service: {self.service}")
                return None
                
        except Exception as e:
            logger.error(f"Error solving reCAPTCHA: {e}")
            return None
    
    def _solve_2captcha_image(self, image_data: bytes) -> Optional[str]:
        """Solve image CAPTCHA using 2Captcha"""
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Submit CAPTCHA
            submit_data = {
                'key': self.api_key,
                'method': 'base64',
                'body': image_b64,
                'json': 1
            }
            
            response = requests.post(f"{self.base_url}/in.php", data=submit_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 1:
                logger.error(f"2Captcha submission failed: {result}")
                return None
            
            captcha_id = result['request']
            
            # Wait for solution
            for _ in range(30):  # Wait up to 5 minutes
                time.sleep(10)
                
                check_data = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }
                
                response = requests.get(f"{self.base_url}/res.php", params=check_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get('status') == 1:
                    logger.info("2Captcha image solved successfully")
                    return result['request']
                elif result.get('request') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    logger.error(f"2Captcha solution failed: {result}")
                    return None
            
            logger.error("2Captcha image solving timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error in 2Captcha image solving: {e}")
            return None
    
    def _solve_2captcha_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA using 2Captcha"""
        try:
            # Submit reCAPTCHA
            submit_data = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1
            }
            
            response = requests.post(f"{self.base_url}/in.php", data=submit_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 1:
                logger.error(f"2Captcha reCAPTCHA submission failed: {result}")
                return None
            
            captcha_id = result['request']
            
            # Wait for solution
            for _ in range(60):  # Wait up to 10 minutes for reCAPTCHA
                time.sleep(10)
                
                check_data = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }
                
                response = requests.get(f"{self.base_url}/res.php", params=check_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get('status') == 1:
                    logger.info("2Captcha reCAPTCHA solved successfully")
                    return result['request']
                elif result.get('request') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    logger.error(f"2Captcha reCAPTCHA solution failed: {result}")
                    return None
            
            logger.error("2Captcha reCAPTCHA solving timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error in 2Captcha reCAPTCHA solving: {e}")
            return None
    
    def _solve_anticaptcha_image(self, image_data: bytes) -> Optional[str]:
        """Solve image CAPTCHA using Anti-Captcha"""
        try:
            # Encode image to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Submit CAPTCHA
            submit_data = {
                'clientKey': self.api_key,
                'task': {
                    'type': 'ImageToTextTask',
                    'body': image_b64
                }
            }
            
            response = requests.post(f"{self.base_url}/createTask", json=submit_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errorId') != 0:
                logger.error(f"Anti-Captcha submission failed: {result}")
                return None
            
            task_id = result['taskId']
            
            # Wait for solution
            for _ in range(30):  # Wait up to 5 minutes
                time.sleep(10)
                
                check_data = {
                    'clientKey': self.api_key,
                    'taskId': task_id
                }
                
                response = requests.post(f"{self.base_url}/getTaskResult", json=check_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get('status') == 'ready':
                    logger.info("Anti-Captcha image solved successfully")
                    return result['solution']['text']
                elif result.get('status') == 'processing':
                    continue
                else:
                    logger.error(f"Anti-Captcha solution failed: {result}")
                    return None
            
            logger.error("Anti-Captcha image solving timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error in Anti-Captcha image solving: {e}")
            return None
    
    def _solve_anticaptcha_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA using Anti-Captcha"""
        try:
            # Submit reCAPTCHA
            submit_data = {
                'clientKey': self.api_key,
                'task': {
                    'type': 'RecaptchaV2TaskProxyless',
                    'websiteURL': page_url,
                    'websiteKey': site_key
                }
            }
            
            response = requests.post(f"{self.base_url}/createTask", json=submit_data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errorId') != 0:
                logger.error(f"Anti-Captcha reCAPTCHA submission failed: {result}")
                return None
            
            task_id = result['taskId']
            
            # Wait for solution
            for _ in range(60):  # Wait up to 10 minutes for reCAPTCHA
                time.sleep(10)
                
                check_data = {
                    'clientKey': self.api_key,
                    'taskId': task_id
                }
                
                response = requests.post(f"{self.base_url}/getTaskResult", json=check_data)
                response.raise_for_status()
                
                result = response.json()
                if result.get('status') == 'ready':
                    logger.info("Anti-Captcha reCAPTCHA solved successfully")
                    return result['solution']['gRecaptchaResponse']
                elif result.get('status') == 'processing':
                    continue
                else:
                    logger.error(f"Anti-Captcha reCAPTCHA solution failed: {result}")
                    return None
            
            logger.error("Anti-Captcha reCAPTCHA solving timed out")
            return None
            
        except Exception as e:
            logger.error(f"Error in Anti-Captcha reCAPTCHA solving: {e}")
            return None
    
    def detect_captcha_type(self, soup) -> Dict[str, Any]:
        """
        Detect CAPTCHA type on a page
        Returns captcha info or None if no CAPTCHA found
        """
        captcha_info = {
            'has_captcha': False,
            'type': None,
            'site_key': None,
            'image_src': None
        }
        
        try:
            # Check for reCAPTCHA
            recaptcha_div = soup.find('div', class_='g-recaptcha')
            if recaptcha_div:
                captcha_info['has_captcha'] = True
                captcha_info['type'] = 'recaptcha'
                captcha_info['site_key'] = recaptcha_div.get('data-sitekey')
                return captcha_info
            
            # Check for hCaptcha
            hcaptcha_div = soup.find('div', class_='h-captcha')
            if hcaptcha_div:
                captcha_info['has_captcha'] = True
                captcha_info['type'] = 'hcaptcha'
                captcha_info['site_key'] = hcaptcha_div.get('data-sitekey')
                return captcha_info
            
            # Check for image CAPTCHA
            captcha_img = soup.find('img', src=lambda x: x and 'captcha' in x.lower())
            if captcha_img:
                captcha_info['has_captcha'] = True
                captcha_info['type'] = 'image'
                captcha_info['image_src'] = captcha_img.get('src')
                return captcha_info
            
            # Check for text-based CAPTCHA
            captcha_text = soup.find(text=lambda x: x and 'captcha' in x.lower())
            if captcha_text:
                captcha_info['has_captcha'] = True
                captcha_info['type'] = 'text'
                return captcha_info
            
            return captcha_info
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA type: {e}")
            return captcha_info
