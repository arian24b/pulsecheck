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

## Commit messages (Conventional Commits)
Releases are automatic, so commit messages matter. Use `<type>(<scope>): <subject>` (imperative, lowercase, no trailing dot). `git config commit.template .gitmessage` shows the list.
- `feat` → minor release, `fix` / `perf` → patch release, `BREAKING CHANGE:` in the footer (or `feat!:`) → minor while the version is 0.x, major after 1.0.
- `docs`, `test`, `ci`, `chore`, `refactor`, `style`, `build` do not release by themselves.

## Releasing to PyPI (maintainers)
The PyPI project is **`pulsecheckcli`** (the commands are `pulsecheck` and `pck`). The pipeline is `.github/workflows/publish.yml` and uses python-semantic-release plus a PyPI Trusted Publisher, so no token is stored anywhere:
1. One time on pypi.org: the publisher for project `pulsecheckcli`, owner `arian24b`, repository `pulsecheck`, workflow `publish.yml`, environment `pypi`. The `pypi` environment already exists on GitHub.
2. Merge to `main`. When CI passes, the `publish` workflow reads the commits since the last tag, bumps `version` in `pyproject.toml`, updates `CHANGELOG.md`, tags `vX.Y.Z`, creates the GitHub release, builds and uploads to PyPI. The very first run releases the version already in `pyproject.toml` (0.1.0).
3. Safety switch: automatic releases only run when the repository variable `AUTO_RELEASE` is `true` (`gh variable set AUTO_RELEASE --body true`). *Actions → publish → Run workflow* always works and can force `patch`, `minor` or `major`.
Never edit `version` or `CHANGELOG.md` by hand.

## Documentation
The guide lives in the [wiki](https://github.com/arian24b/pulsecheck/wiki). Edit the pages there; the README only links to them.

## Reporting bugs and ideas
Use the issue forms. Security problems: see [SECURITY.md](SECURITY.md).
