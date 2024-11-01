from dataclasses import dataclass

from web3 import Account

from snail.gqlclient.types import Snail


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
        """
        >>> w = Wallet('aa', Account())
        >>> str(w)
        'Wallet(aa)'
        >>> f'x{w}x'
        'xWallet(aa)x'
        """
        return f'Wallet({self.address})'

    def __repr__(self) -> str:
        return str(self)


@dataclass
class RaceCandidate:
    score: int
    snail: Snail
