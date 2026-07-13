# macOS Scheduling

ParakeetNest can install a local macOS LaunchAgent that runs the existing daily
runtime script once per day. This is local runtime tooling only: it does not add
cloud scheduling, automatic trading, direct scheduler email delivery, or new
investment logic.

## Default Schedule

The default schedule is daily at 7:30 AM local time.

The generated LaunchAgent runs:

```sh
scripts/run_parakeetnest_daily.sh
```

The script loads `.env` from the repository root if present, then invokes the
existing daily report CLI. The scheduler passes the selected report mode to the
script explicitly:

```sh
scripts/run_parakeetnest_daily.sh --mode morning
```

Secrets are not written into the LaunchAgent plist.

To make the scheduled report use your Robinhood holdings as the default ticker
coverage, configure the local `.env` file rather than the plist:

```sh
PARAKEETNEST_PORTFOLIO_PROVIDER=robinhood
PARAKEETNEST_PORTFOLIO_ACCOUNT_ID=default
PARAKEETNEST_ROBINHOOD_USERNAME=...
PARAKEETNEST_ROBINHOOD_PASSWORD=...
```

You can also use `PARAKEETNEST_ROBINHOOD_SESSION_TOKEN` or
`PARAKEETNEST_ROBINHOOD_SESSION_CACHE_PATH` instead of username/password when
available.

To email the generated report, configure the existing email provider and default
recipient in `.env`:

```sh
GOOGLE_APPLICATION_CREDENTIALS=secrets/gmail-client-secret.json
PARAKEETNEST_GMAIL_TOKEN_PATH=.gmail-token/token.json
PARAKEETNEST_REPORT_RECIPIENT=you@example.com
```

The scheduler still does not send email directly; it launches the runtime script,
and the daily report CLI delegates delivery to ParakeetNest's configured email
provider.

## Commands

Preview the LaunchAgent plist:

```sh
parakeetnest schedule print-plist
```

Install the LaunchAgent:

```sh
parakeetnest schedule install
```

Show launchd status:

```sh
parakeetnest schedule status
```

Uninstall the LaunchAgent:

```sh
parakeetnest schedule uninstall
```

## Custom Time

Use `--hour` and `--minute` with `install` or `print-plist`:

```sh
parakeetnest schedule install --hour 8 --minute 15
```

The schedule uses local macOS time.

Use `--mode morning` or `--mode evening` to select the report type. For example,
install an evening report at 6:30 PM local time with:

```sh
parakeetnest schedule install --mode evening --hour 18 --minute 30
```

The runtime script also accepts the mode directly for manual validation:

```sh
scripts/run_parakeetnest_daily.sh --mode evening
```

`schedule install` must run from a macOS GUI login session where `launchctl`
can bootstrap a user LaunchAgent. If `launchctl bootstrap` fails, fix the local
launchd/session issue and rerun the install command.

## Files

The installed plist path is:

```text
~/Library/LaunchAgents/com.parakeetnest.daily.plist
```

The plist uses absolute paths for the runtime script, working directory, and log
files. Runtime logs are written under:

```text
logs/parakeetnest-daily.out.log
logs/parakeetnest-daily.err.log
```
