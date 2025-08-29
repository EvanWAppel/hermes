import base64
import json
import os
import smtplib
import traceback
import socket
import getpass
import inspect
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
import time


def email_on_failure(
    origin: str,
    destination: str,
    markdown: Optional[os.PathLike[str] | str] = None,
    retries: int = 1,
    delay: float = 60,

) -> Callable:
    """Decorator to send an email if the wrapped function raises an exception.

    Parameters
    ----------
    origin: str
        Email address from which the notification will be sent.
    destination: str
        Email address to which the notification will be sent.
    markdown: PathLike or str, optional
        Path to a Markdown template used to format the email body. The file
        may reference ``{function}``, ``{start}``, ``{fail_time}``,
        ``{machine}``, ``{user}``, ``{error}``, and ``{traceback}``.

    retries: int, optional
        Number of times to retry ``func`` after an exception. Defaults to one
        additional attempt.
    delay: float, optional
        Seconds to wait between retries. Defaults to 60 seconds.

    """

    template = Path(markdown).read_text() if markdown else None

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start = datetime.now()

            attempts = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - network call
                    if attempts >= retries:
                        fail_time = datetime.now()
                        machine = socket.gethostname()
                        user = getpass.getuser()
                        tb = traceback.format_exc()
                        file_path = Path(inspect.getfile(func)).resolve()
                        parent_dir = file_path.parent.name
                        subject = f"{parent_dir} has failed."
                        context = {
                            "function": func.__name__,
                            "start": start.isoformat(),
                            "fail_time": fail_time.isoformat(),
                            "machine": machine,
                            "user": user,
                            "error": exc,
                            "traceback": tb,
                        }
                        if template is not None:
                            body = template.format(**context)
                        else:
                            body = (
                                f"Function {func.__name__} initiated at {start.isoformat()}\n"
                                f"Failed at {fail_time.isoformat()}\n"
                                f"Machine: {machine}\n"
                                f"User: {user}\n"
                                f"Error: {exc}\n\n"
                                f"Traceback:\n{tb}"
                            )
                        _send_mail(origin, destination, subject, body)
                        webhook = os.getenv("TEAMS_WEBHOOK")
                        if webhook:
                            _send_to_teams(webhook, subject, body)
                        jira_url = os.getenv("JIRA_URL")
                        jira_email = os.getenv("JIRA_EMAIL")
                        jira_token = os.getenv("JIRA_TOKEN")
                        jira_project = os.getenv("JIRA_PROJECT")
                        jira_type = os.getenv("JIRA_ISSUE_TYPE", "Task")
                        if all([jira_url, jira_email, jira_token, jira_project]):
                            _create_jira_ticket(
                                jira_url,
                                jira_email,
                                jira_token,
                                jira_project,
                                jira_type,
                                subject,
                                body,
                            )
                        raise
                    attempts += 1
                    time.sleep(delay)


        return wrapper

    return decorator


def _send_mail(origin: str, destination: str, subject: str, body: str) -> None:
    """Send ``body`` with ``subject`` from ``origin`` to ``destination``.

    If the environment variable ``OUTLOOK_TOKEN`` is set, the message is sent
    using the Microsoft Outlook API. Otherwise, a local SMTP server on
    ``localhost`` is used.
    """

    token = os.getenv("OUTLOOK_TOKEN")
    if token:
        _send_via_outlook(origin, destination, subject, body, token)
    else:
        _send_via_smtp(origin, destination, subject, body)


def _send_via_smtp(origin: str, destination: str, subject: str, body: str) -> None:
    message = f"Subject: {subject}\n\n{body}"
    with smtplib.SMTP("localhost") as smtp:  # pragma: no cover - network call
        smtp.sendmail(origin, destination, message)


def _send_via_outlook(
    origin: str, destination: str, subject: str, body: str, token: str
) -> None:
    payload = json.dumps(
        {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "from": {"emailAddress": {"address": origin}},
                "toRecipients": [
                    {"emailAddress": {"address": destination}}
                ],
            },
            "saveToSentItems": "false",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        data=payload,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req):  # pragma: no cover - network call
        pass


def _send_to_teams(webhook: str, subject: str, body: str) -> None:
    payload = json.dumps({"text": f"**{subject}**\n\n{body}"}).encode("utf-8")
    req = urllib.request.Request(webhook, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req):  # pragma: no cover - network call
        pass


def _create_jira_ticket(
    url: str,
    email: str,
    token: str,
    project: str,
    issue_type: str,
    summary: str,
    description: str,
) -> None:
    payload = json.dumps(
        {
            "fields": {
                "summary": summary,
                "description": description,
                "project": {"key": project},
                "issuetype": {"name": issue_type},
            }
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{url.rstrip('/')}/rest/api/3/issue", data=payload, method="POST"
    )
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req):  # pragma: no cover - network call
        pass
