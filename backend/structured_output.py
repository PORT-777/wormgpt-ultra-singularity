"""Structured output validation (JSON Schema-lite)."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional


def validate(data: Any, schema: Dict) -> dict:
    errors = []
    typ = schema.get("type")
    if typ == "object":
        if not isinstance(data, dict):
            errors.append("expected object")
            return {"valid": False, "errors": errors}
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"missing required: {req}")
        props = schema.get("properties", {})
        for k, v in data.items():
            if k in props:
                r = validate(v, props[k])
                if not r["valid"]:
                    for e in r["errors"]:
                        errors.append(f"{k}: {e}")
    elif typ == "array":
        if not isinstance(data, list):
            errors.append("expected array")
            return {"valid": False, "errors": errors}
        item_schema = schema.get("items")
        if item_schema:
            for i, v in enumerate(data):
                r = validate(v, item_schema)
                if not r["valid"]:
                    for e in r["errors"]:
                        errors.append(f"[{i}]: {e}")
    elif typ == "string":
        if not isinstance(data, str):
            errors.append("expected string")
        if "enum" in schema and data not in schema["enum"]:
            errors.append(f"not in enum: {schema['enum']}")
        if "minLength" in schema and isinstance(data, str) and len(data) < schema["minLength"]:
            errors.append("too short")
    elif typ == "number" or typ == "integer":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errors.append(f"expected {typ}")
        if typ == "integer" and isinstance(data, float) and not data.is_integer():
            errors.append("expected integer")
    elif typ == "boolean":
        if not isinstance(data, bool):
            errors.append("expected boolean")
    elif typ == "null":
        if data is not None:
            errors.append("expected null")
    return {"valid": len(errors) == 0, "errors": errors}


def parse_and_validate(text: str, schema: Dict) -> dict:
    try:
        data = json.loads(text)
    except Exception as e:
        return {"valid": False, "errors": [f"json parse error: {e}"], "data": None}
    r = validate(data, schema)
    r["data"] = data if r["valid"] else None
    return r
