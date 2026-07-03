# Clean Machine Validation

Validated on macOS from a fresh local clone on 2026-07-03. This guide captures
the first-time installation path and the manual steps that still require a
human operator.

## Expected Workflow

```bash
git clone <repo-url> parakeetnest
cd parakeetnest

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,openai,yahoo,robinhood,gmail]"

cp .env.example .env
```

Edit `.env` with local credentials and paths. For mock-only local validation,
the copied `.env.example` values can stay blank.

Before live-provider diagnostics, export the `.env` values into the shell:

```bash
set -a
source .env
set +a
```

Run the local checks:

```bash
parakeetnest doctor
parakeetnest meeting "Should I buy NVDA now?" --ticker NVDA
parakeetnest daily-report --mode morning --tickers NVDA AAPL --archive
parakeetnest schedule print-plist
parakeetnest schedule install
```

If the virtualenv is not activated, prefix CLI commands with
`.venv/bin/parakeetnest`.

Run live-provider readiness checks:

```bash
parakeetnest doctor --config examples/config-real.toml
```

## Manual Steps Still Required

- Install command-line prerequisites: Git and Python 3.11 or newer.
- Ensure internet access to PyPI for `pip install`.
- Copy `.env.example` to `.env`.
- Fill real provider credentials only in `.env`.
- Create or obtain an `OPENAI_API_KEY` for live LLM runs.
- Create or obtain a `FRED_API_KEY` for live macro data.
- Set `SEC_USER_AGENT` to an identifying value, usually app name plus contact
  email.
- Configure Robinhood read-only credentials or an existing session cache if
  testing the Robinhood provider.
- Create a Google OAuth client credentials JSON file and set
  `GOOGLE_APPLICATION_CREDENTIALS` to its local path.
- Complete the Gmail OAuth flow outside ParakeetNest and set
  `PARAKEETNEST_GMAIL_TOKEN_PATH` to the authorized-user token JSON path.
- Set `PARAKEETNEST_REPORT_RECIPIENT` or pass `--email` only when intentionally
  testing report delivery output.
- Run `schedule install` from a macOS GUI login session. `launchctl bootstrap`
  can fail outside a normal user GUI session.

## Validation Results

The fresh-clone workflow succeeds for:

- Virtualenv creation.
- Editable package install with all optional provider extras.
- `.env.example` copy.
- Mock-mode doctor.
- Mock committee meeting.
- Local daily report generation and archive writing.
- LaunchAgent plist rendering.

Live-provider doctor correctly reports missing credentials until the operator
sets the required `.env` values and local credential files.

## Current First-Time User Blockers

- A brand new Mac must already have Git and Python 3.11 or newer installed.
  The project does not install those system prerequisites.
- `pip install` requires internet access to download build and runtime
  dependencies.
- Live-provider validation cannot pass until the operator manually provisions
  API keys, Robinhood credentials/session, SEC User-Agent, and Gmail OAuth
  files.
- Gmail has a provider implementation, but there is no dedicated
  `parakeetnest gmail test` command. Use `doctor --config
  examples/config-real.toml` to validate Gmail credential paths before any
  intentional provider-level send test.
- The daily report CLI `--email` option uses the console provider for local
  output capture; it does not send through Gmail by itself.
- `schedule install` depends on macOS `launchctl` and the current user GUI
  session. If bootstrap fails, fix the launchd/session issue and rerun
  `parakeetnest schedule install`.

## Gmail Smoke Test

There is no non-sending Gmail smoke test beyond doctor today. A real Gmail send
uses the existing provider and will send an email:

```bash
parakeetnest doctor --config examples/config-real.toml
```

Only after doctor reports Gmail ready, run a deliberate provider-level send
from Python if you need to verify Gmail delivery:

```bash
.venv/bin/python - <<'PY'
from parakeetnest.config import EmailConfig
from parakeetnest.email import create_email_provider_registry

recipient = "you@example.com"
provider = create_email_provider_registry().resolve(EmailConfig(provider="gmail"))
provider.send(
    subject="ParakeetNest Gmail smoke test",
    body="Gmail provider smoke test.",
    recipient=recipient,
)
print(f"Sent Gmail smoke test to {recipient}")
PY
```

Replace `you@example.com` before running. This command sends real email and
requires valid Gmail OAuth files.
