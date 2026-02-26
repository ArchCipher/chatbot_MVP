"""Map file path to modification time for incremental re-indexing."""

import json
import logging
from pathlib import Path

logger = logging.getLogger("FileHashManager")


class FileHashManager:
    """
    Manage file hashes saved in JSON file.
    Maps file path to mtime. Used to skip unchanged files on re-index.
    """

    def __init__(self, hash_file: Path | str) -> None:
        if not isinstance(hash_file, Path):
            hash_file = Path(hash_file)
        # store hash file path
        self.hash_file: Path = hash_file
        # create hash file parent directory if it doesn't exist
        self.hash_file.parent.mkdir(parents=True, exist_ok=True)
        # load hash file
        self.file_hashes: dict[str, float] = self.load()

    def load(self) -> dict[str, float]:
        if not self.hash_file.exists():
            return {}
        try:
            with open(self.hash_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading file hashes: {e}")
            return {}

    def save(self, hashes: dict[str, float]) -> None:
        try:
            with open(self.hash_file, "w", encoding="utf-8") as f:
                json.dump(hashes, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving file hashes: {e}")

    def update(self, file: str) -> None:
        try:
            # store file's mtime to current time in file_hashes
            self.file_hashes[file] = Path(file).stat().st_mtime
        except Exception as e:
            logger.error(f"Error updating file hash for {file}: {e}")
