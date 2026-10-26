"""Berichte von Agenten (z. B. Energie-Coach) als Sensor, damit Dashboards sie anzeigen können."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, REPORTS, SERVICE_SET_REPORT

ATTR_REPORT = "report"
ATTR_TITLE = "title"
ATTR_MESSAGE = "message"

SET_REPORT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REPORT): vol.In(REPORTS),
        vol.Required(ATTR_TITLE): cv.string,
        vol.Required(ATTR_MESSAGE): cv.string,
    }
)


def report_signal(key: str) -> str:
    return f"{DOMAIN}_report_{key}"


@callback
def async_register_report(hass: HomeAssistant) -> None:
    async def handle(call: ServiceCall) -> None:
        async_dispatcher_send(
            hass, report_signal(call.data[ATTR_REPORT]), call.data[ATTR_TITLE], call.data[ATTR_MESSAGE]
        )

    hass.services.async_register(DOMAIN, SERVICE_SET_REPORT, handle, schema=SET_REPORT_SCHEMA)
