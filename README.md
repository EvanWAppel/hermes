# hermes

Hermes provides a decorator that emails a notification when a wrapped function
completes, indicating success or failure.

## Usage

```python
from hermes import email_on_failure

@email_on_failure("origin@example.com", "dest@example.com")
def my_task():
    ...
```

The email includes the start and completion times, machine name and user. On
failure the error message and traceback are included, and the subject line is
"[parent directory] has failed.". On success the subject line is "[parent
directory] has succeeded.".

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

The decorator retries once after 60 seconds by default. To control retry
behavior, supply ``retries`` and ``delay`` in seconds:

```python
@email_on_failure(
    "origin@example.com", "dest@example.com", retries=3, delay=30
)
def my_task():
    ...
```

By default a local SMTP server on `localhost` is used to deliver messages. If an
Outlook token is supplied via the ``OUTLOOK_TOKEN`` environment variable, the
Microsoft Outlook API is used instead.
If a Teams webhook URL is provided via ``TEAMS_WEBHOOK``, the message is also
posted to Microsoft Teams.
When the environment variables ``JIRA_URL``, ``JIRA_EMAIL``, ``JIRA_TOKEN`` and
``JIRA_PROJECT`` are present, a Jira ticket is created with the failure details.
The issue type defaults to ``Task`` but can be changed with ``JIRA_ISSUE_TYPE``.
