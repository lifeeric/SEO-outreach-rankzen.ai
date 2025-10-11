import unittest
import requests
from unittest import mock
from urllib.parse import urlparse

from app.network_client import http_client


class NetworkClientTests(unittest.TestCase):
    def test_dead_host_cache_prevents_repeated_requests(self):
        """Verify that once a host times out we don't keep retrying it immediately."""
        test_url = "https://unreachable.example.test/contact"
        domain = urlparse(test_url).netloc

        call_counter = {"count": 0}

        def raise_timeout(*args, **kwargs):
            call_counter["count"] += 1
            raise requests.exceptions.Timeout()

        try:
            with mock.patch.object(http_client._session, "request", side_effect=raise_timeout):
                self.assertFalse(http_client.is_reachable(test_url))

            # Subsequent reachability checks should short-circuit without hitting the session
            with mock.patch.object(http_client._session, "request", side_effect=AssertionError("should not be called")):
                self.assertFalse(http_client.is_reachable(test_url))

            # We should only have attempted the underlying request once (HEAD) before caching
            self.assertEqual(call_counter["count"], 1)
        finally:
            http_client.revive_host(domain)


if __name__ == "__main__":
    unittest.main()
