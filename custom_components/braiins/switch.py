"""Switch entities for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BraiinsAPIError, BraiinsConnectionError
from .const import DOMAIN, COMPUTED_ONLINE, COMPUTED_IS_PAUSED
from .coordinator import BraiinsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BraiinsOS switch entities."""
    coordinator: BraiinsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrainsMiningSwitch(coordinator)])


class BrainsMiningSwitch(
    CoordinatorEntity[BraiinsDataUpdateCoordinator], SwitchEntity
):
    """Switch to pause / resume mining on the BraiinsOS miner.

    ON  = mining is active (not paused)
    OFF = mining is paused
    """

    _attr_has_entity_name = True
    _attr_name = "Mining"
    _attr_icon = "mdi:pickaxe"

    def __init__(self, coordinator: BraiinsDataUpdateCoordinator) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_mining_switch"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True when miner is reachable."""
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get(COMPUTED_ONLINE, False))

    @property
    def is_on(self) -> bool:
        """Return True when mining is active (not paused)."""
        return not bool(self.coordinator.get_computed(COMPUTED_IS_PAUSED))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Resume mining."""
        try:
            await self.coordinator.api.resume()
            # Update local paused state immediately so UI responds fast
            if self.coordinator.data:
                computed = self.coordinator.data.get("computed", {})
                computed[COMPUTED_IS_PAUSED] = False
        except (BraiinsAPIError, BraiinsConnectionError) as err:
            _LOGGER.error("Failed to resume mining: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause mining."""
        try:
            await self.coordinator.api.pause()
            if self.coordinator.data:
                computed = self.coordinator.data.get("computed", {})
                computed[COMPUTED_IS_PAUSED] = True
        except (BraiinsAPIError, BraiinsConnectionError) as err:
            _LOGGER.error("Failed to pause mining: %s", err)
        await self.coordinator.async_request_refresh()
