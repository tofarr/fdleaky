from dataclasses import dataclass, field
import time
from typing import Any


@dataclass(frozen=True)
class Fd:
    """File descriptor object created each time a file descriptor is opened."""

    subject: Any
    stack: list[str]
    created_at: float = field(default_factory=time.time)
