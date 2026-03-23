"""Button entities for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BraiinsAPIError, BraiinsConnectionError
from .const import DOMAIN, COMPUTED_ONLINE
from .coordinator import BraiinsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BraiinsOS button entities."""
    coordinator: BraiinsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrainsRefreshButton(coordinator)])


class BrainsRefreshButton(
    CoordinatorEntity[BraiinsDataUpdateCoordinator], ButtonEntity
):
    """Button to manually trigger a data refresh from the miner."""

    _attr_has_entity_name = True
    _attr_name = "Refresh"
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BraiinsDataUpdateCoordinator) -> None:
        """Initialise the button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_refresh_button"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True when miner is reachable."""
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get(COMPUTED_ONLINE, False))

    async def async_press(self) -> None:
        """Trigger an immediate data refresh."""
        await self.coordinator.async_request_refresh()
