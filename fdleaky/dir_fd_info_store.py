

from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
from fdleaky.fd_info import FdInfo
from fdleaky.fd_info_store import FdInfoStore


@dataclass
class DirFdInfoStore(FdInfoStore):
    dir: Path = Path("fdleaky/")

    def create(self, fd_info: FdInfo):
        json_obj = asdict(fd_info)
        json_obj['created_at'] = str(json_obj['created_at'])
        with open(self.dir / f"{fd_info.id}.json", mode="w") as file:
            json.dump(json_obj, file, indent=2)

    def delete(self, stored_id: str) -> bool:
        """ Load an FdInfo object from its id """
        file_path = self.dir / f"{stored_id}.json"
        try:
            file_path.unlink()
            return True
        except FileNotFoundError:
            return False
