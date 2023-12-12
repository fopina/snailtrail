import json
from pathlib import Path

from pydantic import Field


class SetQueue(dict):
    def __init__(self, *args, capacity=10, **kwargs):
        super().__init__(*args, **kwargs)
        self.capacity = capacity
        self.size = 0

    def add(self, item):
        # delete first to make sure it ends in last
        try:
            self.remove(item)
        except KeyError:
            pass
        self[item] = None
        self.size += 1
        self.truncate()

    def truncate(self, capacity=None):
        capacity = capacity or self.capacity
        while self.size > capacity:
            _f = next(iter(self.keys()))
            self.remove(_f)

    def remove(self, item):
        del self[item]
        self.size -= 1


class DBPersistMixin:
    save_file: Path = Field(default=None, exclude=True)

    @classmethod
    def load_from_file(cls, filename: Path):
        if not filename.exists():
            # all good, create file whenever save is called
            return cls(save_file=filename)
        raw_data = filename.read_text()
        if not raw_data:
            # empty file is also ok
            data = {}
        else:
            data = json.loads(raw_data)
        data['save_file'] = filename
        return cls(**data)

    def save(self, to: Path = None) -> bool:
        if to is None:
            to = self.save_file
        if to is None:
            return False
        to.write_text(self.model_dump_json())
        return True
