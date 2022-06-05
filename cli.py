import logging
import os
import argparse
import time
from colorama import Fore
from datetime import datetime, timezone
from requests.exceptions import HTTPError
from snail import proxy, client

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logging.addLevelName(logging.WARNING, f'{Fore.YELLOW}{logging.getLevelName(logging.WARNING)}{Fore.RESET}')
logging.addLevelName(logging.ERROR, f'{Fore.RED}{logging.getLevelName(logging.ERROR)}{Fore.RESET}')
logger = logging.getLogger(__name__)


class CLI:
    client = None
    owner = None

    def __init__(self, proxy_url, args):
        self.args = args
        self._read_conf()
        self.client = client.Client(proxy=proxy_url, private_key=self.wallet_key, web3_provider=self.web3provider)
        if self.args.owner:
            self.owner = self.args.owner

    def find_female_snails(self):
        all_snails = []
        for snail in self.client.iterate_all_snails_marketplace():
            if snail['market']['price'] > 2:
                break
            all_snails.append(snail)

        cycle_end = []
        for snail in all_snails:
            if snail['gender']['id'] == 1:
                if snail['breeding']['breed_status'] and snail['breeding']['breed_status']['cycle_remaining'] > 0:
                    print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'])
                else:
                    cycle_end.append(snail)

        cycle_end.sort(key=lambda snail:snail['breeding']['breed_status']['cycle_end'])

        for snail in cycle_end:
            print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'], snail['breeding']['breed_status']['cycle_end'])
    
    def list_owned_snails(self):
        for snail in self.client.iterate_all_snails(filters={'owner': self.owner}):
            print(snail)

    def list_missions(self):
        for x in self.client.iterate_mission_races(filters={'owner': self.owner}):
            x['athletes'] = len(x['athletes'])
            if x['participation']:
                color = Fore.BLACK
            elif x['athletes'] == 9:
                color = Fore.RED
            else:
                color = Fore.GREEN
            for k in ('__typename', 'distance', 'participation'):
                del x[k]
            print(f'{color}{x}{Fore.RESET}')

    def join_missions(self):
        now = datetime.now(tz=timezone.utc)
        queueable = []

        for x in self.client.iterate_my_snails_for_missions(self.owner):
            to_queue = datetime.strptime(x['queueable_at'], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
            if to_queue < now:
                queueable.append(x)
                logger.info(f"{Fore.GREEN}{x['id']} : {x['name']} : {x['adaptations']}{Fore.RESET}")
            else:
                logger.info(f"{Fore.YELLOW}{x['id']} : {x['name']} : {to_queue - now}{Fore.RESET}")
        
        if not queueable:
            return

        for race in self.client.iterate_mission_races(filters={'owner': self.owner}):
            if race['participation']:
                # already joined
                continue
            if len(race['athletes']) == 9:
                # cannot afford
                continue
            for snail in queueable:
                # FIXME: update for multiple adaptations
                if snail['adaptations'][0] in race['conditions']:
                    break
            else:
                # no snail for this track
                continue
            logger.info(f'{Fore.CYAN}Joining {race["id"]} ({race["conditions"]}) with {snail["name"]} ({snail["adaptations"]}){Fore.RESET}')
            logger.info(self.client.join_mission_races(snail['id'], race['id'], self.owner))
            # remove snail from queueable (as it is no longer available)
            queueable.remove(snail)

    def _read_conf(self):
        with open('owner.conf') as f:
            self.owner = f.read().strip()
        try:
            with open('web3provider.conf') as f:
                self.web3provider = f.read().strip()
        except FileNotFoundError:
            """ignore, optional config"""
        try:
            with open('pkey.conf') as f:
                self.wallet_key = f.read().strip()
        except FileNotFoundError:
            """ignore, optional config"""

    def run(self):
        if self.args.cmd == 'missions':
            if self.args.auto:
                while True:
                    try:
                        self.join_missions()
                        time.sleep(30)
                    except HTTPError as e:
                        if e.response.status_code == 502:
                            logger.error('site 502... waiting')
                        else:
                            logger.exception('crash, waiting 2min')
                        time.sleep(120)
                    except Exception:
                        logger.exception('crash, waiting 2min')
                        time.sleep(120)
            else:
                self.list_missions()
        elif self.args.cmd == 'snails':
            if self.args.females:
                self.find_female_snails()
            elif self.args.mine:
                self.list_owned_snails()


def build_parser():
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument('--owner', type=str, help='owner wallet (used for some filters/queries)')
    parser.add_argument('--proxy', type=str, help='Use this mitmproxy instead of starting one')
    subparsers = parser.add_subparsers(title='commands', dest='cmd')
    pm = subparsers.add_parser('missions')
    pm.add_argument('-a', '--auto', action='store_true', help='Auto join daily missions (non-last/free)')
    ps = subparsers.add_parser('snails')
    ps.add_argument('-m', '--mine', action='store_true', help='show owned')
    ps.add_argument('-f', '--females', action='store_true', help='breeders in marketplace')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
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
    try:
        CLI(proxy_url, args).run()
    finally:
        if not args.proxy:
            p.stop()


if __name__ == '__main__':
    main()
