"""
Shared async-in-sync helper for running coroutines from synchronous contexts.

Used by Celery tasks and email service where async DB access is needed
from non-async code.
"""
import asyncio
import concurrent.futures


def run_async(coro):
    """Run a coroutine in sync context (Celery worker, email service, etc.).

    Handles both cases: when event loop exists and when it doesn't.
    """
    try:
        asyncio.get_running_loop()
        # Already in a running loop - run in separate thread with new loop
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - use asyncio.run()
        return asyncio.run(coro)
