'''
ChromaDB client
'''

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# in memory client:
chroma_client = chromadb.Client()

# for persistent data storage across restarts, use:
# chroma_client = chromadb.PersistentClient(path="./chroma_db")

collection = chroma_client.get_or_create_collection("all-my-documents")

def add_docs_to_chroma(files):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(os.getenv("CHUNK_SIZE", 500)),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 50))
    )
    for file in files:
        try:
            with open(file, 'r') as f:
                content = f.read()
            chunks = text_splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                if chunk.strip(): # skip empty chunks
                    collection.add(
                        documents=[chunk], # handles tokenization, embedding, and indexing automatically
                        metadatas=[{"source": file, "chunk_index": i}], # unique for each doc
                        ids=[f"{file}_chunk_{i}"] # filter on these
                    )
        except FileNotFoundError:
            print(f"File not found: {file}")
            continue
        except Exception as e:
            print(f"Error processing file {file}: {e}")
            continue
