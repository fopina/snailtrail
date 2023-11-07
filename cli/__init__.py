#!/usr/bin/env python

import atexit
import logging
import os
from pathlib import Path

import configargparse
from colorama import Fore

from snail import proxy

from . import commands, multicli, tempconfigparser, tgbot, types

configargparse.ArgParser = tempconfigparser.ArgumentParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class StoreBotConfig(configargparse.argparse._StoreAction):
    def __call__(self, parser, namespace, values, option_string=None):
        bot = tgbot.Notifier(commands.FileOrString(values[0]), commands.FileOrInt(values[1]), None)
        bot._settings_list = [
            x
            for x in parser._subparsers._actions[-1].choices['bot']._actions
            if isinstance(x, configargparse.argparse._StoreTrueAction)
        ]
        bot._read_only_settings = [
            x
            for x in parser._subparsers._actions[-1].choices['bot']._actions
            if not isinstance(x, configargparse.argparse._StoreTrueAction)
        ]
        super().__call__(parser, namespace, bot, option_string)


def build_parser():
    parser = configargparse.ArgParser(
        prog=__name__,
        auto_env_var_prefix='snailbot_',
        default_config_files=['~/.snailbot.conf'],
        args_for_writing_out_config_file=['--output-config'],
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-c',
        '--config',
        # FIXME: I do not want main.conf to be part of the merged ones but I also do not want it to cause failure if doesn't exist
        # dirty hack for now...
        default='main.conf' if Path('main.conf').exists() else '',
        is_config_file_arg=True,
    )
    parser.add_argument(
        '--wallet',
        metavar='ADDRESS_OR_PRIVATE_KEY',
        action=commands.AppendWalletAction,
        help='wallet address (or private key) - if only address, most features not available (values or path to files with value)',
    )
    parser.add_argument(
        '--friend',
        metavar='ADDRESS_OR_PRIVATE_KEY',
        action=commands.AppendWalletAction,
        help='FRIEND wallet address (or private key) - if only address, most features not available (values or path to files with value)',
    )
    parser.add_argument(
        '--friends',
        action='store_true',
        help='Also process friends wallets',
    )
    parser.add_argument(
        '--web3-rpc',
        type=commands.FileOrString,
        default='https://api.avax.network/ext/bc/C/rpc',
        help='web3 http endpoint (value or path to file with value)',
    )
    parser.add_argument(
        '--web3-base-fee', type=float, default=25, help='Base fee to be used for max fee calculation, in nAVAX'
    )
    parser.add_argument(
        '--web3-priority-fee',
        type=float,
        default=1.25,
        help='Priority fee to be used for time-sensitive transactions (such as joining last spots), in nAVAX',
    )
    parser.add_argument('--proxy', help='Use this proxy for graphql (recommended: mitmproxy, burp)')
    parser.add_argument(
        '--graphql-endpoint',
        help='Snailtrail graphql endpoint',
        default=commands.DefaultOption('https://api.snailtrail.art/graphql/'),
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
        action='append',
        help='Use subset of accounts (if multiple accounts in config) - 0-index of the wallet array (in config)',
    )
    parser.add_argument('--debug-http', action='store_true', help='Debug all http requests made')
    parser.add_argument('--no-colors', action='store_true', help='Disable colors in output')

    subparsers = parser.add_subparsers(title='commands', dest='cmd')

    for k, v in commands.command.commands.items():
        pm = subparsers.add_parser(k, help=v.help)
        for a in reversed(v.arguments):
            pm.add_argument(*a[0], **a[1])

    pm = subparsers.add_parser('utils', help='Random set of utilities')
    utils_parsers = pm.add_subparsers(title='util command', dest='util_cmd')
    for k, v in commands.util_command.commands.items():
        pm = utils_parsers.add_parser(k, help=v.help)
        for a in reversed(v.arguments):
            pm.add_argument(*a[0], **a[1])

    return parser


def main(argv=None):
    p = build_parser()
    args = p.parse_args(argv)
    if not args.cmd:
        p.error('choose a command')
    if args.cmd == 'utils' and not args.util_cmd:
        p.error('choose an "utils" sub-command')

    if args.debug_http:
        import http.client as http_client

        http_client.HTTPConnection.debuglevel = 1

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
    if not args.proxy and isinstance(args.graphql_endpoint, commands.DefaultOption):
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
        args.notify.owner_chat_id = args.tg_bot_owner

    if not args.wallet:
        args.wallet = [types.Wallet.from_private_key(commands.FileOrString('pkey.conf'))]
    wallets = args.wallet
    if args.friends:
        wallets.extend(args.friend)
    if args.account is not None:
        wallets = []
        for account in args.account:
            if account < 1 or account > len(args.wallet):
                logger.error(
                    'you have %d wallets, --account must be between 1 and %d',
                    len(args.wallet),
                    len(args.wallet),
                )
                return 1
            wallets.append(args.wallet[account - 1])

    cli = multicli.MultiCLI(wallets=wallets, proxy_url=args.proxy, args=args)
    cli.run()


if __name__ == '__main__':
    exit(main() or 0)
