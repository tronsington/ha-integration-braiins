"""Number entities for the Exergy - BraiinsOS Miner integration.

The Power Target entity lets you set a desired wattage target in Home Assistant.
This value is stored in HA state (persisted across restarts via RestoreEntity)
and can be used in automations to alert when actual power deviates from the
target. The BraiinsOS CGMiner API does not expose a power-set command, so
the target is not sent to the miner directly — BraiinsOS autotuning manages
actual power based on its internal configuration.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, COMPUTED_ONLINE
from .coordinator import BraiinsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Sensible watt range covering most BraiinsOS-compatible hardware
POWER_TARGET_MIN = 100.0
POWER_TARGET_MAX = 10000.0
POWER_TARGET_STEP = 10.0
POWER_TARGET_DEFAULT = 3500.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BraiinsOS number entities."""
    coordinator: BraiinsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BrainsPowerTargetNumber(coordinator)])


class BrainsPowerTargetNumber(
    CoordinatorEntity[BraiinsDataUpdateCoordinator],
    NumberEntity,
    RestoreEntity,
):
    """Number entity representing the user's desired power target in watts.

    The value is persisted in HA state across restarts. It is intentionally
    decoupled from the miner's internal autotuner so it can be used freely
    in dashboards and automations (e.g. "alert when actual power > target + 5%").
    """

    _attr_has_entity_name = True
    _attr_name = "Power Target"
    _attr_icon = "mdi:lightning-bolt"
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = POWER_TARGET_MIN
    _attr_native_max_value = POWER_TARGET_MAX
    _attr_native_step = POWER_TARGET_STEP
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: BraiinsDataUpdateCoordinator) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_power_target"
        self._attr_device_info = coordinator.device_info
        self._target: float = POWER_TARGET_DEFAULT

    async def async_added_to_hass(self) -> None:
        """Restore previous state on startup."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._target = float(last_state.state)
                self.coordinator.target_power_watts = self._target
            except (ValueError, TypeError):
                pass

    @property
    def available(self) -> bool:
        """Power target is always available for editing."""
        return True

    @property
    def native_value(self) -> float:
        """Return the current target wattage."""
        return self._target

    async def async_set_native_value(self, value: float) -> None:
        """Store the new target wattage (HA-side only)."""
        self._target = value
        self.coordinator.target_power_watts = value
        _LOGGER.debug(
            "Power target set to %.0f W (stored in HA, not sent to miner)", value
        )
        self.async_write_ha_state()
