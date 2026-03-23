"""Sensor entities for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfFrequency,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    COMPUTED_POWER,
    COMPUTED_POWER_LIMIT,
    COMPUTED_EFFICIENCY,
    COMPUTED_TEMP_MAX,
    COMPUTED_TEMP_BOARD_0,
    COMPUTED_TEMP_BOARD_1,
    COMPUTED_TEMP_BOARD_2,
    COMPUTED_FAN_0_RPM,
    COMPUTED_FAN_1_RPM,
    COMPUTED_FAN_0_SPEED,
    COMPUTED_FAN_1_SPEED,
    COMPUTED_AVG_FAN_RPM,
    COMPUTED_TUNER_STATUS,
    COMPUTED_FREQUENCY,
    COMPUTED_BOARD_COUNT,
    COMPUTED_ACTIVE_POOL_URL,
    COMPUTED_ACTIVE_POOL_USER,
    COMPUTED_ACTIVE_POOL_DIFF,
    COMPUTED_ACTIVE_POOL_GROUP,
    COMPUTED_FW_VERSION,
    COMPUTED_ONLINE,
)
from .coordinator import BraiinsDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class BrainsSensorEntityDescription(SensorEntityDescription):
    """Extended description with a value accessor function."""

    value_fn: Callable[[BraiinsDataUpdateCoordinator], Any] = lambda c: None


# ---------------------------------------------------------------------------
# Sensor definitions
# ---------------------------------------------------------------------------
# value_fn receives the coordinator and returns the sensor value (or None).
# ---------------------------------------------------------------------------

SENSOR_TYPES: tuple[BrainsSensorEntityDescription, ...] = (
    # ── Hashrate ────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="hashrate_5s",
        name="Hashrate (5s)",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pickaxe",
        value_fn=lambda c: (
            round(float(c.get_value("summary.MHS 5s")) / 1_000_000, 4)
            if c.get_value("summary.MHS 5s") not in (None, 0)
            else None
        ),
    ),
    BrainsSensorEntityDescription(
        key="hashrate_avg",
        name="Hashrate (avg)",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pickaxe",
        value_fn=lambda c: (
            round(float(c.get_value("summary.MHS av")) / 1_000_000, 4)
            if c.get_value("summary.MHS av") not in (None, 0)
            else None
        ),
    ),
    # ── Shares ──────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="shares_accepted",
        name="Shares Accepted",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:check-circle-outline",
        value_fn=lambda c: c.get_value("summary.Accepted"),
    ),
    BrainsSensorEntityDescription(
        key="shares_rejected",
        name="Shares Rejected",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:close-circle-outline",
        value_fn=lambda c: c.get_value("summary.Rejected"),
    ),
    BrainsSensorEntityDescription(
        key="shares_hardware_errors",
        name="Hardware Errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_value("summary.Hardware Errors"),
    ),
    BrainsSensorEntityDescription(
        key="shares_stale",
        name="Stale Shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:timer-sand",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.get_value("summary.Stale"),
    ),
    BrainsSensorEntityDescription(
        key="best_share",
        name="Best Share",
        icon="mdi:star-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.get_value("summary.Best Share"),
    ),
    # ── Uptime ──────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="uptime",
        name="Uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_value("summary.Elapsed"),
    ),
    # ── Power ───────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.get_computed(COMPUTED_POWER),
    ),
    BrainsSensorEntityDescription(
        key="power_limit",
        name="Power Limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lightning-bolt-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_POWER_LIMIT),
    ),
    # ── Efficiency ──────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="efficiency",
        name="Efficiency",
        native_unit_of_measurement="W/TH",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        value_fn=lambda c: c.get_computed(COMPUTED_EFFICIENCY),
    ),
    # ── Temperature ─────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="temperature_max",
        name="Temperature Max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda c: c.get_computed(COMPUTED_TEMP_MAX),
    ),
    BrainsSensorEntityDescription(
        key="temperature_board_0",
        name="Board 0 Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_TEMP_BOARD_0),
    ),
    BrainsSensorEntityDescription(
        key="temperature_board_1",
        name="Board 1 Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_TEMP_BOARD_1),
    ),
    BrainsSensorEntityDescription(
        key="temperature_board_2",
        name="Board 2 Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_TEMP_BOARD_2),
    ),
    # ── Fans ────────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="avg_fan_rpm",
        name="Avg Fan Speed",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda c: c.get_computed(COMPUTED_AVG_FAN_RPM),
    ),
    BrainsSensorEntityDescription(
        key="fan_0_rpm",
        name="Fan 0 Speed",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_FAN_0_RPM),
    ),
    BrainsSensorEntityDescription(
        key="fan_1_rpm",
        name="Fan 1 Speed",
        native_unit_of_measurement="RPM",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_FAN_1_RPM),
    ),
    BrainsSensorEntityDescription(
        key="fan_0_speed_pct",
        name="Fan 0 Speed %",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.get_computed(COMPUTED_FAN_0_SPEED),
    ),
    BrainsSensorEntityDescription(
        key="fan_1_speed_pct",
        name="Fan 1 Speed %",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.get_computed(COMPUTED_FAN_1_SPEED),
    ),
    # ── Tuner ───────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="tuner_status",
        name="Tuner Status",
        icon="mdi:tune",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_TUNER_STATUS),
    ),
    BrainsSensorEntityDescription(
        key="frequency",
        name="Frequency",
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.get_computed(COMPUTED_FREQUENCY),
    ),
    # ── Pool ────────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="pool_url",
        name="Pool URL",
        icon="mdi:pool",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_ACTIVE_POOL_URL),
    ),
    BrainsSensorEntityDescription(
        key="pool_user",
        name="Pool User",
        icon="mdi:account-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_ACTIVE_POOL_USER),
    ),
    BrainsSensorEntityDescription(
        key="pool_difficulty",
        name="Pool Difficulty",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:approximately-equal",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.get_computed(COMPUTED_ACTIVE_POOL_DIFF),
    ),
    BrainsSensorEntityDescription(
        key="pool_group",
        name="Pool Group",
        icon="mdi:server-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_ACTIVE_POOL_GROUP),
    ),
    # ── System ──────────────────────────────────────────────────────────────
    BrainsSensorEntityDescription(
        key="fw_version",
        name="Firmware Version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_FW_VERSION),
    ),
    BrainsSensorEntityDescription(
        key="board_count",
        name="Board Count",
        icon="mdi:developer-board",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.get_computed(COMPUTED_BOARD_COUNT),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BraiinsOS sensor entities."""
    coordinator: BraiinsDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrainsSensor(coordinator, description) for description in SENSOR_TYPES
    )


class BrainsSensor(CoordinatorEntity[BraiinsDataUpdateCoordinator], SensorEntity):
    """A sensor entity for BraiinsOS miner data."""

    _attr_has_entity_name = True
    entity_description: BrainsSensorEntityDescription

    def __init__(
        self,
        coordinator: BraiinsDataUpdateCoordinator,
        description: BrainsSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True when the miner is reachable."""
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.get(COMPUTED_ONLINE, False))

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        try:
            return self.entity_description.value_fn(self.coordinator)
        except Exception:  # noqa: BLE001
            return None
