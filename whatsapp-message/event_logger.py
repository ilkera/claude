from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone


MAX_EVENTS = 10_000


class EventLogger:
    def __init__(self, filepath: str = "events_log.json") -> None:
        self.filepath = filepath

    def log(self, event_type: str, **kwargs: object) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **kwargs,
        }
        with open(self.filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._rotate_if_needed()

    def _rotate_if_needed(self) -> None:
        try:
            with open(self.filepath, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return

        if len(lines) <= MAX_EVENTS:
            return

        keep = lines[-MAX_EVENTS:]
        dir_name = os.path.dirname(os.path.abspath(self.filepath))
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as tmp:
                tmp.writelines(keep)
            os.replace(tmp_path, self.filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
