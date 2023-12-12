from pathlib import Path
from typing import Optional

from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field, model_validator
from typing_extensions import Annotated

from .helpers import DBPersistMixin, SetQueue


def dictToSetQueue(x):
    return SetQueue(x, capacity=100)


SetQueueField = Annotated[SetQueue, BeforeValidator(dictToSetQueue)]


class WalletDB(BaseModel, DBPersistMixin):
    class Config:
        arbitrary_types_allowed = True

    slime_won: float = 0
    notify_auto_claim: Optional[AwareDatetime] = None
    notified_races: SetQueueField = Field(default_factory=lambda: SetQueue(capacity=100))
    notified_races_over: SetQueueField = Field(default_factory=lambda: SetQueue(capacity=100))

    global_db: 'GlobalDB' = Field(default=None, exclude=True)


class GlobalDB(BaseModel, DBPersistMixin):
    wallets: dict[str, WalletDB] = Field(exclude=True, default={})

    def add_wallet(self, owner):
        if owner not in self.wallets:
            if self.save_file:
                self.wallets[owner] = WalletDB.load_from_file(self.save_file.with_stem(f'db-{owner}'))
            else:
                self.wallets[owner] = WalletDB(global_db=self)
        return self.wallets[owner]

    def total_slime_won(self) -> float:
        total = 0.0
        for w in self.wallets.values():
            total += w.slime_won
        return total
