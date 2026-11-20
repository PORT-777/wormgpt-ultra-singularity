import asyncio
import logging
import sys

logging.basicConfig(level=logging.ERROR)

from plugins_system.registry import registry_instance


async def main() -> None:
    await registry_instance.discover_plugins()
    reports = await registry_instance.validate_all_plugins()
    bad = {pid: r["errors"] for pid, r in reports.items() if not r["valid"]}
    print(f"TOTAL={len(reports)} VALID={len(reports) - len(bad)} INVALID={len(bad)}")
    for pid, errs in bad.items():
        print(f"  !! {pid}: {errs}")

    manifests = registry_instance.get_all_manifests()
    by_cat = {}
    for m in manifests:
        by_cat.setdefault(m["category"], []).append(m["id"])
    for cat in sorted(by_cat):
        print(f"  {cat:14s} {len(by_cat[cat]):3d}  {', '.join(sorted(by_cat[cat]))}")

    creds = {
        "api_key": "x", "access_token": "x", "token": "x", "api_token": "x",
        "auth_token": "x", "app_password": "x", "handle": "x", "user": "x",
        "password": "x", "url": "https://example.com", "username": "x",
        "account_sid": "x", "threads_user_id": "x", "phone_number_id": "x",
        "ig_user_id": "x", "page_token": "x", "page_id": "x", "client_id": "x",
        "client_secret": "x", "app_key": "x", "key": "x", "instance": "x",
        "base_id": "x", "org_slug": "x", "homeserver": "x", "from_number": "x",
    }
    for pid, cls in sorted(registry_instance._plugins.items()):
        try:
            cls(creds)
        except Exception as exc:
            print(f"  __init__ FAIL {pid}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
