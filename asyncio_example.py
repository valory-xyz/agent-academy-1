import asyncio
import threading
import time
from datetime import datetime
from typing import List

# subtasks of task A
subtasks: List[asyncio.Future] = []
loop = asyncio.get_event_loop()


def add_blocked_task():
    def blocking_task():
        print(f"\trunning blocking subtask in thread {threading.current_thread().name}")
        time.sleep(20)
        print(f"\tblocking subtask finished")

    subtasks.append(loop.run_in_executor(None, blocking_task))


def add_normal_task():
    def normal_task():
        print(f"\trunning normal subtask in thread {threading.current_thread().name}")
        time.sleep(1)
        print(f"\tnormal subtask finished @ {datetime.now().isoformat()}")

    subtasks.append(loop.run_in_executor(None, normal_task))


async def task_a():
    done, pending = await asyncio.wait(subtasks, return_when=asyncio.FIRST_COMPLETED)
    print("task a finished")
    return "task_a"

async def task_b():
    await asyncio.sleep(3)
    print("task b finished")
    return "task_b"

async def main():
    add_blocked_task()
    task_a_fut = asyncio.ensure_future(loop.create_task(task_a()))
    task_b_fut = asyncio.ensure_future(loop.create_task(task_b()))

    while True:
        done, pending = await asyncio.wait([task_a_fut, task_b_fut], return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.result() == "task_a":
                task_a_fut = asyncio.ensure_future(loop.create_task(task_a()))
            else:
                task_b_fut = asyncio.ensure_future(loop.create_task(task_b()))

        await asyncio.sleep(3)
        add_normal_task()

loop.run_until_complete(main())
