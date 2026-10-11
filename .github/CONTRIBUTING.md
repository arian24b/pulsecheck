# Contributing

Thanks for helping. Small, focused pull requests are easiest to review.

## Set up
```bash
git clone https://github.com/arian24b/pulsecheck && cd pulsecheck
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```
Python 3.12 to 3.15 are supported (3.15 preferred).

## Rules of thumb
- Keep it small. The standard library first; a new dependency needs a good reason. The Cloudflare Worker must stay free of third-party packages.
- Anything with logic gets a test in `tests/`. The engine takes its I/O as arguments, so most things can be tested without a network.
- Changing behaviour or config? Update the wiki page too (English and Persian) and mention it in the pull request.
- Do not add checks that need platform features the serverless modes lack without making them skip cleanly (see the Serverless wiki page).

## Releasing to PyPI (maintainers)
Publishing uses a PyPI **Trusted Publisher** (OpenID Connect), so no API token is stored anywhere.
1. One time on pypi.org: *Your account → Publishing → Add a pending publisher*: project `pulsecheck`, owner `arian24b`, repository `pulsecheck`, workflow `publish.yml`, environment `pypi`. The `pypi` environment already exists on GitHub (optionally add required reviewers).
2. Bump `version` in `pyproject.toml` and merge it.
3. Create a GitHub release with the tag `v<version>` (for example `v0.1.0`). The `publish` workflow builds, checks that the tag matches the version, and uploads. `workflow_dispatch` only builds and runs `twine check`.

## Documentation
The guide lives in the [wiki](https://github.com/arian24b/pulsecheck/wiki). Edit the pages there; the README only links to them.

## Reporting bugs and ideas
Use the issue forms. Security problems: see [SECURITY.md](SECURITY.md).
