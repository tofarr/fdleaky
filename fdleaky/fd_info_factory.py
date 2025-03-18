

from dataclasses import dataclass, field
from datetime import datetime
import time
from fdleaky.fd import Fd
from fdleaky.fd_info import FdInfo


@dataclass
class FdInfoFactory:
    """
    Object for creating a FdInfo object from an Fd - also useful for determining if an fd should be transferred 
    to long term storage. This is Useful for filtering out general cases we don't want to monitor, such as
    database connection pools and listen operations on server sockets.

    The default implementation stores any open file descriptor over 1 minute old.
    """
    min_age: int = 60
    identifier_include_any_of: list[str] = field(default_factory=lambda: [""])

    def create_fd_info(self, fd: Fd) -> FdInfo | None:
        time_alive = time.time() - fd.created_at
        if time_alive < self.min_age:
            return None
        identifier = self.get_identifier(fd)
        if identifier is None:
            return None
        return FdInfo(
            identifier=identifier,
            stack=fd.stack,
            created_at=datetime.fromtimestamp(fd.created_at),
        )

    def get_identifier(self, fd: Fd) -> str | None:
        return next((
            frame for frame in fd.stack
            if next((
                True for include in self.identifier_include_any_of
                if include in frame
            ), False)
        ), None)
