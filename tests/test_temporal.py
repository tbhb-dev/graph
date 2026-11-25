# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

import asyncio
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from temporalio.client import Client

from tbhbgraph.temporal import PingWorkflow, echo, run_worker

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterator
    from pathlib import Path


_LOG = logging.getLogger(__name__)


def test_echo() -> None:
    assert asyncio.run(echo("ping")) == "ping"


def test_ping_workflow_without_server(monkeypatch: pytest.MonkeyPatch) -> None:
    async def execute_activity(
        activity: Callable[[str], Awaitable[str]],
        value: str,
        *,
        start_to_close_timeout: timedelta,
    ) -> str:
        assert activity is echo
        assert start_to_close_timeout == timedelta(seconds=10)
        return value

    monkeypatch.setattr("temporalio.workflow.execute_activity", execute_activity)
    assert asyncio.run(PingWorkflow().run("ping")) == "ping"


def test_run_worker_without_server(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object()
    runs: list[bool] = []

    async def connect(address: str) -> object:
        assert address == "localhost:7233"
        return client

    class FakeWorker:
        def __init__(
            self,
            connected_client: object,
            *,
            task_queue: str,
            workflows: list[type[PingWorkflow]],
            activities: list[Callable[[str], Awaitable[str]]],
        ) -> None:
            assert connected_client is client
            assert task_queue == "test-ping"
            assert workflows == [PingWorkflow]
            assert activities == [echo]

        async def run(self) -> None:
            runs.append(True)

    monkeypatch.setattr("temporalio.client.Client.connect", connect)
    monkeypatch.setattr("tbhbgraph.temporal.Worker", FakeWorker)
    asyncio.run(run_worker("localhost:7233", "test-ping"))
    assert runs == [True]


@pytest.fixture
def temporal_address(tmp_path: Path) -> Iterator[str]:
    binary = shutil.which(os.environ["TEMPORAL_BINARY"])
    assert binary is not None
    for port in range(17233, 17333):
        with socket.socket() as connection:
            connection.settimeout(1)
            if connection.connect_ex(("127.0.0.1", port)) != 0:
                break
    else:
        pytest.fail("No free Temporal port found")

    address = f"127.0.0.1:{port}"
    with (tmp_path / "temporal-server.log").open("w+") as server_log:
        process = subprocess.Popen(
            [
                binary,
                "server",
                "start-dev",
                "--headless",
                "--ip",
                "127.0.0.1",
                "--port",
                str(port),
                "--dynamic-config-value",
                "frontend.enableServerVersionCheck=false",
            ],
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    server_log.seek(0)
                    pytest.fail(f"Temporal dev server exited: {server_log.read()}")
                health = subprocess.run(
                    [
                        binary,
                        "operator",
                        "cluster",
                        "health",
                        "--address",
                        address,
                        "--command-timeout",
                        "1s",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2,
                )
                if health.returncode == 0:
                    _LOG.info("Started Temporal dev server; cluster is healthy")
                    break
                time.sleep(1)
            else:
                server_log.seek(0)
                pytest.fail(f"Temporal health timed out: {server_log.read()}")
            yield address
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                pytest.fail(
                    "Temporal dev server leaked after shutdown; killed and reaped"
                )
            _LOG.info("Stopped and reaped Temporal dev server")


async def _execute_ping(address: str) -> None:
    task_queue = "test-ping"
    worker = asyncio.create_task(run_worker(address, task_queue))
    try:
        client = await Client.connect(address)
        result = await client.execute_workflow(
            PingWorkflow.run,
            "ping",
            id="test-ping",
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=15),
            rpc_timeout=timedelta(seconds=20),
        )
        assert result == "ping"
        _LOG.info("Ping workflow echoed its input through the activity")
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Tech debt: pytest dev-server test skipped on Windows (same gap as PR #5)",
)
def test_ping_workflow(temporal_address: str) -> None:
    asyncio.run(_execute_ping(temporal_address))
