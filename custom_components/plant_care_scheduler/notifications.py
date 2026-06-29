"""Built-in actionable reminders (opt-in)."""
from __future__ import annotations

from .const import ACTIONS


def encode_action(subentry_id: str, action: str) -> str:
    """Encode a callback payload (Telegram callback_data / mobile_app action id)."""
    return f"pcs::{subentry_id}::{action}"


def decode_action(payload: str | None) -> tuple[str, str] | None:
    """Parse a callback payload back to (subentry_id, action); None if invalid."""
    if not payload:
        return None
    parts = payload.split("::")
    if len(parts) == 3 and parts[0] == "pcs" and parts[2] in ACTIONS:
        return parts[1], parts[2]
    return None
