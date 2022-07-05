from typing import Any
from enum import Enum
from datetime import datetime, timezone


class Gender(Enum):
    UNDEFINED = 0
    FEMALE = 1
    MALE = 2

    def __str__(self) -> str:
        return self.name


class AttrDict(dict):
    _DICT_METHODS = set(dir(dict))

    def __getattribute__(self, __name: str) -> Any:
        if __name in AttrDict._DICT_METHODS:
            return super().__getattribute__(__name)
        if __name in self.__class__.__dict__.keys():
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
    def genome_str(self):
        return ''.join(self.genome)

    @property
    def level(self):
        return self.stats['experience']['level']

    @property
    def breed_status(self):
        """
        return < 0 if breeding available: -1 for normal ones, -2 if it's the first breed (ex-newborn)
        otherwise returns number of days left to be able to breed
        """
        if self.monthly_breed_available > 0:
            return -1
        elif self.gender == Gender.UNDEFINED and self.breed_cycle_end is None:
            return -2
        else:
            # cannot use `days_remaining` because new borns will have it as 0, but they do have cycle_end :shrug:
            return (self.breed_cycle_end - datetime.now(tz=timezone.utc)).total_seconds() / (60 * 60 * 24)

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

    def __str__(self) -> str:
        """
        >>> s = Snail({'id': 8940, 'adaptations': ['Glacier'], 'name': 'Snail #8940', 'gender': {'id': 1}, 'new_born': True, 'genome': ['H', 'H', 'G', 'A', 'H', 'A', 'A', 'G', 'M', 'H', 'M', 'H', 'H', 'G', 'H', 'H', 'X', 'H', 'H', 'H'], 'klass': 'Expert', 'family': 'Helix', 'purity': 11, 'breeding': {'breed_detail': {'cycle_end': '2022-07-25 16:50:19', 'monthly_breed_available': 0}}, 'stats': {'elo': '1424', 'experience': {'level': 1, 'xp': 50, 'remaining': 200}, 'mission_tickets': -1}})
        >>> s.name
        'Snail #8940'
        >>> str(s)
        'Snail #8940 1 Helix FEMALE Expert 11 HHGAHAAGMHMHHGHHXHHH'
        >>> s = Snail({'id': 8940, 'adaptations': ['Glacier'], 'name': 'Superman', 'gender': {'id': 1}, 'new_born': True, 'genome': ['H', 'H', 'G', 'A', 'H', 'A', 'A', 'G', 'M', 'H', 'M', 'H', 'H', 'G', 'H', 'H', 'X', 'H', 'H', 'H'], 'klass': 'Expert', 'family': 'Helix', 'purity': 11, 'breeding': {'breed_detail': {'cycle_end': '2022-07-25 16:50:19', 'monthly_breed_available': 0}}, 'stats': {'elo': '1424', 'experience': {'level': 1, 'xp': 50, 'remaining': 200}, 'mission_tickets': -1}})
        >>> str(s)
        'Superman #8940 1 Helix FEMALE Expert 11 HHGAHAAGMHMHHGHHXHHH'
        """
        pr = self.name
        if str(self.id) not in pr:
            pr = f'{pr} #{self.id}'
        return f"{pr} {self.level} {self.family} {self.gender} {self.klass} {self.purity} {self.genome_str}"


class Race(AttrDict):
    @property
    def is_mission(self):
        """
        >>> s = Race({'distance': 57})
        >>> s.is_mission
        False
        >>> s = Race({'distance': 'Treasury Run'})
        >>> s.is_mission
        True
        """
        return self.distance == 'Treasury Run'


def _parse_datetime(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


def _parse_datetime_micro(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
