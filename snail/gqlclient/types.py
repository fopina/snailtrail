import itertools
from collections import Counter, defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Gender(Enum):
    UNDEFINED = 0
    FEMALE = 1
    MALE = 2

    def __str__(self) -> str:
        return self.name

    def emoji(self):
        if self == self.MALE:
            return '👨'
        elif self == self.FEMALE:
            return '👩'
        return '🐤'


class Family(Enum):
    """
    Mapping taken directly from game JS
    (search for `Garden = 1` to refresh mapping)

    >>> s = Family.GARDEN
    >>> s.name
    'GARDEN'
    >>> str(s)
    'Garden'
    >>> repr(s)
    "<Family.GARDEN: (1, 'G')>"
    >>> str(Family.from_str('garden'))
    'Garden'
    >>> str(Family.from_id(2))
    'Helix'
    >>> str(Family.from_gene('X'))
    'Atlantis'
    """

    GARDEN = 1, 'G'
    HELIX = 2, 'H'
    MILK = 3, 'M'
    AGATE = 4, 'A'
    ATLANTIS = 5, 'X'

    def __str__(self) -> str:
        return self.name.capitalize()

    @property
    def id(self):
        return self.value[0]

    @property
    def gene(self):
        return self.value[1]

    @classmethod
    def from_id(cls, id: int):
        for i in cls:
            if id == i.id:
                return i

    @classmethod
    def from_gene(cls, gene: str):
        for i in cls:
            if gene == i.gene:
                return i

    @classmethod
    def from_str(cls, id: str):
        return cls[id.upper()]


class Adaptation(Enum):
    """
    Mapping taken directly from game JS

    >>> s = Adaptation.MOUNTAIN
    >>> s.name
    'MOUNTAIN'
    >>> str(s)
    'Mountain'
    >>> s.id
    2
    >>> Adaptation.from_id(2)
    Mountain
    >>> Adaptation.from_str('Mountain')
    Mountain
    >>> str([Adaptation.MOUNTAIN])
    '[Mountain]'
    """

    DESERT = 1, 'Desert'
    MOUNTAIN = 2, 'Mountain'
    BEACH = 3, 'Beach'
    GLACIER = 4, 'Glacier'
    FOREST = 5, 'Forest'
    SPACE = 6, 'Space'

    HOT = 40, 'Hot'
    COLD = 41, 'Cold'
    WIND = 42, 'Wind'
    WET = 43, 'Wet'
    SNOW = 44, 'Snow'
    STORM = 45, 'Storm'

    SLIDE = 80, 'Slide'
    JUMP = 81, 'Jump'
    ROLL = 82, 'Roll'
    DODGE = 83, 'Dodge'

    def __str__(self) -> str:
        return self.value[1]

    def __repr__(self) -> str:
        return str(self)

    def is_athletics(self):
        return int(self.value[0] / 10) == 8

    def is_landscape(self):
        return int(self.value[0] / 10) == 0

    def is_weather(self):
        return int(self.value[0] / 10) == 4

    @property
    def id(self):
        return self.value[0]

    @classmethod
    def from_id(cls, id: int):
        for i in cls:
            if id == i.id:
                return i

    @classmethod
    def from_str(cls, id: str):
        # simplify for now while name matches value text
        return cls[id.upper()]


class AttrDict(dict):
    _DICT_METHODS = set(dir(dict))

    def __getattribute__(self, __name: str) -> Any:
        # FIXME: accessing dict values using this is A LOT slower
        if __name in AttrDict._DICT_METHODS:
            return super().__getattribute__(__name)
        if __name in self.__class__.__dict__.keys():
            return super().__getattribute__(__name)
        return self.get(__name)


class Snail(AttrDict):
    """
    >>> s = Snail({'gender':{'id':2}, 'name': 'ehlo'})
    >>> s.name
    'ehlo'
    >>> s.gender
    <Gender.MALE: 2>
    >>> s.gender.emoji()
    '👨'
    """

    GENE_FEES = {
        'X': 6,
        'A': 5,
        'M': 4,
        'H': 3,
        'G': 2,
    }

    def __hash__(self):
        return self.id

    @property
    def name_id(self):
        pr = self.name or f'#{self.id}'
        if str(self.id) not in pr:
            pr = f'{pr} (#{self.id})'
        return pr

    @property
    def gender(self):
        if 'gender' in self:
            return list(Gender)[self['gender']['id']]

    @property
    def can_change_gender(self):
        if self.breed_status == -2:
            return True
        x = self.can_change_gender_at
        if x:
            return (x - datetime.now(tz=timezone.utc)).total_seconds() < 0
        return False

    @property
    def can_change_gender_at(self):
        if 'gender' in self:
            x = self['gender'].get('can_change_at')
            if x:
                return _parse_datetime(x)

    @property
    def adaptations(self) -> Optional[list[Adaptation]]:
        """
        >>> s = Snail({'gender':{'id':2}, 'adaptations': ['Wet', 'Mountain', 'Jump']})
        >>> s.adaptations
        [Wet, Mountain, Jump]
        """
        if 'adaptations' in self:
            return list(map(Adaptation.from_str, self['adaptations']))

    @property
    def ordered_adaptations(self):
        """
        >>> s = Snail({'gender':{'id':2}, 'adaptations': ['Wet', 'Mountain', 'Jump']})
        >>> s.ordered_adaptations
        [Mountain, Wet, Jump]
        """
        adaptations = self.adaptations
        if adaptations is None:
            return
        r = [None, None, None]
        for adaptation in adaptations:
            if adaptation.is_landscape():
                r[0] = adaptation
            elif adaptation.is_weather():
                r[1] = adaptation
            else:
                r[2] = adaptation
        return r

    @property
    def monthly_breed_available(self):
        return self['breeding']['breed_detail']['monthly_breed_available']

    @property
    def monthly_breed_limit(self):
        return self['breeding']['breed_detail']['monthly_breed_limit']

    @property
    def genome_str(self):
        if self.genome:
            return ''.join(self.genome)

    @property
    def family(self):
        return Family.from_str(self['family'])

    @property
    def level(self):
        return self.stats['experience']['level']

    @property
    def level_str(self):
        return f'L{self.level}'

    @property
    def purity_str(self):
        return f'P{self.purity}'

    @property
    def slime_boost_str(self):
        if self.slime_boost and self.slime_boost > 1:
            return f'S{self.slime_boost}'
        return ''

    @property
    def work_boost_str(self):
        if self.work_boost and self.work_boost > 1:
            return f'W{self.work_boost}'
        return ''

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
        elif self.breed_cycle_end is None:
            # if P20, this is normal, other it is not...
            return -3
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
    def breed_count_total(self):
        return self['breeding']['breed_detail']['breed_count_total']

    @property
    def market_price(self):
        return self.market['price']

    @property
    def gene_market_price(self):
        return self.gene_market['price']

    @property
    def queueable_at(self):
        return _parse_datetime(self['queueable_at'])

    def incubation_fee(self, other_snail: 'Snail', pc=1.0):
        # https://docs.snailtrail.art/reproduction/incubator/incubation_fee/#incubation-fee
        """
        >>> sf = Snail({'id': 8267, 'name': 'X', 'gender': {'id': 1}, 'genome': ['G', 'M', 'G', 'X', 'G', 'G', 'G', 'M', 'G', 'G', 'G', 'G', 'M', 'G', 'A', 'G', 'G', 'G', 'H', 'X'], 'breeding': {'breed_detail': {'breed_count_total': 1}}})
        >>> sm = Snail({'id': 9217, 'name': 'Y', 'gender': {'id': 2}, 'genome': ['X', 'H', 'M', 'H', 'M', 'M', 'M', 'A', 'M', 'X', 'M', 'M', 'M', 'G', 'A', 'H', 'M', 'G', 'M', 'H'], 'breeding': {'breed_detail': {'breed_count_total': 0.333333333}}})
        >>> sf.incubation_fee(sm, pc=7.786)
        1200.0821332980368
        """
        acc = 0
        for i in range(20):
            acc += self.GENE_FEES[self.genome[i]] + self.GENE_FEES[other_snail.genome[i]]
        acc = acc * (1 + (self.breed_count_total + other_snail.breed_count_total) / 10) * pc
        return acc

    def incubation_simulation(self, other_snail: 'Snail'):
        # https://docs.snailtrail.art/reproduction/incubator/incubation_fee/#incubation-fee
        """
        >>> sf = Snail({'id': 8267, 'name': 'X', 'gender': {'id': 1}, 'genome': ['G', 'M', 'G', 'X', 'G', 'G', 'G', 'M', 'G', 'G', 'G', 'G', 'M', 'G', 'A', 'G', 'G', 'G', 'H', 'X']})
        >>> sm = Snail({'id': 2397, 'name': 'Y', 'gender': {'id': 2}, 'genome': ['M', 'H', 'M', 'M', 'A', 'M', 'G', 'M', 'H', 'M', 'M', 'M', 'M', 'M', 'X', 'A', 'M', 'H', 'H', 'X']})
        >>> sf.incubation_simulation(sm)
        ([('M', 75942), ('G', 108814)], [(('M', 12), 10), (('G', 11), 66), (('M', 11), 406), (('M', 6), 420), (('G', 10), 1760), (('M', 10), 4410), (('G', 6), 6496), (('G', 9), 13860), (('M', 7), 15680), (('M', 9), 19260), (('M', 8), 35756), (('G', 7), 43120), (('G', 8), 43512)], 184756)
        """
        counter = defaultdict(lambda: 0)

        total = 0
        for pos in itertools.combinations(range(20), 10):
            total += 1
            genome = other_snail.genome.copy()
            for i in pos:
                genome[i] = self['genome'][i]
            f = self.family_from_genome(genome)
            counter[f] += 1
        r = sorted(counter.items(), key=lambda x: x[1])
        counter_family = defaultdict(lambda: 0)
        for x in r:
            counter_family[x[0][0]] += x[1]
        return sorted(counter_family.items(), key=lambda x: x[1]), r, total

    @staticmethod
    def family_from_genome(genome):
        """
        >>> Snail.family_from_genome(['G', 'M', 'G', 'X', 'G', 'G', 'G', 'M', 'G', 'G', 'G', 'G', 'M', 'G', 'A', 'G', 'G', 'G', 'H', 'X'])
        ('G', 13)
        >>> Snail.family_from_genome(['M', 'H', 'M', 'M', 'A', 'M', 'G', 'M', 'H', 'M', 'M', 'M', 'M', 'M', 'X', 'A', 'M', 'H', 'H', 'X'])
        ('M', 11)
        >>> Snail.family_from_genome(['X', 'X', 'X', 'X', 'X', 'X', 'X', 'X', 'X', 'X', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G', 'G'])
        ('G', 10)
        """
        counter = Counter(genome)
        s = counter.most_common()
        c = s[0]
        for s1 in s[1:]:
            if s1[1] != c[1]:
                break
            # lesser fee, more dominant!
            if Snail.GENE_FEES[s1[0]] < Snail.GENE_FEES[c[0]]:
                c = s1
        return c

    def __str__(self) -> str:
        """
        >>> s = Snail({'id': 8940, 'adaptations': ['Glacier'], 'name': 'Snail #8940', 'gender': {'id': 1}, 'new_born': True, 'genome': ['H', 'H', 'G', 'A', 'H', 'A', 'A', 'G', 'M', 'H', 'M', 'H', 'H', 'G', 'H', 'H', 'X', 'H', 'H', 'H'], 'klass': 'Expert', 'family': 'Helix', 'purity': 11, 'breeding': {'breed_detail': {'cycle_end': '2022-07-25 16:50:19', 'monthly_breed_available': 0}}, 'stats': {'elo': '1424', 'experience': {'level': 1, 'xp': 50, 'remaining': 200}, 'mission_tickets': -1}})
        >>> s.name
        'Snail #8940'
        >>> str(s)
        'Snail #8940 L1 Helix 👩 Expert P11  '
        >>> s = Snail({'id': 8940, 'adaptations': ['Glacier'], 'name': 'Superman', 'gender': {'id': 1}, 'new_born': True, 'genome': ['H', 'H', 'G', 'A', 'H', 'A', 'A', 'G', 'M', 'H', 'M', 'H', 'H', 'G', 'H', 'H', 'X', 'H', 'H', 'H'], 'klass': 'Expert', 'family': 'Helix', 'purity': 11, 'breeding': {'breed_detail': {'cycle_end': '2022-07-25 16:50:19', 'monthly_breed_available': 0}}, 'stats': {'elo': '1424', 'experience': {'level': 1, 'xp': 50, 'remaining': 200}, 'mission_tickets': -1}})
        >>> str(s)
        'Superman (#8940) L1 Helix 👩 Expert P11  '
        """
        return f"{self.name_id} {self.level_str} {self.family} {self.gender.emoji()} {self.klass} {self.purity_str} {self.slime_boost_str} {self.work_boost_str}"


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
        >>> str(s)
        'None (#None): Treasury Run'
        """
        return self.distance == 'Treasury Run'

    @property
    def is_mega(self):
        """
        >>> s = Race({'distance': 57})
        >>> s.is_mega
        False
        >>> s = Race({'distance': 'Mega Run'})
        >>> s.is_mega
        True
        >>> str(s)
        'None (#None): Mega Run'
        """
        return self.distance == 'Mega Run'

    @property
    def is_competitive(self):
        """
        >>> s = Race({'distance': 'Mega Run'})
        >>> s.is_competitive
        False
        >>> s = Race({'distance': 57})
        >>> s.is_competitive
        True
        >>> str(s)
        'None (#None): 57m None 🪙'
        """
        return self.league != 'Tournament' and (type(self.distance) == int or self.distance.isdigit())

    @property
    def is_tournament(self):
        """
        >>> s = Race({'distance': 57})
        >>> s.is_tournament
        False
        >>> s = Race({'distance': 57, 'league': 'Tournament'})
        >>> s.is_tournament
        True
        >>> str(s)
        'None (#None): 57m None 🪙'
        """
        return self.league == 'Tournament'

    def __str__(self):
        if self.is_competitive or self.is_tournament:
            return f"{self.track} (#{self.id}): {self.distance}m {self.race_type} 🪙"
        return f"{self.track} (#{self.id}): {self.distance}"

    @property
    def conditions(self):
        if 'conditions' in self:
            return list(map(Adaptation.from_str, self['conditions']))


class InventoryItem(AttrDict):
    """
    Items returned by inventory_promise
    """


def _parse_datetime(date_str):
    if '.' in date_str:
        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
