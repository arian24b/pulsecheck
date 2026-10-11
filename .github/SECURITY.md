# Security policy

## Reporting a vulnerability
Please **do not open a public issue**. Use GitHub's private reporting: **Security → Report a vulnerability** on this repository. You will get an answer within a few days.

Include what you found, how to reproduce it, and which version or commit you used.

## What counts
pulsecheck holds alert tokens and calls URLs you configure, so the interesting problems are:
- leaking tokens or config values (logs, error messages, the `/api/status` or `/status` endpoints),
- bypassing the `CRON_SECRET` / `STATUS_TOKEN` checks,
- command or URL injection through the config or a check result,
- the installer or CI templates running something you did not expect.

## Supported versions
Only the latest release (or `main`) receives fixes.

## Keeping your own deployment safe
- Keep the repository that holds **your** `pulsecheck.yml` private (it lists your hostnames). The public template repository should never contain your config.
- Keep tokens in `${ENV_VAR}` / CI secrets / platform secrets, never in the file.
- Use a long random `CRON_SECRET` and `STATUS_TOKEN`.
