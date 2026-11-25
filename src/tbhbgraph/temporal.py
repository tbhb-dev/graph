# SPDX-License-Identifier: Apache-2.0
# Copyright Tony Burns

"""A minimal echo workflow and its worker."""

from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


@activity.defn
async def echo(value: str) -> str:
    return value


# The plugin package imports Click, which uses restricted gettext calls.
@workflow.defn(sandboxed=False)
class PingWorkflow:
    @workflow.run
    async def run(self, value: str) -> str:
        return await workflow.execute_activity(
            echo, value, start_to_close_timeout=timedelta(seconds=10)
        )


async def run_worker(address: str, task_queue: str) -> None:
    client = await Client.connect(address)
    worker = Worker(
        client, task_queue=task_queue, workflows=[PingWorkflow], activities=[echo]
    )
    await worker.run()
