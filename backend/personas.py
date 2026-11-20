"""Personas: named system-prompt presets with real effect."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

PERSONAS: Dict[str, dict] = {
    "programmer": {"id": "programmer", "name": "Programmer", "system_prompt": "You are an expert software engineer. Write clean, correct, production-ready code. Explain concisely.", "icon": "code"},
    "researcher": {"id": "researcher", "name": "Researcher", "system_prompt": "You are a meticulous researcher. Cite sources, verify claims, present balanced analysis.", "icon": "search"},
    "creative_writer": {"id": "creative_writer", "name": "Creative Writer", "system_prompt": "You are a creative writing partner. Rich prose, vivid imagery, strong character voice.", "icon": "pen"},
    "data_analyst": {"id": "data_analyst", "name": "Data Analyst", "system_prompt": "You are a data analyst. Interpret data, find patterns, present clear insights with numbers.", "icon": "chart"},
    "study_assistant": {"id": "study_assistant", "name": "Study Assistant", "system_prompt": "You are a patient study tutor. Explain step-by-step, use examples, check understanding.", "icon": "book"},
    "general": {"id": "general", "name": "General Assistant", "system_prompt": "You are a helpful, accurate assistant.", "icon": "chat"},
}


def list_all() -> List[dict]:
    return list(PERSONAS.values())


def get(pid: str) -> Optional[dict]:
    return PERSONAS.get(pid)


def create(name: str, system_prompt: str, icon: str = "chat") -> dict:
    pid = uuid.uuid4().hex[:12]
    p = {"id": pid, "name": name, "system_prompt": system_prompt, "icon": icon,
         "created_at": time.time()}
    PERSONAS[pid] = p
    return p


def update(pid: str, **fields) -> Optional[dict]:
    p = PERSONAS.get(pid)
    if not p:
        return None
    for k, v in fields.items():
        if k in p and k != "id":
            p[k] = v
    return p


def delete(pid: str) -> bool:
    if pid in ("programmer", "researcher", "creative_writer", "data_analyst",
               "study_assistant", "general"):
        return False
    return PERSONAS.pop(pid, None) is not None
