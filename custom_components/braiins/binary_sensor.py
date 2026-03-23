"""Binary sensor entities for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    COMPUTED_ONLINE,
    COMPUTED_IS_PAUSED,
    COMPUTED_ACTIVE_POOL_URL,
)
from .coordinator import BraiinsDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BrainsBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extended binary sensor description with value accessor."""

    value_fn: Callable[[BraiinsDataUpdateCoordinator], bool | None] = lambda c: None


BINARY_SENSOR_TYPES: tuple[BrainsBinarySensorEntityDescription, ...] = (
    BrainsBinarySensorEntityDescription(
        key="online",
        name="Miner Online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda c: bool(c.data.get(COMPUTED_ONLINE)) if c.data else False,
    ),
    BrainsBinarySensorEntityDescription(
        key="mining_paused",
        name="Mining Paused",
        icon="mdi:pause-circle-outline",
        value_fn=lambda c: bool(c.get_computed(COMPUTED_IS_PAUSED)),
    ),
    BrainsBinarySensorEntityDescription(
        key="pool_connected",
        name="Pool Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: bool(c.get_computed(COMPUTED_ACTIVE_POOL_URL)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BraiinsOS binary sensor entities."""
    coordinator: BraiinsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrainsBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_TYPES
    )


class BrainsBinarySensor(
    CoordinatorEntity[BraiinsDataUpdateCoordinator], BinarySensorEntity
):
    """A binary sensor entity for BraiinsOS miner status flags."""

    _attr_has_entity_name = True
    entity_description: BrainsBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: BraiinsDataUpdateCoordinator,
        description: BrainsBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """The Online sensor is always available; others require connectivity."""
        if self.entity_description.key == "online":
            return True
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get(COMPUTED_ONLINE, False))

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        try:
            return self.entity_description.value_fn(self.coordinator)
        except Exception:  # noqa: BLE001
            return None
