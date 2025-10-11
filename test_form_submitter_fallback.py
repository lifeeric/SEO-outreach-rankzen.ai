import unittest
from unittest import mock
from urllib.parse import urlparse

from app.form_submitter import FormSubmitter
from app.models import BusinessSite, OutreachMessage


def make_site_with_email(url: str, email: str) -> BusinessSite:
    parsed = urlparse(url)
    site = BusinessSite(url=url, domain=parsed.netloc)
    site.email = email
    return site


class FormSubmitterFallbackTests(unittest.TestCase):
    def test_email_fallback_returns_submission_object(self):
        submitter = FormSubmitter()
        site = make_site_with_email("https://example.com", "owner@example.com")
        message = OutreachMessage(subject="Test", message="Hello")

        with (
            mock.patch.object(submitter, "_fallback_to_email", wraps=submitter._fallback_to_email) as fallback_spy,
            mock.patch("app.form_submitter.http_client.is_reachable", return_value=False),
            mock.patch("app.form_submitter.data_manager.add_log_entry"),
        ):
            contact_form = submitter.submit_contact_form(site, message)

        fallback_spy.assert_called()
        self.assertIn(contact_form.submission_method, {"email", "none"})
        self.assertIn(contact_form.email_used, {"owner@example.com", None})

    def test_fallback_sends_email_when_available(self):
        submitter = FormSubmitter()
        site = make_site_with_email("https://example.com", "owner@example.com")
        message = OutreachMessage(subject="Test", message="Hello")

        with (
            mock.patch("app.form_submitter.email_sender.send_outreach_email", return_value=True) as email_mock,
            mock.patch("app.form_submitter.data_manager.add_log_entry") as log_mock,
        ):
            contact_form = submitter._fallback_to_email(site, message, reason="no_contact_form")

        email_mock.assert_called_once()
        self.assertEqual(contact_form.submission_method, "email")
        self.assertTrue(contact_form.submitted)
        self.assertEqual(contact_form.email_used, "owner@example.com")
        log_mock.assert_called()


if __name__ == "__main__":
    unittest.main()
