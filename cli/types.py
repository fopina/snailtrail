from dataclasses import dataclass

from web3 import Account


@dataclass
class RaceJoin:
    snail_id: int
    race_id: int


@dataclass
class Wallet:
    address: str
    account: Account

    @classmethod
    def from_private_key(cls, private_key):
        a = Account.from_key(private_key)
        return cls(a.address, a)

    def __str__(self) -> str:
        return f'Wallet({self.address})'
