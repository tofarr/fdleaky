import os
import signal
import threading
import time

import pytest

from leaky.shutdown_listener import (
    should_continue,
    should_exit,
    sleep_if_should_continue,
    async_sleep_if_should_continue,
)


def test_should_continue_initial():
    assert should_continue() is True
    assert should_exit() is False


def test_signal_handling():
    if threading.current_thread() is threading.main_thread():
        os.kill(os.getpid(), signal.SIGINT)
        assert should_continue() is False
        assert should_exit() is True


def test_sleep_if_should_continue():
    start = time.time()
    sleep_if_should_continue(0.1)
    duration = time.time() - start
    assert duration >= 0.1


@pytest.mark.asyncio
async def test_async_sleep_if_should_continue():
    start = time.time()
    await async_sleep_if_should_continue(0.1)
    duration = time.time() - start
    assert duration >= 0.1
