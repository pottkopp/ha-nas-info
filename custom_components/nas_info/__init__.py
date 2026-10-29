"""Einrichtung von NAS-Info."""

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .const import DOMAIN
from .coordinator import MountsCoordinator, async_get_api, read_options

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Coordinator starten und Sensoren anlegen."""
    try:
        client = await async_get_api(hass)
    except ConfigEntryError as err:
        raise ConfigEntryError(
            "NAS-Info braucht Home Assistant OS oder HA Supervised: kein Zugang "
            "zum Supervisor."
        ) from err

    coordinator = MountsCoordinator(hass, client, entry)
    ignored, mode, interval = read_options(entry)
    coordinator.apply_options(ignored, mode, interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Optionen ohne Neustart übernehmen."""
    if entry.state is not ConfigEntryState.LOADED or (
        coordinator := hass.data.get(entry.entry_id)
    ) is None:
        return
    ignored, mode, interval = read_options(entry)
    changed = set(ignored) != set(coordinator.current_ignored)
    coordinator.apply_options(ignored, mode, interval)
    if changed:
        await coordinator.async_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Sensoren abmelden, Geräte bleiben bis zum Entfernen des Eintrags."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    if (coordinator := hass.data.pop(entry.entry_id, None)) is not None:
        coordinator.async_shutdown()
    return True
