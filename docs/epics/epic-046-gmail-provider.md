# Epic 046: Gmail Provider

Status: Completed

## Goal

Replace mock-only email delivery with an optional Gmail provider while preserving
the provider-neutral email and report delivery architecture.

## Scope

- Add `GmailEmailProvider` behind the existing `EmailProvider` interface.
- Keep `MockEmailProvider` as the default configured provider.
- Support daily, morning, and evening report delivery through provider-neutral
  subject, recipient, and plain-text body fields.
- Expose `EmailReportDeliveryProvider` so report delivery can use Gmail without
  importing Gmail-specific code.
- Keep Gmail credentials and OAuth token paths sourced from configured
  environment variables only.

## Configuration

Default configuration remains local and non-sending:

```python
AppConfig(email={"provider": "mock"})
```

Gmail is opt-in:

```python
AppConfig(
    email={
        "provider": "gmail",
        "gmail_credentials_path_env_var": "GOOGLE_APPLICATION_CREDENTIALS",
        "gmail_token_path_env_var": "PARAKEETNEST_GMAIL_TOKEN_PATH",
        "sender_email": "sender@example.com",
    }
)
```

The configured environment variables must point to local credential and token
files. The provider uses the Gmail send-only scope:
`https://www.googleapis.com/auth/gmail.send`.

## Boundaries

- Committee, research, and report composition logic do not import Gmail code.
- Gmail is reached only through the email provider abstraction or the
  provider-neutral report delivery adapter.
- Unit tests use fake Gmail clients only.
- Inbox reading, Gmail search, drafts, attachments, calendar features,
  autonomous sending decisions, and investment judgment changes are out of
  scope.

## Failure Behavior

- Missing credential environment variable or path raises a configuration error.
- Missing token environment variable or path raises a configuration error.
- Invalid recipient, empty subject, and empty body are rejected before a Gmail
  call is attempted.
- Gmail API failures are normalized as `GmailDeliveryError`; report delivery
  converts them into failed `ReportDeliveryResult` values.
