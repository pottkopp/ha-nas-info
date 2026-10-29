"""Datenabruf beim Supervisor fuer NAS-Info."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
import os
from typing import Any
from urllib.parse import quote

from aiohasupervisor import SupervisorClient, SupervisorError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_IGNORED_MOUNTS,
    CONF_UNIT_MODE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UNIT_MODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    KEY_CLIENT,
    MIN_UPDATE_INTERVAL,
    UNIT_MODES,
)

_LOGGER = logging.getLogger(__name__)

NET_TYPES = ("cifs", "nfs")
UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
STATE_LABELS = {
    "active": "aktiv",
    "inactive": "inaktiv",
    "failed": "fehlgeschlagen",
    "maintenance": "Wartung",
    "reloading": "laedt neu",
    "activating": "aktiviert",
    "deactivating": "deaktiviert",
}


def format_bytes(value: int | None, mode: str) -> tuple[str, str]:
    """Wert + Einheit; faellt der Wert unter 0,5, eine Einheit kleiner."""
    if value is None or value < 0:
        return "unavailable", ""
    if mode == "bytes":
        return str(value), "B"
    size, unit = float(value), "B"
    for candidate in UNITS[1:]:
        if size / 1024 < 0.5:
            break
        size, unit = size / 1024, candidate
    if mode == "gb":
        return f"{value / 1024 ** 3:.1f}", "GB"
    if unit == "B":
        return str(int(size)), unit
    text = f"{size:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return text, unit


@dataclass(frozen=True, slots=True)
class NetShare:
    """Ein Netzwerkspeicher mit seinen Kapazitaetszahlen."""

    name: str
    type: str
    usage: str
    server: str | None
    path: str | None
    state: str | None
    read_only: bool
    total_bytes: int | None
    used_bytes: int | None

    @property
    def free_bytes(self) -> int | None:
        """Freier Speicher, None wenn unbekannt."""
        if self.total_bytes is None or self.used_bytes is None:
            return None
        return max(self.total_bytes - self.used_bytes, 0)

    @property
    def percent_used(self) -> float | None:
        """Auslastung in Prozent, None wenn unbekannt."""
        if not self.total_bytes or self.used_bytes is None:
            return None
        return round(100 * self.used_bytes / self.total_bytes, 1)


@dataclass(frozen=True, slots=True)
class MountsData:
    """Ergebnis eines Umlaufs."""

    shares: dict[str, NetShare]
    checked_at: datetime


class MountsCoordinator(DataUpdateCoordinator[MountsData]):
    """Holt Mount-Liste und Belegung beim Supervisor ab."""

    def __init__(
        self, hass: HomeAssistant, client: SupervisorClient, entry: ConfigEntry
    ) -> None:
        """Init coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self._client = client
        self._ignored: list[str] = []
        self._mode = DEFAULT_UNIT_MODE

    @property
    def current_ignored(self) -> list[str]:
        """Aktuell ignorierte Mounts."""
        return list(self._ignored)

    @property
    def unit_mode(self) -> str:
        """Aktueller Anzeigemodus."""
        return self._mode

    def apply_options(self, ignored: list[str], mode: str, interval: int) -> None:
        """Optionen uebernehmen, Intervall sofort setzen."""
        self._ignored = ignored
        self._mode = mode
        self.update_interval = timedelta(seconds=interval)

    async def _async_update_data(self) -> MountsData:
        """Mounts und deren Belegung abrufen."""
        try:
            info = await self._client.mounts.info()
        except SupervisorError as err:
            raise UpdateFailed(f"Supervisor meldet keine Mounts: {err}") from err

        shares: dict[str, NetShare] = {}
        for mount in info.mounts:
            name = str(mount.name)
            if str(mount.type) not in NET_TYPES or name in self._ignored:
                continue
            total, used = await self._usage(name)
            path = str(getattr(mount, "share", "") or getattr(mount, "path", "") or "")
            state = getattr(mount, "state", None)
            shares[name] = NetShare(
                name=name,
                type=str(mount.type),
                usage=str(mount.usage),
                server=str(getattr(mount, "server", "") or "") or None,
                path=path or None,
                state=str(state) if state is not None else None,
                read_only=bool(mount.read_only),
                total_bytes=total,
                used_bytes=used,
            )
        return MountsData(shares=shares, checked_at=datetime.now(UTC))

    async def _usage(self, name: str) -> tuple[int | None, int | None]:
        """total_bytes und used_bytes eines Mounts."""
        try:
            resp = await self._client.get(f"host/disks/{quote(name, safe='')}/usage")
        except SupervisorError as err:
            _LOGGER.warning("Keine Kapazitaetsdaten fuer Mount %r: %s", name, err)
            return None, None
        data: dict[str, Any] = resp.data or {}
        total, used = data.get("total_bytes"), data.get("used_bytes")
        if not isinstance(total, int) or not isinstance(used, int):
            _LOGGER.warning(
                "Ueberraschende Antwort fuer Mount %r: %s", name, sorted(data)
            )
            return None, None
        return total, used


async def async_get_client(hass: HomeAssistant) -> SupervisorClient:
    """Supervisor-Client anlegen oder wiederverwenden."""
    if (client := hass.data.get(KEY_CLIENT)) is not None:
        return client
    if not (token := os.environ.get("SUPERVISOR_TOKEN")):
        raise ConfigEntryError(
            "NAS-Info laeuft nur auf Home Assistant OS oder HA Supervised: kein "
            "Zugang zum Supervisor."
        )
    client = SupervisorClient("http://supervisor", token, session=async_get_clientsession(hass))
    hass.data[KEY_CLIENT] = client
    return client


def read_options(entry: ConfigEntry) -> tuple[list[str], str, int]:
    """Optionen lesen, Intervall nach unten begrenzt."""
    options = dict(entry.options)
    ignored = [str(name) for name in options.get(CONF_IGNORED_MOUNTS) or []]
    mode = str(options.get(CONF_UNIT_MODE) or DEFAULT_UNIT_MODE)
    if mode not in UNIT_MODES:
        mode = DEFAULT_UNIT_MODE
    try:
        interval = int(options.get(CONF_UPDATE_INTERVAL) or DEFAULT_UPDATE_INTERVAL)
    except (TypeError, ValueError):
        interval = DEFAULT_UPDATE_INTERVAL
    return ignored, mode, max(interval, MIN_UPDATE_INTERVAL)
