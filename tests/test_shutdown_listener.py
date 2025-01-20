import os
import signal
import threading

from leaky.shutdown_listener import should_continue


def test_should_continue_initial():
    assert should_continue() is True


def test_signal_handling():
    if threading.current_thread() is threading.main_thread():
        os.kill(os.getpid(), signal.SIGINT)
        assert should_continue() is False
