"""This module monitors the app for shutdown signals"""

import asyncio
import signal
import threading
import time
from types import FrameType
import logging

logger = logging.getLogger(__name__)

HANDLED_SIGNALS = (
    signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)

_should_exit = None


def _register_signal_handler(sig: signal.Signals):
    original_handler = None

    def handler(sig_: int, frame: FrameType | None):
        logger.debug("shutdown_signal:%s", sig_)
        global _should_exit
        _should_exit = True
        if original_handler:
            original_handler(sig_, frame)  # type: ignore[unreachable]

    original_handler = signal.signal(sig, handler)


def _register_signal_handlers():
    global _should_exit
    if _should_exit is not None:
        return
    _should_exit = False
    logger.debug("_register_signal_handlers")
    # Check if we're in the main thread of the main interpreter
    if threading.current_thread() is threading.main_thread():
        logger.debug("_register_signal_handlers:main_thread")
        for sig in HANDLED_SIGNALS:
            _register_signal_handler(sig)
    else:
        logger.debug("_register_signal_handlers:not_main_thread")


def should_exit() -> bool:
    _register_signal_handlers()
    return bool(_should_exit)


def should_continue() -> bool:
    _register_signal_handlers()
    return not _should_exit


def sleep_if_should_continue(timeout: float):
    if timeout <= 1:
        time.sleep(timeout)
        return
    start_time = time.time()
    while (time.time() - start_time) < timeout and should_continue():
        time.sleep(1)


async def async_sleep_if_should_continue(timeout: float):
    if timeout <= 1:
        await asyncio.sleep(timeout)
        return
    start_time = time.time()
    while time.time() - start_time < timeout and should_continue():
        await asyncio.sleep(1)
