"""
Utility script to delete the ChromaDB 'clauses' collection for test/dev purposes.
"""
import chromadb
from chromadb.config import Settings

def delete_chroma_collection(persist_directory: str = "../../chroma", collection_name: str = "clauses"):
    client = chromadb.PersistentClient(path=persist_directory, settings=Settings(allow_reset=True))
    client.delete_collection(collection_name)
    print(f"Deleted collection '{collection_name}' from {persist_directory}")

if __name__ == "__main__":
    delete_chroma_collection()
