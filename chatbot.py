'''
FastAPI chatbot MVP

- FastApi: Python web framework to build APIs
- Uvicorn: ASGI server used to run the FastAPI app
- Pydantic: data validation library for Python
'''

import asyncio
import os

from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from google import genai
from chroma import RAGClient

load_dotenv()

app = FastAPI()

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize RAG client and load knowledge base on startup
rag_client = RAGClient()
rag_client.load_knowledge_base()

# HTTP methods fot RESTful API

@app.get("/")
def root():
    return {"message": "Hello World"}

class ChatRequest(BaseModel):
    session_id: int
    message: str

class ChatResponse(BaseModel):
    reply: str

sessions = {}

SYSTEM_PROMPT = """You are a helpful assistant. Use the provided context from the knowledge base to answer questions accurately.
If the context doesn't contain relevant information, you can use your general knowledge but mention that the information isn't from the knowledge base.
Be concise and helpful."""


def generate_rag_response(message: str, context: str) -> str:
    """Generate response using Gemini with RAG context."""
    if context:
        prompt = f"""Context from knowledge base:
{context}

User question: {message}

Please answer based on the context above when relevant."""
    else:
        prompt = message

    response = gemini_client.models.generate_content(
        model='gemini-2.5-flash',
        contents={'text': prompt},
        config={
            'system_instruction': SYSTEM_PROMPT,
            'temperature': 0.3,
            'top_p': 0.95,
            'top_k': 20,
        },
    )
    return response.text

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Retrieve relevant context from the knowledge base
    context = rag_client.get_context_string(req.message, n_results=3)

    # Generate response with RAG context
    reply = generate_rag_response(req.message, context)

    return ChatResponse(reply=reply)


@app.post("/reload-knowledge-base")
def reload_knowledge_base():
    """Reload the knowledge base from files."""
    rag_client.load_knowledge_base()
    return {"message": "Knowledge base reloaded"}

async def main():
    '''Run Uvicorn programmatically'''
    config = uvicorn.Config("chatbot:app", port=8000)
    # use reload=True if not production?
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
