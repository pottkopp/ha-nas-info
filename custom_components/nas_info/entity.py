"""Basis-Entity fuer NAS-Info."""

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MountsCoordinator, NetShare


@dataclass(frozen=True, kw_only=True)
class NasInfoEntityDescription(SensorEntityDescription):
    """Beschreibung eines NAS-Sensors."""

    bytes_field: str | None = None
    numeric_field: str | None = None
    text_field: str | None = None


class NasInfoEntity(CoordinatorEntity[MountsCoordinator]):
    """Ein Mount = ein Geraet mit dem Namen des Netzwerkspeichers."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MountsCoordinator,
        config_entry: ConfigEntry,
        share: NetShare,
        description: NasInfoEntityDescription,
    ) -> None:
        """Init entity."""
        super().__init__(coordinator, context=share.name)
        self.entity_description = description
        self._config_entry = config_entry
        self._share_name = share.name
        self._attr_unique_id = f"{DOMAIN}_{share.name}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"mount_{share.name}")},
            name=share.name,
            manufacturer=share.server or "Unbekannt",
            model="CIFS/SMB" if share.type == "cifs" else "NFS",
            sw_version=share.usage,
            configuration_url="http://supervisor/stores/storage",
        )

    @property
    def _mount(self) -> NetShare | None:
        """Aktuelle Daten dieses Mounts, None wenn er nicht mehr existiert."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.shares.get(self._share_name)
