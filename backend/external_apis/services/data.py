"""Phase 3 — general/public API specifications (backend enrichment only)."""
from __future__ import annotations

from ..registry import ServiceSpec, registry


def register_data_services() -> None:
    # 3A — data & search
    registry.register(ServiceSpec(
        name="serpapi", category="search", base_url="https://serpapi.com",
        endpoints={"search": "{base}/search.json"}, key_env="SERPAPI_KEY",
        auth_style="query", key_param="api_key", health_path="{base}/healthz"))
    registry.register(ServiceSpec(
        name="crawl4ai", category="crawl", base_url="http://localhost:11235",
        endpoints={"crawl": "{base}/crawl"}, health_path="{base}/health",
        method="POST"))
    registry.register(ServiceSpec(
        name="snaprender", category="capture", base_url="https://api.snaprender.com/v1",
        endpoints={"screenshot": "{base}/capture"},
        key_env="SNAPRENDER_API_KEY", auth_style="bearer", method="POST"))

    # 3B — developer & productivity
    registry.register(ServiceSpec(
        name="github", category="developer", base_url="https://api.github.com",
        endpoints={"search": "{base}/search/repositories",
                   "code": "{base}/search/code",
                   "issues": "{base}/repos/{owner}/{repo}/issues"},
        key_env="GITHUB_TOKEN", auth_style="bearer",
        health_path="{base}/rate_limit"))
    registry.register(ServiceSpec(
        name="transcriptfetch", category="media", base_url="https://transcriptfetch.com/api",
        endpoints={"transcript": "{base}/transcript"}, health_path="{base}/health"))
    registry.register(ServiceSpec(
        name="finsignals", category="finance", base_url="https://api.finsignals.ai/v1",
        endpoints={"finance": "{base}/signals"},
        key_env="FIN_SIGNALS_API_KEY", auth_style="bearer"))

    # 3C — context enrichment
    registry.register(ServiceSpec(
        name="openweathermap", category="data", base_url="https://api.openweathermap.org/data/2.5",
        endpoints={"weather": "{base}/weather"}, key_env="OPENWEATHER_API_KEY",
        auth_style="query", key_param="appid"))
    registry.register(ServiceSpec(
        name="restcountries", category="data", base_url="https://restcountries.com/v3.1",
        endpoints={"countries": "{base}/all"}, health_path="{base}/all"))
    registry.register(ServiceSpec(
        name="newsapi", category="data", base_url="https://newsapi.org/v2",
        endpoints={"news": "{base}/top-headlines"}, key_env="NEWS_API_KEY",
        auth_style="header", key_param="X-Api-Key"))
    registry.register(ServiceSpec(
        name="coingecko", category="data", base_url="https://api.coingecko.com/api/v3",
        endpoints={"crypto": "{base}/coins/markets"},
        health_path="{base}/ping"))
    registry.register(ServiceSpec(
        name="nasa", category="data", base_url="https://api.nasa.gov",
        endpoints={"apod": "{base}/planetary/apod"},
        key_env="NASA_API_KEY", auth_style="query", key_param="api_key"))
