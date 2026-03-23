"""Select entities for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BraiinsAPIError, BraiinsConnectionError
from .const import DOMAIN, COMPUTED_ONLINE, COMPUTED_ACTIVE_POOL_URL
from .coordinator import BraiinsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BraiinsOS select entities."""
    coordinator: BraiinsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrainsPoolSelector(coordinator)])


class BrainsPoolSelector(
    CoordinatorEntity[BraiinsDataUpdateCoordinator], SelectEntity
):
    """Select entity to switch between configured mining pools.

    Note: pool switching in BraiinsOS CGMiner API resets after a miner
    restart. This is a known upstream limitation.
    """

    _attr_has_entity_name = True
    _attr_name = "Active Pool"
    _attr_icon = "mdi:pool"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: BraiinsDataUpdateCoordinator) -> None:
        """Initialise the pool selector."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_pool_selector"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True when miner is reachable and pool data exists."""
        if not self.coordinator.data:
            return False
        if not self.coordinator.data.get(COMPUTED_ONLINE, False):
            return False
        pools = self.coordinator.data.get("pools") or []
        return len(pools) > 0

    @property
    def options(self) -> list[str]:
        """Return list of pool URLs to choose from."""
        pools = (self.coordinator.data or {}).get("pools") or []
        return [p.get("URL", f"Pool {p.get('POOL', i)}") for i, p in enumerate(pools)]

    @property
    def current_option(self) -> str | None:
        """Return the currently active pool URL."""
        return self.coordinator.get_computed(COMPUTED_ACTIVE_POOL_URL)

    async def async_select_option(self, option: str) -> None:
        """Switch to the selected pool.

        Finds the pool index for the chosen URL and sends switchpool.
        """
        pools = (self.coordinator.data or {}).get("pools") or []
        for pool in pools:
            url = pool.get("URL", "")
            if url == option:
                pool_index = pool.get("POOL", 0)
                try:
                    await self.coordinator.api.switch_pool(pool_index)
                    _LOGGER.info("Switched to pool %s (index %s)", option, pool_index)
                except (BraiinsAPIError, BraiinsConnectionError) as err:
                    _LOGGER.error("Failed to switch pool: %s", err)
                await self.coordinator.async_request_refresh()
                return
        _LOGGER.warning("Pool '%s' not found in pool list", option)
