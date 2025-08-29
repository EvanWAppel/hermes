from unittest.mock import patch
import os
import pytest
import sys
from pathlib import Path

# Ensure package root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hermes import email_on_failure


def test_email_sent_on_failure():
    @email_on_failure("from@example.com", "to@example.com")
    def explode():
        raise RuntimeError("boom")

    with patch("hermes.notify.smtplib.SMTP") as smtp, patch(
        "hermes.notify.time.sleep"
    ):
        with pytest.raises(RuntimeError):
            explode()
        smtp.assert_called_with("localhost")
        smtp.return_value.__enter__.return_value.sendmail.assert_called_once()


def test_email_sent_on_success():
    @email_on_failure("from@example.com", "to@example.com")
    def succeed():
        return "ok"

    with patch("hermes.notify._send_mail") as send_mail:
        assert succeed() == "ok"
        send_mail.assert_called_once()


def test_outlook_api_used_when_token_present():
    @email_on_failure("from@example.com", "to@example.com")
    def explode():
        raise RuntimeError("boom")

    with patch.dict(os.environ, {"OUTLOOK_TOKEN": "token"}, clear=True):
        with patch("hermes.notify.urllib.request.urlopen") as urlopen, patch(
            "hermes.notify.smtplib.SMTP"
        ) as smtp, patch("hermes.notify.time.sleep"):
            urlopen.return_value.__enter__.return_value.read.return_value = b""
            with pytest.raises(RuntimeError):
                explode()
            urlopen.assert_called_once()
            smtp.assert_not_called()


def test_markdown_template_used(tmp_path):
    template = tmp_path / "body.md"
    template.write_text("Start: {start}\nError: {error}\n")

    @email_on_failure(
        "from@example.com", "to@example.com", markdown=template
    )
    def explode():
        raise RuntimeError("boom")

    with patch("hermes.notify._send_mail") as send_mail, patch(
        "hermes.notify.time.sleep"
    ):
        with pytest.raises(RuntimeError):
            explode()
        body = send_mail.call_args[0][3]
        assert "Start:" in body
        assert "Error: boom" in body


def test_teams_notification_when_webhook_present():
    @email_on_failure("from@example.com", "to@example.com")
    def explode():
        raise RuntimeError("boom")

    with patch.dict(
        os.environ, {"TEAMS_WEBHOOK": "https://example.com/webhook"}, clear=True
    ):
        with patch("hermes.notify.urllib.request.urlopen") as urlopen, patch(
            "hermes.notify.smtplib.SMTP"
        ) as smtp, patch("hermes.notify.time.sleep"):
            urlopen.return_value.__enter__.return_value.read.return_value = b""
            with pytest.raises(RuntimeError):
                explode()
            urlopen.assert_called_once()
            smtp.assert_called_with("localhost")


def test_teams_notification_on_success():
    @email_on_failure("from@example.com", "to@example.com")
    def succeed():
        return "ok"

    with patch.dict(
        os.environ, {"TEAMS_WEBHOOK": "https://example.com/webhook"}, clear=True
    ):
        with patch("hermes.notify._send_mail"), patch(
            "hermes.notify.urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b""
            assert succeed() == "ok"
            urlopen.assert_called_once()


def test_jira_ticket_when_configured():
    @email_on_failure("from@example.com", "to@example.com")
    def explode():
        raise RuntimeError("boom")

    env = {
        "JIRA_URL": "https://example.atlassian.net",
        "JIRA_EMAIL": "user@example.com",
        "JIRA_TOKEN": "token",
        "JIRA_PROJECT": "PROJ",
    }

    with patch.dict(os.environ, env, clear=True):
        with patch("hermes.notify.urllib.request.urlopen") as urlopen, patch(
            "hermes.notify.smtplib.SMTP"
        ) as smtp, patch("hermes.notify.time.sleep"):
            urlopen.return_value.__enter__.return_value.read.return_value = b""
            with pytest.raises(RuntimeError):
                explode()
            urlopen.assert_called_once()
            smtp.assert_called_with("localhost")


def test_retry_succeeds_sends_email():
    calls = {"count": 0}

    @email_on_failure("from@example.com", "to@example.com", retries=1, delay=1)
    def sometimes():
        calls["count"] += 1
        if calls["count"] < 2:
            raise RuntimeError("boom")
        return "ok"

    with patch("hermes.notify._send_mail") as send_mail, patch(
        "hermes.notify.time.sleep"
    ) as sleep:
        assert sometimes() == "ok"
        assert calls["count"] == 2
        send_mail.assert_called_once()
        sleep.assert_called_once_with(1)


def test_retry_exhausted_sends_email():
    @email_on_failure("from@example.com", "to@example.com", retries=2, delay=5)
    def explode():
        raise RuntimeError("boom")

    with patch("hermes.notify._send_mail") as send_mail, patch(
        "hermes.notify.time.sleep"
    ) as sleep:
        with pytest.raises(RuntimeError):
            explode()
        assert sleep.call_count == 2
        send_mail.assert_called_once()
