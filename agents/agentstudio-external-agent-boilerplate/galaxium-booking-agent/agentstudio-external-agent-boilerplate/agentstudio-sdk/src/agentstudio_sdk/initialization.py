import asyncio
import concurrent.futures
from .hooks import load_hooks_from_env
from .phoenix import initialize_phoenix
from .agent_registration import register_agent_when_ready_in_background
from .settings import ICASettings


def _run_async_init(ica_settings: ICASettings):
    try:
        _ = asyncio.get_running_loop()

        # If we get here, there's a running loop - run in a separate thread
        def _run_in_new_loop():
            """Create a new event loop in this thread and run the initialization."""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(initialize_phoenix(ica_settings))
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_in_new_loop)
            future.result()
    except RuntimeError:
        # No running event loop, safe to use asyncio.run()
        asyncio.run(initialize_phoenix(ica_settings))


def initialize_ica(ica_settings: ICASettings, port: int):
    load_hooks_from_env()
    _run_async_init(ica_settings)
    register_agent_when_ready_in_background(ica_settings, port, max_retries=3, retry_delay=1.0)
