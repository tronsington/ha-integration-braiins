"""Config flow for the Exergy - BraiinsOS Miner integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import BraiinsAPI, BraiinsConnectionError, BraiinsAPIError
from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_GRPC_PORT,
    CONF_SCAN_INTERVAL,
    CONF_PASSWORD,
    CONF_GRPC_PORT,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): vol.All(int, vol.Range(min=5, max=300)),
    }
)


class BraiinsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Exergy - BraiinsOS Miner."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: collect host and port."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Prevent duplicate entries for the same host
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            api = BraiinsAPI(host=host, port=port)
            try:
                await api.test_connection()
            except BraiinsConnectionError:
                errors["base"] = "cannot_connect"
            except BraiinsAPIError:
                errors["base"] = "api_error"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during connection test")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"BraiinsOS Miner ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                    },
                    options={
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BraiinsOptionsFlow:
        """Return the options flow handler."""
        return BraiinsOptionsFlow(config_entry)


class BraiinsOptionsFlow(OptionsFlow):
    """Handle options for an existing BraiinsOS Miner entry."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        current_password = self._config_entry.options.get(CONF_PASSWORD, "")
        current_grpc_port = self._config_entry.options.get(
            CONF_GRPC_PORT, DEFAULT_GRPC_PORT
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=current_scan_interval
                    ): vol.All(int, vol.Range(min=5, max=300)),
                    vol.Optional(CONF_PASSWORD, default=current_password): str,
                    vol.Optional(
                        CONF_GRPC_PORT, default=current_grpc_port
                    ): vol.All(int, vol.Range(min=1, max=65535)),
                }
            ),
        )
