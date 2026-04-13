"""
mobile_backend.py — Backend API for a mobile application.
Manages push notifications, user preferences, XML config imports,
and device registration.
"""

import xml.etree.ElementTree as ET
from lxml import etree
import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PUSH_SERVICE_URL = "https://push.internal/notify"
DEVICE_REGISTRY = {}


def register_device(user_id: int, device_token: str, platform: str) -> dict:
    if platform not in ("ios", "android"):
        raise ValueError(f"Unsupported platform: {platform}")
    DEVICE_REGISTRY[device_token] = {
        "user_id": user_id,
        "platform": platform,
        "active": True,
    }
    return {"status": "registered", "token": device_token}


def deregister_device(device_token: str) -> bool:
    if device_token in DEVICE_REGISTRY:
        DEVICE_REGISTRY[device_token]["active"] = False
        return True
    return False


def get_active_devices(user_id: int) -> list:
    return [
        {"token": tok, **info}
        for tok, info in DEVICE_REGISTRY.items()
        if info["user_id"] == user_id and info["active"]
    ]


# ------------------------------------------------------------------ #
# VULNERABILITY 1: XXE (XML External Entity) — lxml's default parser
# resolves external entities. A crafted XML payload can read local
# files (e.g. /etc/passwd) or trigger SSRF to internal services.
# ------------------------------------------------------------------ #
def import_user_preferences(xml_payload: str) -> dict:
    # Dangerous: default lxml parser resolves external entities
    root = etree.fromstring(xml_payload.encode())
    prefs = {}
    for child in root:
        prefs[child.tag] = child.text
    return prefs


def import_user_preferences_safe(xml_payload: str) -> dict:
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(xml_payload.encode(), parser=parser)
    prefs = {}
    for child in root:
        prefs[child.tag] = child.text
    return prefs


# ------------------------------------------------------------------ #
# VULNERABILITY 2: Insecure Direct Object Reference (IDOR) — the
# endpoint accepts a `target_user_id` parameter without checking
# that the requester owns that account. Any authenticated user can
# read or overwrite another user's notification preferences.
# ------------------------------------------------------------------ #
def get_notification_settings(requester_id: int, target_user_id: int, db) -> dict:
    # Dangerous: no ownership check — IDOR
    return db.get_notification_settings(target_user_id)


def get_notification_settings_safe(requester_id: int, target_user_id: int, db) -> dict:
    if requester_id != target_user_id:
        raise PermissionError("Cannot access another user's notification settings")
    return db.get_notification_settings(target_user_id)


# ------------------------------------------------------------------ #
# VULNERABILITY 3: Mass Assignment — the entire request body is applied
# to the user record without filtering. An attacker can set privileged
# fields such as `is_admin=true` or `subscription_tier=enterprise`.
# ------------------------------------------------------------------ #
def update_user_settings(user_id: int, request_body: dict, db) -> dict:
    # Dangerous: no field allowlist — all keys from request are written
    db.update_user(user_id, **request_body)
    return {"status": "updated"}


def update_user_settings_safe(user_id: int, request_body: dict, db) -> dict:
    ALLOWED_FIELDS = {"display_name", "language", "timezone", "notifications_enabled"}
    filtered = {k: v for k, v in request_body.items() if k in ALLOWED_FIELDS}
    db.update_user(user_id, **filtered)
    return {"status": "updated"}


def send_push_notification(device_token: str, title: str, body: str) -> bool:
    payload = {"token": device_token, "title": title, "body": body}
    try:
        resp = requests.post(PUSH_SERVICE_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("Push notification failed: %s", e)
        return False


def broadcast_to_user(user_id: int, title: str, body: str) -> int:
    devices = get_active_devices(user_id)
    sent = 0
    for device in devices:
        if send_push_notification(device["token"], title, body):
            sent += 1
    return sent


def parse_device_metadata(raw_json: str) -> Optional[dict]:
    try:
        data = json.loads(raw_json)
        return {
            "os_version": data.get("os_version"),
            "app_version": data.get("app_version"),
            "locale": data.get("locale"),
        }
    except (json.JSONDecodeError, KeyError):
        return None
