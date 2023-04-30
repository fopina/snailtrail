#!/usr/bin/env python

import atexit
import logging
import os
from pathlib import Path

import configargparse
from colorama import Fore
from snail import proxy

from . import cli, multicli, tempconfigparser, tgbot

configargparse.ArgParser = tempconfigparser.ArgumentParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


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
        return super().__call__(parser, namespace, cli.Wallet(*map(FileOrString, values)), option_string)


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
        setattr(namespace, self.dest, cli.RaceJoin(*values))


class DefaultOption(str):
    pass


class StoreBotConfig(configargparse.argparse._StoreAction):
    def __call__(self, parser, namespace, values, option_string=None):
        bot = tgbot.Notifier(FileOrString(values[0]), FileOrInt(values[1]), None)
        bot._settings_list = [
            x
            for x in parser._subparsers._actions[-1].choices['bot']._actions
            if isinstance(x, configargparse.argparse._StoreTrueAction)
        ]
        super().__call__(parser, namespace, bot, option_string)


def build_parser():
    parser = configargparse.ArgParser(
        prog=__name__,
        auto_env_var_prefix='snailbot_',
        default_config_files=['./main.conf', '~/.snailbot.conf'],
        args_for_setting_config_path=['-c', '--config'],
        args_for_writing_out_config_file=['--output-config'],
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--wallet',
        nargs=2,
        metavar=('ADDRESS', 'PRIVATE_KEY'),
        action=AppendWalletAction,
        help='owner wallet and its private key (values or path to files with value)',
    )
    parser.add_argument(
        '--web3-rpc',
        type=FileOrString,
        default='https://api.avax.network/ext/bc/C/rpc',
        help='web3 http endpoint (value or path to file with value)',
    )
    parser.add_argument('--proxy', help='Use this proxy for graphql (recommended: mitmproxy, burp)')
    parser.add_argument(
        '--graphql-endpoint',
        help='Snailtrail graphql endpoint',
        default=DefaultOption('https://api.snailtrail.art/graphql/'),
    )
    parser.add_argument(
        '--gotls-bin',
        default=Path(__name__).resolve().parent / 'gotlsproxy' / 'dist' / 'gotlsproxy',
        help='Path to gotlsproxy binary to use',
    )
    parser.add_argument('--debug', action='store_true', help='Debug verbosity')
    parser.add_argument(
        '--notify',
        nargs=2,
        action=StoreBotConfig,
        metavar=('TOKEN', 'CHAT_ID'),
        default=tgbot.Notifier('', ''),
        help='Telegram bot token and target chat id to use for notifications (value or path to file with value)',
    )
    parser.add_argument(
        '--tg-bot',
        action='store_true',
        help='Poll Telegram Bot API for incoming messages/commands',
    )
    parser.add_argument(
        '--tg-bot-owner',
        type=int,
        metavar='CHAT_ID',
        help='Telegram bot will only reply to this chat id (defaults to chat_id in --notify)',
    )
    parser.add_argument(
        '--rate-limit',
        type=float,
        metavar='SECONDS',
        help='Limit GraphQL to one per SECONDS, to avoid getting blocked',
    )
    parser.add_argument(
        '--retry',
        type=int,
        metavar='TRIES',
        default=3,
        help='Retry GraphQL queries that result in 429, 502 and 504 (exponential backoff) - 0 to disable',
    )
    parser.add_argument(
        '-a',
        '--account',
        type=int,
        help='Use single account (if multiple accounts in config) - 0-index of the wallet array (in config)',
    )
    parser.add_argument('--no-colors', action='store_true', help='Disable colors in output')

    subparsers = parser.add_subparsers(title='commands', dest='cmd')

    pm = subparsers.add_parser('missions')
    pm.add_argument('-j', '--join', action=StoreRaceJoin, help='Join mission RACE_ID with SNAIL_ID')
    pm.add_argument('--last-spot', action='store_true', help='Allow last spot (when --join)')
    pm.add_argument('-l', '--limit', type=int, help='Limit history to X missions')
    pm.add_argument('--history', type=int, metavar='SNAIL_ID', help='Get mission history for SNAIL_ID (use 0 for ALL)')
    pm.add_argument('--agg', type=int, help='Aggregate history to X entries')

    pm = subparsers.add_parser('bot')
    pm.add_argument('-m', '--missions', action='store_true', help='Auto join daily missions (non-last/free)')
    pm.add_argument(
        '--mission-chat-id', type=int, help='Notification chat id to be used only for mission join notifications'
    )
    pm.add_argument('-x', '--exclude', type=int, action='append', help='If auto, ignore these snail ids')
    pm.add_argument(
        '-b',
        '--boost',
        type=int,
        action='append',
        help='If auto, these snail ids should always take last spots for missions (boost)',
    )
    pm.add_argument(
        '--minimum-tickets',
        type=int,
        default=0,
        help='Any snail with less tickets than this will only join on last spots',
    )
    pm.add_argument(
        '--settings', type=Path, help='File to save bot settings, most useful when changing settings via telegram'
    )
    pm.add_argument(
        '-f',
        '--fair',
        action='store_true',
        help='Take last spots when negative mission tickets',
    )
    pm.add_argument(
        '--cheap',
        action='store_true',
        help='Cheap mode - only take --fair/--boost last spots if they are low-fee races. Other cheap stuff to be added',
    )
    pm.add_argument('--races', action='store_true', help='Monitor onboarding races for snails lv5+')
    pm.add_argument(
        '--races-join',
        action='store_true',
        help='Auto-join every matched race - use race-matches and race-price to restrict them!',
    )
    pm.add_argument(
        '--race-stats',
        action='store_true',
        help='Include similar race stats for the snail when notifying about a new race and for race over notifications (will generate extra queries)',
    )
    pm.add_argument('--race-matches', type=int, default=1, help='Minimum adaptation matches to notify')
    pm.add_argument('--race-price', type=int, help='Maximum price for race')
    pm.add_argument(
        '-o',
        '--races-over',
        action='store_true',
        help='Monitor finished competitive races with participation and notify on position',
    )
    pm.add_argument(
        '--missions-over',
        action='store_true',
        help='Monitor finished missions with participation and log position/earns (no notification sent)',
    )
    pm.add_argument(
        '--first-run-over',
        action='store_true',
        help='Also trigger log/notify for first run (mostly for testing)',
    )
    pm.add_argument(
        '--mission-matches',
        type=int,
        default=1,
        help='Minimum adaptation matches to join mission - 1 might be worthy, higher might be crazy',
    )
    pm.add_argument('--market', action='store_true', help='Monitor marketplace stats')
    pm.add_argument('-c', '--coefficent', action='store_true', help='Monitor incubation coefficent drops')
    pm.add_argument('--no-adapt', action='store_true', help='If auto, ignore adaptations for boosted snails')
    pm.add_argument('-w', '--wait', type=int, default=30, help='Default wait time between checks')
    pm.add_argument(
        '--paused', action='store_true', help='Start the bot paused (only useful for testing or with --tg-bot)'
    )

    pm = subparsers.add_parser('snails')
    pm.add_argument('-s', '--sort', choices=['breed', 'lvl', 'stats', 'pur'], help='Sort snails by')

    pm = subparsers.add_parser('market')
    pm.add_argument('-f', '--females', action='store_true', help='breeders in marketplace')
    pm.add_argument('-g', '--genes', action='store_true', help='search genes marketplace')
    pm.add_argument('-p', '--price', type=float, default=1, help='price limit for search')
    pm.add_argument('--stats', action='store_true', help='marketplace stats')

    pm = subparsers.add_parser('incubate')
    pm.add_argument(
        '-f',
        '--fee',
        metavar='SNAIL_ID',
        type=int,
        nargs='*',
        help='if not SNAIL_ID is specified, all owned snails will be crossed. If one is, that will be compared against owned snails. If two are specified, only those 2 are used.',
    )
    pm.add_argument(
        '-s',
        '--sim',
        metavar='SNAIL_ID',
        type=int,
        nargs='*',
        help='if not SNAIL_ID is specified, all owned snails will be crossed. If one is, that will be compared against owned snails. If two are specified, only those 2 are used.',
    )
    pm.add_argument(
        '-g', '--genes', type=int, help='search genes marketplace (value is the number of gene search results to fetch)'
    )
    pm.add_argument('-G', '--gene-family', type=int, help='filter gene market by this family (5 is Atlantis)')
    pm.add_argument('-b', '--breeders', action='store_true', help='use only snails that are able to breed NOW')
    pm.add_argument(
        '--plan', action='store_true', help='Lazy (suboptimal) planning for cheapest breeds (only for `-bf`)'
    )

    pm = subparsers.add_parser('rename')
    pm.add_argument('snail', type=int, help='snail')
    pm.add_argument('name', help='new name')

    pm = subparsers.add_parser('balance')
    pm.add_argument('-c', '--claim', action='store_true', help='Claim rewards')
    pm.add_argument('-s', '--send', type=int, metavar='account', help='Transfer slime to this account')

    pm = subparsers.add_parser('races')
    pm.add_argument('-v', '--verbose', action='store_true', help='Verbosity')
    pm.add_argument('-f', '--finished', action='store_true', help='Get YOUR finished races')
    pm.add_argument('-l', '--limit', type=int, help='Limit to X races')
    pm.add_argument('--history', type=int, metavar='SNAIL_ID', help='Get race history for SNAIL_ID (use 0 for ALL)')
    pm.add_argument('-p', '--price', type=int, help='Filter for less or equal to PRICE')
    pm.add_argument('-j', '--join', action=StoreRaceJoin, help='Join competitive race RACE_ID with SNAIL_ID')
    pm.add_argument('--pending', action='store_true', help='Get YOUR pending races (joined but not yet started)')

    pm = subparsers.add_parser('tournament')
    pm.add_argument('-s', '--stats', action='store_true', help='Print only tournament stats')
    return parser


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)

    if args.no_colors:
        from colorama import init

        init(strip=True)

        # FIXME: colorama strip fails in logging...!
        # monkeypatch Fore
        class FakeFore:
            def __getattribute__(self, __name: str):
                return ''

        Fore.__class__ = FakeFore
    else:
        logging.addLevelName(logging.WARNING, f'{Fore.YELLOW}{logging.getLevelName(logging.WARNING)}{Fore.RESET}')
        logging.addLevelName(logging.ERROR, f'{Fore.RED}{logging.getLevelName(logging.ERROR)}{Fore.RESET}')
        logging.addLevelName(logging.DEBUG, f'{Fore.LIGHTRED_EX}{logging.getLevelName(logging.DEBUG)}{Fore.RESET}')

    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug('debug enabled')

    # if no proxy is set and using official graphql, start gotlsproxy
    if not args.proxy and isinstance(args.graphql_endpoint, DefaultOption):
        logger.info('starting proxy')
        use_upstream_proxy = os.getenv('http_proxy') or os.getenv('https_proxy')
        if use_upstream_proxy:
            use_upstream_proxy = use_upstream_proxy.split('://')[-1]
            logger.warning('(upstream proxy %s)', use_upstream_proxy)
        p = proxy.Proxy(args.gotls_bin, upstream_proxy=use_upstream_proxy)
        p.start()
        atexit.register(p.stop)
        logger.info('proxy ready on %s', p.url())
        args.graphql_endpoint = p.url()

    if args.tg_bot_owner is not None:
        args.notifier.owner_chat_id = args.tg_bot_owner

    if not args.wallet:
        args.wallet = [cli.Wallet(FileOrString('owner.conf'), FileOrString('pkey.conf'))]
    wallets = args.wallet
    if args.account is not None:
        if args.account < 1 or args.account > len(args.wallet):
            logger.error(
                'you have %d wallets, --account must be between 1 and %d',
                len(args.wallet),
                len(args.wallet),
            )
            return 1
        wallets = [args.wallet[args.account - 1]]

    cli = multicli.MultiCLI(wallets=wallets, proxy_url=args.proxy, args=args)
    cli.run()


if __name__ == '__main__':
    exit(main() or 0)
