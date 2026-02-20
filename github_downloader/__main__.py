from dotenv import load_dotenv
import logging
import os
from pathlib import Path

from . import GithubDownloader, urls

logger = logging.getLogger("github_downloader")

def main():
    load_dotenv()
    downloader_root = Path(__file__).parent
    filename = downloader_root / "github_downloader.log"
    logging.basicConfig(
        filename=filename,
        level=logging.INFO,
        format= '[%(asctime)s][%(levelname)s][%(name)s][%(message)s]'
        )
    project_root = Path(__file__).parent.parent
    name = os.getenv("COLLECTION_PATH", "source_docs")
    basedir = Path(project_root / name).resolve()
    token = os.getenv("GITHUB_TOKEN")
    for item in urls:
        target_dir = basedir / item["name"]
        downloader = GithubDownloader(item["url"], target_dir, token=token)
        # files = downloader.list_files()
        # logger.info(f"Number of files: {len(files)}")
        # result = downloader.download_files(files=files)
        result = downloader.download_files()
        if result["status"] == "error":
            logger.error(result)
        else:
            logger.info(result)

if __name__ == "__main__":
    main()