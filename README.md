# Chatbot MVP

## Overview
MVP chatbot with RAG (Retrieval-Augmented Generation) capabilities that handles client requests using FastAPI and Uvicorn server.

## Requirements

- Python: Version 3.10 - 3.12
- Dependencies: Check [requirements.txt](./requirements.txt)

## Installation
Make sure you create a virtual environment, activate it, and then install all dependencies mentioned in `requirements.txt`

```sh
python -m venv .venv    # create venv
source .venv/bin/activate   # activate venv

pip install -r requirements.txt # install dependencies
```

## Configuration:

Create `.env` file with variables mentioned in [.env.example](./.env.example)

## Run
As uvicorn runs async with the current code:
`python chatbot.py`

To run the server non async:
`fastapi dev chatbot.py`
or
`uvicorn chatbot:app --reload`

## Architecture

RAG (Retrieval-Augmented Generation)

**Indexing Phase (One-time setup):**
Documents -> Chunks -> Embeddings + Indexing (VectorDB: ChromaDB)

**Query Phase (Per request):**
User Query -> Embed Query -> Search Vector DB -> Retrieve top X Chunks -> Build prompt (retrieved chunks + user query) -> LLM -> Response

**Components:**
- **Chunking**: [langchain_text_splitters.RecursiveCharacterTextSplitter](https://docs.langchain.com/oss/python/integrations/splitters) (configurable via CHUNK_SIZE, CHUNK_OVERLAP)
- **Vector Database**: [chromadb](https://github.com/chroma-core/chroma) (embedding and indexing)
- **LLM**: [google-genai](https://github.com/googleapis/python-genai) (Gemini 2.5 Flash)

**Note:** 

Indexing can be done via the /index_docs API endpoint or on server startup. Re-indexing is necessary when adding more documents to the context.

ChromaDB automatically handles tokenization, embedding, and indexing when documents are added via `collection.add()`.

## Future improvement:
- **Persistence**: Use persistent data storage across restarts instead of in-memory storage:
  `chroma_client = chromadb.PersistentClient(path="./chroma_db")`
- **Folder support**: Enhance `add_docs_to_chroma` to accept folder paths in addition to file lists
- **Production vector DB**: Consider Qdrant, or other vector DBs for production deployment
- **Metadata filtering**: Use ChromaDB's `where` clause to filter by source, date, or other metadata
- **Better error handling**: Add logging and retry logic for API calls

## API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### GET /

Health check endpoint.

**Response:**
```json
{
  "message": "Hello World"
}
```

### POST /chat

Send a message to the chatbot.

**Request:**
```json
{
  "message": "I want to consult",
  "session_id": 1
}
```

**Response:**
```json
{
  "reply": "Hi! Are you looking to buy electricity or sell electricity?"
}
```

**Request schema:**
  `message` (string) – user's message.
  `session_id` (integer) – session identifier for conversation tracking.

**Response schema:**
  `reply` (string) – bot's response message generated using RAG.

### POST /index_docs

Index docs without restarting the server

**Request:**
```json
{
  "files": ["docs/example.md"]
}
```

**Response:**
```json
{
  "message": "",
  "files_indexed": ["docs/example.md", "docs/notes.md"],
  "errors": []
}
```

**Request schema:**
  `files` (array of strings) – list of file paths to index.

**Response schema:**
  `message` (string) – status message.
  `files_indexed` (array of strings) – successfully indexed files.
  `errors` (array of strings) – any errors encountered.

## Testing

1. Start the server using `python chatbot.py`

2. In another terminal, test the health endpoint:
```bash
./curl_scripts/test_health.sh
```

3. Index documents:
```bash
./curl_scripts/index_files.sh
```

4. Test a conversation:
```bash
./curl_scripts/test_chatbot.sh
```
or manually:
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your name?", "session_id": 1}'
```

modify and run [test_chatbot.sh](./curl_scripts/test_chatbot.sh)


## Files Reference
- Main implementation: [chatbot.py](./chatbot.py) – Fast API app and RAG logi
- ChromaDB client implementation: [chroma.py](./chroma.py) – Vector database operations
- Configuration: [requirements.txt](./requirements.txt), [.env.example](./.env.example)
- Curl scripts: [curl_scripts/](./curl_scripts/)
  - [test_health.sh](./curl_scripts/test_health.sh) – Test GET / endpoint
  - [test_chatbot.sh](./curl_scripts/test_chatbot.sh) - Test POST /chat endpoint
  - [index_files.sh](./curl_scripts/index_files.sh) - Index documents via POST /index_docs endpoint