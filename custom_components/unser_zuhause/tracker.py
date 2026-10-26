"""Zählt eingeschaltete Lichter, offene Rollos, offene Fenster/Türen und anwesende Personen."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.const import STATE_HOME, STATE_ON, STATE_OPEN, STATE_OPENING
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import TrackStates, async_track_state_change_filtered

from .const import (
    CONF_COVER_CLASSES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_LABEL,
    CONF_OPENING_CLASSES,
    COVERS_OPEN,
    DEFAULT_OPTIONS,
    DOMAIN,
    LIGHTS_ON,
    OPENINGS_OPEN,
    PERSONS_HOME,
)

TRACKED_DOMAINS = {"light", "cover", "binary_sensor", "person"}


@dataclass
class Counts:
    """Aktuelle Ergebnisse je Gruppe (Liste der Entitäten)."""

    groups: dict[str, list[str]] = field(default_factory=dict)

    def entities(self, key: str) -> list[str]:
        return self.groups.get(key, [])


class UzTracker:
    """Hält die Gruppen aktuell und benachrichtigt die Sensoren bei Änderungen."""

    def __init__(self, hass: HomeAssistant, options: Mapping[str, Any]) -> None:
        self.hass = hass
        self.options = {**DEFAULT_OPTIONS, **options}
        self.counts = Counts()
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []

    # ---- Lebenszyklus ----

    @callback
    def async_start(self) -> None:
        self._recompute()
        tracker = async_track_state_change_filtered(
            self.hass, TrackStates(False, set(), TRACKED_DOMAINS), self._on_state_change
        )
        self._unsubs.append(tracker.async_remove)
        # Labels, Ausblenden oder Deaktivieren ändern die Auswahl
        self._unsubs.append(self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._on_registry_change))
        self._unsubs.append(self.hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._on_registry_change))

    @callback
    def async_stop(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    # ---- Ereignisse ----

    @callback
    def _on_state_change(self, event: Event) -> None:
        self._recompute()

    @callback
    def _on_registry_change(self, event: Event) -> None:
        self._recompute()

    @callback
    def _recompute(self) -> None:
        groups = compute_groups(self.hass, self.options)
        if groups == self.counts.groups:
            return
        self.counts = Counts(groups)
        for listener in list(self._listeners):
            listener()


def _is_excluded(
    hass: HomeAssistant,
    state: State,
    options: Mapping[str, Any],
    ent_reg: er.EntityRegistry,
    dev_reg: dr.DeviceRegistry,
) -> bool:
    entity_id = state.entity_id
    if entity_id in (options.get(CONF_EXCLUDE_ENTITIES) or []):
        return True
    entry = ent_reg.async_get(entity_id)
    if entry is None:
        return False
    if entry.platform == DOMAIN or entry.hidden_by or entry.disabled_by or entry.entity_category:
        return True
    label = options.get(CONF_EXCLUDE_LABEL)
    if label:
        if label in entry.labels:
            return True
        device = dev_reg.async_get(entry.device_id) if entry.device_id else None
        if device and label in device.labels:
            return True
    return False


def compute_groups(hass: HomeAssistant, options: Mapping[str, Any]) -> dict[str, list[str]]:
    """Ermittelt die Entitäten je Gruppe aus dem aktuellen Zustand."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    cover_classes = set(options.get(CONF_COVER_CLASSES) or [])
    opening_classes = set(options.get(CONF_OPENING_CLASSES) or [])
    groups: dict[str, list[str]] = {LIGHTS_ON: [], COVERS_OPEN: [], OPENINGS_OPEN: [], PERSONS_HOME: []}

    for state in hass.states.async_all(TRACKED_DOMAINS):
        domain = state.domain
        if domain == "light":
            # Lichtgruppen nicht doppelt zählen
            if state.state != STATE_ON or "entity_id" in state.attributes:
                continue
            key = LIGHTS_ON
        elif domain == "cover":
            device_class = state.attributes.get("device_class") or "other"
            if state.state not in (STATE_OPEN, STATE_OPENING) or device_class not in cover_classes:
                continue
            if "entity_id" in state.attributes:
                continue
            key = COVERS_OPEN
        elif domain == "binary_sensor":
            if state.state != STATE_ON or state.attributes.get("device_class") not in opening_classes:
                continue
            key = OPENINGS_OPEN
        elif domain == "person":
            if state.state != STATE_HOME:
                continue
            key = PERSONS_HOME
        else:
            continue
        if _is_excluded(hass, state, options, ent_reg, dev_reg):
            continue
        groups[key].append(state.entity_id)

    return {key: sorted(value) for key, value in groups.items()}
