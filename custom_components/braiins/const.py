"""Constants for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

DOMAIN = "braiins"
MANUFACTURER = "Braiins"

# Platforms
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "switch",
    "button",
    "select",
    "number",
]

# Config entry keys
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_PORT = 4028
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 10

# CGMiner / BraiinsOS API commands
CMD_VERSION = "version"
CMD_SUMMARY = "summary"
CMD_POOLS = "pools"
CMD_DEVS = "devs"
CMD_CONFIG = "config"
CMD_FANS = "fans"
CMD_TEMPS = "temps"
CMD_TUNERSTATUS = "tunerstatus"
CMD_PAUSE = "pause"
CMD_RESUME = "resume"
CMD_SWITCHPOOL = "switchpool"
CMD_ENABLEPOOL = "enablepool"
CMD_DISABLEPOOL = "disablepool"

# Combined fetch command
CMD_ALL = "summary+version+pools+fans+temps+tunerstatus+devs"

# Coordinator data keys
DATA_SUMMARY = "summary"
DATA_VERSION = "version"
DATA_POOLS = "pools"
DATA_FANS = "fans"
DATA_TEMPS = "temps"
DATA_TUNERSTATUS = "tunerstatus"
DATA_DEVS = "devs"
DATA_COMPUTED = "computed"

# Computed value keys
COMPUTED_POWER = "power"
COMPUTED_POWER_LIMIT = "power_limit"
COMPUTED_EFFICIENCY = "efficiency"
COMPUTED_TEMP_MAX = "temp_max"
COMPUTED_TEMP_BOARD_0 = "temp_board_0"
COMPUTED_TEMP_BOARD_1 = "temp_board_1"
COMPUTED_TEMP_BOARD_2 = "temp_board_2"
COMPUTED_FAN_0_RPM = "fan_0_rpm"
COMPUTED_FAN_1_RPM = "fan_1_rpm"
COMPUTED_FAN_0_SPEED = "fan_0_speed"
COMPUTED_FAN_1_SPEED = "fan_1_speed"
COMPUTED_AVG_FAN_RPM = "avg_fan_rpm"
COMPUTED_TUNER_STATUS = "tuner_status"
COMPUTED_FREQUENCY = "frequency"
COMPUTED_BOARD_COUNT = "board_count"
COMPUTED_ACTIVE_POOL_URL = "active_pool_url"
COMPUTED_ACTIVE_POOL_USER = "active_pool_user"
COMPUTED_ACTIVE_POOL_DIFF = "active_pool_diff"
COMPUTED_FW_VERSION = "fw_version"
COMPUTED_IS_PAUSED = "is_paused"
COMPUTED_ONLINE = "online"
