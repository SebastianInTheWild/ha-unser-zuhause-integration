"""Gemeinsame Basis der Sensoren."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .tracker import UzTracker


class UzEntity(Entity):
    """Sensor, der eine Gruppe des Trackers abbildet."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, tracker: UzTracker, key: str, group: str) -> None:
        self._tracker = tracker
        self._group = group
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Unser Zuhause",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def _entities(self) -> list[str]:
        return self._tracker.counts.entities(self._group)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entity_id": self._entities, "count": len(self._entities)}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._tracker.async_add_listener(self.async_write_ha_state))
