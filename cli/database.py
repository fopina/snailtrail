import json
from pathlib import Path

from pydantic import BaseModel, Field, PositiveFloat, model_validator


class WalletDB(BaseModel):
    slime_won: PositiveFloat = 0
    global_db: 'GlobalDB' = Field(default=None, exclude=True)

    def save(self) -> bool:
        if self.global_db:
            return self.global_db.save()
        return False


class GlobalDB(BaseModel):
    wallets: dict[str, WalletDB] = {}
    save_file: Path = Field(default=None, exclude=True)

    @model_validator(mode='after')
    def add_db_to_wallets(self) -> 'GlobalDB':
        for w in self.wallets.values():
            w.global_db = self
        return self

    def add_wallet(self, owner):
        if owner not in self.wallets:
            self.wallets[owner] = WalletDB(global_db=self)
        return self.wallets[owner]

    def save(self, to: Path = None) -> bool:
        if to is None:
            to = self.save_file
        if to is None:
            return False
        to.write_text(self.model_dump_json())
        return True

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