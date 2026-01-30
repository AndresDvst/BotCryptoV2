import json
import os
import re

def _load_passwords():
    path = os.path.join(os.getcwd(), "contraseñasBOTS.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("passwords", {})
    except Exception:
        return {}

def _extract_tokens(text: str):
    if not text:
        return []
    return [t for t in re.split(r"[\\s,;:\\|]+", text.strip()) if t]

def validate_access(chat_type: str, text: str, bot_type: str) -> bool:
    if str(chat_type).lower() != "private":
        return True
    passwords = _load_passwords()
    allowed = set()
    if isinstance(passwords, dict):
        key_map = {
            "crypto": ["crypto", "TELEGRAM_BOT_CRYPTO"],
            "markets": ["markets", "TELEGRAM_BOT_MARKETS"],
            "signals": ["signals", "TELEGRAM_BOT_SIGNALS"],
        }
        for k in key_map.get(str(bot_type).lower(), []):
            v = passwords.get(k)
            if isinstance(v, str) and v:
                allowed.add(v)
    elif isinstance(passwords, list):
        for v in passwords:
            if isinstance(v, str) and v:
                allowed.add(v)
    if not allowed:
        return False
    tokens = _extract_tokens(text or "")
    for pwd in allowed:
        if pwd in tokens or f"password={pwd}" in (text or "") or f"pass={pwd}" in (text or ""):
            return True
    return False
