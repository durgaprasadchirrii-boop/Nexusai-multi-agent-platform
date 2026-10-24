
from pathlib import Path
import hashlib
import logging

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "nexusai_documents"


def get_embeddings() -> OllamaEmbeddings:
    settings = get_settings()
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_host,
    )


def get_vectorstore() -> Chroma:
    settings = get_settings()
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.chroma_dir),
    )


def load_file(file_path: Path):
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        documents = PyPDFLoader(str(file_path)).load()
    elif suffix == ".txt":
        documents = TextLoader(
            str(file_path),
            encoding="utf-8",
        ).load()
    else:
        raise ValueError("Only PDF and TXT files are supported.")

    for document in documents:
        document.metadata["source"] = file_path.name

    return documents


def ingest_file(file_path: Path) -> dict:
    settings = get_settings()
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError("Uploaded file was not found.")

    documents = load_file(file_path)

    if not documents:
        raise ValueError("The file contains no readable documents.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(documents)

    if not chunks:
        raise ValueError("No text chunks could be created from this file.")

    # Stable IDs make repeated uploads of the same file replace
    # the previous chunks instead of creating duplicate records.
    file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    for index, chunk in enumerate(chunks):
        chunk.metadata["file_hash"] = file_hash
        chunk.metadata["chunk_index"] = index
        chunk.metadata["chunk_id"] = f"{file_hash}-{index}"

    vectorstore = get_vectorstore()
    ids = [chunk.metadata["chunk_id"] for chunk in chunks]

    # Remove previous chunks for this exact file version if present.
    vectorstore.delete(ids=ids)
    vectorstore.add_documents(documents=chunks, ids=ids)

    logger.info(
        "Indexed %s into %s chunks",
        file_path.name,
        len(chunks),
    )

    return {
        "filename": file_path.name,
        "chunks_indexed": len(chunks),
        "file_hash": file_hash,
    }


def retrieve_documents(
    question: str,
    k: int | None = None,
    source_filter: str | None = None,
) -> list[dict]:
    settings = get_settings()
    vectorstore = get_vectorstore()

    search_kwargs = {"k": k or settings.retrieval_k}

    # Optional exact source-name filter.
    if source_filter:
        search_kwargs["filter"] = {"source": source_filter}

    matches = vectorstore.similarity_search(
        question,
        **search_kwargs,
    )

    results = []
    for document in matches:
        results.append({
            "content": document.page_content,
            "source": document.metadata.get("source", "unknown"),
            "page": document.metadata.get("page"),
            "chunk_index": document.metadata.get("chunk_index"),
            "start_index": document.metadata.get("start_index"),
        })

    return results
