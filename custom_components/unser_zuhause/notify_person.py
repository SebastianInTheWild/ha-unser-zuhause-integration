"""Aktion „Benachrichtigen“: Push an Personen statt an einzelne Handys.

Die Handys werden automatisch gefunden: Jede Companion-App weiß, welcher Benutzer an ihr angemeldet ist,
und jede Person ist mit einem Benutzer verknüpft. Personen ohne Benutzer werden über ihre Tracker gefunden.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.util import slugify

from .const import DOMAIN, SERVICE_NOTIFY

_LOGGER = logging.getLogger(__name__)

MOBILE_APP = "mobile_app"
ATTR_PERSONS = "persons"
ATTR_TITLE = "title"
ATTR_MESSAGE = "message"
ATTR_DATA = "data"

NOTIFY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_PERSONS, default=[]): cv.entity_ids,
        vol.Optional(ATTR_DATA): dict,
    }
)


def _app_entries(hass: HomeAssistant) -> list:
    return [e for e in hass.config_entries.async_entries(MOBILE_APP) if not e.disabled_by]


def _service(entry) -> str:
    """Name des Notify-Dienstes, den die Companion-App für ihr Gerät anlegt."""
    return f"{MOBILE_APP}_{slugify(entry.data.get('device_name') or entry.title)}"


def _entries_for_person(hass: HomeAssistant, person_id: str) -> list:
    state = hass.states.get(person_id)
    if state is None:
        return []
    entries = _app_entries(hass)
    if user_id := state.attributes.get("user_id"):
        found = [e for e in entries if e.data.get("user_id") == user_id]
        if found:
            return found
    # Person ohne Benutzer (oder Benutzer ohne App): Handys über die Tracker der Person
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    found = []
    for tracker in state.attributes.get("device_trackers") or []:
        ent = ent_reg.async_get(tracker)
        dev = dev_reg.async_get(ent.device_id) if ent and ent.device_id else None
        if dev:
            # Ab HA 2026.10 gehört ein Gerät genau einem Eintrag (config_entry_id), davor config_entries
            ids = {dev.config_entry_id} if hasattr(dev, "config_entry_id") else dev.config_entries
            found += [e for e in entries if e.entry_id in ids and e not in found]
    return found


def resolve_services(hass: HomeAssistant, persons: list[str]) -> list[str]:
    """Notify-Dienste für die Personen; ohne Personen alle Handys mit angemeldetem Benutzer."""
    if persons:
        entries = []
        for person in persons:
            entries += [e for e in _entries_for_person(hass, person) if e not in entries]
    else:
        entries = [e for e in _app_entries(hass) if e.data.get("user_id")]
    services = []
    for entry in entries:
        name = _service(entry)
        if not hass.services.has_service("notify", name):
            _LOGGER.warning("Kein Notify-Dienst notify.%s für „%s“ gefunden", name, entry.title)
        elif name not in services:
            services.append(name)
    return services


@callback
def async_register_notify(hass: HomeAssistant) -> None:
    async def handle(call: ServiceCall) -> ServiceResponse:
        persons = call.data[ATTR_PERSONS]
        services = resolve_services(hass, persons)
        if not services:
            _LOGGER.warning("Benachrichtigung ohne Empfänger: %s", ", ".join(persons) or "alle")
        payload: dict[str, Any] = {ATTR_MESSAGE: call.data[ATTR_MESSAGE]}
        for key in (ATTR_TITLE, ATTR_DATA):
            if key in call.data:
                payload[key] = call.data[key]
        for name in services:
            await hass.services.async_call("notify", name, payload, blocking=True, context=call.context)
        return {"sent_to": [f"notify.{name}" for name in services]}

    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY, handle, schema=NOTIFY_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )

