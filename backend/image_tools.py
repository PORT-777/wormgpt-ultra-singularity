"""Image AI helpers: generation + analysis routing metadata."""
from __future__ import annotations

from typing import Optional, Dict

IMAGE_GEN_PROVIDERS = ["openai", "stability", "gemini", "replicate"]
VISION_PROVIDERS = ["openai", "gemini", "anthropic", "groq"]


def supports_image_gen(provider: str, model: str) -> bool:
    return provider in IMAGE_GEN_PROVIDERS


def supports_vision(provider: str, model: str) -> bool:
    return provider in VISION_PROVIDERS


def build_image_gen_request(prompt: str, provider: str, model: str,
                           size: str = "1024x1024", n: int = 1,
                           aspect_ratio: Optional[str] = None) -> Dict:
    return {"provider": provider, "model": model, "prompt": prompt,
            "size": size, "n": n, "aspect_ratio": aspect_ratio}


def validate_image(data: bytes, max_bytes: int = 20_000_000) -> Optional[str]:
    if len(data) > max_bytes:
        return "image too large"
    if not data[:8].startswith((b"\x89PNG", b"\xff\xd8", b"GIF8", b"RIFF")):
        return "not a recognized image format"
    return None
