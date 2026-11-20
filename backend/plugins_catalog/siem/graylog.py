from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class GraylogPlugin(BasePlugin):
    manifest = PluginManifest(
        id="graylog",
        name="Graylog",
        description="Log search, streams, inputs and system health",
        long_description=(
            "Query Graylog's search API with Lucene or relative-time ranges, list "
            "streams and their rules, inspect message inputs and read cluster/system "
            "health. Uses username + API token basic auth."
        ),
        version="1.0.0",
        author="outcome",
        icon="📜",
        category="siem",
        tags=["siem", "graylog", "logs", "search", "observability"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token", "extra_fields": ["url", "username"]},
        tools=[
            PluginTool(
                name="graylog.search",
                display_name="Search Logs",
                description="Run a Lucene query over a relative time range",
                parameters={
                    "query": {"type": "string", "description": "Default *"},
                    "range_seconds": {"type": "integer", "description": "Default 3600"},
                    "limit": {"type": "integer", "description": "Default 50, max 500"},
                    "stream_id": {"type": "string"},
                    "fields": {"type": "string", "description": "Comma separated message fields"},
                },
            ),
            PluginTool(
                name="graylog.listStreams",
                display_name="List Streams",
                description="List streams with descriptions and disabled state",
                parameters={},
            ),
            PluginTool(
                name="graylog.listInputs",
                display_name="List Inputs",
                description="List message inputs with type, title and node",
                parameters={},
            ),
            PluginTool(
                name="graylog.system",
                display_name="System Info",
                description="Read cluster, node and JVM health information",
                parameters={},
            ),
        ],
        website_url="https://graylog.org",
        docs_url="https://go2docs.graylog.org/current/home.htm",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("url")) and bool(
            self.credentials.get("username")
        ) and bool(self.credentials.get("api_token"))

    @property
    def _base(self) -> str:
        raw = self.credentials["url"].strip().rstrip("/")
        if not raw.startswith("http"):
            raw = "http://" + raw
        return raw + "/api"

    @property
    def _auth(self) -> tuple:
        return (self.credentials["username"], self.credentials["api_token"])

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0, auth=self._auth) as client:
            if tool_name == "graylog.search":
                params: Dict[str, Any] = {
                    "query": parameters.get("query") or "*",
                    "range": int(parameters.get("range_seconds") or 3600),
                    "limit": min(int(parameters.get("limit") or 50), 500),
                    "sort": "timestamp:desc",
                }
                if parameters.get("stream_id"):
                    params["filter"] = f"streams:{parameters['stream_id']}"
                if parameters.get("fields"):
                    params["fields"] = parameters["fields"]
                resp = await client.get(
                    f"{self._base}/search/universal/relative",
                    params=params,
                    headers={"Accept": "application/json"},
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Graylog HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
                return {
                    "total_results": data.get("total_results"),
                    "took_ms": data.get("time"),
                    "messages": [
                        {
                            "timestamp": (m.get("message") or {}).get("timestamp"),
                            "source": (m.get("message") or {}).get("source"),
                            "message": (m.get("message") or {}).get("message"),
                            "level": (m.get("message") or {}).get("level"),
                            "streams": (m.get("message") or {}).get("streams"),
                        }
                        for m in data.get("messages", [])
                    ],
                }
            elif tool_name == "graylog.listStreams":
                resp = await client.get(f"{self._base}/streams")
            elif tool_name == "graylog.listInputs":
                resp = await client.get(f"{self._base}/system/inputs")
            elif tool_name == "graylog.system":
                cluster = await client.get(f"{self._base}/cluster")
                jvm = await client.get(f"{self._base}/system/jvm")
                if cluster.status_code >= 400:
                    raise RuntimeError(
                        f"Graylog HTTP {cluster.status_code}: {cluster.text[:400]}"
                    )
                return {
                    "cluster": cluster.json(),
                    "jvm": jvm.json() if jvm.status_code < 400 else {},
                }
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Graylog HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
