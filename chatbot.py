'''
FastAPI client for RAG chatbot

- FastAPI: Python web framework to build APIs
- Uvicorn: ASGI server used to run the FastAPI app
- Pydantic: data validation library for Python
- dotenv/ os: load environment variables from .env file
- google-genai: Google GenAI API client
- chromadb: ChromaDB client
- chroma.py: ChromaDB client implementation
'''

import asyncio
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from pydantic import BaseModel
import uvicorn

load_dotenv()  # Load .env before importing chroma (which uses env vars)
api_key=os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set")

from chroma import RagClient

app = FastAPI()
genai_client = genai.Client(api_key=api_key)

# instantiate RagClient
rag_client = RagClient()

# HTTP methods for RESTful API

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

SYSTEM_PROMPT = """You are a helpful assistant. Use the provided context from
the source documents to answer questions accurately. If the context doesn't
contain relevant information, you can use your general knowledge but mention
that the information isn't from the source documents. Be concise and helpful."""

def generate_response(message, context):
    # build prompt
    if context:
        prompt = f"""Please answer the question based on the context below when relevant:
Context from source documents: {context}
Question: {message}
Answer: """
    else:
        prompt = message
    try:
        response = genai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents={'text': prompt},
        config={
            'system_instruction': SYSTEM_PROMPT,
            'temperature': 0, # how random the response is
            'top_p': 0.95, # probability of selecting the next token
            'top_k': 20, # number of tokens to consider for the next token
            },
        )
    # add HTTP exception handling instead of returning string
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I couldn't process your request. Please try again later."
    return response.text

# API endpoint to chat with the bot
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Generate response with RAG context retrieval
    reply = generate_response(req.message, rag_client.get_context(req.message))
    return ChatResponse(reply=reply)

# API endpoint to add/update documents without restarting server
@app.post("/index_docs", response_model=IndexDocsResponse)
def index_docs(req: IndexDocsRequest):
    files_indexed, errors = rag_client.add_docs_to_chroma(req.files)
    if not errors:
        message = "Documents indexed successfully"
    else:
        message = f"Completed with {len(errors)} error(s)"
    return IndexDocsResponse(
        message=message,
        files_indexed=files_indexed,
        errors=errors
    )

@app.post("/reload_docs")
def reload_docs():
    load_dotenv(override=True)
    status = rag_client.reload_collection()
    if status is not None:
        raise HTTPException(status_code=404, detail=status)
    return {"message": "Documents reloaded successfully"}

async def main():
    '''Run Uvicorn programmatically'''
    config = uvicorn.Config("chatbot:app", port=8000)
    # use reload=True if not production?
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    status = rag_client.reload_collection()
    if status is not None:
        raise HTTPException(status_code=404, detail=status)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
