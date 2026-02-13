'''
FastAPI client for RAG chatbot

- FastApi: Python web framework to build APIs
- Uvicorn: ASGI server used to run the FastAPI app
- Pydantic: data validation library for Python
- dotenv/ os: load environment variables from .env file
- google-genai: Google GenAI API client
- chromadb: ChromaDB client
- chroma.py: ChromaDB client implementation
'''

import asyncio

import uvicorn
from fastapi import FastAPI

from pydantic import BaseModel

from dotenv import load_dotenv
import os
load_dotenv()  # Load .env before importing chroma (which uses env vars)

from google import genai

from chroma import collection, add_docs_to_chroma

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# HTTP methods fot RESTful API

# API endpoint to health check
@app.get("/")
def root():
    return {"message": "Hello World"}

class ChatRequest(BaseModel):
    session_id: int
    message: str

class ChatResponse(BaseModel):
    reply: str

class IndexDocsRequest(BaseModel):
    files: list[str]

class IndexDocsResponse(BaseModel):
    message: str
    files_indexed: list[str] = []
    errors: list[str] = []

def ai_llm(message, context):
    # query chroma for context
    results = collection.query(
        query_texts=[message],
        n_results=int(os.getenv("N_RESULTS", 5)),
    )
    # build context
    context_chunks = results.get("documents", [[]])[0] if results.get("documents") else []
    context_text = "\n\n".join(context_chunks) if context_chunks else ""
    # build prompt
    prompt = f"""You are a helpful assistant. Use the following context to answer the user's question
    Context: {context_text}
    Question: {message}
    Answer:"""
    response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents={'text': prompt},
    config={
        'temperature': 0, # how random the response is
        'top_p': 0.95, # probability of selecting the next token
        'top_k': 20, # number of tokens to consider for the next token
    },
)
    return response.text

# API endpoint to chat with the bot
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = ai_llm(req.message, req.session_id)
    return ChatResponse(reply=reply)

# API endpoint to add/update documents without restarting server
@app.post("/index_docs", response_model=IndexDocsResponse)
def index_docs(req: IndexDocsRequest):
    try:
        add_docs_to_chroma(req.files)
        return IndexDocsResponse(
            message="Documents indexed successfully",
            files_indexed=req.files
        )
    except Exception as e:
        return IndexDocsResponse(
            message=f"Error indexing documents: {e}",
            errors=[str(e)]
        )

async def main():
    '''Run Uvicorn programmatically'''
    config = uvicorn.Config("chatbot:app", port=8000)
    # use reload=True if not production?
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    add_docs_to_chroma(["docs/example.md"])
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
