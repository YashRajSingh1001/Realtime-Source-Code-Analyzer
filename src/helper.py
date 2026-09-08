import os
import stat
import shutil
from git import Repo
from langchain.document_loaders.generic import GenericLoader
# from langchain.document_loaders.parsers import LanguageParser
# from langchain.document_loaders.parsers import Language
from langchain.document_loaders.parsers.language import LanguageParser
from langchain.text_splitter import Language
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings

#git marks files inside .git read-only, which makes shutil.rmtree fail on
#Windows. This clears the read-only bit and retries.
def _force_remove(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

#removing a previously analyzed repo
def clear_repo(repo_path="repo"):
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, onerror=_force_remove)

#clone the github repositories
def repo_ingestion(repo_url):
    repo_path = "repo"
    #git refuses to clone into a non-empty directory, so the previous
    #repo has to go before a new one can be pulled in
    clear_repo(repo_path)
    os.makedirs(repo_path, exist_ok=True)
    Repo.clone_from(repo_url, to_path=repo_path)

#Loading repositories as documents
def load_repo(repo_path):
    loader = GenericLoader.from_filesystem(repo_path,
                                        glob = "**/*",
                                       suffixes=[".py"],
                                       parser = LanguageParser(language=Language.PYTHON, parser_threshold=500)
                                        )
    
    documents = loader.load()

    return documents

#Creating text chunks 
def text_splitter(documents):
    documents_splitter = RecursiveCharacterTextSplitter.from_language(language = Language.PYTHON,
                                                             chunk_size = 2000,
                                                             chunk_overlap = 200)
    
    text_chunks = documents_splitter.split_documents(documents)

    return text_chunks

#loading embeddings model
def load_embedding():
    embeddings=OpenAIEmbeddings(disallowed_special=())
    return embeddings
