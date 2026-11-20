from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class PluginTool(BaseModel):
    """A single tool/action a plugin provides to the agent"""
    name: str                                   # e.g. virustotal.lookupHash
    display_name: Optional[str] = None          # falls back to name if absent
    description: str                            # what it does (the agent reads this)
    parameters: Dict[str, Any] = {}             # JSON Schema of parameters
    requires_auth: bool = True                  # needs plugin to be authenticated

    def model_post_init(self, __context: Any) -> None:
        if not self.display_name:
            # Derive a readable label from the tool suffix, e.g. "lookupHash"
            suffix = self.name.split(".", 1)[-1]
            self.display_name = suffix

class PluginManifest(BaseModel):
    """Plugin definition — describes everything about a plugin"""
    id: str                      # Unique ID: virustotal
    name: str                    # Display name: VirusTotal
    description: str             # Short description
    long_description: str        # Full description shown in store
    version: str                 # Semver: 1.0.0
    author: str
    icon: str                    # URL or emoji
    category: str                # security | social | productivity | communication | devops | cloud | siem | custom
    tags: List[str]              # ['threat-intel', 'malware', 'ioc']
    auth_type: str               # apikey | oauth2 | webhook | none
    auth_config: Dict[str, Any]  # OAuth endpoints, API key field names, etc.
    tools: List[PluginTool]      # All tools this plugin provides
    website_url: str
    docs_url: str
    is_free: bool = True
    is_official: bool = False    # Built by the agent team

class BasePlugin(ABC):
    """Base class all plugins inherit from"""

    manifest: PluginManifest

    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials or {}
        if not self._validate_credentials():
            raise ValueError(
                f"invalid or missing credentials for plugin '{self.manifest.id}'"
            )

    @abstractmethod
    def _validate_credentials(self) -> bool:
        """Verify credentials are valid"""
        pass

    @abstractmethod
    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool call"""
        pass

    async def test_connection(self) -> Dict[str, Any]:
        """Test if plugin connection works"""
        return {"status": "ok", "message": "Connection successful"}
