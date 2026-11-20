from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://api.linear.app/graphql"


@register_plugin
class LinearPlugin(BasePlugin):
    manifest = PluginManifest(
        id="linear",
        name="Linear",
        description="Issues, teams and projects through Linear's GraphQL API",
        long_description=(
            "Create and triage issues, move them through workflow states, post "
            "comments, list teams and projects, and search issues by text — all via "
            "Linear's GraphQL endpoint with a personal API key."
        ),
        version="1.0.0",
        author="outcome",
        icon="📐",
        category="productivity",
        tags=["productivity", "linear", "issues", "graphql", "project-management"],
        auth_type="oauth2",
        auth_config={"auth_method": "oauth2", "token_field": "access_token"},
        tools=[
            PluginTool(
                name="linear.listIssues",
                display_name="List Issues",
                description="List the most recent issues, optionally filtered by team",
                parameters={
                    "team_id": {"type": "string"},
                    "limit": {"type": "integer", "description": "Default 25, max 100"},
                },
            ),
            PluginTool(
                name="linear.searchIssues",
                display_name="Search Issues",
                description="Search issues by free text",
                parameters={"term": {"type": "string"}, "limit": {"type": "integer"}},
            ),
            PluginTool(
                name="linear.createIssue",
                display_name="Create Issue",
                description="Create an issue in a team with title, description and priority",
                parameters={
                    "team_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "priority": {"type": "integer", "description": "0 none, 1 urgent, 4 low"},
                    "assignee_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="linear.updateIssue",
                display_name="Update Issue",
                description="Change an issue's title, state, priority or assignee",
                parameters={
                    "issue_id": {"type": "string"},
                    "title": {"type": "string"},
                    "state_id": {"type": "string"},
                    "priority": {"type": "integer"},
                    "assignee_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="linear.listTeams",
                display_name="List Teams",
                description="List teams with their keys and ids",
                parameters={},
            ),
            PluginTool(
                name="linear.addComment",
                display_name="Add Comment",
                description="Comment on an issue",
                parameters={"issue_id": {"type": "string"}, "body": {"type": "string"}},
            ),
        ],
        website_url="https://linear.app",
        docs_url="https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token") or self.credentials.get("api_key"))

    @property
    def _headers(self) -> Dict[str, str]:
        # OAuth 2.0 access tokens use the Bearer scheme; personal API keys are
        # sent verbatim, as documented by Linear.
        oauth_token = self.credentials.get("access_token")
        authorization = (
            f"Bearer {oauth_token}" if oauth_token else self.credentials["api_key"]
        )
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
        }

    async def _query(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                BASE, headers=self._headers, json={"query": query, "variables": variables}
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Linear HTTP {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
        if data.get("errors"):
            raise RuntimeError(f"Linear GraphQL error: {data['errors']}")
        return data.get("data") or {}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        if tool_name == "linear.listIssues":
            query = """
            query Issues($first: Int!, $teamId: ID) {
              issues(first: $first, filter: {team: {id: {eq: $teamId}}}, orderBy: updatedAt) {
                nodes { id identifier title url state { name } priority assignee { name } updatedAt }
              }
            }
            """
            data = await self._query(
                query,
                {
                    "first": min(int(parameters.get("limit") or 25), 100),
                    "teamId": parameters.get("team_id"),
                },
            )
            return data.get("issues", {})

        if tool_name == "linear.searchIssues":
            query = """
            query Search($term: String!, $first: Int!) {
              searchIssues(term: $term, first: $first) {
                nodes { id identifier title url state { name } priority }
              }
            }
            """
            data = await self._query(
                query,
                {
                    "term": parameters.get("term", ""),
                    "first": min(int(parameters.get("limit") or 20), 50),
                },
            )
            return data.get("searchIssues", {})

        if tool_name == "linear.createIssue":
            mutation = """
            mutation Create($input: IssueCreateInput!) {
              issueCreate(input: $input) {
                success
                issue { id identifier title url }
              }
            }
            """
            payload: Dict[str, Any] = {
                "teamId": parameters["team_id"],
                "title": parameters["title"],
            }
            if parameters.get("description"):
                payload["description"] = parameters["description"]
            if parameters.get("priority") is not None:
                payload["priority"] = int(parameters["priority"])
            if parameters.get("assignee_id"):
                payload["assigneeId"] = parameters["assignee_id"]
            return await self._query(mutation, {"input": payload})

        if tool_name == "linear.updateIssue":
            mutation = """
            mutation Update($id: String!, $input: IssueUpdateInput!) {
              issueUpdate(id: $id, input: $input) { success issue { id title state { name } } }
            }
            """
            payload = {}
            if parameters.get("title"):
                payload["title"] = parameters["title"]
            if parameters.get("state_id"):
                payload["stateId"] = parameters["state_id"]
            if parameters.get("priority") is not None:
                payload["priority"] = int(parameters["priority"])
            if parameters.get("assignee_id"):
                payload["assigneeId"] = parameters["assignee_id"]
            return await self._query(
                mutation, {"id": parameters["issue_id"], "input": payload}
            )

        if tool_name == "linear.listTeams":
            query = """
            query Teams { teams { nodes { id key name description } } }
            """
            return await self._query(query, {})

        if tool_name == "linear.addComment":
            mutation = """
            mutation Comment($input: CommentCreateInput!) {
              commentCreate(input: $input) { success comment { id url } }
            }
            """
            return await self._query(
                mutation,
                {"input": {"issueId": parameters["issue_id"], "body": parameters.get("body", "")}},
            )

        raise ValueError(f"Unknown tool: {tool_name}")
