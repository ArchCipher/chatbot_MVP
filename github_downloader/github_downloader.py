from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path

import requests

GITHUB_BASE_URL = "https://github.com/"

class GithubDownloader:
    """
    Downloads files from a GitHub repository.

    By default, only downloads markdown files and excludes README.md files.
    Override the config parameter to change this behavior.
    """

    DEFAULT_CONFIG = {
            "extensions": [".md"],
            "exclude_files": ["README.md"]
        }
    MAX_WORKERS = 5
    MAX_RECURSION_DEPTH = 3

    def __init__(self,
            repo_url: str,
            target_dir: Path | str,
            http_client=requests,
            token: str | None = None,
            config: dict | None = None
        ):
        # validate repo url
        if not repo_url or not repo_url.startswith(GITHUB_BASE_URL):
            raise ValueError("Invalid repo URL")
        # normalize target directory
        if not isinstance(target_dir, Path):
            target_dir = Path(target_dir)
        # initialize
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.headers = {"Authorization": f"token {token}"} if token else {}
        self.repo_url = repo_url.rstrip('/')
        self.target_dir = target_dir
        self.http_client = http_client

    def list_files(self) -> list[str]:
        """List relative paths of files to download (per config extensions/exclude)"""
        contents_url = GitHubURLTransformer._get_contents_url(self.repo_url)
        try:
            return self._fetch_files_recursive(contents_url)
        except requests.RequestException as e:
            raise RuntimeError(f"Error listing files: {e}") from e

    def _fetch_files_recursive(self, contents_url, path_prefix="", depth=0):
        """Recurse repo contents API and return list of relative file paths."""
        if depth > self.MAX_RECURSION_DEPTH:
            raise ValueError(f"Max depth reached: {self.MAX_RECURSION_DEPTH}")
        url = contents_url
        if path_prefix:
            url = f"{contents_url}/{path_prefix}"
        response = self.http_client.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return []
        files = []
        for item in data:
            name = item.get("name")
            if not name:
                continue
            rel_path = f"{path_prefix}/{name}" if path_prefix else name
            if item.get("type") == "dir":
                rec_files = self._fetch_files_recursive(contents_url, rel_path, depth + 1)
                files.extend(rec_files)
            elif self._valid_file(item):
                files.append(rel_path)
        return files

    def _valid_file(self, item):
        """Check if item is a valid file to include."""
        if item.get("type") != "file":
            return False
        name = item.get("name")
        if name in self.config["exclude_files"]:
            return False
        return any(name.endswith(ext) for ext in self.config["extensions"])

    def download_files(self, files=None):
        """
        Download files (default: list_files()) to target_dir.
        skip existing. Return status dict.
        """
        if not files:
            files = self.list_files()
        if not files:
            raise ValueError("No files to download")
        os.makedirs(self.target_dir, exist_ok=True)
        raw_url = GitHubURLTransformer._get_raw_url(self.repo_url)
        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_file = {
                executor.submit(self._download_file, raw_url, file):file
                for file in files
            }
            files_downloaded = []
            files_skipped = 0
            errors = []
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    if future.result():
                        files_downloaded.append(file)
                    else:
                        files_skipped += 1
                except Exception as e:
                    errors.append({"file": file, "error": str(e)})
        return {
            "status": "success" if not errors else "error",
            "total files": len(files),
            "skipped file count": files_skipped,
            "downloaded files": files_downloaded,
            "errors": errors
        }

    def _download_file(self, raw_url, file):
        """Download a file to target_dir/file. Return True if written"""
        path = Path(self.target_dir) / file
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return False
        url = f"{raw_url}/{file}"
        response = self.http_client.get(url, headers=self.headers)
        response.raise_for_status()
        with open(path, "w", encoding="utf-8") as f:
            f.write(response.text)
        return True

class GitHubURLTransformer:
    """Transforms GitHub web URLs to API contents URL and raw content URL."""

    GITHUB_API_BASE_URL = "https://api.github.com/repos/"
    GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/"
    BRANCH_PREFIXES = ["/tree/", "/blob/"]

    @staticmethod
    def _get_contents_url(url):
        """Convert github.com/org/repo/tree/branch to api.github.com/repos/org/repo/contents."""
        branch = GitHubURLTransformer._get_branch_from_url(url)
        url = url.replace(
            GITHUB_BASE_URL,
            GitHubURLTransformer.GITHUB_API_BASE_URL
            )
        for prefix in GitHubURLTransformer.BRANCH_PREFIXES:
            if prefix in url:
                to_remove = prefix + branch
                url = url.replace(to_remove, "/contents")
                return url.rstrip('/')
        return url.rstrip('/')

    @staticmethod
    def _get_branch_from_url(url):
        """Extract branch name"""
        for prefix in GitHubURLTransformer.BRANCH_PREFIXES:
            if prefix in url:
                branch = url.split(prefix, 1)[1]
                branch = branch.rstrip('/')
                return branch.split('/')[0]
        return 'master'

    @staticmethod
    def _get_raw_url(url):
        """Convert github.com/org/repo/tree|blob/branch to raw.githubusercontent.com/org/repo/branch."""
        url = url.replace(
            GITHUB_BASE_URL,
            GitHubURLTransformer.GITHUB_RAW_BASE_URL
            )
        if "/tree" in url or "/blob" in url:
            url = url.replace("/tree", "", 1)
            url = url.replace("/blob", "", 1)
        return url.rstrip('/')
