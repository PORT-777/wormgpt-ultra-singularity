from typing import Any, Dict
import httpx
from backend.plugins.sdk import BasePlugin, PluginManifest, PluginTool
from backend.plugins.registry import register_plugin


@register_plugin
class OpenCTIPlugin(BasePlugin):
    manifest = PluginManifest(
        id="opencti",
        name="OpenCTI",
        description="Open Cyber Threat Intelligence platform",
        long_description="OpenCTI structures threat intelligence as STIX 2.1 entities. Search indicators, pull threat actor profiles, and push finished analysis as reports.",
        version="1.0.0",
        author="outcome",
        icon="🧠",
        category="security",
        tags=["threat-intel", "cti", "stix"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key", "url_field": "opencti_url"},
        tools=[
            PluginTool(
                name="opencti.searchIndicator",
                display_name="Search Indicator",
                description="Search for an IOC in OpenCTI",
                parameters={"search": {"type": "string"}},
            ),
            PluginTool(
                name="opencti.getActor",
                display_name="Get Threat Actor",
                description="Get a threat actor profile by name or ID",
                parameters={"search": {"type": "string"}},
            ),
            PluginTool(
                name="opencti.createReport",
                display_name="Create Report",
                description="Push an analysis report into OpenCTI",
                parameters={"name": {"type": "string"}, "content": {"type": "string"}},
            ),
            PluginTool(
                name="opencti.getRelationships",
                display_name="Get Relationships",
                description="Get STIX relationships for an entity",
                parameters={"entity_id": {"type": "string"}},
            ),
        ],
        website_url="https://www.opencti.io",
        docs_url="https://docs.opencti.io/latest/reference/api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key")) and bool(self.credentials.get("opencti_url"))

    @property
    def _url(self) -> str:
        return self.credentials["opencti_url"].rstrip("/") + "/graphql"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['api_key']}",
            "Content-Type": "application/json",
        }

    async def _graphql(self, client: httpx.AsyncClient, query: str, variables: Dict[str, Any]) -> Any:
        resp = await client.post(
            self._url, headers=self._headers, json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise RuntimeError(f"OpenCTI GraphQL error: {body['errors']}")
        return body.get("data", {})

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if tool_name == "opencti.searchIndicator":
                query = """
                query Search($search: String) {
                  indicators(search: $search, first: 25) {
                    edges { node { id name pattern indicator_types valid_from } }
                  }
                }"""
                return await self._graphql(client, query, {"search": parameters["search"]})

            if tool_name == "opencti.getActor":
                query = """
                query Actors($search: String) {
                  threatActorsGroup(search: $search, first: 10) {
                    edges { node { id name description aliases } }
                  }
                }"""
                return await self._graphql(client, query, {"search": parameters["search"]})

            if tool_name == "opencti.createReport":
                mutation = """
                mutation CreateReport($input: ReportAddInput!) {
                  reportAdd(input: $input) { id name }
                }"""
                variables = {
                    "input": {
                        "name": parameters["name"],
                        "description": parameters.get("content", ""),
                        "published": True,
                    }
                }
                return await self._graphql(client, mutation, variables)

            if tool_name == "opencti.getRelationships":
                query = """
                query Relationships($id: String!) {
                  stixCoreObject(id: $id) {
                    id entity_type
                    ... on StixCoreObject {
                      relationships(first: 50) {
                        edges { node { id relationship_type to { id } } }
                      }
                    }
                  }
                }"""
                return await self._graphql(client, query, {"id": parameters["entity_id"]})

            raise ValueError(f"Unknown tool: {tool_name}")
