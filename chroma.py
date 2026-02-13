import chromadb

chroma_client = chromadb.Client()

collection = chroma_client.get_or_create_collection("all-my-documents")

def add_docs_to_chroma(files):
    for file in files:
        with open(file, 'r') as f:
            content = f.read()
        chunks = content.split("\n\n")
        for i, chunk in enumerate(chunks):
            if chunk.strip(): # skip empty chunks
                collection.add(
                    documents=[chunk], # handles tokenization, embedding, and indexing automatically
                    metadatas=[{"source": file, "chunk_index": i}], # unique for each doc
                    ids=[f"{file}_chunk_{i}"], # filter on these
                )

"""
from langchain.text_splitter import RecursiveCharacterTextSplitter

def add_documents_to_chroma(file_paths):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            content = f.read()
        
        chunks = text_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            kb_collection.add(
                documents=[chunk],
                ids=[f"{file_path}_chunk_{i}"],
                metadatas=[{"source": file_path}]
            )
"""