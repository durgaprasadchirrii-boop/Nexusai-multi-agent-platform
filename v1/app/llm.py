
from langchain_ollama import ChatOllama

from app.config import get_settings


def get_llm() -> ChatOllama:
    settings = get_settings()

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_host,
        temperature=0,
    )


def invoke_llm(prompt: str) -> str:
    response = get_llm().invoke(prompt)
    return str(response.content)
