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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_DISPLAY_LANGUAGE,
    CONF_FAVORITE_RECITERS,
    CONF_SURAH_REPEAT,
    DEFAULT_DISPLAY_LANGUAGE,
    DEFAULT_SURAH_REPEAT,
    DISPLAY_LANGUAGES,
    DOMAIN,
    MAX_SURAH_REPEAT,
    MIN_SURAH_REPEAT,
    get_display_language,
    get_favorite_reciter_ids,
)


def _reciter_select_options(hass: HomeAssistant | None, language: str) -> list[dict[str, str]]:
    """Build reciter choices from a loaded catalog, if one exists."""
    if hass is None:
        return []
    try:
        entries = hass.config_entries.async_entries(DOMAIN)
    except Exception:  # noqa: BLE001 - flow tests use a bare hass stub
        return []

    for entry in entries:
        runtime = getattr(entry, "runtime_data", None)
        coordinator = getattr(runtime, "coordinator", None)
        catalog = getattr(coordinator, "data", None)
        if catalog is None:
            continue
        return [
            {"value": str(reciter.id), "label": reciter.browse_title(language)}
            for reciter in catalog.sorted_reciters(language)
        ]
    return []


def _options_schema(
    defaults: dict[str, Any],
    reciter_options: list[dict[str, str]],
) -> vol.Schema:
    """Build the shared options schema."""
    schema: dict[Any, Any] = {
        vol.Required(
            CONF_DISPLAY_LANGUAGE,
            default=get_display_language(defaults),
        ): SelectSelector(
            SelectSelectorConfig(
                options=DISPLAY_LANGUAGES,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_DISPLAY_LANGUAGE,
            )
        ),
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
    if reciter_options:
        current = [str(item) for item in get_favorite_reciter_ids(defaults)]
        schema[
            vol.Optional(CONF_FAVORITE_RECITERS, default=current)
        ] = SelectSelector(
            SelectSelectorConfig(
                options=reciter_options,
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    return vol.Schema(schema)


def _stored_options(user_input: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """Normalize submitted options, keeping favorites when the selector was hidden."""
    if CONF_FAVORITE_RECITERS in user_input:
        favorites = get_favorite_reciter_ids(
            {CONF_FAVORITE_RECITERS: user_input.get(CONF_FAVORITE_RECITERS)}
        )
    else:
        favorites = get_favorite_reciter_ids(previous)
    return {
        CONF_DISPLAY_LANGUAGE: user_input.get(
            CONF_DISPLAY_LANGUAGE, get_display_language(previous)
        ),
        CONF_SURAH_REPEAT: int(
            user_input.get(CONF_SURAH_REPEAT, previous.get(CONF_SURAH_REPEAT, DEFAULT_SURAH_REPEAT))
        ),
        CONF_FAVORITE_RECITERS: favorites,
    }


class Mp3QuranConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MP3 Quran."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        language = get_display_language(user_input or {})
        reciter_options = _reciter_select_options(getattr(self, "hass", None), language)

        if user_input is not None:
            return self.async_create_entry(
                title="MP3 Quran",
                data={},
                options=_stored_options(user_input, {}),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_options_schema(
                {
                    CONF_DISPLAY_LANGUAGE: DEFAULT_DISPLAY_LANGUAGE,
                    CONF_SURAH_REPEAT: DEFAULT_SURAH_REPEAT,
                    CONF_FAVORITE_RECITERS: [],
                },
                reciter_options,
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
        current = dict(self.config_entry.options)
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=_stored_options(user_input, current),
            )

        language = get_display_language(current)
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(
                current,
                _reciter_select_options(self.hass, language),
            ),
        )
