#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, timezone
import json

CACHE_TTL_SECONDS = 15
_cache = {
    "timestamp": 0,
    "data": None
}

MODELS_METADATA = {
    "gemini": [
        {"id": "gemini-3.8-flash-high", "name": "Gemini 3.8 Flash (High)", "type": "Flash / High Reasoning", "badge": "High Effort"},
        {"id": "gemini-3.8-flash-medium", "name": "Gemini 3.8 Flash (Medium)", "type": "Flash / Balanced", "badge": "Medium"},
        {"id": "gemini-3.8-flash-low", "name": "Gemini 3.8 Flash (Low)", "type": "Flash / Ultra Fast", "badge": "Low"},
        {"id": "gemini-3.7-flash-high", "name": "Gemini 3.7 Flash (High)", "type": "Flash 3.7 / High Reasoning", "badge": "High Effort"},
        {"id": "gemini-3.7-flash-medium", "name": "Gemini 3.7 Flash (Medium)", "type": "Flash 3.7 / Balanced", "badge": "Medium"},
        {"id": "gemini-3.7-flash-low", "name": "Gemini 3.7 Flash (Low)", "type": "Flash 3.7 / Ultra Fast", "badge": "Low"},
        {"id": "gemini-3.6-flash-high", "name": "Gemini 3.6 Flash (High)", "type": "Flash 3.6 / High Reasoning", "badge": "High Effort"},
        {"id": "gemini-3.6-flash-medium", "name": "Gemini 3.6 Flash (Medium)", "type": "Flash 3.6 / Balanced", "badge": "Medium"},
        {"id": "gemini-3.6-flash-low", "name": "Gemini 3.6 Flash (Low)", "type": "Flash 3.6 / Fast", "badge": "Low"},
        {"id": "gemini-3.1-pro-high", "name": "Gemini 3.1 Pro (High)", "type": "Pro / Deep Architecture", "badge": "Pro High"},
        {"id": "gemini-3.1-pro-low", "name": "Gemini 3.1 Pro (Low)", "type": "Pro / Standard", "badge": "Pro Low"},
    ],
    "claude_gpt": [
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6 (Thinking)", "type": "Anthropic Reasoning", "badge": "Thinking"},
        {"id": "claude-opus-4-6-thinking", "name": "Claude Opus 4.6 (Thinking)", "type": "Anthropic Flagship", "badge": "Opus Flagship"},
        {"id": "gpt-oss-120b-medium", "name": "GPT-OSS 120B (Medium)", "type": "Open Weights 120B", "badge": "OSS 120B"},
    ]
}

def format_time_diff(target_iso: str) -> str:
    try:
        # e.g. 2026-10-14T05:02:41Z
        target = datetime.fromisoformat(target_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = target - now
        total_seconds = int(diff.total_seconds())
        if total_seconds <= 0:
            return "Resetting soon"
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts) + " left"
    except Exception:
        return target_iso

def get_quota_data(force_refresh: bool = False):
    global _cache
    now = time.time()
    if not force_refresh and _cache["data"] is not None and (now - _cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        res = subprocess.run(
            ["agy", "-p", "/quota"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
            check=True
        )
        raw_output = res.stdout.strip()
    except Exception as e:
        if _cache["data"] is not None:
            return _cache["data"]
        return {
            "error": str(e),
            "raw": "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    gemini_data = {"weekly": None, "five_hour": None}
    claude_gpt_data = {"weekly": None, "five_hour": None}

    for line in raw_output.split("\n"):
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        family, window, percent_str, reset_iso = [p.strip() for p in parts[:4]]
        try:
            percent_val = int(percent_str.replace("%", ""))
        except ValueError:
            percent_val = 0

        item = {
            "percent": percent_val,
            "reset_iso": reset_iso,
            "time_left": format_time_diff(reset_iso)
        }

        if "Gemini" in family:
            if "Weekly" in window:
                gemini_data["weekly"] = item
            elif "Five Hour" in window:
                gemini_data["five_hour"] = item
        elif "Claude" in family or "GPT" in family:
            if "Weekly" in window:
                claude_gpt_data["weekly"] = item
            elif "Five Hour" in window:
                claude_gpt_data["five_hour"] = item

    result = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gemini": gemini_data,
        "claude_gpt": claude_gpt_data,
        "models": MODELS_METADATA
    }

    _cache["timestamp"] = now
    _cache["data"] = result
    return result

if __name__ == "__main__":
    print(json.dumps(get_quota_data(force_refresh=True), indent=2))
