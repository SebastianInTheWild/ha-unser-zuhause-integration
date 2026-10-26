"""WebSocket-Befehle, damit die Dashboard-Strategy die Einstellungen anzeigen und ändern kann."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .config_flow import clean_options
from .const import (
    CONF_COVER_CLASSES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_LABEL,
    CONF_OPENING_CLASSES,
    COVER_CLASSES,
    DEFAULT_OPTIONS,
    DOMAIN,
    HOUSE_MODES_FILE,
    OPENING_CLASSES,
)


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_get_options)
    websocket_api.async_register_command(hass, ws_set_options)


def _entry(hass: HomeAssistant):
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _payload(hass: HomeAssistant, entry) -> dict[str, Any]:
    return {
        "house_modes_file": hass.config.path(DOMAIN, HOUSE_MODES_FILE),
        "entry_id": entry.entry_id,
        "options": {**DEFAULT_OPTIONS, **entry.options},
        "cover_classes": COVER_CLASSES,
        "opening_classes": OPENING_CLASSES,
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/get_options"})
@callback
def ws_get_options(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "Unser Zuhause ist nicht eingerichtet")
        return
    connection.send_result(msg["id"], _payload(hass, entry))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/set_options",
        vol.Optional(CONF_EXCLUDE_LABEL): vol.Any(str, None),
        vol.Optional(CONF_EXCLUDE_ENTITIES): [str],
        vol.Optional(CONF_COVER_CLASSES): [vol.In(COVER_CLASSES)],
        vol.Optional(CONF_OPENING_CLASSES): [vol.In(OPENING_CLASSES)],
    }
)
@websocket_api.require_admin
@callback
def ws_set_options(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry = _entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "Unser Zuhause ist nicht eingerichtet")
        return
    changes = {k: v for k, v in msg.items() if k not in ("id", "type")}
    options = clean_options({**DEFAULT_OPTIONS, **entry.options, **changes})
    hass.config_entries.async_update_entry(entry, options=options)
    connection.send_result(msg["id"], _payload(hass, entry))
