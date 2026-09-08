# Debian 12 (bookworm). The older -bullseye tag is Debian 11, which reached
# end-of-life - its security repo metadata has expired, so apt-get update
# fails inside it.
FROM python:3.11-slim-bookworm

WORKDIR /app

# Dependencies get their own layer, copied before the source.
# Docker caches each layer and only rebuilds from the first one that
# changed - so editing app.py reuses the cached install instead of
# re-downloading langchain and chromadb every single build.
COPY requirements.txt setup.py ./

# Two different kinds of dependency are handled here:
#
#   git             stays in the image. GitPython does not clone repos
#                   itself, it shells out to the real git binary, so the
#                   "paste a GitHub URL" feature needs it at runtime.
#
#   build-essential is only needed while pip compiles chroma-hnswlib's C++
#                   extension, which has no prebuilt wheel for this
#                   platform. It is installed, used and purged inside a
#                   single RUN, because Docker layers only ever add -
#                   purging it in a later layer would leave the ~300MB
#                   sitting in this one regardless.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces run the container as uid 1000 rather than root. The
# app writes into its working directory when it indexes - repo/ for the
# clone, db/ for the rebuilt index - so that directory has to belong to
# that user. Without this the Space fails on ingestion with permission
# errors while working perfectly on a local docker run as root.
RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

# Source code last, because it changes most often.
# .dockerignore keeps the venv, .env and .git out of this.
COPY --chown=user:user . .

EXPOSE 8080

CMD ["python3", "app.py"]
