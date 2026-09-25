"""Offline, fail-closed reproduction of a narrow MCP argument-schema rename.

This module never connects to a provider or executes a tool. Incident values stay
in the caller's local file and are deliberately absent from generated reports.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
SCALAR_TYPES = {"string", "integer", "number", "boolean"}
TOP_LEVEL_KEYS = {"type", "properties", "required", "additionalProperties", "title", "description"}
PROPERTY_KEYS = {"type", "title", "description"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _schema(schema: Any, label: str) -> dict[str, Any]:
    if not isinstance(schema, dict) or set(schema) - TOP_LEVEL_KEYS or schema.get("type") != "object":
        raise ValueError(f"{label} must be a supported top-level object schema")
    props = schema.get("properties")
    if not isinstance(props, dict) or not props or len(props) > 64:
        raise ValueError(f"{label} needs 1..64 properties")
    for name, definition in props.items():
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
            raise ValueError(f"{label} has an invalid property name")
        if not isinstance(definition, dict) or set(definition) - PROPERTY_KEYS or definition.get("type") not in SCALAR_TYPES:
            raise ValueError(f"{label} uses an unsupported property constraint")
    required = schema.get("required", [])
    if not isinstance(required, list) or any(not isinstance(name, str) for name in required) or len(set(required)) != len(required) or any(name not in props for name in required):
        raise ValueError(f"{label} has invalid required properties")
    if schema.get("additionalProperties", True) is not False:
        raise ValueError(f"{label} must set additionalProperties=false for a reliable reproduction")
    return schema


def _type_ok(value: Any, kind: str) -> bool:
    if kind == "string": return isinstance(value, str)
    if kind == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number": return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    return isinstance(value, bool)


def _errors(schema: dict[str, Any], arguments: dict[str, Any]) -> list[str]:
    props = schema["properties"]
    errors = [f"missing:{name}" for name in schema.get("required", []) if name not in arguments]
    for name, value in arguments.items():
        if name not in props: errors.append(f"unknown:{name}")
        elif not _type_ok(value, props[name]["type"]): errors.append(f"type:{name}")
    return sorted(errors)


def _incident(raw: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not isinstance(raw, dict) or raw.get("schema_version") != "1.0" or set(raw) != {"schema_version", "incident_id", "tool_name", "original_schema", "current_schema", "arguments", "renames"}:
        raise ValueError("Expected repair incident schema_version 1.0 with exact fields")
    if not all(isinstance(raw.get(key), str) and IDENTIFIER.fullmatch(raw[key]) for key in ("incident_id", "tool_name")):
        raise ValueError("Incident and tool identifiers must be safe")
    original = _schema(raw["original_schema"], "original_schema")
    current = _schema(raw["current_schema"], "current_schema")
    arguments = raw["arguments"]
    renames = raw["renames"]
    if not isinstance(arguments, dict) or len(arguments) > 64 or any(not isinstance(k, str) or not IDENTIFIER.fullmatch(k) for k in arguments):
        raise ValueError("arguments must be a bounded object with safe names")
    if not isinstance(renames, dict) or not renames or len(renames) > 16 or any(not isinstance(value, str) for value in renames.values()) or len(set(renames.values())) != len(renames):
        raise ValueError("renames must map 1..16 distinct source and target names")
    for source, target in renames.items():
        if not isinstance(source, str) or not isinstance(target, str) or not IDENTIFIER.fullmatch(source) or not IDENTIFIER.fullmatch(target) or source == target:
            raise ValueError("Invalid rename")
        if source not in original["properties"] or source not in arguments or target not in current["properties"] or target in arguments:
            raise ValueError("Rename must connect an old argument to an unused current property")
        if original["properties"][source]["type"] != current["properties"][target]["type"]:
            raise ValueError("Rename cannot change an argument type")
    return original, current, arguments, renames


def transform(arguments: dict[str, Any], renames: dict[str, str]) -> dict[str, Any]:
    return {renames.get(key, key): value for key, value in arguments.items()}


def analyze(raw: Any) -> dict[str, Any]:
    original, current, arguments, renames = _incident(raw)
    old_errors = _errors(original, arguments)
    current_errors = _errors(current, arguments)
    repaired = transform(arguments, renames)
    repaired_errors = _errors(current, repaired)
    # Strictly require that the proposed rename explains every current-schema
    # error. Existing type failures and unrelated missing fields are not repairs.
    expected = sorted([f"unknown:{source}" for source in renames] + [f"missing:{target}" for target in renames.values() if target in current.get("required", [])])
    candidate = not old_errors and current_errors == expected and not repaired_errors
    basis = {"tool_name": raw["tool_name"], "original_schema": original, "current_schema": current, "renames": renames}
    fingerprint = _digest(basis)
    adapter = {"schema_version": "1.0", "kind": "mcp-argument-rename", "tool_name": raw["tool_name"], "original_schema_sha256": _digest(original), "current_schema_sha256": _digest(current), "renames": renames, "fingerprint_sha256": fingerprint}
    return {"schema_version": "1.0", "incident_id_sha256": _digest(raw["incident_id"]), "status": "candidate" if candidate else "manual_review", "fingerprint_sha256": fingerprint, "old_schema_errors": old_errors, "current_schema_errors": current_errors, "repaired_schema_errors": repaired_errors, "checks": {"original_call_valid_before": not old_errors, "original_call_rejected_now": bool(current_errors), "rename_fully_explains_failure": current_errors == expected, "repaired_call_valid_now": not repaired_errors, "unrelated_arguments_unchanged": all(repaired.get(name) == value for name, value in arguments.items() if name not in renames)}, "adapter": adapter if candidate else None, "claim_boundary": "Offline schema-level reproduction only. No provider call, authorization check, business-effect verification, or production repair was performed. Input argument values and incident ID are omitted from this report."}


def apply_adapter(raw: Any, adapter: Any) -> dict[str, Any]:
    result = analyze(raw)
    if result["status"] != "candidate" or adapter != result["adapter"]:
        raise ValueError("Adapter does not match a passing incident analysis")
    return {"tool_name": raw["tool_name"], "arguments": transform(raw["arguments"], raw["renames"]), "warning": "Local transformed call only; no provider call was made. This file may contain sensitive argument values."}
