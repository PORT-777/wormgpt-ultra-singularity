from typing import Any, Dict, List, Optional
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


@register_plugin
class DevOpsPlugin(BasePlugin):
    manifest = PluginManifest(
        id="devops",
        name="DevOps & CI/CD",
        description="Manage builds, deployments, and infrastructure",
        long_description=(
            "End-to-end DevOps control: trigger Jenkins jobs, manage Vercel "
            "deployments, monitor Sentry errors, and track Datadog metrics. "
            "Automate the lifecycle of your software from code to cloud."
        ),
        version="1.0.0",
        author="outcome",
        icon="⚙️",
        category="devops",
        tags=["devops", "jenkins", "vercel", "sentry", "datadog", "ci", "cd"],
        auth_type="apikey",
        auth_config={"api_key_field": "api_key"},
        tools=[
            PluginTool(
                name="devops.jenkins_build",
                display_name="Trigger Jenkins Job",
                description="Start a Jenkins build or trigger a parameterized job",
                parameters={
                    "url": {"type": "string", "description": "Jenkins job URL"},
                    "user": {"type": "string"},
                    "token": {"type": "string"},
                    "params": {"type": "object", "description": "Job parameters"},
                },
            ),
            PluginTool(
                name="devops.vercel_deployments",
                display_name="Vercel Deployments",
                description="List recent deployments for a project",
                parameters={
                    "project_id": {"type": "string"},
                    "limit": {"type": "integer", "description": "Default 10"},
                },
            ),
            PluginTool(
                name="devops.sentry_issues",
                display_name="Sentry Issues",
                description="Fetch recent errors and issues from Sentry",
                parameters={
                    "org_slug": {"type": "string"},
                    "project_slug": {"type": "string"},
                    "limit": {"type": "integer", "description": "Default 20"},
                },
            ),
            PluginTool(
                name="devops.datadog_metrics",
                display_name="Datadog Metrics",
                description="Query time-series metrics from Datadog",
                parameters={
                    "query": {"type": "string", "description": "e.g. avg:system.cpu.idle{host:myhost}"},
                    "from": {"type": "integer", "description": "Unix timestamp"},
                    "to": {"type": "integer", "description": "Unix timestamp"},
                },
            ),
        ],
        website_url="https://www.jenkins.io",
        docs_url="https://www.jenkins.io/doc/",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("api_key"))

    async def execute(self, tool_name: str, parameters:Dict[str, Any]) -> Any:
        # Simulating common DevOps orchestration logic
        if tool_name == "devops.jenkins_build":
            return {"status": "triggered", "job_url": parameters.get("url")}
        
        if tool_name == "devops.vercel_deployments":
            return {"deployments": [{"id": "d_123", "status": "ready", "url": "https://myapp.vercel.app"}]}

        if tool_name == "devops.sentry_issues":
            return {"issues": [{"id": "issue_1", "title": "NullPointerException at Auth", "level": "error"}]}

        if tool_name == "devops.datadog_metrics":
            return {"metrics": [{"timestamp": 1700000000, "value": 42.5}]}

        raise ValueError(f"Unknown devops tool: {tool_name}")
