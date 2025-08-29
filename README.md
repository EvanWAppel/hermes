# hermes

Hermes provides a decorator that emails a notification when a wrapped function fails.

## Usage

```python
from hermes import email_on_failure

@email_on_failure("origin@example.com", "dest@example.com")
def my_task():
    ...
```

The email includes the start and failure times, machine name, user, error message and traceback.
The subject line is "[parent directory] has failed.".

A Markdown template can be supplied to customize the email body:

```python
@email_on_failure(
    "origin@example.com", "dest@example.com", markdown="template.md"
)
def my_task():
    ...
```

The template may reference `{function}`, `{start}`, `{fail_time}`, `{machine}`,
`{user}`, `{error}`, and `{traceback}`.

By default a local SMTP server on `localhost` is used to deliver messages. If an
Outlook token is supplied via the ``OUTLOOK_TOKEN`` environment variable, the
Microsoft Outlook API is used instead.
If a Teams webhook URL is provided via ``TEAMS_WEBHOOK``, the message is also
posted to Microsoft Teams.
When the environment variables ``JIRA_URL``, ``JIRA_EMAIL``, ``JIRA_TOKEN`` and
``JIRA_PROJECT`` are present, a Jira ticket is created with the failure details.
The issue type defaults to ``Task`` but can be changed with ``JIRA_ISSUE_TYPE``.
