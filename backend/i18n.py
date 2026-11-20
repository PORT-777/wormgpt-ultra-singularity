"""Simple i18n locale store (backend-side message catalog)."""
from __future__ import annotations

LOCALES: dict = {
    "en": {"greeting": "Hello", "error": "Error", "loading": "Loading..."},
    "ar": {"greeting": "مرحبا", "error": "خطأ", "loading": "جارٍ التحميل..."},
}

USER_LANG: dict = {}


def set_user_lang(user: str, lang: str) -> None:
    USER_LANG[user] = lang


def get_user_lang(user: str) -> str:
    return USER_LANG.get(user, "en")


def t(key: str, lang: str = "en") -> str:
    return LOCALES.get(lang, LOCALES["en"]).get(key, key)


def add_locale(lang: str, messages: dict) -> None:
    LOCALES.setdefault(lang, {}).update(messages)


def list_locales() -> list:
    return list(LOCALES.keys())
