from pathlib import Path

import configargparse

from ..types import RaceJoin, Wallet
from ._eth_acc_hdpath_patch_ import cached_path


class FileOrString(str):
    def __new__(cls, content):
        if content:
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
    FRIENDS = []

    def __call__(self, parser, namespace, value, option_string=None):
        if not value:
            w = None
        else:
            val = FileOrString(value)
            if val[:2].lower() == '0x':
                w = Wallet(val, None)
            elif val[0].lower() == '+':
                from web3 import Web3

                w3 = Web3()
                ind = int(val[1:])
                private_key = cached_path(namespace.wallet_seed).derive(ind)
                key = w3.eth.account._parsePrivateKey(private_key)
                w = Wallet.from_private_key(key)
            else:
                w = Wallet.from_private_key(val)

        if option_string == '--wallet':
            self.WALLETS.append(w)
        else:
            self.FRIENDS.append(w)
        return super().__call__(parser, namespace, w, option_string)


class NoRentalStoreTrueAction(configargparse.argparse._StoreTrueAction):
    IS_RENTAL = False

    def __call__(self, parser, namespace, value, option_string=None):
        if self.IS_RENTAL:
            raise configargparse.ArgumentError(self, 'cannot be used with --rental')
        return super().__call__(parser, namespace, value, option_string)


class SetRentalAction(configargparse.argparse._StoreTrueAction):
    def __call__(self, parser, namespace, value, option_string=None):
        NoRentalStoreTrueAction.IS_RENTAL = True
        return super().__call__(parser, namespace, value, option_string)


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
        nargs='+',
        const=None,
        default=None,
        type=str,
        choices=None,
        required=False,
        help=None,
        metavar=('account_or_address', 'snail_id'),
    ):
        if type != str:
            raise ValueError('type must always be str (default)')
        if nargs != '+':
            raise ValueError('nargs must always be 2 (default)')
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)

    def __call__(self, parser, namespace, values, option_string):
        aoa, *snail_id = values
        setattr(namespace, self.dest, (wallet_ext_or_int(aoa), set(map(int, snail_id))))


class StoreBotConfig(configargparse.argparse._StoreAction):
    def __call__(self, parser, namespace, values, option_string=None):
        from .. import tgbot

        bot = tgbot.Notifier(FileOrString(values[0]), FileOrInt(values[1]), None)
        bot.cli_parser = parser
        super().__call__(parser, namespace, bot, option_string)
