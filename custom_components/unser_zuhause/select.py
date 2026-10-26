"""Hausmodus: Auswahl, deren Werte aus einer Textdatei kommen."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from . import UzConfigEntry
from .const import DEFAULT_HOUSE_MODES, DOMAIN, HOUSE_MODE, HOUSE_MODES_FILE

CHECK_INTERVAL = timedelta(seconds=30)

FILE_HEADER = """\
# Hausmodus / House mode
#
# Ein Modus pro Zeile. Änderungen werden nach spätestens 30 Sekunden übernommen.
# One mode per line. Changes are picked up within 30 seconds.
#
# „anwesend“ und „abwesend“ werden übersetzt (Deutsch: Anwesend/Abwesend, English: Home/Away).
# Eigene Modi erscheinen genau so, wie sie hier stehen, z. B. „Urlaub“.
# "anwesend" and "abwesend" are translated; your own modes appear exactly as written.
"""


def modes_file(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DOMAIN, HOUSE_MODES_FILE))


def read_modes(path: Path) -> list[str]:
    """Liest die Modi; legt die Datei mit Standardwerten an, falls sie fehlt."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FILE_HEADER + "\n".join(DEFAULT_HOUSE_MODES) + "\n", encoding="utf-8")
    modes: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        mode = line.strip()
        if mode and not mode.startswith("#") and mode not in modes:
            modes.append(mode)
    return modes or list(DEFAULT_HOUSE_MODES)


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: UzConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    path = modes_file(hass)
    modes = await hass.async_add_executor_job(read_modes, path)
    async_add_entities([UzHouseModeSelect(entry, path, modes)])


class UzHouseModeSelect(SelectEntity, RestoreEntity):
    """Hausmodus; der gewählte Wert bleibt über Neustarts erhalten."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = HOUSE_MODE

    def __init__(self, entry: UzConfigEntry, path: Path, modes: list[str]) -> None:
        self._path = path
        self._mtime: float | None = None
        self._attr_options = modes
        self._attr_current_option = modes[0]
        self._attr_unique_id = f"{entry.entry_id}_{HOUSE_MODE}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Unser Zuhause",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {"file": str(self._path)}

    async def async_added_to_hass(self) -> None:
        last = await self.async_get_last_state()
        if last and last.state in self._attr_options:
            self._attr_current_option = last.state
        self._mtime = await self.hass.async_add_executor_job(_mtime, self._path)
        self.async_on_remove(async_track_time_interval(self.hass, self._async_check_file, CHECK_INTERVAL))

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()

    async def _async_check_file(self, _now=None) -> None:
        """Datei geändert? Dann Modi neu einlesen."""
        mtime = await self.hass.async_add_executor_job(_mtime, self._path)
        if mtime == self._mtime and mtime is not None:
            return
        self._mtime = mtime
        modes = await self.hass.async_add_executor_job(read_modes, self._path)
        self._apply_modes(modes)

    @callback
    def _apply_modes(self, modes: list[str]) -> None:
        if modes == self._attr_options:
            return
        self._attr_options = modes
        if self._attr_current_option not in modes:
            self._attr_current_option = modes[0]
        self.async_write_ha_state()
