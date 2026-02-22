"""
Download markdown (and other) files from GitHub repo trees.
Run via python -m github_downloader.
"""

from .github_downloader import GithubDownloader

urls = [
    {"name": "ASVS", "url": "https://github.com/OWASP/ASVS/tree/master/5.0/en/"},
    {
        "name": "Top10",
        "url": "https://github.com/OWASP/Top10/blob/master/2025/docs/en/",
    },
    {
        "name": "Proactive_Controls",
        "url": "https://github.com/OWASP/www-project-proactive-controls/tree/master/docs/the-top-10",
    },
    {
        "name": "Cheatsheets",
        "url": "https://github.com/OWASP/CheatSheetSeries/tree/master/cheatsheets",
    },
    {
        "name": "Testing_Framework",
        "url": "https://github.com/OWASP/wstg/tree/master/document/3-The_OWASP_Testing_Framework",
    },
    {
        "name": "Web_Application_Security_Testing",
        "url": "https://github.com/OWASP/wstg/tree/master/document/4-Web_Application_Security_Testing",
    },
]
