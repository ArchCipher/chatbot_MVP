# Chatbot MVP

## About

Personal project: RAG chatbot to explore document Q&A and retrieval. I'm developing it toward secure-coding use (e.g. querying coding standards and eventually checking code for security issues). The current MVP ingests PDFs and markdown and answers from those documents.

## Overview

Lets you ask questions over your own documents and get answers grounded in them. For structured rule sets (e.g. coding standards), it can prioritize the relevant rule when you ask by name (e.g. "What is PRE30-C?"). Built with FastAPI and ChromaDB.

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

## Configuration

- Create `.env` file with variables mentioned in [.env.example](./.env.example)

- Use a folder named `source_docs` for your documents, or set the `COLLECTION_PATH` env variable to your folder path. To fetch docs from GitHub into source_docs, see [github_downloader/README.md](./github_downloader/README.md).

**Note:** The chatbot accepts any markdown/pdf documents you provide. PDFs are automatically converted to markdown during indexing. The `source_docs` folder is not included in this repository—you must add your own documents.

- The vectordb uses persistent storage (default `./chroma_db`). Override with `PERSISTENT_STORAGE` in `.env` (see [.env.example](./.env.example)).

- File modification times are stored in a JSON file there (default `file_hashes.json`, override `HASH_FILE`) for incremental re-indexing. Format: [sample_file_hashes.json](docs/sample_file_hashes.json).

- Logging goes to standard output by default. Set `LOG_FILE` in `.env` (e.g. `LOG_FILE=chatbot.log`) to write logs to a file.

## Run

To run programmatically:
`python chatbot.py`

To run via CLI (non-programmatically):
`fastapi dev chatbot.py`
or
`uvicorn chatbot:app --reload`

## Architecture

RAG (Retrieval-Augmented Generation)

**Indexing Phase (One-time setup):**
Documents -> Chunks -> Embeddings + Indexing (VectorDB: ChromaDB)

**Query Phase (Per request):**
User Query -> Embed Query -> Search Vector DB -> Retrieve top X Chunks -> Build prompt (retrieved chunks + user query) -> LLM -> Response

```mermaid
flowchart LR
  subgraph Indexing["Indexing"]
    D[Documents] --> C[Chunks]
    C --> E[Embed]
    E --> V[(ChromaDB)]
  end
  subgraph Query["Query"]
    Q[User Query] --> EQ[Embed Query]
    EQ --> R[Retrieve]
    R --> CTX[Build Context]
    CTX --> LLM[LLM]
    LLM --> RES[Response]
  end
  V -.-> R
```

**Components:**
- **Chunking**:
  1. Header-based splitting: Regex-based splitting on chapter-level markdown headers (`## \*\*\d+ `) to preserve semantic boundaries
  2. Recursive character splitting: [langchain_text_splitters.RecursiveCharacterTextSplitter](https://docs.langchain.com/oss/python/integrations/splitters) for further chunking if sections exceed chunk_size (configurable via `CHUNK_SIZE`, `CHUNK_OVERLAP`)
- **Vector Database**: [chromadb](https://github.com/chroma-core/chroma) (embedding and indexing)
- **LLM**: [google-genai](https://github.com/googleapis/python-genai) (Gemini 2.5 Flash)

**Note:**

Docs are loaded from the collection folder at server startup (default `source_docs`, overridable via `COLLECTION_PATH`). Reload when you update docs.

ChromaDB automatically handles tokenization, embedding, and indexing when documents are added via `collection.add()`.

## Sample retrieval

For a rule-specific query, the retrieval pipeline prepends the matching rule chunk (distance 0.0) then fills the rest with semantic search. The example below uses coding-standard documents (e.g. CERT C/C++ rules); you add your own in `source_docs`. Example for "What is PRE30-C?" with `N_RESULTS=5`:

| Step            | Result |
|-----------------|--------|
| Rule boost      | 1 chunk (PRE30-C definition) |
| Semantic search | Top 4 additional chunks (after dedup) |
| Total returned  | 5 chunks; first chunk = PRE30-C (distance 0.0) |

Example `query_summary` (concise): `distances: [0.0, 1.28, 1.33, ...], rules_found_in_chunks: ["PRE30-C"]`. See [sample retrieval output](docs/sample_retrieval_output.md) for a short sanitized log excerpt. The sample uses [SEI CERT C and C++ Coding Standards](https://www.sei.cmu.edu/library/sei-cert-c-and-c-coding-standards/)(2016 editions)

## Future improvement

### Core Stability
- **Distance-based filtering**: Use the distance returned by get_query_results in get_context (e.g. only include chunks with distance below a threshold, or within a narrow range)
- **Better error handling:** Add logging and retry logic for API calls

### Code Analysis (Core Value)
- **Code input endpoint**: Add `/analyze_code` endpoint for semantic code → rule retrieval (no AST parsing needed)
- **42 Integration**: Test against personal C projects and document security findings
- **Security report generation**: CLI tool to scan code and output markdown security reports

### Future (When Needed)
- **Metadata filtering**: Extend filtering using ChromaDB's `where` clause for source, date, or other metadata
- **Document automation**: Automate document updates and indexing (e.g., watch for new PDF releases)
- **Production optimizations**: Vector DB migration, performance improvements (only when real users exist)

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
  "message": "What is PRE30-C?",
  "session_id": 1
}
```

**Response:**
```json
{
  "reply": "Based on the provided context, \"-C\" in \"PRE30-C\" indicates that it pertains to the C programming language. While the specific meaning of \"PRE30\" is not detailed, the document discusses coding standards, guidelines, and noncompliant code examples, suggesting that \"PRE30-C\" is likely a specific guideline or rule within a C coding standard."
}
```

**Request schema:**
  `message` (string) – user's message.
  `session_id` (integer) – session identifier for conversation tracking.

**Response schema:**
  `reply` (string) – bot's response message generated using RAG.

## Testing

1. Start the server using `python chatbot.py`

2. In another terminal, test the health endpoint:
```bash
./curl_scripts/test_health.sh
```

3. Test a conversation:
```bash
./curl_scripts/test_chatbot.sh
```

or run multiple tests:
```bash
./curl_scripts/tests.sh
```

or manually:
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is PRE30-C?", "session_id": 1}'
```

## Formatting

Format code with [Black](https://github.com/psf/black) (install via `pip install -r requirements.txt`):

```bash
make fmt
```

Check only (no write): `black --check .`

## File structure

chatbot/
├── README.md
├── requirements.txt
├── .env.example
├── chatbot.py
│
├── chroma/
│   ├── __init__.py
│   ├── chroma.py
│   ├── indexer.py
│   ├── retriever.py
│   ├── hash_manager.py
│   └── text_splitter.py
│
├── github_downloader/
│   ├── __init__.py
│   ├── __main__.py
│   ├── github_downloader.py
│   └── README.md
│
├── scripts/
│   ├── __init__.py
│   ├── reload_db.py
│   └── remove_db_files.py
│
├── curl_scripts/
│   ├── test_health.sh
│   ├── test_chatbot.sh
│   └── tests.sh
│
└── docs/
    ├── sample_retrieval_output.md
    └── sample_file_hashes.json

## Files Reference

- Main implementation: [chatbot.py](chatbot.py) – FastAPI app. RAG and vector DB in the [chroma/](chroma/) package
- Configuration: [requirements.txt](requirements.txt), [.env.example](.env.example)
- Packages
  - [chroma/](chroma/) - ChromaDB client implementation with vector database operations
  - [github_downloader/](github_downloader/) - see [github_downloader/README.md](./github_downloader/README.md)
- Scripts: [scripts/](scripts/)
  - [reload_db.py](scripts/reload_db.py) - script to reload Chroma collection. Run using `python -m scripts.reload_db`
  - [remove_db_files.py](scripts/remove_db_files.py) - script to remove file from Chroma collection. Run using `python -m scripts.remove_db_files`
- Curl scripts: [curl_scripts/](curl_scripts/)
  - [test_health.sh](curl_scripts/test_health.sh) – Test GET / endpoint
  - [test_chatbot.sh](curl_scripts/test_chatbot.sh) - Test POST /chat endpoint
  - [tests.sh](curl_scripts/tests.sh) - Multiple tests POST /chat endpoint
