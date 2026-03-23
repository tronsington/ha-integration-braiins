"""The Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .api import BraiinsAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_GRPC_PORT,
    CONF_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_GRPC_PORT,
)
from .coordinator import BraiinsDataUpdateCoordinator
from .grpc_client import BraiinsGRPCClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Exergy - BraiinsOS Miner from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    api = BraiinsAPI(host=host, port=port)

    coordinator = BraiinsDataUpdateCoordinator(
        hass=hass,
        api=api,
        host=host,
        scan_interval=scan_interval,
    )

    # gRPC client setup (optional — requires password in options)
    coordinator.grpc_client = None
    password = entry.options.get(CONF_PASSWORD) or entry.data.get(CONF_PASSWORD)
    if password:
        grpc_port = entry.options.get(CONF_GRPC_PORT) or entry.data.get(
            CONF_GRPC_PORT, DEFAULT_GRPC_PORT
        )
        grpc_client = BraiinsGRPCClient(host=host, port=grpc_port, password=password)
        try:
            await grpc_client.authenticate()
            coordinator.grpc_client = grpc_client
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "gRPC authentication failed for %s; power target will be stored locally only: %s",
                host,
                err,
            )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
