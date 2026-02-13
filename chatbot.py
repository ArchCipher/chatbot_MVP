'''
FastAPI chatbot MVP

- dotenv/ os: load environment variables from .env file
- FastApi: Python web framework to build APIs
- Uvicorn: ASGI server used to run the FastAPI app
- Pydantic: data validation library for Python
- google-genai: Google GenAI API client
- chromadb: ChromaDB client
'''

import asyncio

from dotenv import load_dotenv
import os

import uvicorn
from fastapi import FastAPI

from pydantic import BaseModel

from google import genai

from chroma import collection, add_docs_to_chroma

app = FastAPI()

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# HTTP methods fot RESTful API

@app.get("/")
def root():
    return {"message": "Hello World"}

class ChatRequest(BaseModel):
    session_id: int
    message: str

class ChatResponse(BaseModel):
    reply: str

# gemini api fallback, but api call per message is expensive
# could be used later for flow and intent classification
# https://github.com/googleapis/python-genai
def ai_llm(message, context):
    # query chroma for context
    results = collection.query(
        query_texts=[message],
        n_results=2,
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

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = ai_llm(req.message, req.session_id)
    return ChatResponse(reply=reply)

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
