"""Zähler: Lichter an, offene Rollos, offene Fenster & Türen, Personen zu Hause."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import UzConfigEntry
from .const import COVERS_OPEN, DOMAIN, LIGHTS_ON, OPENINGS_COUNT, OPENINGS_OPEN, PERSONS_HOME, REPORTS
from .entity import UzEntity
from .report import report_signal

# translation_key → Gruppe im Tracker
SENSORS = {
    LIGHTS_ON: LIGHTS_ON,
    COVERS_OPEN: COVERS_OPEN,
    OPENINGS_COUNT: OPENINGS_OPEN,
    PERSONS_HOME: PERSONS_HOME,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: UzConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(UzCountSensor(entry, entry.runtime_data, key, group) for key, group in SENSORS.items())
    async_add_entities(UzReportSensor(entry, key) for key in REPORTS)


class UzCountSensor(UzEntity, SensorEntity):
    """Anzahl der Entitäten einer Gruppe."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        return len(self._entities)


class UzReportSensor(RestoreEntity, SensorEntity):
    """Letzter Bericht eines Agenten: Zustand = Zeitpunkt, Titel und Text als Attribute."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # Langer Text gehört nicht in die Verlaufsdatenbank
    _unrecorded_attributes = frozenset({"title", "message"})

    def __init__(self, entry, key: str) -> None:
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Unser Zuhause", entry_type=DeviceEntryType.SERVICE
        )
        self._updated: datetime | None = None
        self._title = ""
        self._message = ""

    @property
    def native_value(self) -> datetime | None:
        return self._updated

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"title": self._title, "message": self._message}

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None:
            if last.state not in ("unknown", "unavailable"):
                self._updated = dt_util.parse_datetime(last.state)
            self._title = last.attributes.get("title", "")
            self._message = last.attributes.get("message", "")
        self.async_on_remove(async_dispatcher_connect(self.hass, report_signal(self._key), self._async_set))

    @callback
    def _async_set(self, title: str, message: str) -> None:
        self._updated = dt_util.utcnow()
        self._title = title
        self._message = message
        self.async_write_ha_state()
