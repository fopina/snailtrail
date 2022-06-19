from typing import Any
from enum import Enum
from datetime import datetime, timezone


class Gender(Enum):
    UNDEFINED = 0
    FEMALE = 1
    MALE = 2


class AttrDict(dict):
    def __getattribute__(self, __name: str) -> Any:
        if __name in Snail.__dict__.keys():
            return super().__getattribute__(__name)
        return self[__name]


class Snail(AttrDict):
    """
    >>> s = Snail({'gender':{'id':2}, 'name': 'ehlo'})
    >>> s.name
    'ehlo'
    >>> s.gender
    <Gender.MALE: 2>
    """

    @property
    def gender(self):
        return list(Gender)[self['gender']['id']]

    @property
    def monthly_breed_available(self):
        return self['breeding']['breed_detail']['monthly_breed_available']
    
    @property
    def breed_cycle_end(self):
        x = self['breeding']['breed_detail']['cycle_end']
        if x is None:
            return x
        return _parse_datetime(x)

    @property
    def market_price(self):
        return self.market['price']
    
    @property
    def queueable_at(self):
        return _parse_datetime_micro(self['queueable_at'])


def _parse_datetime(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


def _parse_datetime_micro(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)