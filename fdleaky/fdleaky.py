import builtins
import fcntl
import logging
import os
import socket
import sys
import termios
import time
import traceback
from dataclasses import dataclass, field
from threading import Thread
from typing import Any, Callable, Iterator
from tempfile import _io


@dataclass(frozen=True)
class FD:
    subject: Any
    stack: list[str]
    created_at: float = field(default_factory=time.time)


FDS: dict[int, FD] = {}
INTERVAL = 1
_patched = False


def get_self(args, kwargs):
    if len(args) >= 1:
        return args[0]
    return kwargs["self"]


original_open = builtins.open
original_init = socket.socket.__init__
original_close = socket.socket.close
original_detach = socket.socket.detach

logger = logging.getLogger(__name__)


def print_error(msg: str, stack_trace: list[str]):
    output = [f"\n===== {msg} =====\n"]
    output.extend(stack_trace[:-1])
    logger.error("".join(output))


def patched_open(*args, **kwargs):
    file_obj = original_open(*args, **kwargs)
    id_ = id(file_obj)
    file_close = file_obj.close

    def patched_file_close(*args, **kwargs):
        FDS.pop(id_, None)
        result = file_close(*args, **kwargs)
        return result

    file_obj.close = patched_file_close
    FDS[id_] = FD(file_obj, traceback.format_stack())
    return file_obj


def patched_init(*args, **kwargs):
    result = original_init(*args, **kwargs)
    self = get_self(args, kwargs)
    id_ = id(self)
    FDS[id_] = FD(self, traceback.format_stack())
    return result


def patched_close(*args, **kwargs):
    self = get_self(args, kwargs)
    id_ = id(self)
    FDS.pop(id_, None)
    result = original_close(*args, **kwargs)
    return result


def patched_detach(*args, **kwargs):
    self = get_self(args, kwargs)
    id_ = id(self)
    FDS.pop(id_, None)
    result = original_detach(*args, **kwargs)
    return result


def getch():
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    try:
        while True:
            try:
                c = sys.stdin.read(1)
                return c
            except IOError:
                pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


def sample_fds(matcher: Callable[[FD], bool]) -> Iterator[FD]:
    for id_, fd in list(FDS.items()):
        if matcher(fd):
            FDS.pop(id_)
            yield fd


def sample_at_interval(matcher: Callable[[FD], bool], processor: Callable[[FD], None]):
    while True:
        for fd in sample_fds(matcher):
            processor(fd)
        time.sleep(INTERVAL)


def start_sample_at_interval(
    matcher: Callable[[FD], bool], processor: Callable[[FD], None]
):
    Thread(target=sample_at_interval, args=(matcher, processor), daemon=True).start()


def sample_on_key_press(matcher: Callable[[FD], bool]):
    try:
        while True:
            if getch() == "p":
                logger.error("\n===== LISTING =====\n")
                for fd in sample_fds(matcher):
                    print_error("UNCLOSED", fd.stack)
            time.sleep(INTERVAL)
    except SystemExit:
        for fd in FDS.values():
            print_error("UNCLOSED", fd.stack)


def start_sample_on_key_press():
    Thread(target=sample_on_key_press, args=(lambda fd: True,), daemon=True).start()


def patch_fds():
    global _patched  # pylint: disable=W0603
    if _patched:
        return
    _patched = True
    builtins.open = patched_open
    _io.open = patched_open  # Also patch _io.open for tempfile module
    socket.socket.__init__ = patched_init  # type: ignore
    socket.socket.close = patched_close  # type: ignore
    socket.socket.detach = patched_detach  # type: ignore
