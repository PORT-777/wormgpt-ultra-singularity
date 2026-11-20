from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class JenkinsPlugin(BasePlugin):
    manifest = PluginManifest(
        id="jenkins",
        name="Jenkins",
        description="Trigger builds, read job status and stream console output",
        long_description=(
            "Control any Jenkins controller over its REST API: list jobs and folders, "
            "trigger builds with parameters, poll queue items, read the last build "
            "result and fetch console logs."
        ),
        version="1.0.0",
        author="outcome",
        icon="🧰",
        category="devops",
        tags=["devops", "jenkins", "ci", "builds", "automation"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_token", "extra_fields": ["url", "username"]},
        tools=[
            PluginTool(
                name="jenkins.listJobs",
                display_name="List Jobs",
                description="List top-level jobs with their colour/status",
                parameters={"folder": {"type": "string", "description": "Optional job/folder path"}},
            ),
            PluginTool(
                name="jenkins.getJob",
                display_name="Job Info",
                description="Get a job's health, last build number and result",
                parameters={"job": {"type": "string"}},
            ),
            PluginTool(
                name="jenkins.triggerBuild",
                display_name="Trigger Build",
                description="Start a build, optionally with parameters",
                parameters={
                    "job": {"type": "string"},
                    "parameters": {"type": "object", "description": "name to value map"},
                },
            ),
            PluginTool(
                name="jenkins.buildStatus",
                display_name="Build Status",
                description="Read building/result/duration for a build number",
                parameters={
                    "job": {"type": "string"},
                    "build_number": {"type": "integer", "description": "Default lastBuild"},
                },
            ),
            PluginTool(
                name="jenkins.consoleLog",
                display_name="Console Log",
                description="Fetch the console output of a build (optionally only the tail)",
                parameters={
                    "job": {"type": "string"},
                    "build_number": {"type": "integer"},
                    "tail_lines": {"type": "integer", "description": "Default 200"},
                },
            ),
        ],
        website_url="https://www.jenkins.io",
        docs_url="https://www.jenkins.io/doc/book/using/remote-access-api/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("url")) and bool(self.credentials.get("username")) and bool(
            self.credentials.get("api_token")
        )

    @property
    def _base(self) -> str:
        return self.credentials["url"].rstrip("/")

    @property
    def _auth(self) -> tuple:
        return (self.credentials["username"], self.credentials["api_token"])

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with httpx.AsyncClient(timeout=60.0, auth=self._auth) as client:
            if tool_name == "jenkins.listJobs":
                path = parameters.get("folder") or ""
                suffix = f"/job/{path.replace('/', '/job/')}" if path else ""
                resp = await client.get(f"{self._base}{suffix}/api/json?tree=jobs[name,url,color]")
            elif tool_name == "jenkins.getJob":
                job = parameters["job"].replace("/", "/job/")
                resp = await client.get(
                    f"{self._base}/job/{job}/api/json?tree=name,url,color,healthReport[score,description],lastBuild[number,result,duration,timestamp]"
                )
            elif tool_name == "jenkins.triggerBuild":
                job = parameters["job"].replace("/", "/job/")
                params = parameters.get("parameters") or {}
                if params:
                    resp = await client.post(
                        f"{self._base}/job/{job}/buildWithParameters",
                        params={k: str(v) for k, v in params.items()},
                    )
                else:
                    resp = await client.post(f"{self._base}/job/{job}/build")
                if resp.status_code >= 400:
                    raise RuntimeError(f"Jenkins HTTP {resp.status_code}: {resp.text[:400]}")
                return {
                    "status": "queued",
                    "queue_url": resp.headers.get("Location", ""),
                }
            elif tool_name == "jenkins.buildStatus":
                job = parameters["job"].replace("/", "/job/")
                num = parameters.get("build_number") or "lastBuild"
                resp = await client.get(
                    f"{self._base}/job/{job}/{num}/api/json",
                    params={"tree": "number,result,building,duration,timestamp,url,displayName"},
                )
            elif tool_name == "jenkins.consoleLog":
                job = parameters["job"].replace("/", "/job/")
                num = parameters.get("build_number") or "lastBuild"
                resp = await client.get(f"{self._base}/job/{job}/{num}/consoleText")
                if resp.status_code >= 400:
                    raise RuntimeError(f"Jenkins HTTP {resp.status_code}: {resp.text[:400]}")
                lines = resp.text.splitlines()
                tail = int(parameters.get("tail_lines") or 200)
                return {"lines": lines[-tail:], "total_lines": len(lines)}
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Jenkins HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
