from __future__ import annotations

import json
import urllib.request
from collections.abc import Mapping
from typing import Any


LATEST_MANIFEST_URL = "https://raw.githubusercontent.com/LumyQAQ/sector-rotation-v2/main/outputs/latest.json"


def parse_latest_manifest(payload: bytes | str) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("latest manifest must be a JSON object")
    return data


def load_remote_latest_manifest(url: str = LATEST_MANIFEST_URL, timeout: int = 5) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return parse_latest_manifest(response.read())


def freshness_status(local_date: str, remote_manifest: Mapping[str, Any] | None) -> tuple[str, str | None]:
    if not remote_manifest:
        return "unknown", None

    remote_date = str(remote_manifest.get("date") or "")
    if not remote_date:
        return "unknown", None

    if remote_date > local_date:
        return (
            "stale",
            f"GitHub 最新数据已到 {remote_date}，当前网页加载的是 {local_date}。请刷新页面或等待 Streamlit 重新部署；若仍不一致，需要检查缓存和部署日志。",
        )
    return "fresh", None
