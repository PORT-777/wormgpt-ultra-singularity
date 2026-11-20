"""
Real OAuth 2.0 / OIDC provider descriptors.

Every endpoint below is an official authorization-server endpoint published by
the provider. Nothing here is simulated: if a provider does not expose a
delegated OAuth flow for the capability our plugin uses, it is deliberately
absent from PROVIDERS and the UI reports that honestly.

Client identifiers live exclusively in environment variables:

    <PROVIDER>_CLIENT_ID / <PROVIDER>_CLIENT_SECRET

The frontend only ever receives the public descriptor (scopes, docs, whether
the server has been configured). Secrets never leave this process.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ProviderSpec:
    """Descriptor for one plugin's delegated OAuth integration."""

    plugin_id: str
    group: str
    name: str
    category: str
    icon: str
    description: str
    docs_url: str

    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: Optional[str] = None
    revocation_endpoint: Optional[str] = None

    scopes: Tuple[str, ...] = ()
    # Token-endpoint client authentication: basic | post | none
    token_auth: str = "post"
    # Authorization Code + PKCE (S256)
    pkce: bool = True
    # Whether a refresh_token is issued by this authorization server.
    refresh: bool = True
    # Whether the provider supports OIDC nonce.
    oidc: bool = False

    # Where the resulting access token must be placed for the plugin to use it.
    credential_key: str = "access_token"

    client_id_env: str = ""
    client_secret_env: str = ""

    # OAuth parameter names (TikTok uses client_key / comma scopes).
    client_id_param: str = "client_id"
    token_client_id_field: str = "client_id"
    token_client_secret_field: str = "client_secret"
    scope_separator: str = " "
    scope_param: str = "scope"

    authorize_extra: Dict[str, str] = field(default_factory=dict)
    token_extra: Dict[str, str] = field(default_factory=dict)
    userinfo_method: str = "GET"
    userinfo_body: Optional[Dict[str, Any]] = None
    userinfo_headers: Dict[str, str] = field(default_factory=dict)

    # userinfo | token
    account_source: str = "userinfo"
    account_id_path: str = "id"
    account_name_path: str = "name"
    account_email_path: str = "email"
    account_workspace_path: str = ""

    # Additional capability-specific credentials derived during the callback
    # (page tokens, workspace ids, cloud ids, ...). Values are dot-paths into
    # the userinfo or token response.
    extra_credentials: Dict[str, str] = field(default_factory=dict)

    # Human-readable limitations surfaced in the UI, never hidden.
    notes: str = ""

    # ------------------------------------------------------------------ config

    def client_id(self) -> str:
        return (os.getenv(self.client_id_env) or "").strip()

    def client_secret(self) -> str:
        return (os.getenv(self.client_secret_env) or "").strip()

    def missing_config(self) -> List[str]:
        missing: List[str] = []
        if not self.client_id():
            missing.append(self.client_id_env)
        # Public clients (token_auth == "none") only need the client id.
        if self.token_auth != "none" and not self.client_secret():
            missing.append(self.client_secret_env)
        return missing

    def is_configured(self) -> bool:
        return not self.missing_config()

    def public(self) -> Dict[str, Any]:
        """Frontend-safe descriptor. Never contains a secret value."""
        return {
            "plugin_id": self.plugin_id,
            "group": self.group,
            "name": self.name,
            "category": self.category,
            "icon": self.icon,
            "description": self.description,
            "docs_url": self.docs_url,
            "oauth_supported": True,
            "configured": self.is_configured(),
            "missing_config": self.missing_config(),
            "scopes": list(self.scopes),
            "pkce": self.pkce,
            "refresh": self.refresh,
            "oidc": self.oidc,
            "token_auth": self.token_auth,
            "authorization_endpoint": self.authorization_endpoint,
            "revocation_supported": bool(self.revocation_endpoint),
            "notes": self.notes,
        }

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
#  Google Workspace (OIDC + offline access)
# --------------------------------------------------------------------------- #

_GOOGLE = dict(
    group="google",
    authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    revocation_endpoint="https://oauth2.googleapis.com/revoke",
    token_auth="post",
    pkce=True,
    refresh=True,
    oidc=True,
    client_id_env="GOOGLE_CLIENT_ID",
    client_secret_env="GOOGLE_CLIENT_SECRET",
    authorize_extra={
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    },
    account_id_path="sub",
    account_name_path="name",
    account_email_path="email",
)

_GOOGLE_BASE_SCOPES = (
    "openid",
    "email",
    "profile",
)

# --------------------------------------------------------------------------- #
#  Microsoft identity platform
# --------------------------------------------------------------------------- #

_MICROSOFT = dict(
    group="microsoft",
    authorization_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    token_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/token",
    userinfo_endpoint="https://graph.microsoft.com/v1.0/me",
    token_auth="post",
    pkce=True,
    refresh=True,
    oidc=True,
    client_id_env="MICROSOFT_CLIENT_ID",
    client_secret_env="MICROSOFT_CLIENT_SECRET",
    authorize_extra={"prompt": "select_account"},
    account_id_path="id",
    account_name_path="displayName",
    account_email_path="mail",
)

# --------------------------------------------------------------------------- #
#  Provider registry (keyed by plugin id)
# --------------------------------------------------------------------------- #

PROVIDERS: Dict[str, ProviderSpec] = {}


def _register(spec: ProviderSpec) -> None:
    PROVIDERS[spec.plugin_id] = spec


# ------------------------------- Google ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="google_drive",
        name="Google Drive",
        icon="📁",
        category="productivity",
        description="Browse, search, upload, share and delete Drive files",
        docs_url="https://developers.google.com/drive/api/guides/about-auth",
        scopes=_GOOGLE_BASE_SCOPES + ("https://www.googleapis.com/auth/drive",),
        **_GOOGLE,
    )
)

_register(
    ProviderSpec(
        plugin_id="google_calendar",
        name="Google Calendar",
        icon="📅",
        category="productivity",
        description="Read and create calendar events",
        docs_url="https://developers.google.com/calendar/api/guides/auth",
        scopes=_GOOGLE_BASE_SCOPES + ("https://www.googleapis.com/auth/calendar",),
        **_GOOGLE,
    )
)

_register(
    ProviderSpec(
        plugin_id="google_sheets",
        name="Google Sheets",
        icon="📊",
        category="productivity",
        description="Read and write spreadsheet ranges",
        docs_url="https://developers.google.com/sheets/api/guides/authorizing",
        scopes=_GOOGLE_BASE_SCOPES + ("https://www.googleapis.com/auth/spreadsheets",),
        **_GOOGLE,
    )
)

# ------------------------------- GitHub ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="github",
        group="github",
        name="GitHub",
        icon="🐙",
        category="devops",
        description="Repositories, issues, pull requests and code search",
        docs_url="https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps",
        authorization_endpoint="https://github.com/login/oauth/authorize",
        token_endpoint="https://github.com/login/oauth/access_token",
        userinfo_endpoint="https://api.github.com/user",
        revocation_endpoint="https://api.github.com/applications/{client_id}/token",
        scopes=("read:user", "user:email", "repo"),
        token_auth="post",
        # GitHub OAuth Apps issue non-expiring tokens unless token expiration
        # is enabled on the app; refresh is therefore not assumed.
        pkce=False,
        refresh=False,
        credential_key="token",
        client_id_env="GITHUB_CLIENT_ID",
        client_secret_env="GITHUB_CLIENT_SECRET",
        userinfo_headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        account_id_path="id",
        account_name_path="login",
        account_email_path="email",
        notes="GitHub OAuth App tokens are long-lived; revoke from GitHub settings or Disconnect here.",
    )
)

# ------------------------------- GitLab ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="gitlab",
        group="gitlab",
        name="GitLab",
        icon="🦊",
        category="devops",
        description="Issues, merge requests, pipelines and code search",
        docs_url="https://docs.gitlab.com/ee/api/oauth2.html",
        authorization_endpoint="https://gitlab.com/oauth/authorize",
        token_endpoint="https://gitlab.com/oauth/token",
        userinfo_endpoint="https://gitlab.com/api/v4/user",
        revocation_endpoint="https://gitlab.com/oauth/revoke",
        scopes=("api", "read_user"),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="GITLAB_CLIENT_ID",
        client_secret_env="GITLAB_CLIENT_SECRET",
        account_id_path="id",
        account_name_path="name",
        account_email_path="email",
    )
)

# ------------------------------- Notion ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="notion",
        group="notion",
        name="Notion",
        icon="📓",
        category="productivity",
        description="Pages, databases and knowledge-base entries",
        docs_url="https://developers.notion.com/docs/authorization",
        authorization_endpoint="https://api.notion.com/v1/oauth/authorize",
        token_endpoint="https://api.notion.com/v1/oauth/token",
        userinfo_endpoint=None,
        revocation_endpoint=None,
        scopes=(),
        token_auth="basic",
        pkce=False,
        refresh=False,
        credential_key="access_token",
        client_id_env="NOTION_CLIENT_ID",
        client_secret_env="NOTION_CLIENT_SECRET",
        authorize_extra={"owner": "user"},
        token_extra={"grant_type": "authorization_code"},
        account_source="token",
        account_id_path="bot_id",
        account_name_path="owner.user.name",
        account_email_path="owner.user.person.email",
        account_workspace_path="workspace_name",
        notes="Notion issues non-expiring workspace tokens; revoke access from Notion settings.",
    )
)

# ------------------------------- Slack ------------------------------------- #

_register(
    ProviderSpec(
        plugin_id="slack",
        group="slack",
        name="Slack",
        icon="🖖",
        category="communication",
        description="Post messages and alerts to channels",
        docs_url="https://api.slack.com/authentication/oauth-v2",
        authorization_endpoint="https://slack.com/oauth/v2/authorize",
        token_endpoint="https://slack.com/api/oauth.v2.access",
        userinfo_endpoint="https://slack.com/api/auth.test",
        revocation_endpoint="https://slack.com/api/auth.revoke",
        scopes=("chat:write", "channels:read", "groups:read", "files:write"),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="SLACK_CLIENT_ID",
        client_secret_env="SLACK_CLIENT_SECRET",
        userinfo_method="POST",
        account_source="token",
        account_id_path="team.id",
        account_name_path="team.name",
        account_email_path="",
        account_workspace_path="team.name",
        notes="Messages are sent with the bot token; choose a channel in the plugin call.",
    )
)

# --------------------------- Atlassian Jira -------------------------------- #

_register(
    ProviderSpec(
        plugin_id="jira",
        group="atlassian",
        name="Jira",
        icon="📋",
        category="productivity",
        description="Issues, comments, JQL search and incident tickets",
        docs_url="https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/",
        authorization_endpoint="https://auth.atlassian.com/authorize",
        token_endpoint="https://auth.atlassian.com/oauth/token",
        userinfo_endpoint="https://api.atlassian.com/me",
        scopes=(
            "read:jira-work",
            "write:jira-work",
            "read:jira-user",
            "offline_access",
        ),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="JIRA_CLIENT_ID",
        client_secret_env="JIRA_CLIENT_SECRET",
        authorize_extra={"audience": "api.atlassian.com", "prompt": "consent"},
        account_id_path="account_id",
        account_name_path="name",
        account_email_path="email",
        notes="A cloud site id is discovered automatically after authorization.",
    )
)

# ------------------------------- Linear ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="linear",
        group="linear",
        name="Linear",
        icon="📐",
        category="productivity",
        description="Issues, teams, projects and comments",
        docs_url="https://developers.linear.app/docs/oauth/authentication",
        authorization_endpoint="https://linear.app/oauth/authorize",
        token_endpoint="https://api.linear.app/oauth/token",
        userinfo_endpoint="https://api.linear.app/graphql",
        scopes=("read", "write", "issues:create"),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="LINEAR_CLIENT_ID",
        client_secret_env="LINEAR_CLIENT_SECRET",
        userinfo_method="POST",
        userinfo_body={"query": "query { viewer { id name email } }"},
        account_id_path="data.viewer.id",
        account_name_path="data.viewer.name",
        account_email_path="data.viewer.email",
    )
)

# ------------------------------- Airtable ---------------------------------- #

_register(
    ProviderSpec(
        plugin_id="airtable",
        group="airtable",
        name="Airtable",
        icon="🗃️",
        category="productivity",
        description="Bases, tables, records and schema",
        docs_url="https://airtable.com/developers/web/guides/oauth-integrations",
        authorization_endpoint="https://airtable.com/oauth2/v1/authorize",
        token_endpoint="https://airtable.com/oauth2/v1/token",
        userinfo_endpoint="https://api.airtable.com/v0/meta/whoami",
        scopes=(
            "data.records:read",
            "data.records:write",
            "schema.bases:read",
        ),
        token_auth="basic",
        pkce=True,
        refresh=True,
        # The plugin already uses the token as a Bearer api_key.
        credential_key="api_key",
        client_id_env="AIRTABLE_CLIENT_ID",
        client_secret_env="AIRTABLE_CLIENT_SECRET",
        account_id_path="id",
        account_name_path="email",
        account_email_path="email",
    )
)

# ------------------------------- Sentry ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="sentry",
        group="sentry",
        name="Sentry",
        icon="🛡️",
        category="devops",
        description="Issues, events and project health",
        docs_url="https://docs.sentry.io/product/accounts/auth/",
        authorization_endpoint="https://sentry.io/oauth/authorize/",
        token_endpoint="https://sentry.io/oauth/token/",
        userinfo_endpoint="https://sentry.io/api/0/auth/",
        scopes=("org:read", "project:read", "event:read"),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="auth_token",
        client_id_env="SENTRY_CLIENT_ID",
        client_secret_env="SENTRY_CLIENT_SECRET",
        account_id_path="user.id",
        account_name_path="user.name",
        account_email_path="user.email",
    )
)

# ------------------------------- Vercel ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="vercel",
        group="vercel",
        name="Vercel",
        icon="▲",
        category="devops",
        description="Deployments, projects and environment metadata",
        docs_url="https://vercel.com/docs/integrations/create-integration/oauth",
        authorization_endpoint="https://vercel.com/oauth/authorize",
        token_endpoint="https://api.vercel.com/v2/oauth/access_token",
        userinfo_endpoint="https://api.vercel.com/v2/user",
        scopes=("offline_access",),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="api_key",
        client_id_env="VERCEL_CLIENT_ID",
        client_secret_env="VERCEL_CLIENT_SECRET",
        account_id_path="user.id",
        account_name_path="user.username",
        account_email_path="user.email",
        revocation_endpoint="",
    )
)

# ------------------------------ Microsoft ---------------------------------- #

_register(
    ProviderSpec(
        plugin_id="azure",
        name="Microsoft Azure",
        icon="🟦",
        category="cloud",
        description="Activity logs, Defender alerts, sign-ins and resources",
        docs_url="https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow",
        scopes=("openid", "profile", "email", "offline_access", "https://management.azure.com/.default"),
        **_MICROSOFT,
    )
)

_register(
    ProviderSpec(
        plugin_id="sentinel",
        name="Microsoft Sentinel",
        icon="🛡️",
        category="siem",
        description="KQL queries, incidents, alerts and analytics rules",
        docs_url="https://learn.microsoft.com/en-us/azure/sentinel/rest-api-overview",
        scopes=("openid", "profile", "email", "offline_access", "https://management.azure.com/.default"),
        **_MICROSOFT,
    )
)

_register(
    ProviderSpec(
        plugin_id="teams",
        name="Microsoft Teams",
        icon="🟪",
        category="communication",
        description="Teams, channels, online meetings and channel files via Graph",
        docs_url="https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview",
        scopes=(
            "openid",
            "profile",
            "email",
            "offline_access",
            "User.Read",
            "Team.ReadBasic.All",
            "Channel.ReadBasic.All",
            "OnlineMeetings.ReadWrite",
            "Files.ReadWrite.All",
        ),
        **_MICROSOFT,
    )
)

# ------------------------------- Twitter / X ------------------------------- #

_register(
    ProviderSpec(
        plugin_id="twitter",
        group="twitter",
        name="Twitter / X",
        icon="🐦",
        category="social",
        description="Post, search and monitor conversations",
        docs_url="https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code",
        authorization_endpoint="https://twitter.com/i/oauth2/authorize",
        token_endpoint="https://api.twitter.com/2/oauth2/token",
        userinfo_endpoint="https://api.twitter.com/2/users/me",
        revocation_endpoint="https://api.twitter.com/2/oauth2/revoke",
        scopes=("tweet.read", "tweet.write", "users.read", "offline.access"),
        token_auth="basic",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="TWITTER_CLIENT_ID",
        client_secret_env="TWITTER_CLIENT_SECRET",
        account_id_path="data.id",
        account_name_path="data.name",
        account_email_path="data.username",
    )
)

# ------------------------------- Reddit ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="reddit",
        group="reddit",
        name="Reddit",
        icon="👽",
        category="social",
        description="Search, post and monitor communities",
        docs_url="https://github.com/reddit-archive/reddit/wiki/OAuth2",
        authorization_endpoint="https://www.reddit.com/api/v1/authorize",
        token_endpoint="https://www.reddit.com/api/v1/access_token",
        userinfo_endpoint="https://oauth.reddit.com/api/v1/me",
        revocation_endpoint="https://www.reddit.com/api/v1/revoke_token",
        scopes=("identity", "read", "submit"),
        token_auth="basic",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="REDDIT_CLIENT_ID",
        client_secret_env="REDDIT_CLIENT_SECRET",
        authorize_extra={"duration": "permanent"},
        userinfo_headers={"User-Agent": "WormGPT-Ultra/1.0 (integration)"},
        account_id_path="id",
        account_name_path="name",
        account_email_path="",
    )
)

# ------------------------------- Meta -------------------------------------- #

_META = dict(
    group="meta",
    authorization_endpoint="https://www.facebook.com/v19.0/dialog/oauth",
    token_endpoint="https://graph.facebook.com/v19.0/oauth/access_token",
    userinfo_endpoint="https://graph.facebook.com/v19.0/me",
    token_auth="post",
    pkce=False,
    refresh=False,
    client_id_env="META_CLIENT_ID",
    client_secret_env="META_CLIENT_SECRET",
    account_id_path="id",
    account_name_path="name",
    account_email_path="email",
    notes="Meta issues long-lived user tokens; page/IG identifiers are discovered automatically.",
)

_register(
    ProviderSpec(
        plugin_id="facebook",
        name="Facebook Pages",
        icon="📘",
        category="social",
        description="Publish and manage Facebook Page content",
        docs_url="https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow",
        scopes=(
            "public_profile",
            "email",
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
        ),
        **_META,
    )
)

_register(
    ProviderSpec(
        plugin_id="instagram",
        name="Instagram",
        icon="📸",
        category="social",
        description="Publish and inspect Instagram Business content",
        docs_url="https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login",
        scopes=(
            "public_profile",
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "business_management",
        ),
        **_META,
    )
)

_register(
    ProviderSpec(
        plugin_id="threads",
        group="threads",
        name="Threads",
        icon="🧵",
        category="social",
        description="Publish and inspect Threads posts",
        docs_url="https://developers.facebook.com/docs/threads/get-started",
        authorization_endpoint="https://threads.net/oauth/authorize",
        token_endpoint="https://graph.threads.net/oauth/access_token",
        userinfo_endpoint="https://graph.threads.net/v1.0/me",
        token_auth="post",
        pkce=False,
        refresh=True,
        client_id_env="THREADS_CLIENT_ID",
        client_secret_env="THREADS_CLIENT_SECRET",
        account_id_path="id",
        account_name_path="username",
        account_email_path="",
        notes="Threads user id is written into the plugin automatically.",
    )
)

# ------------------------------- LinkedIn ---------------------------------- #

_register(
    ProviderSpec(
        plugin_id="linkedin",
        group="linkedin",
        name="LinkedIn",
        icon="💼",
        category="social",
        description="Profile access and member posts",
        docs_url="https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow",
        authorization_endpoint="https://www.linkedin.com/oauth/v2/authorization",
        token_endpoint="https://www.linkedin.com/oauth/v2/accessToken",
        userinfo_endpoint="https://api.linkedin.com/v2/userinfo",
        scopes=("openid", "profile", "email", "w_member_social"),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="LINKEDIN_CLIENT_ID",
        client_secret_env="LINKEDIN_CLIENT_SECRET",
        account_id_path="sub",
        account_name_path="name",
        account_email_path="email",
    )
)

# ------------------------------- TikTok ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="tiktok",
        group="tiktok",
        name="TikTok",
        icon="🎵",
        category="social",
        description="Publish and inspect TikTok videos",
        docs_url="https://developers.tiktok.com/doc/oauth-user-access-token-management",
        authorization_endpoint="https://www.tiktok.com/v2/auth/authorize/",
        token_endpoint="https://open.tiktokapis.com/v2/oauth/token/",
        userinfo_endpoint="https://open.tiktokapis.com/v2/user/info/",
        revocation_endpoint="https://open.tiktokapis.com/v2/oauth/revoke/",
        scopes=("user.info.basic", "video.publish", "video.upload"),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="TIKTOK_CLIENT_ID",
        client_secret_env="TIKTOK_CLIENT_SECRET",
        client_id_param="client_key",
        token_client_id_field="client_key",
        scope_separator=",",
        authorize_extra={"disable_auto_auth": "1"},
        userinfo_method="GET",
        account_id_path="data.user.open_id",
        account_name_path="data.user.display_name",
        account_email_path="",
    )
)


# ------------------------------- Dropbox ----------------------------------- #

_register(
    ProviderSpec(
        plugin_id="dropbox",
        group="dropbox",
        name="Dropbox",
        icon="📦",
        category="productivity",
        description="Browse, search, upload and share Dropbox files",
        docs_url="https://www.dropbox.com/developers/documentation/http/documentation",
        authorization_endpoint="https://www.dropbox.com/oauth2/authorize",
        token_endpoint="https://api.dropboxapi.com/oauth2/token",
        userinfo_endpoint="https://api.dropboxapi.com/2/users/get_current_account",
        revocation_endpoint="https://api.dropboxapi.com/2/auth/token/revoke",
        scopes=(
            "account_info.read",
            "files.metadata.read",
            "files.content.read",
            "files.content.write",
            "sharing.read",
            "sharing.write",
        ),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="DROPBOX_CLIENT_ID",
        client_secret_env="DROPBOX_CLIENT_SECRET",
        authorize_extra={"token_access_type": "offline"},
        userinfo_method="POST",
        userinfo_body=None,
        account_id_path="account_id",
        account_name_path="name.display_name",
        account_email_path="email",
    )
)

# ------------------------------- Spotify ----------------------------------- #

_register(
    ProviderSpec(
        plugin_id="spotify",
        group="spotify",
        name="Spotify",
        icon="🎧",
        category="social",
        description="Search music, manage playlists and inspect your profile",
        docs_url="https://developer.spotify.com/documentation/web-api",
        authorization_endpoint="https://accounts.spotify.com/authorize",
        token_endpoint="https://accounts.spotify.com/api/token",
        userinfo_endpoint="https://api.spotify.com/v1/me",
        scopes=(
            "user-read-email",
            "user-read-private",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
        ),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="SPOTIFY_CLIENT_ID",
        client_secret_env="SPOTIFY_CLIENT_SECRET",
        account_id_path="id",
        account_name_path="display_name",
        account_email_path="email",
    )
)

# ------------------------------- HubSpot ----------------------------------- #

_register(
    ProviderSpec(
        plugin_id="hubspot",
        group="hubspot",
        name="HubSpot",
        icon="🧲",
        category="marketing",
        description="Read and create CRM contacts and deals",
        docs_url="https://developers.hubspot.com/docs/api/crm/understanding-the-crm",
        authorization_endpoint="https://app.hubspot.com/oauth/authorize",
        token_endpoint="https://api.hubapi.com/oauth/v1/token",
        # HubSpot exposes identity via a token-in-path endpoint.
        userinfo_endpoint="https://api.hubapi.com/oauth/v1/access-tokens/{access_token}",
        scopes=("crm.objects.contacts.read", "crm.objects.contacts.write", "crm.objects.deals.read", "crm.objects.deals.write"),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="HUBSPOT_CLIENT_ID",
        client_secret_env="HUBSPOT_CLIENT_SECRET",
        account_id_path="hub_id",
        account_name_path="user",
        account_email_path="user",
        account_workspace_path="hub_domain",
    )
)

# ------------------------------ Salesforce --------------------------------- #

_register(
    ProviderSpec(
        plugin_id="salesforce",
        group="salesforce",
        name="Salesforce",
        icon="☁️",
        category="marketing",
        description="Run SOQL queries and manage Salesforce records",
        docs_url="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest",
        authorization_endpoint="https://login.salesforce.com/services/oauth2/authorize",
        token_endpoint="https://login.salesforce.com/services/oauth2/token",
        userinfo_endpoint="https://login.salesforce.com/services/oauth2/userinfo",
        revocation_endpoint="https://login.salesforce.com/services/oauth2/revoke",
        scopes=("api", "refresh_token", "offline_access"),
        token_auth="post",
        pkce=True,
        refresh=True,
        credential_key="access_token",
        client_id_env="SALESFORCE_CLIENT_ID",
        client_secret_env="SALESFORCE_CLIENT_SECRET",
        # The token response carries the org-specific API host.
        extra_credentials={"instance_url": "instance_url"},
        account_id_path="user_id",
        account_name_path="name",
        account_email_path="email",
    )
)

# -------------------------------- Asana ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="asana",
        group="asana",
        name="Asana",
        icon="🔺",
        category="productivity",
        description="Manage Asana projects, tasks and workspaces",
        docs_url="https://developers.asana.com/docs",
        authorization_endpoint="https://app.asana.com/-/oauth_authorize",
        token_endpoint="https://app.asana.com/-/oauth_token",
        userinfo_endpoint="https://app.asana.com/api/1.0/users/me",
        scopes=(),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="ASANA_CLIENT_ID",
        client_secret_env="ASANA_CLIENT_SECRET",
        account_id_path="data.gid",
        account_name_path="data.name",
        account_email_path="data.email",
    )
)

# -------------------------------- ClickUp ---------------------------------- #

_register(
    ProviderSpec(
        plugin_id="clickup",
        group="clickup",
        name="ClickUp",
        icon="✅",
        category="productivity",
        description="Manage ClickUp spaces, lists and tasks",
        docs_url="https://clickup.com/api",
        authorization_endpoint="https://app.clickup.com/api",
        token_endpoint="https://api.clickup.com/api/v2/oauth/token",
        userinfo_endpoint="https://api.clickup.com/api/v2/user",
        scopes=(),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="CLICKUP_CLIENT_ID",
        client_secret_env="CLICKUP_CLIENT_SECRET",
        account_id_path="user.id",
        account_name_path="user.username",
        account_email_path="user.email",
    )
)

# ------------------------------- Monday.com -------------------------------- #

_register(
    ProviderSpec(
        plugin_id="monday",
        group="monday",
        name="Monday.com",
        icon="🟣",
        category="productivity",
        description="Manage Monday.com boards, items and updates",
        docs_url="https://developer.monday.com/api-reference/docs",
        authorization_endpoint="https://auth.monday.com/oauth2/authorize",
        token_endpoint="https://auth.monday.com/oauth2/token",
        userinfo_endpoint="https://api.monday.com/v2",
        scopes=("boards:read", "boards:write"),
        token_auth="post",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="MONDAY_CLIENT_ID",
        client_secret_env="MONDAY_CLIENT_SECRET",
        userinfo_method="POST",
        userinfo_body={"query": "query { me { id name email } }"},
        account_id_path="data.me.id",
        account_name_path="data.me.name",
        account_email_path="data.me.email",
    )
)

# --------------------------------- Zoom ------------------------------------ #

_register(
    ProviderSpec(
        plugin_id="zoom",
        group="zoom",
        name="Zoom",
        icon="🎥",
        category="communication",
        description="Schedule meetings and inspect recordings",
        docs_url="https://developers.zoom.us/docs/api/",
        authorization_endpoint="https://zoom.us/oauth/authorize",
        token_endpoint="https://zoom.us/oauth/token",
        userinfo_endpoint="https://api.zoom.us/v2/users/me",
        revocation_endpoint="https://zoom.us/oauth/revoke",
        scopes=("meeting:read", "meeting:write", "user:read", "recording:read"),
        token_auth="basic",
        pkce=False,
        refresh=True,
        credential_key="access_token",
        client_id_env="ZOOM_CLIENT_ID",
        client_secret_env="ZOOM_CLIENT_SECRET",
        account_id_path="id",
        account_name_path="display_name",
        account_email_path="email",
    )
)

# --------------------------------------------------------------------------- #
#  Providers that honestly do not expose the needed delegated OAuth flow.
# --------------------------------------------------------------------------- #

NO_OAUTH_REASONS: Dict[str, str] = {
    "whatsapp": (
        "WhatsApp Cloud API authenticates with a Meta system-user token tied to a "
        "verified business account; there is no user-delegated OAuth flow for this plugin."
    ),
    "discord": (
        "Discord's OAuth identifies users and adds bots to guilds, but message "
        "delivery for this plugin uses an incoming webhook. Connect Discord with a "
        "webhook URL instead."
    ),
    "teams": (
        "Microsoft Teams now supports Graph OAuth for teams/channels, online "
        "meetings and channel files; the messaging tools still use incoming "
        "webhooks, so a webhook URL remains the fastest setup."
    ),
    "trello": (
        "Trello only offers OAuth 1.0a. This subsystem implements OAuth 2.0 / OIDC, "
        "so Trello remains API-key based."
    ),
    "splunk": (
        "Splunk uses its own token/credential scheme, not delegated OAuth 2.0."
    ),
    "wazuh": (
        "Wazuh uses local API users and JWT credentials, not an external OAuth 2.0 "
        "identity provider."
    ),
}


def get_provider(plugin_id: str) -> Optional[ProviderSpec]:
    return PROVIDERS.get(plugin_id)


def provider_catalog() -> List[Dict[str, Any]]:
    return [spec.public() for spec in sorted(PROVIDERS.values(), key=lambda s: (s.category, s.name))]


def no_oauth_reason(plugin_id: str) -> str:
    return NO_OAUTH_REASONS.get(
        plugin_id,
        "This integration has no official user-delegated OAuth 2.0 authorization "
        "server for the capabilities exposed by its tools.",
    )
