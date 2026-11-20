from typing import Any, Dict, List, Optional
import subprocess
from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

@register_plugin
class GitPlugin(BasePlugin):
    manifest = PluginManifest(
        id="git",
        name="Git Controller",
        description="Manage repositories: clone, commit, push, pull, and branch",
        long_description=(
            "Full Git workflow integration: clone remote repositories into the "
            "workspace, manage local branches, stage changes, commit with messages, "
            "push/pull to/from remotes, and view log history."
        ),
        version="1.0.0",
        author="outcome",
        icon="Git",
        category="git",
        tags=["git", "version-control", "devops", "repository"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="git.clone",
                display_name="Clone Repo",
                description="Clone a remote repository into a new directory",
                parameters={
                    "url": {"type": "string"},
                    "directory": {"type": "string"},
                },
            ),
            PluginTool(
                name="git.status",
                display_name="Status",
                description="Show current repository status",
                parameters={"directory": {"type": "string"}},
            ),
            PluginTool(
                name="git.add",
                display_name="Stage Files",
                description="Add files to the staging area",
                parameters={
                    "directory": {"type": "string"},
                    "files": {"type": "array", "description": "List of file paths or '.' for all"},
                },
            ),
            PluginTool(
                name="git.commit",
                display_name="Commit",
                description="Commit staged changes with a message",
                parameters={
                    "directory": {"type": "string"},
                    "message": {"type": "string"},
                },
            ),
            PluginTool(
                name="git.push",
                display_name="Push",
                description="Push commits to the remote repository",
                parameters={
                    "directory": {"type": "string"},
                    "remote": {"type": "string", "description": "Default 'origin'"},
                    "branch": {"type": "string", "description": "Default 'main'"},
                },
            ),
            PluginTool(
                name="git.pull",
                display_name="Pull",
                description="Pull changes from the remote repository",
                parameters={
                    "directory": {"type": "string"},
                    "remote": {"type": "string", "description": "Default 'origin'"},
                    "branch": {"type": "string", "description": "Default 'main'"},
                },
            ),
            PluginTool(
                name="git.log",
                display_name="Log History",
                description="View the commit history",
                parameters={
                    "directory": {"type": "string"},
                    "limit": {"type": "integer", "description": "Number of commits to show"},
                },
            ),
        ],
        website_url="https://git-scm.com",
        docs_url="https://git-scm.com/doc",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def _run_command(self, cmd: List[str], cwd: str) -> str:
        import asyncio
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"Git command failed: {stderr.decode().strip()}")
        return stdout.decode().strip()

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        cwd = parameters.get("directory", ".")

        if tool_name == "git.clone":
            target = parameters["directory"]
            return await self._run_command(["git", "clone", parameters["url"], target], cwd=".")

        if tool_name == "git.status":
            return await self._run_command(["git", "status"], cwd)

        if tool_name == "git.add":
            files = parameters.get("files", ["."])
            cmd = ["git", "add"] + files
            return await self._run_command(cmd, cwd)

        if tool_name == "git.commit":
            return await self._run_command(["git", "commit", "-m", parameters["message"]], cwd)

        if tool_name == "git.push":
            return await self._run_command(
                ["git", "push", parameters.get("remote", "origin"), parameters.get("branch", "main")],
                cwd
            )

        if tool_name == "git.pull":
            return await self._run_command(
                ["git", "pull", parameters.get("remote", "origin"), parameters.get("branch", "main")],
                cwd
            )

        if tool_name == "git.log":
            limit = parameters.get("limit", 10)
            return await self._run_command(["git", "log", f"-n {limit}", "--oneline"], cwd)

        raise ValueError(f"Unknown git tool: {tool_name}")
