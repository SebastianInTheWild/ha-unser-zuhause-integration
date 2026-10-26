"""Einrichtung und Einstellungen der Integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    LabelSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_COVER_CLASSES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_LABEL,
    CONF_OPENING_CLASSES,
    COVER_CLASSES,
    DEFAULT_OPTIONS,
    DOMAIN,
    OPENING_CLASSES,
)


def options_schema(options: dict[str, Any]) -> vol.Schema:
    current = {**DEFAULT_OPTIONS, **options}
    label = current.get(CONF_EXCLUDE_LABEL)
    return vol.Schema(
        {
            vol.Optional(
                CONF_EXCLUDE_LABEL, **({"description": {"suggested_value": label}} if label else {})
            ): LabelSelector(),
            vol.Optional(CONF_EXCLUDE_ENTITIES, default=current[CONF_EXCLUDE_ENTITIES]): EntitySelector(
                EntitySelectorConfig(multiple=True, domain=["light", "cover", "binary_sensor", "person"])
            ),
            vol.Optional(CONF_COVER_CLASSES, default=current[CONF_COVER_CLASSES]): SelectSelector(
                SelectSelectorConfig(
                    options=COVER_CLASSES,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_COVER_CLASSES,
                )
            ),
            vol.Optional(CONF_OPENING_CLASSES, default=current[CONF_OPENING_CLASSES]): SelectSelector(
                SelectSelectorConfig(
                    options=OPENING_CLASSES,
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key=CONF_OPENING_CLASSES,
                )
            ),
        }
    )


def clean_options(user_input: dict[str, Any]) -> dict[str, Any]:
    """Leeres Label heißt: kein Ausschluss."""
    return {
        CONF_EXCLUDE_LABEL: user_input.get(CONF_EXCLUDE_LABEL) or "",
        CONF_EXCLUDE_ENTITIES: list(user_input.get(CONF_EXCLUDE_ENTITIES) or []),
        CONF_COVER_CLASSES: list(user_input.get(CONF_COVER_CLASSES) or []),
        CONF_OPENING_CLASSES: list(user_input.get(CONF_OPENING_CLASSES) or []),
    }


class UzConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung mit einem Schritt (Standardwerte passen meistens)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="Unser Zuhause", data={}, options=clean_options(user_input))
        return self.async_show_form(step_id="user", data_schema=options_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return UzOptionsFlow()


class UzOptionsFlow(OptionsFlow):
    """Einstellungen ändern (auch im Dashboard unter „Unser Zuhause“ möglich)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=clean_options(user_input))
        return self.async_show_form(step_id="init", data_schema=options_schema(dict(self.config_entry.options)))
