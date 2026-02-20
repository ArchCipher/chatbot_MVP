import os
import logging

logger = logging.getLogger("reload_db")

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from chroma import RagClient

# instantiate RagClient
rag_client = RagClient(
        name=os.getenv("COLLECTION_NAME", "my-collection"),
        persistent_storage=os.getenv("PERSISTENT_STORAGE", "./chroma_db"),
        collection_path=os.getenv("COLLECTION_PATH", "source_docs"),
        hash_filename=os.getenv("HASH_FILE", "file_hashes.json")
    )

def main():
    logging.basicConfig(
        filename='chatbot.log',
        level=logging.INFO,
        format= '[%(asctime)s][%(levelname)s][%(name)s][%(message)s]'
        )
    # Reload documents
    response = rag_client.reload_collection()
    status = response["status"]
    log = f"Documents reloaded: status: {status}, {len(response['files indexed'])} Files indexed: {response['files indexed']}, Errors: {response['errors']}"
    if status == "error":
        logger.error(log)
    else:
        logger.info(log)

if __name__ == "__main__":
    main()
