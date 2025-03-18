from abc import ABC, abstractmethod

from fdleaky.fd_info import FdInfo


class FdInfoStore(ABC):
    @abstractmethod
    def create(self, fd_info: FdInfo):
        """Load an FdInfo object from its id"""

    @abstractmethod
    def delete(self, stored_id: str) -> bool:
        """Load an FdInfo object from its id"""
