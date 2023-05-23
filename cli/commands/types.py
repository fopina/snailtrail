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
    # FIXME: hack to access wallet list from any other action as the primary parser namespace is not available to subparsers...
    WALLETS = []

    def __call__(self, parser, namespace, values, option_string=None):
        w = Wallet(*map(FileOrString, values))
        self.WALLETS.append(w)
        return super().__call__(parser, namespace, w, option_string)


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


def wallet_ext_or_int(index_or_address: str):
    if index_or_address[:2].lower() == '0x':
        return Wallet(index_or_address, '')

    if not index_or_address.isnumeric():
        raise ValueError('must start with 0x (address) or be a number (account index)')

    index_or_address = int(index_or_address)
    l = len(AppendWalletAction.WALLETS)
    if index_or_address < 1 or index_or_address > l:
        raise ValueError('you have %d wallets, index must be between 1 and %d' % (l, l))
    return AppendWalletAction.WALLETS[index_or_address - 1]


class TransferParamsAction(configargparse.argparse.Action):
    def __init__(
        self,
        option_strings,
        dest,
        nargs=2,
        const=None,
        default=None,
        type=str,
        choices=None,
        required=False,
        help=None,
        metavar=('snail_id', 'account_or_address'),
    ):
        if type != str:
            raise ValueError('type must always be str (default)')
        if nargs != 2:
            raise ValueError('nargs must always be 2 (default)')
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)

    def __call__(self, parser, namespace, values, option_string):
        snail_id, aoa = values
        setattr(namespace, self.dest, (int(snail_id), wallet_ext_or_int(aoa)))
