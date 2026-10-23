"""Thin LLM wrapper for OpenAI, Gemini or Groq (LLM_PROVIDER in .env).

Embeddings come from EMBED_PROVIDER: openai, gemini, or local (fastembed; Groq has no embeddings API).

The LLM never does arithmetic; callers pass it masked text only.
"""
import json
import re

from pydantic import BaseModel, ValidationError

from app.config import settings

TIMEOUT_SECONDS = 20
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
EMBED_BATCH = 100

_client = None
_local_embedder = None


class LLMUnavailable(Exception):
    """The provider is not configured, timed out, or returned an error."""


def _provider() -> str:
    return settings.LLM_PROVIDER.strip().lower()


def _get_client():
    """Create the provider client on first use."""
    global _client
    if _client is not None:
        return _client
    provider = _provider()
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise LLMUnavailable("OPENAI_API_KEY is not set")
        from openai import OpenAI

        _client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=TIMEOUT_SECONDS, max_retries=1)
    elif provider == "groq":
        if not settings.GROQ_API_KEY:
            raise LLMUnavailable("GROQ_API_KEY is not set")
        from openai import OpenAI

        # Groq speaks the OpenAI API, so the same SDK works with a different base URL.
        _client = OpenAI(api_key=settings.GROQ_API_KEY, base_url=GROQ_BASE_URL, timeout=TIMEOUT_SECONDS,
                         max_retries=1)
    elif provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        from google import genai
        from google.genai import types

        _client = genai.Client(api_key=settings.GEMINI_API_KEY,
                               http_options=types.HttpOptions(timeout=TIMEOUT_SECONDS * 1000))
    else:
        raise LLMUnavailable(f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}' (use openai, gemini or groq)")
    return _client


def _complete(system: str, user: str, temperature: float = 0, json_mode: bool = False) -> str:
    """One chat completion; any provider/network error becomes LLMUnavailable."""
    client = _get_client()
    try:
        if _provider() in ("openai", "groq"):
            kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
            resp = client.chat.completions.create(
                model=settings.LLM_MODEL,
                temperature=temperature,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                **kwargs,
            )
            return resp.choices[0].message.content or ""

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if json_mode else None,
        )
        resp = client.models.generate_content(model=settings.LLM_MODEL, contents=user, config=config)
        return resp.text or ""
    except LLMUnavailable:
        raise
    except Exception as exc:
        raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc


def chat(system: str, user: str, temperature: float = 0) -> str:
    """Plain-text reply. Raises LLMUnavailable."""
    return _complete(system, user, temperature).strip()


def _strip_fences(text: str) -> str:
    """Some models wrap JSON in ```json fences; remove them."""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


def chat_json(system: str, user: str, model_cls: type[BaseModel]):
    """JSON reply validated as model_cls. Retries once with the validation error; returns None on failure."""
    schema = json.dumps(model_cls.model_json_schema())
    full_system = f"{system}\n\nRespond with ONE JSON object only, matching this JSON schema:\n{schema}"
    prompt = user
    for attempt in range(2):
        try:
            raw = _complete(full_system, prompt, temperature=0, json_mode=True)
        except LLMUnavailable as exc:
            print(f"LLM unavailable: {exc}")
            return None
        try:
            return model_cls.model_validate_json(_strip_fences(raw))
        except ValidationError as exc:
            if attempt == 0:
                prompt = (f"{user}\n\nYour previous reply was not valid for the schema. Error:\n{exc}\n"
                          "Return only corrected JSON.")
    return None


def _embed_provider() -> str:
    provider = settings.EMBED_PROVIDER.strip().lower() or _provider()
    return "local" if provider == "groq" else provider


def _embed_local(texts: list[str]) -> list[list[float]]:
    """Free local embeddings with fastembed (model downloads once, ~130 MB)."""
    global _local_embedder
    if _local_embedder is None:
        from fastembed import TextEmbedding

        _local_embedder = TextEmbedding(model_name=settings.EMBED_MODEL)
    vectors = [v.tolist() for v in _local_embedder.embed(texts)]
    if vectors and len(vectors[0]) != settings.EMBED_DIM:
        raise LLMUnavailable(f"{settings.EMBED_MODEL} returns {len(vectors[0])} dimensions but EMBED_DIM is "
                             f"{settings.EMBED_DIM}")
    return vectors


def embed_many(texts: list[str]) -> list[list[float]]:
    """Embeddings of size EMBED_DIM for each text. Raises LLMUnavailable."""
    if not texts:
        return []
    if _embed_provider() == "local":
        try:
            return _embed_local(texts)
        except LLMUnavailable:
            raise
        except Exception as exc:
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
    client = _get_client()
    vectors: list[list[float]] = []
    try:
        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start:start + EMBED_BATCH]
            if _embed_provider() == "openai":
                resp = client.embeddings.create(model=settings.EMBED_MODEL, input=batch, dimensions=settings.EMBED_DIM)
                vectors.extend(item.embedding for item in resp.data)
            else:
                from google.genai import types

                resp = client.models.embed_content(
                    model=settings.EMBED_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(output_dimensionality=settings.EMBED_DIM),
                )
                vectors.extend(list(e.values) for e in resp.embeddings)
    except LLMUnavailable:
        raise
    except Exception as exc:
        raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc
    return vectors


def embed(text: str) -> list[float]:
    """Embedding for one text. Raises LLMUnavailable."""
    return embed_many([text])[0]


if __name__ == "__main__":
    print(chat("You are helpful", "Say hi"))
    print(len(embed("test")))
