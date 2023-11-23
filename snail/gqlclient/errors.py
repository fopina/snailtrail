class APIError(Exception):
    """API expected errors"""

    def __str__(self) -> str:
        """
        >>> str(APIError([['a']]))
        'a'
        >>> str(APIError([['a', 'b']]))
        'a|b'
        >>> str(APIError([['a', 'b'], ['c']]))
        'a|b\\nc'
        >>> e = APIError.make([['This snail tried joining a mission as last, needs to rest 92 seconds']])
        >>> e
        NeedsToRestAPIError([['This snail tried joining a mission as last, needs to rest 92 seconds']])
        >>> e.seconds
        92.0
        """
        return '\n'.join('|'.join(y) for x in self.args for y in x)

    @classmethod
    def make(cls, problems):
        if len(problems) == 1 and len(problems[0]) == 1:
            if problems[0][0] == 'Race is already full':
                return RaceAlreadyFullAPIError(problems)
            if problems[0][0] == 'Number of registrants for race is inaccurate':
                return RaceInnacurateRegistrantsAPIError(problems)
            if problems[0][0] == 'Race entry failed':
                return RaceEntryFailedAPIError(problems)
            if problems[0][0].startswith('This snail tried joining a mission as last, needs to rest '):
                return NeedsToRestAPIError(problems)
        return cls(problems)


class RaceAlreadyFullAPIError(APIError):
    """Specific type for "Race is already full" """


class RaceInnacurateRegistrantsAPIError(APIError):
    """Specific type for "Number of registrants for race is inaccurate" """


class RaceEntryFailedAPIError(APIError):
    """Specific type for "Race entry failed" """


class NeedsToRestAPIError(APIError):
    """Specific type for "This snail tried joining a mission as last, needs to rest ..." """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.seconds = float(args[0][0][0][58:].split(' ', 1)[0])
