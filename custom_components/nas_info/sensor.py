"""Sensoren fuer NAS-Info."""

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import STATE_LABELS, MountsCoordinator, format_bytes
from .entity import NasInfoEntity, NasInfoEntityDescription

DESCRIPTIONS: tuple[NasInfoEntityDescription, ...] = (
    NasInfoEntityDescription(
        key="total",
        name="Gesamt",
        bytes_field="total_bytes",
        icon="mdi:database-outline",
    ),
    NasInfoEntityDescription(
        key="used",
        name="Belegt",
        bytes_field="used_bytes",
        icon="mdi:database",
    ),
    NasInfoEntityDescription(
        key="free",
        name="Frei",
        bytes_field="free_bytes",
        icon="mdi:database-edit-outline",
    ),
    NasInfoEntityDescription(
        key="used_percent",
        name="Auslastung",
        numeric_field="percent_used",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
    ),
    NasInfoEntityDescription(
        key="mount_state",
        name="Status",
        text_field="state",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:lan-connect",
    ),
    NasInfoEntityDescription(
        key="server",
        name="Server",
        text_field="server",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:server-network",
    ),
    NasInfoEntityDescription(
        key="path",
        name="Freigabe",
        text_field="path",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:folder-shared",
    ),
    NasInfoEntityDescription(
        key="read_only",
        name="Schreibgeschuetzt",
        text_field="read_only",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:lock-check-outline",
    ),
    NasInfoEntityDescription(
        key="last_check",
        name="Zuletzt geprueft",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-check-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Ein Sensor-Satz pro gemeldetem Netzwerkspeicher."""
    coordinator: MountsCoordinator = hass.data[config_entry.entry_id]
    known: set[str] = set()

    def build() -> list[NasInfoEntity]:
        """Sensoren fuer alle noch nicht angelegten Mounts."""
        entities: list[NasInfoEntity] = []
        if coordinator.data is None:
            return entities
        for share in coordinator.data.shares.values():
            if share.name in known:
                continue
            known.add(share.name)
            entities.extend(
                NasInfoSensor(coordinator, config_entry, share, description)
                for description in DESCRIPTIONS
            )
        return entities

    async_add_entities(build())

    def _new_shares() -> None:
        """Neu hinzugekommene Mounts bekommen ebenfalls Sensoren."""
        async_add_entities(build())

    config_entry.async_on_unload(coordinator.async_add_listener(_new_shares))


class NasInfoSensor(NasInfoEntity, SensorEntity):
    """Sensor eines Netzwerkspeichers."""

    entity_description: NasInfoEntityDescription

    @property
    def native_value(self) -> Any:
        """Zustand des Sensors."""
        desc = self.entity_description
        if desc.key == "last_check":
            if self.coordinator.data is None:
                return None
            return self.coordinator.data.checked_at
        mount = self._mount
        if mount is None:
            return None
        if desc.bytes_field:
            value, _ = format_bytes(
                getattr(mount, desc.bytes_field), self.coordinator.unit_mode
            )
            return value
        if desc.numeric_field:
            return getattr(mount, desc.numeric_field)
        if desc.text_field == "state":
            return STATE_LABELS.get(str(mount.state), "unbekannt")
        value = getattr(mount, desc.text_field or "", None)
        if isinstance(value, bool):
            return "ja" if value else "nein"
        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Anzeigeeinheit, wechselt mit der 0,5-Regel mit."""
        desc = self.entity_description
        if not desc.bytes_field:
            return desc.native_unit_of_measurement
        mount = self._mount
        if mount is None:
            return None
        _, unit = format_bytes(
            getattr(mount, desc.bytes_field), self.coordinator.unit_mode
        )
        return unit
