"""DataUpdateCoordinator for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BraiinsAPI, BraiinsConnectionError, BraiinsAPIError
from .const import (
    DOMAIN,
    MANUFACTURER,
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
    COMPUTED_IS_PAUSED,
    COMPUTED_ONLINE,
    COMPUTED_MODEL,
)

_LOGGER = logging.getLogger(__name__)


class BraiinsDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches all BraiinsOS miner data and computes derived values."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: BraiinsAPI,
        host: str,
        scan_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.host = host
        self._device_info: DeviceInfo | None = None
        # Persisted target wattage set by the user via the number entity
        self.target_power_watts: float | None = None
        # Optional gRPC client; set by __init__.py after authentication
        self.grpc_client: Any = None

    # ------------------------------------------------------------------
    # Update logic
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from miner and compute derived values."""
        try:
            raw = await self.api.get_all_data()
        except BraiinsConnectionError as err:
            _LOGGER.debug("Connection error fetching data: %s", err)
            # Return a minimal dict so entities stay available but show unavailable
            return {COMPUTED_ONLINE: False}
        except BraiinsAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err

        data: dict[str, Any] = {COMPUTED_ONLINE: True}

        # ------------------------------------------------------------------
        # Parse each sub-command from the combined response.
        # BraiinsOS combined commands nest each result under its lowercase key.
        # ------------------------------------------------------------------
        summary = self._parse_sub(raw, "summary", "SUMMARY")
        version = self._parse_sub(raw, "version", "VERSION")
        pools = self._parse_sub_list(raw, "pools", "POOLS")
        fans = self._parse_sub_list(raw, "fans", "FANS")
        temps = self._parse_sub_list(raw, "temps", "TEMPS")
        tunerstatus = self._parse_sub(raw, "tunerstatus", "TUNERSTATUS")
        devs = self._parse_sub_list(raw, "devs", "DEVS")
        devdetails = self._parse_sub_list(raw, "devdetails", "DEVDETAILS")

        data["summary"] = summary
        data["version"] = version
        data["pools"] = pools
        data["fans"] = fans
        data["temps"] = temps
        data["tunerstatus"] = tunerstatus
        data["devs"] = devs
        data["devdetails"] = devdetails

        # ------------------------------------------------------------------
        # Computed values
        # ------------------------------------------------------------------
        computed: dict[str, Any] = {}

        # Firmware version — BraiinsOS reports as "BOSer" field
        computed[COMPUTED_FW_VERSION] = version.get("BOSer") if version else None

        # Hardware model from devdetails (e.g. "Antminer S19J Pro NoPic")
        computed[COMPUTED_MODEL] = devdetails[0].get("Model") if devdetails else None

        # Board count
        computed[COMPUTED_BOARD_COUNT] = len(devs) if devs else 0

        # Per-board temperatures (from TEMPS list, keyed by TEMP index 0/1/2)
        # BraiinsOS returns "Board" (PCB) and "Chip" temps per board.
        # We display Chip temp as it better reflects thermal load.
        temp_map = {t.get("TEMP", i): t for i, t in enumerate(temps or [])}
        board_temps: list[float] = []
        for board_idx, key in enumerate([COMPUTED_TEMP_BOARD_0, COMPUTED_TEMP_BOARD_1, COMPUTED_TEMP_BOARD_2]):
            t = temp_map.get(board_idx)
            if t is not None:
                chip_temp = t.get("Chip")
                board_temp = t.get("Board")
                # Prefer chip temp, fall back to board (PCB) temp
                val = chip_temp if chip_temp not in (None, 0.0) else board_temp
                if val and float(val) > 0:
                    computed[key] = round(float(val), 1)
                    board_temps.append(float(val))
                else:
                    computed[key] = None
            else:
                computed[key] = None

        computed[COMPUTED_TEMP_MAX] = max(board_temps) if board_temps else None

        # Fan speeds — expose Fan 0 and Fan 1 individually; average ALL fans
        fan_map = {f.get("FAN", i): f for i, f in enumerate(fans or [])}
        fan_rpms: list[float] = []
        for fan_idx, (rpm_key, speed_key) in enumerate(
            [(COMPUTED_FAN_0_RPM, COMPUTED_FAN_0_SPEED), (COMPUTED_FAN_1_RPM, COMPUTED_FAN_1_SPEED)]
        ):
            f = fan_map.get(fan_idx)
            if f is not None:
                rpm = f.get("RPM")
                speed = f.get("Speed")
                computed[rpm_key] = int(rpm) if rpm is not None else None
                computed[speed_key] = int(speed) if speed is not None else None
            else:
                computed[rpm_key] = None
                computed[speed_key] = None

        # Average across ALL fans reported by the miner (may be 2, 4, or more)
        for f in (fans or []):
            rpm = f.get("RPM")
            if rpm is not None:
                fan_rpms.append(float(rpm))

        computed[COMPUTED_AVG_FAN_RPM] = round(sum(fan_rpms) / len(fan_rpms)) if fan_rpms else None

        # Power & power limit from top-level tunerstatus fields.
        # "ApproximateMinerPowerConsumption" is the total miner draw in watts.
        # "PowerLimit" is the configured watt ceiling sent to the autotuner.
        total_power: float = 0.0
        total_power_limit: float = 0.0
        tuner_statuses: list[str] = []

        if tunerstatus:
            miner_power = tunerstatus.get("ApproximateMinerPowerConsumption")
            power_limit = tunerstatus.get("PowerLimit")
            if miner_power is not None:
                total_power = float(miner_power)
            if power_limit is not None:
                total_power_limit = float(power_limit)

            # Collect per-chain tuner statuses (e.g. "Stable", "Tuning")
            for chain in tunerstatus.get("TunerChainStatus", []):
                status = chain.get("Status")
                if status:
                    tuner_statuses.append(str(status))

        computed[COMPUTED_POWER] = round(total_power, 1) if total_power > 0 else None
        computed[COMPUTED_POWER_LIMIT] = round(total_power_limit, 1) if total_power_limit > 0 else None

        # Frequency: average across all boards from devdetails
        freq_values = [
            float(d["Frequency"]) for d in (devdetails or []) if d.get("Frequency")
        ]
        computed[COMPUTED_FREQUENCY] = (
            round(sum(freq_values) / len(freq_values), 1) if freq_values else None
        )

        # Tuner status: deduplicated summary across chains
        if tuner_statuses:
            unique = list(dict.fromkeys(tuner_statuses))  # preserve order
            computed[COMPUTED_TUNER_STATUS] = ", ".join(unique)
        else:
            computed[COMPUTED_TUNER_STATUS] = None

        # Efficiency: W per TH/s — API reports hashrate in MH/s (1 TH = 1,000,000 MH)
        hashrate_mhs = summary.get("MHS 5s") if summary else None
        if hashrate_mhs and total_power > 0:
            hashrate_ths = float(hashrate_mhs) / 1_000_000.0
            computed[COMPUTED_EFFICIENCY] = round(total_power / hashrate_ths, 2) if hashrate_ths > 0 else None
        else:
            computed[COMPUTED_EFFICIENCY] = None

        # Active pool (first pool with Status == "Alive" and Stratum Active)
        active_pool: dict[str, Any] | None = None
        for pool in (pools or []):
            if pool.get("Status") == "Alive" and pool.get("Stratum Active"):
                active_pool = pool
                break
        if active_pool is None and pools:
            active_pool = pools[0]

        computed[COMPUTED_ACTIVE_POOL_URL] = active_pool.get("URL") if active_pool else None
        computed[COMPUTED_ACTIVE_POOL_USER] = active_pool.get("User") if active_pool else None
        computed[COMPUTED_ACTIVE_POOL_DIFF] = active_pool.get("Stratum Difficulty") if active_pool else None

        # Pause state: no direct field in data – we track it via is_paused flag
        # We preserve is_paused from previous data if connection is live
        prev_paused = (self.data or {}).get(COMPUTED_IS_PAUSED, False)
        computed[COMPUTED_IS_PAUSED] = prev_paused

        # Active pool group name via gRPC (optional)
        computed[COMPUTED_ACTIVE_POOL_GROUP] = None
        if self.grpc_client is not None:
            try:
                groups = await self.grpc_client.get_pool_groups()
                for group in groups:
                    if group.get("active"):
                        computed[COMPUTED_ACTIVE_POOL_GROUP] = group.get("name")
                        break
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("gRPC GetPoolGroups failed (non-fatal): %s", err)

        data["computed"] = computed

        # Build / refresh device info
        self._build_device_info(version, computed)

        return data

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_sub(raw: dict[str, Any], cmd: str, data_key: str) -> dict[str, Any] | None:
        """Extract the first item dict from a sub-command's data list.

        BraiinsOS combined-command responses wrap each sub-result in a list:
          raw["summary"] = [{"STATUS": [...], "SUMMARY": [...]}]
        Single-command responses have the data key at the top level:
          raw["SUMMARY"] = [...]
        """
        sub = raw.get(cmd)
        # Unwrap the list wrapper used in combined responses
        if isinstance(sub, list) and sub:
            sub = sub[0]
        if isinstance(sub, dict):
            items = sub.get(data_key, [])
        else:
            # Single-command response: data key sits at top level
            items = raw.get(data_key, [])
        if items and isinstance(items, list):
            return items[0]
        return None

    @staticmethod
    def _parse_sub_list(raw: dict[str, Any], cmd: str, data_key: str) -> list[dict[str, Any]]:
        """Extract the data list from a sub-command's response."""
        sub = raw.get(cmd)
        # Unwrap the list wrapper used in combined responses
        if isinstance(sub, list) and sub:
            sub = sub[0]
        if isinstance(sub, dict):
            return sub.get(data_key, [])
        return raw.get(data_key, [])

    # ------------------------------------------------------------------
    # Device info
    # ------------------------------------------------------------------

    def _build_device_info(
        self,
        version: dict[str, Any] | None,
        computed: dict[str, Any],
    ) -> None:
        """Build or refresh HA device info from API data."""
        fw_version = version.get("BOSer") if version else None
        # Hardware model comes from devdetails (e.g. "Antminer S19J Pro NoPic")
        hw_model = computed.get(COMPUTED_MODEL)

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, self.host)},
            name=f"BraiinsOS Miner ({self.host})",
            manufacturer=MANUFACTURER,
            model=hw_model,
            sw_version=fw_version,
            configuration_url=f"http://{self.host}",
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return HA device info, building a minimal version if not yet populated."""
        if self._device_info is None:
            self._device_info = DeviceInfo(
                identifiers={(DOMAIN, self.host)},
                name=f"BraiinsOS Miner ({self.host})",
                manufacturer=MANUFACTURER,
                configuration_url=f"http://{self.host}",
            )
        return self._device_info

    # ------------------------------------------------------------------
    # Data accessors
    # ------------------------------------------------------------------

    def get_value(self, path: str) -> Any:
        """Retrieve a value from coordinator data using dot-notation path.

        Example: get_value("summary.GHS 5s")
        """
        if not self.data:
            return None
        parts = path.split(".", 1)
        section = self.data.get(parts[0])
        if len(parts) == 1:
            return section
        if isinstance(section, dict):
            return section.get(parts[1])
        return None

    def get_computed(self, key: str) -> Any:
        """Retrieve a pre-computed value."""
        if not self.data:
            return None
        return (self.data.get("computed") or {}).get(key)
