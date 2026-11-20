import json
from typing import Any, Dict, List, Optional
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin

@register_plugin
class ElasticPlugin(BasePlugin):
    manifest = PluginManifest(
        id="elastic",
        name="Elastic SIEM",
        description="Query Elasticsearch and manage Elastic alerts",
        long_description="Elastic integration allows the agent to run Elasticsearch queries, EQL event correlation queries, and manage Elastic security alerts and detection rules.",
        version="1.0.0",
        author="outcome",
        icon="🔍",
        category="siem",
        tags=["siem", "elastic", "logs", "eql"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "host_field": "host"},
        tools=[
            PluginTool(name="elastic.search", description="Run Elasticsearch query", parameters={"host": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="elastic.eqlSearch", description="Run EQL event correlation query", parameters={"host": {"type": "string"}, "query": {"type": "string"}}),
            PluginTool(name="elastic.getAlerts", description="Get Elastic security alerts", parameters={"host": {"type": "string"}}),
            PluginTool(name="elastic.createRule", description="Create a detection rule", parameters={"host": {"type": "string"}, "name": {"type": "string"}, "query": {"type": "string"}}),
        ],
        website_url="https://www.elastic.co",
        docs_url="https://www.elastic.co/guide/en/elasticsearch/reference/current/rest-apis.html",
        is_free=True,
        is_official=True
    )

    def _validate_credentials(self) -> bool:
        return self.credentials.get('api_key') is not None and self.credentials.get('host') is not None

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        host = parameters.get('host') or self.credentials.get('host')
        api_key = self.credentials.get('api_key')
        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if tool_name == "elastic.search":
                url = f"https://{host}:9200/_search"
                payload = {"query": parameters['query']} if isinstance(parameters['query'], dict) else {"query": {"match_all": {}}}
                # If query is string, assume it's Lucene or simple DSL
                if isinstance(parameters['query'], str):
                    payload = {"query": {"query_string": {"query": parameters['query']}}}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "elastic.eqlSearch":
                url = f"https://{host}:9200/_eql/search"
                payload = {"query": parameters['query']}
                resp = await client.post(url, headers=headers, json=payload)
            elif tool_name == "elastic.getAlerts":
                url = f"https://{host}:9200/security_alerts/_search"
                resp = await client.get(url, headers=headers)
            elif tool_name == "elastic.createRule":
                url = f"https://{host}:9200/security/api/rules"
                payload = {
                    "name": parameters['name'],
                    "query": parameters['query'],
                    "enabled": True
                }
                resp = await client.post(url, headers=headers, json=payload)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            resp.raise_for_status()
            return resp.json()
