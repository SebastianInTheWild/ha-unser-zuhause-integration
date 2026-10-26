"""Unser Zuhause: Sammelsensoren für das Dashboard „Unser Zuhause“ und Benachrichtigungen an Personen."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .notify_person import async_register_notify
from .report import async_register_report
from .tracker import UzTracker
from .websocket import async_register_websocket

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type UzConfigEntry = ConfigEntry[UzTracker]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_register_websocket(hass)
    async_register_notify(hass)
    async_register_report(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: UzConfigEntry) -> bool:
    tracker = UzTracker(hass, entry.options)
    tracker.async_start()
    entry.runtime_data = tracker
    entry.async_on_unload(tracker.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: UzConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: UzConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
