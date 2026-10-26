"""Sammelsensor: mindestens ein Fenster oder eine Tür offen."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import UzConfigEntry
from .const import OPENINGS_OPEN
from .entity import UzEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: UzConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([UzOpeningsSensor(entry, entry.runtime_data, OPENINGS_OPEN, OPENINGS_OPEN)])


class UzOpeningsSensor(UzEntity, BinarySensorEntity):
    """An, sobald ein Fenster oder eine Tür offen ist."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    @property
    def is_on(self) -> bool:
        return bool(self._entities)
