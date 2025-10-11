import logging
import time
from threading import Lock
from typing import Optional, Tuple
from urllib.parse import urlparse

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import config

logger = logging.getLogger(__name__)


class DeadHostError(RuntimeError):
    """Raised when a host was recently marked unreachable and is still cooling down."""

    def __init__(self, domain: str, last_failure: float):
        super().__init__(f"Host {domain} marked unreachable at {last_failure}")
        self.domain = domain
        self.last_failure = last_failure


class RobustHttpClient:
    """Central HTTP client with retries, timeouts, and dead-host caching."""

    def __init__(self):
        self._session = requests.Session()
        retry = Retry(
            total=config.HTTP_MAX_RETRIES,
            backoff_factor=config.HTTP_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_maxsize=128, pool_connections=64)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._default_timeout: Tuple[float, float] = (
            config.REQUEST_CONNECT_TIMEOUT,
            config.REQUEST_READ_TIMEOUT,
        )
        self._dead_hosts: dict[str, float] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _extract_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    def _should_skip(self, domain: str) -> Optional[float]:
        with self._lock:
            last_failure = self._dead_hosts.get(domain)
        if not last_failure:
            return None

        if time.time() - last_failure < config.DEAD_HOST_CACHE_SECONDS:
            return last_failure

        # TTL expired, purge cache entry
        with self._lock:
            self._dead_hosts.pop(domain, None)
        return None

    def _mark_dead(self, domain: str):
        with self._lock:
            self._dead_hosts[domain] = time.time()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def request(self, method: str, url: str, **kwargs) -> Response:
        domain = self._extract_domain(url)
        last_failure = self._should_skip(domain)
        if last_failure is not None:
            raise DeadHostError(domain, last_failure)

        timeout = kwargs.pop("timeout", None)
        if timeout is None:
            timeout = self._default_timeout

        try:
            response = self._session.request(method, url, timeout=timeout, **kwargs)
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            self._mark_dead(domain)
            logger.warning("HTTP %s %s failed, marking host dead: %s", method, url, exc)
            raise

    def get(self, url: str, **kwargs) -> Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.request("POST", url, **kwargs)

    def head(self, url: str, **kwargs) -> Response:
        return self.request("HEAD", url, **kwargs)

    def is_reachable(self, url: str, *, allow_redirects: bool = True) -> bool:
        """Lightweight reachability probe with graceful failure handling."""
        try:
            response = self.head(url, allow_redirects=allow_redirects)
            if response.status_code < 400:
                return True
        except DeadHostError:
            return False
        except requests.RequestException:
            # We'll fallback to a lightweight GET below
            pass

        try:
            response = self.get(url, stream=True, allow_redirects=allow_redirects)
            response.close()
            return response.status_code < 400
        except DeadHostError:
            return False
        except requests.RequestException:
            return False

    def revive_host(self, domain: str):
        """Manually remove a domain from the dead-host cache."""
        with self._lock:
            self._dead_hosts.pop(domain, None)


http_client = RobustHttpClient()

