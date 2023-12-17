from typing import Optional

from pydantic import AwareDatetime, BeforeValidator, Field, model_validator
from pydantic.functional_serializers import PlainSerializer
from typing_extensions import Annotated

from .helpers import PersistingBaseModel, SetQueue


def dictToSetQueue(x):
    return SetQueue(x, capacity=100)


def set_queue_to_list(x):
    return list(x.keys())


SetQueueField = Annotated[SetQueue, BeforeValidator(dictToSetQueue), PlainSerializer(set_queue_to_list)]


class WalletDB(PersistingBaseModel):
    model_config = dict(arbitrary_types_allowed=True)

    slime_won: float = 0
    slime_won_normal: float = 0
    slime_won_last: float = 0
    notify_auto_claim: Optional[AwareDatetime] = None
    notified_races: SetQueueField = Field(default_factory=lambda: SetQueue(capacity=100))
    notified_races_over: SetQueueField = Field(default_factory=lambda: SetQueue(capacity=100))
    joins_last: SetQueueField = Field(default_factory=lambda: SetQueue(capacity=100))
    joins_normal: SetQueueField = Field(default_factory=lambda: SetQueue(capacity=100))
    tournament_market_cache: dict[int, tuple] = {}
    notify_burn_coefficent: Optional[float] = None
    notify_fee_monitor: Optional[float] = None

    global_db: 'GlobalDB' = Field(default_factory=lambda: GlobalDB(), exclude=True)


class GlobalDB(PersistingBaseModel):
    wallets: dict[str, WalletDB] = Field(exclude=True, default={})
    fee_spike_start: Optional[AwareDatetime] = None
    fee_spike_notified: bool = False

    @model_validator(mode='after')
    def add_db_to_wallets(self) -> 'GlobalDB':
        for k, w in self.wallets.items():
            w.global_db = self
            w.save_file = None if not self.save_file else self.save_file.with_stem(f'db-{k}')
        return self

    def add_wallet(self, owner):
        if owner not in self.wallets:
            if self.save_file:
                self.wallets[owner] = WalletDB.load_from_file(self.save_file.with_stem(f'db-{owner}'))
                self.wallets[owner].global_db = self
            else:
                self.wallets[owner] = WalletDB(global_db=self)
        return self.wallets[owner]

    def total_slime_won(self) -> tuple[float, float, float]:
        """aggregates totals of every wallet and returns tuple with: total, total_last, total_normal"""
        total = 0
        total_last = 0
        total_normal = 0
        for w in self.wallets.values():
            total += w.slime_won
            total_last += w.slime_won_last
            total_normal += w.slime_won_normal
        return total, total_last, total_normal