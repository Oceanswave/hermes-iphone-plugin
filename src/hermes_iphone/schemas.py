from __future__ import annotations


def schema(
    name: str,
    description: str,
    properties: dict | None = None,
    required: list[str] | None = None,
) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties or {},
            "required": required or [],
            "additionalProperties": False,
        },
    }


UDID = {
    "type": "string",
    "description": "Optional iPhone UDID. If omitted, backend chooses the first connected/trusted device.",
}
