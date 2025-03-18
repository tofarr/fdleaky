from dataclasses import dataclass, field
import datetime
from uuid import uuid4


@dataclass
class FdInfo:
    """File descriptor info saved to longer term storage after a file descirptor has been left open for some time."""

    id: str = field(default_factory=uuid4)
    identifier: str
    stack: list[str]
    created_at: datetime
