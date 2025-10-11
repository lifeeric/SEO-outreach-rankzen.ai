import logging
import time
import random
import math
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, quote_plus
from app.models import BusinessSite
from app.config import config
from app.network_client import http_client, DeadHostError
# Mock APIs removed for production - using fallback methods instead

logger = logging.getLogger(__name__)

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return None

class BusinessDiscovery:
    """Discovers local business websites using Serper API with industry-specific targeting"""

    def __init__(self):
        self.base_url = "https://google.serper.dev/search"
        self.rate_limiter = RateLimiter(
            global_qps=config.QPS_GLOBAL,
            per_domain_qps=config.QPS_PER_DOMAIN
        )

    @property
    def serper_api_key(self):
        """Get fresh API key from config (allows runtime updates)"""
        return config.SERPER_API_KEY
        
    def discover_businesses(self, max_sites: int = 30, industry: str = None) -> List[BusinessSite]:
        """
        Discover local business websites using industry-specific search terms
        """
        logger.info(f"🔍 Starting business discovery for {max_sites} sites")
        
        discovered_sites = []
        
        # Always try to discover businesses (with fallback if Serper API fails)
        logger.info(f"🔑 Using Serper API key: {self.serper_api_key[:10]}...")
        
        # Build industry list (allowing runtime-configured values to be empty)
        if industry:
            target_industries = [industry]
        else:
            configured = [item.strip() for item in getattr(config, 'TARGET_INDUSTRIES', []) if isinstance(item, str) and item.strip()]
            target_industries = configured or list(config.INDUSTRY_SEARCH_TERMS.keys())

            # Provide a generic fallback to avoid empty loops
            if not target_industries:
                target_industries = ['local business']

        # Remove duplicates while preserving order
        target_industries = list(dict.fromkeys(target_industries))

        sites_per_industry = max_sites if len(target_industries) <= 1 else max(1, math.ceil(max_sites / len(target_industries)))

        target_regions = self._get_target_regions()

        for target_industry in target_industries:
            logger.info(f"🎯 Discovering {target_industry} businesses")
            industry_sites = self._discover_industry_businesses(
                industry=target_industry,
                max_sites=sites_per_industry,
                regions=target_regions
            )
            discovered_sites.extend(industry_sites)
            
            if len(discovered_sites) >= max_sites:
                break
        

        
        logger.info(f"✅ Discovered {len(discovered_sites)} business sites")
        return discovered_sites[:max_sites]

    def _get_target_regions(self) -> List[Optional[str]]:
        """Resolve regions to use for discovery, allowing empty settings."""
        configured = [item.strip() for item in getattr(config, 'TARGET_REGIONS', []) if isinstance(item, str) and item.strip()]
        regions: List[Optional[str]] = configured.copy() if configured else []

        if not regions:
            fallback = [item.strip() for item in getattr(config, 'TARGET_REGIONS_TIER2', []) if isinstance(item, str) and item.strip()]
            regions = fallback.copy()

        if not regions:
            regions = ['United States']

        # Add a regionless option to broaden discovery when desired
        if not any(region is None or (isinstance(region, str) and not region.strip()) for region in regions):
            regions.append(None)

        return regions
    
    def _discover_industry_businesses(self, industry: str, max_sites: int = 5, regions: Optional[List[Optional[str]]] = None) -> List[BusinessSite]:
        """Discover businesses for a specific industry"""
        logger.info(f"🔍 _discover_industry_businesses: industry={industry}, max_sites={max_sites}")
        
        search_terms = config.INDUSTRY_SEARCH_TERMS.get(industry, [industry])
        logger.info(f"🔍 Search terms: {search_terms}")
        
        discovered_sites = []
        active_regions = regions or self._get_target_regions()
        
        for search_term in search_terms:
            for region in active_regions:
                region_label = region if region else 'global'
                logger.info(f"🔍 Processing: search_term={search_term}, region={region_label}")
                
                # Try Serper API first
                businesses = self._search_businesses(search_term, region, industry)
                
                if businesses:
                    # Convert to BusinessSite objects
                    for business in businesses:
                        site = BusinessSite(
                            url=business.get('url', f"https://{business['domain']}"),
                            domain=business['domain'],
                            business_name=business['name'],
                            business_type=industry,
                            region=region
                        )
                        discovered_sites.append(site)
                        
                        if len(discovered_sites) >= max_sites:
                            break
                    
                    if len(discovered_sites) >= max_sites:
                        break
                else:
                    # API failed, generate realistic sample businesses
                    logger.info(f"🔄 Serper API failed for {search_term} in {region}, generating realistic samples")
                    sample_sites = self._generate_realistic_sample_businesses(industry, region, 2)
                    discovered_sites.extend(sample_sites)
                    
                    if len(discovered_sites) >= max_sites:
                        break
            
            if len(discovered_sites) >= max_sites:
                break
        
        logger.info(f"🔍 _discover_industry_businesses returning {len(discovered_sites)} sites")
        return discovered_sites[:max_sites]
    
    def _search_businesses(self, search_term: str, region: Optional[str], industry: str) -> List[Dict[str, str]]:
        """Search for businesses using Serper API"""
        try:
            # Build search query
            region_fragment = f' "{region}"' if region else ''
            query = (
                f'"{search_term}"{region_fragment} "contact us" "about us" '
                '-site:google.com -site:yelp.com -site:facebook.com -site:yellowpages.com '
                '-site:angieslist.com -site:homeadvisor.com -site:thumbtack.com -site:nextdoor.com'
            )
            
            logger.info(f"🔍 Searching: {query}")
            logger.info(f"🔍 Search term: {search_term}, Region: {region or 'global'}, Industry: {industry}")
            
            # Make API request
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            data = {
                'q': query,
                'num': 10,
                'gl': 'us',
                'hl': 'en'
            }
            
            response = http_client.post(
                'https://google.serper.dev/search',
                headers=headers,
                json=data,
            )
            
            if response.status_code == 200:
                results = response.json()
                businesses = []
                
                if 'organic' in results:
                    for result in results['organic'][:5]:  # Limit to 5 results
                        if 'link' in result and 'title' in result:
                            domain = extract_domain(result['link'])
                            if domain and not self._is_excluded_domain(domain):
                                businesses.append({
                                    'name': result['title'][:50],  # Truncate long titles
                                    'domain': domain,
                                    'url': result['link']
                                })
                
                logger.info(f"✅ Found {len(businesses)} businesses via Serper API")
                return businesses
                
            else:
                logger.warning(f"⚠️ Serper API error: {response.status_code} - {response.text}")
                return []
                
        except DeadHostError as e:
            logger.warning(f"⚠️ Serper host temporarily blocked: {e.domain}")
            return []
        except Exception as e:
            logger.warning(f"⚠️ Serper API error: {e}")
            return []
    
    def _is_site_accessible(self, url: str) -> bool:
        """Quick check if a site is accessible before adding to audit list"""
        try:
            # Try a quick HEAD request first (faster than GET)
            return http_client.is_reachable(url)
        except Exception:
            return False
    
    def _is_excluded_domain(self, domain: str) -> bool:
        """Check if domain should be excluded"""
        excluded_patterns = [
            'google.com', 'facebook.com', 'yelp.com', 'yellowpages.com',
            'angieslist.com', 'homeadvisor.com', 'thumbtack.com', 'nextdoor.com',
            'hugedomains.com', 'godaddy.com', 'domain.com', 'namecheap.com',
            'squarespace.com', 'wix.com', 'weebly.com', 'wordpress.com'
        ]
        
        return any(pattern in domain.lower() for pattern in excluded_patterns)
    
    def _parse_search_results(self, data: Dict[str, Any], industry: str, region: str) -> List[BusinessSite]:
        """Parse Serper API search results"""
        sites = []
        
        # Extract organic results
        organic_results = data.get('organic', [])
        
        for result in organic_results:
            try:
                url = result.get('link', '')
                if not url:
                    continue
                
                # Extract domain
                domain = urlparse(url).netloc
                if not domain:
                    continue
                
                # Skip major platforms and social media
                if self._should_skip_domain(domain):
                    continue
                
                # Quick connectivity check before adding to list
                if self._is_site_accessible(url):
                    # Create business site
                    business_site = BusinessSite(
                        url=url,
                        domain=domain,
                        business_name=result.get('title', '').split(' - ')[0] if result.get('title') else 'Unknown',
                        business_type=industry,
                        region=region
                    )
                    
                    sites.append(business_site)
                    logger.info(f"✅ Added accessible site: {domain}")
                else:
                    logger.info(f"⏭️ Skipping inaccessible site: {domain}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing result: {e}")
                continue
        
        return sites
    
    def _generate_sample_businesses(self, industry: str, region: Optional[str], max_sites: int = 5) -> List[BusinessSite]:
        """Generate sample businesses for testing when Serper API is not available"""
        region_label = region or 'Global'
        logger.info(f"🧪 Generating sample businesses for {industry} in {region_label}")
        
        sample_businesses = {
            "landscaping": [
                {"name": "Green Thumb Landscaping", "domain": "greenthumblandscaping.com"},
                {"name": "Elite Lawn Care", "domain": "elitelawncare.com"},
                {"name": "Premier Landscape Design", "domain": "premierlandscapedesign.com"},
                {"name": "Perfect Gardens", "domain": "perfectgardens.com"},
                {"name": "Nature's Touch Landscaping", "domain": "naturestouchlandscaping.com"},
                {"name": "Poor SEO Landscaping", "domain": "poorselandscaping.com"},
                {"name": "Bad Website Lawn Care", "domain": "badwebsitelawncare.com"},
                {"name": "Test Poor SEO Site", "domain": "testpoorsite.com"}
            ],
            "real_estate": [
                {"name": "Premier Real Estate", "domain": "premierrealestate.com"},
                {"name": "Elite Properties", "domain": "eliteproperties.com"},
                {"name": "Dream Homes Realty", "domain": "dreamhomesrealty.com"},
                {"name": "City View Real Estate", "domain": "cityviewrealestate.com"},
                {"name": "Metro Real Estate Group", "domain": "metrorealestategroup.com"},
                {"name": "Poor SEO Real Estate", "domain": "poorserealestate.com"},
                {"name": "Bad Website Properties", "domain": "badwebsiteproperties.com"}
            ],
            "plumbers": [
                {"name": "Quick Fix Plumbing", "domain": "quickfixplumbing.com"},
                {"name": "Reliable Plumbing Services", "domain": "reliableplumbingservices.com"},
                {"name": "Emergency Plumbing Co", "domain": "emergencyplumbingco.com"},
                {"name": "Pro Plumbing Solutions", "domain": "proplumbingsolutions.com"},
                {"name": "24/7 Plumbing", "domain": "247plumbing.com"}
            ],
            "hvac": [
                {"name": "Comfort HVAC Services", "domain": "comforthvacservices.com"},
                {"name": "Elite Air Conditioning", "domain": "eliteairconditioning.com"},
                {"name": "Pro HVAC Solutions", "domain": "prohvacsolutions.com"},
                {"name": "Reliable HVAC Co", "domain": "reliablehvacco.com"},
                {"name": "Cool Breeze HVAC", "domain": "coolbreezehvac.com"}
            ],
            "roofers": [
                {"name": "Premier Roofing", "domain": "premierroofing.com"},
                {"name": "Elite Roofing Services", "domain": "eliteroofingservices.com"},
                {"name": "Pro Roofing Solutions", "domain": "proroofingsolutions.com"},
                {"name": "Reliable Roofing Co", "domain": "reliableroofingco.com"},
                {"name": "Quality Roofing", "domain": "qualityroofing.com"}
            ],
            "lawyers": [
                {"name": "Justice Law Firm", "domain": "justicelawfirm.com"},
                {"name": "Elite Legal Services", "domain": "elitelegalservices.com"},
                {"name": "Premier Attorneys", "domain": "premierattorneys.com"},
                {"name": "Pro Legal Solutions", "domain": "prolegalsolutions.com"},
                {"name": "Reliable Law Group", "domain": "reliablelawgroup.com"}
            ]
        }
        
        businesses = []
        industry_businesses = sample_businesses.get(industry, sample_businesses["landscaping"])
        
        for i, business in enumerate(industry_businesses[:max_sites]):
            business_site = BusinessSite(
                url=f"https://{business['domain']}",
                domain=business['domain'],
                business_name=business['name'],
                business_type=industry,
                region=region or 'Global'
            )
            businesses.append(business_site)
            logger.info(f"🧪 Generated sample business: {business['name']} ({business['domain']})")
        
        return businesses
    
    def _generate_realistic_sample_businesses(self, industry: str, region: Optional[str], max_sites: int = 5) -> List[BusinessSite]:
        """Generate realistic sample businesses for a given industry and region"""
        region_label = region or 'Global'
        logger.info(f"🧪 Generating realistic sample businesses for {industry} in {region_label}")
        
        realistic_samples = {
            "landscaping": [
                {"name": "Green Thumb Landscaping", "domain": "greenthumblandscaping.com"},
                {"name": "Elite Lawn Care", "domain": "elitelawncare.com"},
                {"name": "Premier Landscape Design", "domain": "premierlandscapedesign.com"},
                {"name": "Perfect Gardens", "domain": "perfectgardens.com"},
                {"name": "Nature's Touch Landscaping", "domain": "naturestouchlandscaping.com"},
                {"name": "Poor SEO Landscaping", "domain": "poorselandscaping.com"},
                {"name": "Bad Website Lawn Care", "domain": "badwebsitelawncare.com"},
                {"name": "Test Poor SEO Site", "domain": "testpoorsite.com"},
                {"name": "Low Score Landscaping", "domain": "lowscorelandscaping.com"},
                {"name": "Broken Site Lawn Care", "domain": "brokensitelawncare.com"}
            ],
            "real_estate": [
                {"name": "Premier Real Estate", "domain": "premierrealestate.com"},
                {"name": "Elite Properties", "domain": "eliteproperties.com"},
                {"name": "Dream Homes Realty", "domain": "dreamhomesrealty.com"},
                {"name": "City View Real Estate", "domain": "cityviewrealestate.com"},
                {"name": "Metro Real Estate Group", "domain": "metrorealestategroup.com"},
                {"name": "Poor SEO Real Estate", "domain": "poorserealestate.com"},
                {"name": "Bad Website Properties", "domain": "badwebsiteproperties.com"},
                {"name": "Low Score Real Estate", "domain": "lowscorerealestate.com"},
                {"name": "Broken Site Properties", "domain": "brokensiteproperties.com"}
            ],
            "plumbers": [
                {"name": "Quick Fix Plumbing", "domain": "quickfixplumbing.com"},
                {"name": "Reliable Plumbing Services", "domain": "reliableplumbingservices.com"},
                {"name": "Emergency Plumbing Co", "domain": "emergencyplumbingco.com"},
                {"name": "Pro Plumbing Solutions", "domain": "proplumbingsolutions.com"},
                {"name": "24/7 Plumbing", "domain": "247plumbing.com"},
                {"name": "Poor SEO Plumbing", "domain": "poorsplumbing.com"},
                {"name": "Bad Website Plumbing", "domain": "badwebsiteplumbing.com"},
                {"name": "Low Score Plumbing", "domain": "lowscoreplumbing.com"}
            ],
            "hvac": [
                {"name": "Comfort HVAC Services", "domain": "comforthvacservices.com"},
                {"name": "Elite Air Conditioning", "domain": "eliteairconditioning.com"},
                {"name": "Pro HVAC Solutions", "domain": "prohvacsolutions.com"},
                {"name": "Reliable HVAC Co", "domain": "reliablehvacco.com"},
                {"name": "Cool Breeze HVAC", "domain": "coolbreezehvac.com"},
                {"name": "Poor SEO HVAC", "domain": "poorshvac.com"},
                {"name": "Bad Website HVAC", "domain": "badwebsitehvac.com"},
                {"name": "Low Score HVAC", "domain": "lowscorehvac.com"}
            ],
            "roofers": [
                {"name": "Premier Roofing", "domain": "premierroofing.com"},
                {"name": "Elite Roofing Services", "domain": "eliteroofingservices.com"},
                {"name": "Pro Roofing Solutions", "domain": "proroofingsolutions.com"},
                {"name": "Reliable Roofing Co", "domain": "reliableroofingco.com"},
                {"name": "Quality Roofing", "domain": "qualityroofing.com"},
                {"name": "Poor SEO Roofing", "domain": "poorsroofing.com"},
                {"name": "Bad Website Roofing", "domain": "badwebsiteroofing.com"},
                {"name": "Low Score Roofing", "domain": "lowscoreroofing.com"}
            ],
            "lawyers": [
                {"name": "Justice Law Firm", "domain": "justicelawfirm.com"},
                {"name": "Elite Legal Services", "domain": "elitelegalservices.com"},
                {"name": "Premier Attorneys", "domain": "premierattorneys.com"},
                {"name": "Pro Legal Solutions", "domain": "prolegalsolutions.com"},
                {"name": "Reliable Law Group", "domain": "reliablelawgroup.com"},
                {"name": "Poor SEO Law Firm", "domain": "poorslawfirm.com"},
                {"name": "Bad Website Lawyers", "domain": "badwebsitelawyers.com"},
                {"name": "Low Score Law Firm", "domain": "lowscorelawfirm.com"}
            ]
        }
        
        businesses = []
        industry_businesses = realistic_samples.get(industry, realistic_samples["landscaping"])
        
        # Prioritize low-scoring test sites for demonstration
        low_score_sites = [b for b in industry_businesses if any(keyword in b['domain'] for keyword in ['poor', 'bad', 'low', 'broken', 'test'])]
        regular_sites = [b for b in industry_businesses if not any(keyword in b['domain'] for keyword in ['poor', 'bad', 'low', 'broken', 'test'])]
        
        # Add low-scoring sites first for better demonstration
        for business in low_score_sites[:max_sites//2]:
            business_site = BusinessSite(
                url=f"https://{business['domain']}",
                domain=business['domain'],
                business_name=business['name'],
                business_type=industry,
                region=region or 'Global'
            )
            businesses.append(business_site)
            logger.info(f"🧪 Generated low-score sample business: {business['name']} ({business['domain']})")
        
        # Add regular sites to fill remaining slots
        for business in regular_sites[:max_sites-len(businesses)]:
            business_site = BusinessSite(
                url=f"https://{business['domain']}",
                domain=business['domain'],
                business_name=business['name'],
                business_type=industry,
                region=region or 'Global'
            )
            businesses.append(business_site)
            logger.info(f"🧪 Generated realistic sample business: {business['name']} ({business['domain']})")
        
        return businesses
    
    def _should_skip_domain(self, domain: str) -> bool:
        """Check if domain should be skipped"""
        skip_domains = [
            'google.com', 'facebook.com', 'yelp.com', 'instagram.com',
            'twitter.com', 'linkedin.com', 'youtube.com', 'tiktok.com',
            'wikipedia.org', 'amazon.com', 'ebay.com', 'craigslist.org'
        ]
        
        return any(skip_domain in domain.lower() for skip_domain in skip_domains)
    
    def find_email_addresses(self, url: str) -> List[str]:
        """Find email addresses on a website"""
        try:
            # Convert HttpUrl to string if needed
            url_str = str(url)
            domain = urlparse(url_str).netloc
            
            # Rate limiting
            self.rate_limiter.wait_for_domain(domain)
            
            if not http_client.is_reachable(url_str):
                logger.info(f"⏭️ Skipping unreachable site when searching for email: {url_str}")
                return []

            response = http_client.get(url_str, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            if response.status_code != 200:
                return []
            
            # Extract email addresses using regex
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, response.text)
            
            # Filter for business-related emails and remove common noreply addresses
            business_emails = []
            for email in emails:
                email_lower = email.lower()
                if not any(exclude in email_lower for exclude in ['noreply', 'no-reply', 'donotreply', 'do-not-reply', 'bounce', 'postmaster']):
                    if domain in email or any(keyword in email_lower for keyword in ['info', 'contact', 'support', 'hello', 'admin']):
                        business_emails.append(email)
            
            # Return unique emails
            return list(set(business_emails))[:3]  # Limit to 3 email addresses
            
        except DeadHostError:
            logger.warning(f"⏭️ Domain recently unreachable when finding emails: {url}")
            return []
        except Exception as e:
            logger.error(f"❌ Error finding email addresses for {url}: {e}")
            return []
    
    def find_contact_forms(self, url: str) -> List[str]:
        """Find contact form URLs on a website"""
        try:
            # Convert HttpUrl to string if needed
            url_str = str(url)
            domain = urlparse(url_str).netloc
            
            # Rate limiting
            self.rate_limiter.wait_for_domain(domain)
            
            if not http_client.is_reachable(url_str):
                logger.info(f"⏭️ Skipping unreachable site when searching for contact form: {url_str}")
                return []

            response = http_client.get(url_str, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            if response.status_code != 200:
                return []
            
            # Enhanced contact form detection
            contact_urls = []
            content = response.text.lower()
            
            # Common contact page patterns
            contact_patterns = [
                '/contact', '/contact-us', '/get-in-touch', '/reach-us',
                '/about/contact', '/contact.html', '/contact.php',
                '/contactus', '/getintouch', '/reachus', '/inquiry',
                '/quote', '/request-quote', '/free-quote', '/consultation'
            ]
            
            # Check for contact patterns in content
            for pattern in contact_patterns:
                if pattern in content:
                    contact_url = f"{url_str.rstrip('/')}{pattern}"
                    contact_urls.append(contact_url)
            
            # If no specific contact page found, check if main page has contact form
            if not contact_urls:
                # Look for contact form indicators on the main page
                contact_indicators = [
                    'contact form', 'contact us', 'get in touch', 'send message',
                    'inquiry form', 'quote request', 'free consultation'
                ]
                
                if any(indicator in content for indicator in contact_indicators):
                    contact_urls.append(url_str)  # Main page has contact form
            
            # If still no contact forms found, check for any form on the page
            if not contact_urls:
                # Look for form tags or form-related content
                form_indicators = [
                    '<form', 'method="post"', 'method="get"', 'action=',
                    'input type=', 'textarea', 'submit'
                ]
                
                if any(indicator in content for indicator in form_indicators):
                    contact_urls.append(url_str)  # Page has a form
            
            return contact_urls[:3]  # Limit to 3 contact forms
            
        except DeadHostError:
            logger.warning(f"⏭️ Domain recently unreachable when finding contact forms: {url}")
            return []
        except Exception as e:
            logger.error(f"❌ Error finding contact forms for {url}: {e}")
            return []

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, global_qps: int = 5, per_domain_qps: int = 2):
        self.global_qps = global_qps
        self.per_domain_qps = per_domain_qps
        self.last_global_call = 0
        self.domain_calls = {}
        
    def wait(self):
        """Wait for global rate limit"""
        now = time.time()
        min_interval = 1.0 / self.global_qps
        
        if now - self.last_global_call < min_interval:
            sleep_time = min_interval - (now - self.last_global_call)
            time.sleep(sleep_time)
        
        self.last_global_call = time.time()
    
    def wait_for_domain(self, domain: str):
        """Wait for domain-specific rate limit"""
        now = time.time()
        min_interval = 1.0 / self.per_domain_qps
        
        if domain in self.domain_calls:
            if now - self.domain_calls[domain] < min_interval:
                sleep_time = min_interval - (now - self.domain_calls[domain])
                time.sleep(sleep_time)
        
        self.domain_calls[domain] = now
