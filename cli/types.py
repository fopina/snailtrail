from dataclasses import dataclass


@dataclass
class RaceJoin:
    snail_id: int
    race_id: int


@dataclass
class Wallet:
    address: str
    private_key: str
