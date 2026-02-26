import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from github_downloader import GithubDownloader

# Constants
PKG_NAME = "github_downloader"
DEFAULT_COLLECTION_PATH = "source_docs"
URLS_FILE = "urls.json"

# Logger
logger = logging.getLogger(PKG_NAME)


def main() -> None:
    """
    Download each repo from urls into COLLECTION_PATH/<name>
    Log to github_downloader.log.
    """
    load_dotenv()
    downloader_root = Path(__file__).parent
    logfile = downloader_root / f"{PKG_NAME}.log"
    logging.basicConfig(
        filename=logfile,
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s][%(name)s][%(message)s]",
    )
    project_root = Path(__file__).parent.parent
    name = os.getenv("COLLECTION_PATH", DEFAULT_COLLECTION_PATH)
    basedir = Path(project_root / name).resolve()
    token = os.getenv("GITHUB_TOKEN")
    try:
        with open(downloader_root / URLS_FILE, "r") as f:
            urls = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading {URLS_FILE}: {e}")
        return
    if not isinstance(urls, list):
        logger.error(f"{URLS_FILE} is not a list")
        return
    for item in urls:
        if not isinstance(item, dict) or "name" not in item or "url" not in item:
            logger.error(f"{URLS_FILE} item is not a dict with name and url")
            break
        target_dir = basedir / item["name"]
        downloader = GithubDownloader(item["url"], target_dir, token=token)
        result = downloader.download_files()
        if result["errors"]:
            logger.error(result)
            break
        logger.info(f"{result['total_files']} files downloaded successfully")


if __name__ == "__main__":
    main()
