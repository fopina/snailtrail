import configargparse
from pathlib import Path

from ..types import Wallet, RaceJoin


class FileOrString(str):
    def __new__(cls, content):
        f = Path(content)
        if f.exists():
            return str.__new__(cls, f.read_text().strip())
        return str.__new__(cls, content)


class FileOrInt(int):
    def __new__(cls, content):
        f = Path(content)
        if f.exists():
            return int.__new__(cls, f.read_text().strip())
        return int.__new__(cls, content)


class AppendWalletAction(configargparse.argparse._AppendAction):
    def __call__(self, parser, namespace, values, option_string=None):
        return super().__call__(parser, namespace, Wallet(*map(FileOrString, values)), option_string)


class DefaultOption(str):
    pass


class StoreRaceJoin(configargparse.argparse.Action):
    def __init__(
        self,
        option_strings,
        dest,
        nargs=2,
        const=None,
        default=None,
        type=int,
        choices=None,
        required=False,
        help=None,
        metavar=('SNAIL_ID', 'RACE_ID'),
    ):
        if type != int:
            raise ValueError('type must always be int (default)')
        if nargs != 2:
            raise ValueError('nargs must always be 2 (default)')
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)

    def __call__(self, parser, namespace, values, option_string):
        setattr(namespace, self.dest, RaceJoin(*values))
