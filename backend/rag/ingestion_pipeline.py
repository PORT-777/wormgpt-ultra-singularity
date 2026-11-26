"""Any source -> cleaned Document(s) with enriched metadata."""
from __future__ import annotations

from typing import Any, Dict, List

from . import document_loader as dl
from .models import Document


async def ingest(source: str, metadata: Dict[str, Any] | None = None) -> List[Document]:
    metadata = metadata or {}
    source_type = str(metadata.get("source_type") or "").lower()
    if source.startswith("http://") or source.startswith("https://"):
        doc = await ingest_url(source)
    elif source_type == "youtube":
        doc = await ingest_youtube(source)
    elif source_type == "github_repo":
        return await ingest_github(source)
    elif source_type == "audio":
        doc = await ingest_audio(source)
    elif source_type == "image":
        doc = Document(dl.ocr_pdf(source), {**dl._meta("image", source)})
    else:
        doc = dl.load(source)
    doc.metadata.update(metadata)
    doc.metadata.setdefault("word_count", len(doc.text.split()))
    doc.metadata.setdefault("language", "und")
    return [doc]


async def ingest_url(url: str) -> Document:
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("crawl4ai")
    if spec and spec.available():
        try:
            result = await ExternalService(spec).query("crawl", {"url": url})
            return Document(dl.clean_text(str(result.get("markdown", result))),
                            dl._meta("url", url))
        except Exception:
            pass
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(url)
        return Document(dl.clean_text(r.text), dl._meta("url", url))
    except Exception as exc:
        return Document("", {**dl._meta("url", url), "error": str(exc)[:200]})


async def ingest_youtube(url: str) -> Document:
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("transcriptfetch")
    if spec and spec.available():
        try:
            result = await ExternalService(spec).query("transcript", {"url": url})
            return Document(dl.clean_text(str(result)), dl._meta("youtube", url))
        except Exception:
            pass
    return Document("", {**dl._meta("youtube", url), "reason": "transcript service unavailable"})


async def ingest_github(repo: str) -> List[Document]:
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("github")
    if spec is None or not spec.available():
        return []
    try:
        result = await ExternalService(spec).query("search", {"q": f"repo:{repo} extension:md"})
        return [Document(str(item.get("text", "")), dl._meta("github_repo", repo))
                for item in result.get("items", [])[:50]]
    except Exception:
        return []


async def ingest_audio(path: str) -> Document:
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("assemblyai")
    if spec and spec.available():
        try:
            result = await ExternalService(spec).query("assembly", {"audio": path})
            return Document(dl.clean_text(str(result.get("text", ""))), dl._meta("audio", path))
        except Exception:
            pass
    return Document("", {**dl._meta("audio", path), "reason": "transcription unavailable"})
