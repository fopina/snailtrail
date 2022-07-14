#!/usr/bin/env python

from pathlib import Path
import logging
import os
from colorama import Fore
import configargparse

from snail import proxy
from . import tgbot, cli, tempconfigparser

configargparse.ArgParser = tempconfigparser.ArgumentParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logging.addLevelName(logging.WARNING, f'{Fore.YELLOW}{logging.getLevelName(logging.WARNING)}{Fore.RESET}')
logging.addLevelName(logging.ERROR, f'{Fore.RED}{logging.getLevelName(logging.ERROR)}{Fore.RESET}')
logging.addLevelName(logging.DEBUG, f'{Fore.LIGHTRED_EX}{logging.getLevelName(logging.DEBUG)}{Fore.RESET}')
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


class StoreBotConfig(configargparse.argparse._StoreAction):
    def __call__(self, parser, namespace, values, option_string=None):
        super().__call__(
            parser, namespace, tgbot.Notifier(FileOrString(values[0]), FileOrInt(values[1]), None), option_string
        )


def build_parser():
    parser = configargparse.ArgParser(
        prog=__name__,
        auto_env_var_prefix='snailbot_',
        default_config_files=['./main.conf', '~/.snailbot.conf'],
        args_for_setting_config_path=['-c', '--config'],
        args_for_writing_out_config_file=['--output-config'],
    )
    parser.add_argument(
        '--owner', type=FileOrString, default='owner.conf', help='owner wallet (value or path to file with value)'
    )
    parser.add_argument(
        '--web3-rpc',
        type=FileOrString,
        default='https://api.avax.network/ext/bc/C/rpc',
        help='web3 http endpoint (value or path to file with value)',
    )
    parser.add_argument(
        '--web3-wallet-key',
        type=FileOrString,
        default='pkey.conf',
        help='wallet private key (value or path to file with value)',
    )
    parser.add_argument('--proxy', help='Use this mitmproxy instead of starting one')
    parser.add_argument('--debug', action='store_true', help='Debug verbosity')
    parser.add_argument(
        '--notify',
        nargs=2,
        action=StoreBotConfig,
        metavar=('TOKEN', 'CHAT_ID'),
        help='Telegram bot token and target chat id to use for notifications (value or path to file with value)',
    )
    parser.add_argument(
        '--tg-bot',
        action='store_true',
        help='Poll Telegram Bot API for incoming messages/commands',
    )
    parser.add_argument(
        '--rate-limit',
        type=int,
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

    subparsers = parser.add_subparsers(title='commands', dest='cmd')

    pm = subparsers.add_parser('missions')
    pm.add_argument('-j', '--join', action=StoreRaceJoin, help='Join mission RACE_ID with SNAIL_ID')
    pm.add_argument('--last-spot', action='store_true', help='Allow last spot (when --join)')

    pm = subparsers.add_parser('bot')
    pm.add_argument('-m', '--missions', action='store_true', help='Auto join daily missions (non-last/free)')
    pm.add_argument('-x', '--exclude', type=int, action='append', help='If auto, ignore these snail ids')
    pm.add_argument(
        '-b',
        '--boost',
        type=int,
        action='append',
        help='If auto, these snail ids should always take last spots for missions (boost)',
    )
    pm.add_argument(
        '-f',
        '--fair',
        action='store_true',
        help='Take last spots when negative mission tickets',
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
        help='Include similar race stats for the snail when notifying about a new race (will generate extra queries)',
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
        help='Monitor finished missions with participation and notify on position (when top3)',
    )
    pm.add_argument('--market', action='store_true', help='Monitor marketplace stats')
    pm.add_argument('-c', '--coefficent', action='store_true', help='Monitor incubation coefficent drops')
    pm.add_argument('--no-adapt', action='store_true', help='If auto, ignore adaptations for boosted snails')
    pm.add_argument('-w', '--wait', type=int, default=30, help='Default wait time between checks')

    pm = subparsers.add_parser('snails')
    pm.add_argument('-s', '--sort', choices=['breed', 'lvl'], help='Sort snails by')

    pm = subparsers.add_parser('market')
    pm.add_argument('-f', '--females', action='store_true', help='breeders in marketplace')
    pm.add_argument('-p', '--price', type=float, default=1.5, help='price limit for search')
    pm.add_argument('--stats', action='store_true', help='marketplace stats')

    pm = subparsers.add_parser('incubate')

    pm = subparsers.add_parser('rename')
    pm.add_argument('snail', type=int, help='snail')
    pm.add_argument('name', help='new name')

    subparsers.add_parser('balance')

    pm = subparsers.add_parser('races')
    pm.add_argument('-v', '--verbose', action='store_true', help='Verbosity')
    pm.add_argument('-f', '--finished', action='store_true', help='Get YOUR finished races')
    pm.add_argument('-l', '--limit', type=int, help='Limit to X races')
    pm.add_argument('--history', type=int, metavar='SNAIL_ID', help='Get race history for SNAIL_ID (use 0 for ALL)')
    pm.add_argument('-p', '--price', type=int, help='Filter for less or equal to PRICE')
    pm.add_argument('-j', '--join', action=StoreRaceJoin, help='Join competitive race RACE_ID with SNAIL_ID')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.notify:
        args.notify._settings_list = [
                x
                for x in build_parser()._subparsers._actions[-1].choices['bot']._actions
                if isinstance(x, configargparse.argparse._StoreTrueAction)
            ]
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug('debug enabled')
    if args.proxy:
        proxy_url = args.proxy
    else:
        logger.info('starting proxy')
        use_upstream_proxy = os.getenv('http_proxy') or os.getenv('https_proxy')
        if use_upstream_proxy:
            use_upstream_proxy = use_upstream_proxy.split('://')[-1]
            logger.warning('(upstream proxy %s)', use_upstream_proxy)
        p = proxy.Proxy(upstream_proxy=use_upstream_proxy)
        p.start()
        logger.info('proxy ready on %s', p.url())
        proxy_url = p.url()

    c = cli.CLI(proxy_url, args)
    try:
        c.run()
    except KeyboardInterrupt:
        logger.info('Stopping...')
    finally:
        c.notifier.stop_polling()
        if not args.proxy:
            p.stop()


if __name__ == '__main__':
    main()
