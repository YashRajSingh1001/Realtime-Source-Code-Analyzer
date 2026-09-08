from src.helper import load_repo, text_splitter, load_embedding
from dotenv import load_dotenv
from langchain.vectorstores import Chroma
import os
import shutil

load_dotenv()

PERSIST_DIR = "db"

#Every chunk indexed is a paid embeddings call. On a public deployment the
#key belongs to whoever hosts it, so an unbounded repo is an unbounded bill.
#This caps a single ingestion; raise it locally if you need a fuller index.
MAX_CHUNKS = int(os.environ.get("MAX_CHUNKS", "400"))


def create_index(repo_path="repo/", persist_directory=PERSIST_DIR):
    """Embed every .py file under repo_path into a fresh Chroma index.

    Chroma appends to a collection rather than replacing it, so the old
    collection is dropped first. Without that, a newly analyzed repo would
    be blended with whatever was indexed before it and answers would mix
    the two codebases.
    """
    embeddings = load_embedding()

    #Start from an empty directory rather than dropping the collection.
    #delete_collection() detaches a collection but reclaims neither its HNSW
    #segment files nor its rows in the embeddings table, so repeated
    #ingestions would pile up ~6MB of orphaned index each time until the
    #disk filled. Removing the directory is the only way to actually free it.
    if os.path.isdir(persist_directory):
        shutil.rmtree(persist_directory)

    documents = load_repo(repo_path)
    text_chunks = text_splitter(documents)

    if len(text_chunks) > MAX_CHUNKS:
        print(f"repo produced {len(text_chunks)} chunks, indexing first {MAX_CHUNKS}")
        text_chunks = text_chunks[:MAX_CHUNKS]

    #storing vector in chroma vector database
    vectordb = Chroma.from_documents(text_chunks,
                                     embedding=embeddings,
                                     persist_directory=persist_directory)
    vectordb.persist()

    return vectordb


if __name__ == "__main__":
    db = create_index()
    print(f"Indexed {db._collection.count()} chunks into '{PERSIST_DIR}'.")

