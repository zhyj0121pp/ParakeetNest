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
existing daily report CLI:

```sh
python -m parakeetnest.cli.daily_report --mode morning --archive
```

Secrets are not written into the LaunchAgent plist.

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
