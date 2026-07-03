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
python -m parakeetnest schedule print-plist
```

Install the LaunchAgent:

```sh
python -m parakeetnest schedule install
```

Show launchd status:

```sh
python -m parakeetnest schedule status
```

Uninstall the LaunchAgent:

```sh
python -m parakeetnest schedule uninstall
```

## Custom Time

Use `--hour` and `--minute` with `install` or `print-plist`:

```sh
python -m parakeetnest schedule install --hour 8 --minute 15
```

The schedule uses local macOS time.

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
