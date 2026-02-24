"""
Download markdown (and other) files from GitHub repo trees.
Run via python -m github_downloader.
"""

from .github_downloader import GithubDownloader

__all__ = ["GithubDownloader"]