---
title: Realtime Source Code Analyzer
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8080
pinned: false
---

# Realtime Source Code Analyzer

Ask questions about a codebase in plain English. Point it at a public GitHub
repository and it clones the repo, splits the Python source along syntactic
boundaries, embeds the chunks into a Chroma vector store, and answers questions
against them with retrieval-augmented generation.

This deployment ships with its own source already indexed, so you can ask about
how it works without pasting anything.

## How it works

```
GitHub repo
  -> GenericLoader + LanguageParser        load .py files as documents
  -> RecursiveCharacterTextSplitter        split on def/class boundaries
  -> OpenAIEmbeddings                      embed each chunk
  -> Chroma (persisted to db/)             vector store
  -> retriever (MMR, k=8)                  fetch relevant chunks
  -> ConversationalRetrievalChain          answer, with summary memory
```

Splitting on syntax rather than a fixed character count is what makes the
retrieved context useful: a chunk tends to be a whole function rather than an
arbitrary window that starts mid-expression.

## Running locally

```bash
docker build -t source-code-analyzer .
docker run -d -p 8080:8080 -e OPENAI_API_KEY="sk-..." source-code-analyzer
```

Then open <http://localhost:8080>.

To run without Docker, install the dependencies and build an index first:

```bash
pip install -r requirements.txt
python -m src.store_index      # indexes whatever is in repo/
python app.py
```

Note that `store_index` has to run as a module, not as `python src/store_index.py`
- running the file directly puts `src/` itself on the path, so `from src.helper
import ...` cannot resolve.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | required | used for both embeddings and chat completion |
| `PORT` | `8080` | port the Flask app binds to |
| `MAX_CHUNKS` | `400` | ceiling on chunks indexed per ingestion |
| `FLASK_DEBUG` | off | enables the Werkzeug debugger; never set this in a deployment |

`MAX_CHUNKS` exists because every chunk is a billed embeddings call. On a public
deployment the key belongs to whoever hosts it, so an uncapped repository is an
uncapped bill.

## Notes and limitations

- Only `.py` files are indexed.
- The retrieval chain and its conversation memory live in process memory, so the
  app runs as a single worker. Ingesting a repo rebuilds both.
- Storage is ephemeral on Hugging Face Spaces: a repo you ingest lasts until the
  Space restarts, after which it reverts to the bundled index.
