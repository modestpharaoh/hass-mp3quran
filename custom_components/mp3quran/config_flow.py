"""Config flow for MP3 Quran."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_AUTO_ADVANCE,
    CONF_SORT_LANGUAGE,
    CONF_SURAH_REPEAT,
    DEFAULT_AUTO_ADVANCE,
    DEFAULT_SORT_LANGUAGE,
    DEFAULT_SURAH_REPEAT,
    DOMAIN,
    MAX_SURAH_REPEAT,
    MIN_SURAH_REPEAT,
    SORT_LANGUAGES,
)


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the shared options schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SORT_LANGUAGE,
                default=defaults.get(CONF_SORT_LANGUAGE, DEFAULT_SORT_LANGUAGE),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=SORT_LANGUAGES,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_SORT_LANGUAGE,
                )
            ),
            vol.Required(
                CONF_AUTO_ADVANCE,
                default=defaults.get(CONF_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE),
            ): bool,
            vol.Required(
                CONF_SURAH_REPEAT,
                default=defaults.get(CONF_SURAH_REPEAT, DEFAULT_SURAH_REPEAT),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SURAH_REPEAT,
                    max=MAX_SURAH_REPEAT,
                    mode=NumberSelectorMode.BOX,
                    step=1,
                )
            ),
        }
    )


class Mp3QuranConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MP3 Quran."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="MP3 Quran",
                data={},
                options={
                    CONF_SORT_LANGUAGE: user_input.get(
                        CONF_SORT_LANGUAGE, DEFAULT_SORT_LANGUAGE
                    ),
                    CONF_AUTO_ADVANCE: user_input.get(
                        CONF_AUTO_ADVANCE, DEFAULT_AUTO_ADVANCE
                    ),
                    CONF_SURAH_REPEAT: int(
                        user_input.get(CONF_SURAH_REPEAT, DEFAULT_SURAH_REPEAT)
                    ),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_options_schema(
                {
                    CONF_SORT_LANGUAGE: DEFAULT_SORT_LANGUAGE,
                    CONF_AUTO_ADVANCE: DEFAULT_AUTO_ADVANCE,
                    CONF_SURAH_REPEAT: DEFAULT_SURAH_REPEAT,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return Mp3QuranOptionsFlowHandler()


class Mp3QuranOptionsFlowHandler(OptionsFlow):
    """Handle options for MP3 Quran."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage MP3 Quran options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_SORT_LANGUAGE: user_input[CONF_SORT_LANGUAGE],
                    CONF_AUTO_ADVANCE: user_input[CONF_AUTO_ADVANCE],
                    CONF_SURAH_REPEAT: int(user_input[CONF_SURAH_REPEAT]),
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self.config_entry.options)),
        )
