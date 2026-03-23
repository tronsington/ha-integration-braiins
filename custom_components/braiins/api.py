"""BraiinsOS CGMiner TCP API client."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from .const import (
    CMD_ALL,
    CMD_PAUSE,
    CMD_RESUME,
    CMD_SWITCHPOOL,
    CMD_ENABLEPOOL,
    CMD_DISABLEPOOL,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class BraiinsAPIError(Exception):
    """Generic BraiinsOS API error."""


class BraiinsConnectionError(BraiinsAPIError):
    """BraiinsOS connection error."""


class BraiinsAPI:
    """Client for the BraiinsOS CGMiner API (TCP port 4028)."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialise the API client."""
        self._host = host
        self._port = port
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Low-level transport
    # ------------------------------------------------------------------

    async def _send_command(self, command: str, parameter: str | None = None) -> dict[str, Any]:
        """Open a TCP connection, send a command and return the parsed JSON response."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
        except (OSError, asyncio.TimeoutError) as err:
            raise BraiinsConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {err}"
            ) from err

        try:
            payload: dict[str, Any] = {"command": command}
            if parameter is not None:
                payload["parameter"] = parameter

            message = json.dumps(payload) + "\n"
            writer.write(message.encode("utf-8"))
            await writer.drain()

            # Read until connection closed or timeout
            data = b""
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        reader.read(4096), timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    break
                data += chunk

        except (OSError, asyncio.TimeoutError) as err:
            raise BraiinsConnectionError(
                f"Communication error with {self._host}:{self._port}: {err}"
            ) from err
        finally:
            try:
                writer.close()
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:  # noqa: BLE001
                pass

        if not data:
            raise BraiinsAPIError("Empty response received from miner")

        # Strip any trailing NUL bytes before parsing
        text = data.decode("utf-8", errors="replace").rstrip("\x00").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise BraiinsAPIError(f"Failed to parse JSON response: {err}") from err

    # ------------------------------------------------------------------
    # Data-fetch helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract(response: dict[str, Any], key: str) -> list[dict[str, Any]]:
        """Extract the data list for *key* from a (possibly combined) response."""
        # Combined response wraps each sub-command under its lowercase name
        sub = response.get(key.lower())
        if isinstance(sub, dict):
            # e.g. response["summary"]["SUMMARY"][0]
            return sub.get(key.upper(), [])
        # Single-command response has the key at the top level
        return response.get(key.upper(), [])

    async def get_all_data(self) -> dict[str, Any]:
        """Fetch all monitoring data in a single combined command."""
        response = await self._send_command(CMD_ALL)
        return response

    async def test_connection(self) -> dict[str, Any]:
        """Send a version command; raises on failure."""
        return await self._send_command("version")

    # ------------------------------------------------------------------
    # Control commands
    # ------------------------------------------------------------------

    async def pause(self) -> dict[str, Any]:
        """Pause mining."""
        return await self._send_command(CMD_PAUSE)

    async def resume(self) -> dict[str, Any]:
        """Resume mining after a pause."""
        return await self._send_command(CMD_RESUME)

    async def switch_pool(self, pool_index: int) -> dict[str, Any]:
        """Switch the active pool to *pool_index*."""
        return await self._send_command(CMD_SWITCHPOOL, str(pool_index))

    async def enable_pool(self, pool_index: int) -> dict[str, Any]:
        """Enable pool *pool_index*."""
        return await self._send_command(CMD_ENABLEPOOL, str(pool_index))

    async def disable_pool(self, pool_index: int) -> dict[str, Any]:
        """Disable pool *pool_index*."""
        return await self._send_command(CMD_DISABLEPOOL, str(pool_index))
