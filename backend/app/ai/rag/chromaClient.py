import re
from functools import cache

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from core.config import settings


client = chromadb.PersistentClient(path=settings.CHROMA_PATH, settings=Settings(anonymized_telemetry=False))


def get_embeddings() -> Embeddings:
    """Embedding model for the handbook, Gemini by default so no local Ollama is needed."""
    if settings.EMBEDDING_PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings

        kwargs = {"base_url": settings.OLLAMA_BASE_URL} if settings.OLLAMA_BASE_URL else {}
        return OllamaEmbeddings(model=settings.EMBEDDING_MODEL or "bge-m3", **kwargs)

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.GOOGLE_EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        output_dimensionality=768,
    )


def collection_name() -> str:
    """One collection per embedding model, vectors of different models can't be mixed."""
    model = settings.EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "ollama" else settings.GOOGLE_EMBEDDING_MODEL
    return "handbook_" + re.sub(r"[^a-zA-Z0-9_-]", "_", f"{settings.EMBEDDING_PROVIDER}_{model}")


@cache
def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=collection_name(),
        embedding_function=get_embeddings(),
        client=client,
        collection_metadata={"hnsw:space": "cosine"},
        create_collection_if_not_exists=True,
    )
