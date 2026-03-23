"""BraiinsOS gRPC client for power target control (port 50051)."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Ensure bundled proto stubs are importable as 'bos.v1.*'
_COMP_DIR = os.path.dirname(os.path.abspath(__file__))
if _COMP_DIR not in sys.path:
    sys.path.insert(0, _COMP_DIR)

try:
    import grpc
    from bos.v1 import authentication_pb2, authentication_pb2_grpc  # noqa: E402
    from bos.v1 import performance_pb2, performance_pb2_grpc  # noqa: E402
    from bos.v1 import pool_pb2, pool_pb2_grpc  # noqa: E402
    from bos.v1 import units_pb2, common_pb2  # noqa: E402
    _GRPC_AVAILABLE = True
except ImportError as _err:
    _LOGGER.warning("grpcio or proto stubs not available; gRPC features disabled: %s", _err)
    _GRPC_AVAILABLE = False


class BraiinsGRPCError(Exception):
    """Raised when a gRPC call fails."""


class BraiinsGRPCClient:
    """Thin gRPC client covering power-target control and pool-group status."""

    def __init__(self, host: str, port: int, password: str) -> None:
        self._host = host
        self._port = port
        self._password = password
        self._token: str = ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _channel(self) -> "grpc.Channel":
        return grpc.insecure_channel(f"{self._host}:{self._port}")

    def _authenticate_sync(self) -> str:
        """Blocking login — run via executor."""
        with self._channel() as channel:
            stub = authentication_pb2_grpc.AuthenticationServiceStub(channel)
            future = stub.Login.future(
                authentication_pb2.LoginRequest(username="root", password=self._password)
            )
            future.result()  # wait for completion
            # Token arrives in initial gRPC metadata, not the response body
            token = dict(future.initial_metadata()).get("authorization", "")
        if not token:
            raise BraiinsGRPCError(
                "gRPC login succeeded but returned no token — check password"
            )
        return token

    def _set_power_target_sync(self, watts: int) -> int:
        """Blocking SetPowerTarget call — run via executor."""
        meta = [("authorization", self._token)]
        with self._channel() as channel:
            stub = performance_pb2_grpc.PerformanceServiceStub(channel)
            req = performance_pb2.SetPowerTargetRequest(
                save_action=common_pb2.SAVE_ACTION_SAVE_AND_APPLY,
                power_target=units_pb2.Power(watt=watts),
            )
            resp = stub.SetPowerTarget(req, metadata=meta)
        return int(resp.power_target.watt)

    def _get_pool_groups_sync(self) -> list[dict[str, Any]]:
        """Blocking GetPoolGroups call — run via executor."""
        meta = [("authorization", self._token)]
        with self._channel() as channel:
            stub = pool_pb2_grpc.PoolServiceStub(channel)
            resp = stub.GetPoolGroups(pool_pb2.GetPoolGroupsRequest(), metadata=meta)
        groups: list[dict[str, Any]] = []
        for pg in resp.pool_groups:
            pools_data = [
                {
                    "url": p.url,
                    "user": p.user,
                    "enabled": p.enabled,
                    "active": p.active,
                }
                for p in pg.pools
            ]
            groups.append(
                {
                    "name": pg.name,
                    "pools": pools_data,
                    "active": any(p["active"] for p in pools_data),
                }
            )
        return groups

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Authenticate and cache the session token."""
        loop = asyncio.get_event_loop()
        self._token = await loop.run_in_executor(None, self._authenticate_sync)
        _LOGGER.debug("gRPC authenticated to %s:%s", self._host, self._port)

    async def set_power_target(self, watts: int) -> int:
        """Set the miner's power target and return the confirmed watt value."""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._set_power_target_sync, watts)
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.UNAUTHENTICATED:
                _LOGGER.debug("gRPC token expired, re-authenticating")
                await self.authenticate()
                return await loop.run_in_executor(None, self._set_power_target_sync, watts)
            raise BraiinsGRPCError(
                f"SetPowerTarget failed ({err.code()}): {err.details()}"
            ) from err

    async def get_pool_groups(self) -> list[dict[str, Any]]:
        """Return pool groups with active-pool flags from the miner."""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._get_pool_groups_sync)
        except grpc.RpcError as err:
            if err.code() == grpc.StatusCode.UNAUTHENTICATED:
                await self.authenticate()
                return await loop.run_in_executor(None, self._get_pool_groups_sync)
            raise BraiinsGRPCError(
                f"GetPoolGroups failed ({err.code()}): {err.details()}"
            ) from err
