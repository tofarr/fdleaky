import builtins
from dataclasses import dataclass, field
import socket
from tempfile import _io
from threading import Thread
import traceback as tb

from fdleaky.dir_fd_info_store import DirFdInfoStore
from fdleaky.fd import Fd
from fdleaky.fd_info_factory import FdInfoFactory
from fdleaky.fd_info_store import FdInfoStore


# pylint: disable=R0902, W0622
@dataclass
class FdTracker:
    """
    Tracker for leaking file descriptors. Patches built in function storing a stack trace for when
    they are File Descriptors are Opened in a local dictionary. A file descriptor may be copied to
    long term storage, if the associated factory can create an info object for it.
    """

    fd_info_factory: FdInfoFactory = field(default_factory=FdInfoFactory)
    long_term_store: FdInfoStore = field(default_factory=DirFdInfoStore)
    short_term_store: dict[int, Fd] = field(default_factory=dict)
    sleep_interval: int = 5
    is_open: bool = False
    _id_mapping: dict[int, str] = field(default_factory=dict)
    _original_open: callable = None
    _original_init: callable = None
    _original_close: callable = None
    _original_detach: callable = None
    _worker: Thread = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        return False

    def start(self):
        if self.is_open:
            return
        self._original_open = builtins.open
        self._original_init = socket.socket.__init__
        self._original_close = socket.socket.close
        self._original_detach = socket.socket.detach
        builtins.open = self._patched_open
        _io.open = self._patched_open
        socket.socket.__init__ = self._patched_init
        socket.socket.close = self._patched_close
        socket.socket.detach = self._patched_detach
        self._worker = Thread(target=self._do_long_term_store, daemon=True)
        self._worker.start()
        self.is_open = True

    def close(self):
        if not self.is_open:
            return
        builtins.open = self._patched_open  # pylint: disable=W0622
        socket.socket.__init__ = self._original_init
        socket.socket.close = self._original_close
        socket.socket.detach = self._original_detach
        self.is_open = False
        self._worker.join()

    def _create_fd(self, file_obj) -> int:
        fd = Fd(file_obj, tb.format_stack())
        id_ = id(file_obj)
        self.short_term_store[id_] = fd
        return id_

    def _close_fd(self, id_: int):
        self.short_term_store.pop(id_)
        stored_id = self._id_mapping.pop(id_, None)
        if stored_id:
            self.long_term_store.delete(stored_id)

    def _patched_open(self, *args, **kwargs):
        file_obj = self._original_open(*args, **kwargs)
        fd = self._create_fd(file_obj)
        file_close = file_obj.close

        def patched_file_close(*args, **kwargs):
            result = file_close(*args, **kwargs)
            self._close_fd(fd)
            return result

        file_obj.close = patched_file_close
        return file_obj

    def _patched_init(self, *args, **kwargs):
        result = self._original_init(*args, **kwargs)
        subject = _get_subject(args, kwargs)
        self._create_fd(subject)
        return result

    def _patched_close(self, *args, **kwargs):
        result = self._original_close(*args, **kwargs)
        subject = _get_subject(args, kwargs)
        id_ = id(subject)
        self._close_fd(id_)
        return result

    def _patched_detach(self, *args, **kwargs):
        result = self._original_detach(*args, **kwargs)
        subject = _get_subject(args, kwargs)
        id_ = id(subject)
        self._close_fd(id_)
        return result

    def _do_long_term_store(self):
        while self.is_open:
            for fd in list(self.short_term_store.values()):
                id_ = id(fd.subject)
                if id_ not in self._id_mapping:
                    fd_info = self.fd_info_factory.create_fd_info(fd)
                    if fd_info:
                        self.long_term_store.create(fd_info)
                        self._id_mapping[id_] = fd_info.id


def _get_subject(args, kwargs):
    if len(args) >= 1:
        return args[0]
    return kwargs["self"]
