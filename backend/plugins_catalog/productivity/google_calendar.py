from typing import Any, Dict
import httpx

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin

BASE = "https://www.googleapis.com/calendar/v3"


@register_plugin
class GoogleCalendarPlugin(BasePlugin):
    manifest = PluginManifest(
        id="google_calendar",
        name="Google Calendar",
        description="List, create, update and delete events; check free/busy",
        long_description=(
            "Calendar v3: read upcoming events across a time window, create events "
            "with attendees and reminders, patch or delete them, list calendars and "
            "query free/busy blocks for scheduling."
        ),
        version="1.0.0",
        author="outcome",
        icon="📅",
        category="productivity",
        tags=["productivity", "google", "calendar", "scheduling", "events"],
        auth_type="oauth2",
        auth_config={"token_field": "access_token"},
        tools=[
            PluginTool(
                name="google_calendar.listEvents",
                display_name="List Events",
                description="List events in a time range (RFC3339 timestamps)",
                parameters={
                    "calendar_id": {"type": "string", "description": "Default primary"},
                    "time_min": {"type": "string"},
                    "time_max": {"type": "string"},
                    "max_results": {"type": "integer", "description": "Default 25"},
                    "query": {"type": "string"},
                },
            ),
            PluginTool(
                name="google_calendar.createEvent",
                display_name="Create Event",
                description="Create an event with start/end, attendees and location",
                parameters={
                    "summary": {"type": "string"},
                    "start": {"type": "string", "description": "RFC3339, e.g. 2026-01-01T10:00:00Z"},
                    "end": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                    "attendees": {"type": "array", "description": "Email addresses"},
                    "calendar_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="google_calendar.updateEvent",
                display_name="Update Event",
                description="Patch an event's summary, time or description",
                parameters={
                    "event_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "description": {"type": "string"},
                    "calendar_id": {"type": "string"},
                },
            ),
            PluginTool(
                name="google_calendar.deleteEvent",
                display_name="Delete Event",
                description="Delete an event by id",
                parameters={"event_id": {"type": "string"}, "calendar_id": {"type": "string"}},
            ),
            PluginTool(
                name="google_calendar.listCalendars",
                display_name="List Calendars",
                description="List calendars the user can access with their roles",
                parameters={},
            ),
            PluginTool(
                name="google_calendar.freeBusy",
                display_name="Free / Busy",
                description="Query busy intervals for one or more calendars",
                parameters={
                    "time_min": {"type": "string"},
                    "time_max": {"type": "string"},
                    "calendar_ids": {"type": "array"},
                },
            ),
        ],
        website_url="https://calendar.google.com",
        docs_url="https://developers.google.com/calendar/api/v3/reference",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return bool(self.credentials.get("access_token"))

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.credentials['access_token']}",
            "Content-Type": "application/json",
        }

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        headers = self._headers
        cal = parameters.get("calendar_id") or "primary"
        async with httpx.AsyncClient(timeout=60.0) as client:
            if tool_name == "google_calendar.listEvents":
                params: Dict[str, Any] = {
                    "singleEvents": True,
                    "orderBy": "startTime",
                    "maxResults": min(int(parameters.get("max_results") or 25), 250),
                }
                if parameters.get("time_min"):
                    params["timeMin"] = parameters["time_min"]
                if parameters.get("time_max"):
                    params["timeMax"] = parameters["time_max"]
                if parameters.get("query"):
                    params["q"] = parameters["query"]
                resp = await client.get(
                    f"{BASE}/calendars/{cal}/events", headers=headers, params=params
                )
            elif tool_name == "google_calendar.createEvent":
                body: Dict[str, Any] = {
                    "summary": parameters["summary"],
                    "start": {"dateTime": parameters["start"]},
                    "end": {"dateTime": parameters["end"]},
                }
                if parameters.get("description"):
                    body["description"] = parameters["description"]
                if parameters.get("location"):
                    body["location"] = parameters["location"]
                if parameters.get("attendees"):
                    body["attendees"] = [{"email": e} for e in parameters["attendees"]]
                resp = await client.post(
                    f"{BASE}/calendars/{cal}/events", headers=headers, json=body
                )
            elif tool_name == "google_calendar.updateEvent":
                patch: Dict[str, Any] = {}
                if parameters.get("summary"):
                    patch["summary"] = parameters["summary"]
                if parameters.get("description") is not None:
                    patch["description"] = parameters["description"]
                if parameters.get("start"):
                    patch["start"] = {"dateTime": parameters["start"]}
                if parameters.get("end"):
                    patch["end"] = {"dateTime": parameters["end"]}
                resp = await client.patch(
                    f"{BASE}/calendars/{cal}/events/{parameters['event_id']}",
                    headers=headers,
                    json=patch,
                )
            elif tool_name == "google_calendar.deleteEvent":
                resp = await client.delete(
                    f"{BASE}/calendars/{cal}/events/{parameters['event_id']}", headers=headers
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"Calendar HTTP {resp.status_code}: {resp.text[:400]}")
                return {"status": "deleted", "event_id": parameters["event_id"]}
            elif tool_name == "google_calendar.listCalendars":
                resp = await client.get(
                    f"{BASE}/users/me/calendarList", headers=headers
                )
            elif tool_name == "google_calendar.freeBusy":
                resp = await client.post(
                    f"{BASE}/freeBusy",
                    headers=headers,
                    json={
                        "timeMin": parameters["time_min"],
                        "timeMax": parameters["time_max"],
                        "items": [
                            {"id": c} for c in (parameters.get("calendar_ids") or ["primary"])
                        ],
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if resp.status_code >= 400:
                raise RuntimeError(f"Calendar HTTP {resp.status_code}: {resp.text[:400]}")
            return resp.json()
