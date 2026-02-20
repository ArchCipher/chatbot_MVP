# GithubDownloader

Downloads markdown from GitHub repo URLs into a target directory (default `source_docs`). Used to fetch docs from GitHub for the chatbot.

Note:

Unlike `git clone`, it downloads only matching files (e.g. `.md` only, excluding `README.md`) — no full repo or history.
With Git you can do something similar using sparse checkout, but that is path-based, not filter-by-extension or exclude-by-filename like this tool.

Git alternative (path-based):
```sh
git clone --filter=blob:none --sparse <repo_url>
cd <repo>
git sparse-checkout set <path_in_repo>
```

## Requirements

- Python 3.10+
- Dependencies: `requests`. Check [requirements.txt](../requirements.txt)

## Run

Make sure you create a virtual environment, activate it, then from repo root:

```sh
python -m github_downloader
```

## Configuration

- **Env:** `GITHUB_TOKEN` (recommended for rate limits), `COLLECTION_PATH` (default `source_docs`).
- **Constructor:** `config` (see class docstring).

## Future improvements:

- Add CLI arguments instead of hardcoded repo URLs. But there is a need to add a parser to split input or have one repo per run.

---

## Issues and Learnings

- URLs for listing directory contents (API) and for file contents (raw) are different.
- GitHub API is rate limited; use a `GITHUB_TOKEN` for higher limits.

**Config:** Extensions (e.g. `.md`) and exclude patterns (e.g. `README.md`) are already constructor args; could be driven by env later if you want different defaults.

---
