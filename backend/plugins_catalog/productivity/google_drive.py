from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"


@register_plugin
class GoogleDrivePlugin(BasePlugin):
    manifest = PluginManifest(
        id="google_drive",
        name="Google Drive",
        description="List, search, create, share and delete Drive files",
        long_description=(
            "Drive v3 with an OAuth access token: browse and search files with Drive "
            "query syntax, inspect metadata, create folders, upload text as a document, "
            "share with users and clean up files."
        ),
        version="1.0.0",
        author="outcome",
        icon="📁",
        category="productivity",
        tags=["productivity", "google", "drive", "files", "storage"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token"},
        tools=[
            PluginTool(
                name="google_drive.listFiles",
                display_name="List Files",
                description="List files in a folder (or root) with pagination",
                parameters={
                    "folder_id": {"type": "string", "description": "Default root"},
                    "page_size": {"type": "integer", "description": "Default 50, max 1000"},
                    "page_token": {"type": "string"},
                },
            ),
            PluginTool(
                name="google_drive.search",
                display_name="Search",
                description="Search with Drive query syntax, e.g. name contains 'report'",
                parameters={
                    "query": {"type": "string"},
                    "page_size": {"type": "integer"},
                },
            ),
            PluginTool(
                name="google_drive.getFile",
                display_name="File Metadata",
                description="Get name, mime type, size, owners and web link for a file",
                parameters={"file_id": {"type": "string"}},
            ),
            PluginTool(
                name="google_drive.createFolder",
                display_name="Create Folder",
                description="Create a folder, optionally inside another folder",
                parameters={"name": {"type": "string"}, "parent_id": {"type": "string"}},
            ),
            PluginTool(
                name="google_drive.uploadText",
                display_name="Upload Text",
                description="Upload plain text as a file (optionally converted to a Google Doc)",
                parameters={
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                    "mime_type": {"type": "string", "description": "text/plain or application/vnd.google-apps.document"},
                    "parent_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="google_drive.share",
                display_name="Share",
                description="Grant reader/writer access to an email address or make it public",
                parameters={
                    "file_id": {"type": "string"},
                    "email": {"type": "string"},
                    "role": {"type": "string", "description": "reader | writer | commenter"},
                    "type": {"type": "string", "description": "user | anyone"},
                },
            ),
            PluginTool(
                name="google_drive.delete",
                display_name="Delete",
                description="Permanently delete a file by id",
                parameters={"file_id": {"type": "string"}},
            ),
        ],
        website_url="https://drive.google.com",
        docs_url="https://developers.google.com/drive/api/reference/rest/v3",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.credentials['access_token']}"}

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "google_drive.listFiles":
                folder = parameters.get("folder_id") or "root"
                resp = await client.get(
                    f"{BASE}/files",
                    headers=headers,
                    params={
                        "q": f"'{folder}' in parents and trashed = false",
                        "pageSize": min(int(parameters.get("page_size") or 50), 1000),
                        "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,webViewLink)",
                        **({"pageToken": parameters["page_token"]} if parameters.get("page_token") else {}),
                    },
                )
            elif tool_name == "google_drive.search":
                resp = await client.get(
                    f"{BASE}/files",
                    headers=headers,
                    params={
                        "q": parameters.get("query", ""),
                        "pageSize": min(int(parameters.get("page_size") or 50), 1000),
                        "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,webViewLink)",
                    },
                )
            elif tool_name == "google_drive.getFile":
                resp = await client.get(
                    f"{BASE}/files/{parameters['file_id']}",
                    headers=headers,
                    params={
                        "fields": "id,name,mimeType,size,createdTime,modifiedTime,owners,webViewLink,parents"
                    },
                )
            elif tool_name == "google_drive.createFolder":
                body = {
                    "name": parameters["name"],
                    "mimeType": "application/vnd.google-apps.folder",
                }
                if parameters.get("parent_id"):
                    body["parents"] = [parameters["parent_id"]]
                resp = await client.post(f"{BASE}/files", headers=headers, json=body)
            elif tool_name == "google_drive.uploadText":
                metadata: Dict[str, Any] = {"name": parameters["name"]}
                if parameters.get("parent_id"):
                    metadata["parents"] = [parameters["parent_id"]]
                mime = parameters.get("mime_type") or "text/plain"
                resp = await client.post(
                    f"{UPLOAD}/files",
                    headers=headers,
                    params={"uploadType": "multipart", "fields": "id,name,mimeType,webViewLink"},
                    files={
                        "metadata": ("metadata.json", _json(metadata), "application/json"),
                        "file": ("content.txt", parameters.get("content", ""), mime),
                    },
                )
            elif tool_name == "google_drive.share":
                body = {
                    "role": parameters.get("role") or "reader",
                    "type": parameters.get("type") or "user",
                }
                if body["type"] == "user":
                    body["emailAddress"] = parameters["email"]
                resp = await client.post(
                    f"{BASE}/files/{parameters['file_id']}/permissions",
                    headers=headers,
                    json=body,
                    params={"sendNotificationEmail": bool(parameters.get("email"))},
                )
            elif tool_name == "google_drive.delete":
                resp = await client.delete(
                    f"{BASE}/files/{parameters['file_id']}", headers=headers
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Drive HTTP {resp.status_code}: {resp.text[:400]}")
                return {"status": "deleted", "file_id": parameters["file_id"]}
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Drive HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()


def _json(data: Dict[str, Any]) -> str:
    import json

    return json.dumps(data)
