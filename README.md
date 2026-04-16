# cronwrap

A CLI wrapper that adds logging, alerting, and retry logic to any cron job.

## Installation

```bash
pip install cronwrap
```

## Usage

Wrap any command by passing it to `cronwrap`:

```bash
cronwrap --retries 3 --alert email@example.com -- /path/to/your/script.sh
```

### Options

| Flag | Description |
|------|-------------|
| `--retries N` | Retry the command up to N times on failure |
| `--alert EMAIL` | Send an alert email if the command fails |
| `--log FILE` | Write output to a log file |
| `--timeout SEC` | Kill the command after SEC seconds |

### Example crontab entry

```
0 2 * * * cronwrap --retries 3 --log /var/log/backup.log --alert ops@example.com -- /opt/scripts/backup.sh
```

### Example log output

```
[2024-01-15 02:00:01] INFO  Starting: /opt/scripts/backup.sh
[2024-01-15 02:00:01] INFO  Attempt 1 of 3
[2024-01-15 02:00:45] INFO  Command exited with code 0
[2024-01-15 02:00:45] INFO  Duration: 44s
```

## Why cronwrap?

Plain cron jobs fail silently. `cronwrap` ensures you always know when something goes wrong, with automatic retries to handle transient failures and structured logs for easy debugging.

## Contributing

Pull requests are welcome. Please open an issue first to discuss any major changes.

## License

MIT © 2024