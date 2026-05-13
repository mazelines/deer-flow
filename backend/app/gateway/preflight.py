"""Gateway startup preflight tasks.

Runs once before multi-worker Uvicorn starts so shared persistence schemas are
created by a single process. This avoids first-boot DDL races when Postgres is
used with multiple gateway workers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import AsyncExitStack

from deerflow.config.app_config import AppConfig
from deerflow.persistence.engine import close_engine, init_engine_from_config
from deerflow.runtime.checkpointer.async_provider import make_checkpointer
from deerflow.runtime.store.async_provider import make_store

logger = logging.getLogger(__name__)


async def run_preflight(config_path: str = "config.yaml") -> None:
    """Initialize persistence schemas before the gateway workers start."""
    resolved_config_path = os.getenv("DEER_FLOW_CONFIG_PATH") or config_path
    config = AppConfig.from_file(resolved_config_path)

    try:
        async with AsyncExitStack() as stack:
            await init_engine_from_config(config.database)
            await stack.enter_async_context(make_checkpointer(config))
            await stack.enter_async_context(make_store(config))
    finally:
        await close_engine()

    logger.info("Gateway preflight completed")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_preflight())


if __name__ == "__main__":
    main()
