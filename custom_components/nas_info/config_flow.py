"""Config flow fuer NAS-Info."""

import logging
from typing import Any

import probatio

from aiohasupervisor import SupervisorClient, SupervisorError
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_IGNORED_MOUNTS,
    CONF_UNIT_MODE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UNIT_MODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    KEY_CLIENT,
    MIN_UPDATE_INTERVAL,
)
from .coordinator import NET_TYPES, async_get_client, read_options

_LOGGER = logging.getLogger(__name__)

UNIT_MODE_OPTIONS = [
    selector.SelectOptionDict(value="auto", label="Automatisch (0,5-Regel)"),
    selector.SelectOptionDict(value="gb", label="Immer GB"),
    selector.SelectOptionDict(value="bytes", label="Rohwerte in Bytes"),
]


async def async_known_mounts(hass: HomeAssistant) -> list[str] | None:
    """Netzwerkspeicher; None, wenn der Supervisor nicht erreichbar ist."""
    client: SupervisorClient | None = hass.data.get(KEY_CLIENT)
    if client is None:
        client = await async_get_client(hass)
    try:
        info = await client.mounts.info()
    except SupervisorError as err:
        _LOGGER.warning("Mounts nicht abrufbar: %s", err)
        return None
    return [
        str(mount.name)
        for mount in info.mounts
        if str(mount.type) in NET_TYPES
    ]


class NasInfoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Genau einer Eintrag, dazu Rekonfiguration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Einrichtung bestaetigen lassen."""
        await self.async_set_unique_id(DOMAIN)
        if self.source != SOURCE_RECONFIGURE:
            self._abort_if_unique_id_configured()

        if user_input is None:
            names = await async_known_mounts(self.hass)
            if names is None:
                return self.async_show_form(
                    step_id="user", errors={"base": "supervisor_error"}
                )
            if not names:
                return self.async_show_form(
                    step_id="user", errors={"base": "no_mounts"}
                )
            return self.async_show_form(
                step_id="user",
                description_placeholders={"mounts": ", ".join(names)},
            )

        options = {
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            CONF_IGNORED_MOUNTS: [],
            CONF_UNIT_MODE: DEFAULT_UNIT_MODE,
        }
        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            self.hass.config_entries.async_update_entry(
                entry, options={**dict(entry.options), **options}
            )
            return self.async_create_entry(title="", data={})
        return self.async_create_entry(
            title="Netzwerkspeicher (Supervisor)", data={}, options=options
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Dialog fuer die Einstellungen eines vorhandenen Eintrags."""
        return await self.async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Optionen-Dialog."""
        return NasInfoOptionsFlow()


class NasInfoOptionsFlow(OptionsFlow):
    """Intervall, ignorierte Speicher und Einheit nachtraeglich aendern."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Maske zeigen oder speichern."""
        entry = self.config_entry

        if user_input is not None:
            try:
                interval = int(
                    user_input.get(CONF_UPDATE_INTERVAL) or DEFAULT_UPDATE_INTERVAL
                )
            except (TypeError, ValueError):
                interval = DEFAULT_UPDATE_INTERVAL
            self.hass.config_entries.async_update_entry(
                entry,
                options={
                    **dict(entry.options),
                    CONF_IGNORED_MOUNTS: [
                        str(name) for name in user_input.get(CONF_IGNORED_MOUNTS) or []
                    ],
                    CONF_UNIT_MODE: str(
                        user_input.get(CONF_UNIT_MODE) or DEFAULT_UNIT_MODE
                    ),
                    CONF_UPDATE_INTERVAL: max(MIN_UPDATE_INTERVAL, interval),
                },
            )
            return self.async_create_entry(title="", data={})

        ignored, mode, interval = read_options(entry)
        names = await async_known_mounts(self.hass)
        if names is None:
            names = []
        names += [name for name in ignored if name not in names]
        mount_options = [
            selector.SelectOptionDict(value=name, label=name) for name in names
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_UPDATE_INTERVAL, default=interval
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=86400,
                            step=30,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    probatio.Required(
                        CONF_IGNORED_MOUNTS, default=ignored
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=mount_options,
                            multiple=True,
                            custom_value=True,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    probatio.Required(CONF_UNIT_MODE, default=mode): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=UNIT_MODE_OPTIONS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )
