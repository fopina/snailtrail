#!/usr/bin/env python

import argparse
import logging
import os
import time
from datetime import datetime, timezone
import requests

from colorama import Fore
from requests.exceptions import HTTPError

from snail import client, proxy

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logging.addLevelName(logging.WARNING, f'{Fore.YELLOW}{logging.getLevelName(logging.WARNING)}{Fore.RESET}')
logging.addLevelName(logging.ERROR, f'{Fore.RED}{logging.getLevelName(logging.ERROR)}{Fore.RESET}')
logging.addLevelName(logging.DEBUG, f'{Fore.LIGHTRED_EX}{logging.getLevelName(logging.DEBUG)}{Fore.RESET}')
logger = logging.getLogger(__name__)


class CLI:
    owner = None

    def __init__(self, proxy_url, args):
        self.args = args
        self._read_conf()
        self.client = client.Client(
            proxy=proxy_url, wallet=self.owner, private_key=self.wallet_key, web3_provider=self.web3provider
        )
        self._notified_races = set()

    def _notify(self, message, format='Markdown'):
        if self.args.notify:
            print(
                requests.post(
                    f'https://tgbots.skmobi.com/pushit/{self.args.notify}',
                    json={'msg': message, 'format': format},
                )
            )

    def find_female_snails(self):
        all_snails = []
        for snail in self.client.iterate_all_snails_marketplace():
            if snail['market']['price'] > 2:
                break
            all_snails.append(snail)

        for x in self.client.iterate_all_snails(filters={'id': [x['id'] for x in all_snails][:22]}):
            print(x)
        return
        cycle_end = []
        for snail in all_snails:
            if snail['gender']['id'] == 1:
                if snail['breeding']['breed_status'] and snail['breeding']['breed_status']['cycle_remaining'] > 0:
                    print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'])
                else:
                    cycle_end.append(snail)

        cycle_end.sort(key=lambda snail: snail['breeding']['breed_status']['cycle_end'])

        for snail in cycle_end:
            print(
                f'https://www.snailtrail.art/snails/{snail["id"]}/snail',
                snail['market']['price'],
                snail['breeding']['breed_status']['cycle_end'],
            )

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

        closest = None
        for x in self.client.iterate_my_snails_for_missions(self.owner):
            if self.args.exclude and x['id'] in self.args.exclude:
                continue
            to_queue = datetime.strptime(x['queueable_at'], '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
            if to_queue < now:
                queueable.append(x)
                logger.info(
                    f"{Fore.GREEN}{x['id']} : {x['name']} ({x['stats']['experience']['level']} - {x['stats']['experience']['remaining']}) : {x['adaptations']}{Fore.RESET}"
                )
            else:
                tleft = to_queue - now
                if closest is None or to_queue < closest:
                    closest = to_queue
                logger.info(
                    f"{Fore.YELLOW}{x['id']} : {x['name']} ({x['stats']['experience']['level']} - {x['stats']['experience']['remaining']}) : {tleft}{Fore.RESET}"
                )

        if not queueable:
            return closest

        boosted = set(self.args.boost or [])
        if self.args.fair:
            # add snails with negative tickets to "boosted" to re-use logic
            for s in queueable:
                if s['stats']['mission_tickets'] < 0:
                    boosted.add(s['id'])

        for race in self.client.iterate_mission_races(filters={'owner': self.owner}):
            if race['participation']:
                # already joined
                continue
            athletes = len(race['athletes'])
            if athletes == 10:
                # race full
                continue
            for snail in queueable:
                # FIXME: update for multiple adaptations
                if athletes == 9:
                    # don't queue non-boosted!
                    if snail['id'] in boosted and (
                        (snail['adaptations'][0] in race['conditions']) or self.args.no_adapt
                    ):
                        break
                else:
                    # don't queue boosted here, so they wait for a last spot
                    if snail['id'] not in boosted and (snail['adaptations'][0] in race['conditions']):
                        break
            else:
                # no snail for this track
                continue
            logger.info(
                f'{Fore.CYAN}Joining {race["id"]} ({race["conditions"]}) with {snail["name"]} ({snail["adaptations"]}){Fore.RESET}'
            )
            r = self.client.join_mission_races(snail['id'], race['id'], self.owner)
            if r.get('status') == 0:
                logger.info(f'{Fore.CYAN}{r["message"]}{Fore.RESET}')
                self._notify(
                    f"`{snail['name']}` ({snail['stats']['experience']['level']} - {snail['stats']['experience']['remaining']}) joined mission"
                )
            elif r.get('status') == 1 and snail['id'] in boosted:
                logger.warning('requires transaction')
                print(
                    self.client.web3.join_daily_mission(
                        (
                            r['payload']['race_id'],
                            r['payload']['token_id'],
                            r['payload']['address'],
                        ),
                        r['payload']['size'],
                        [(x['race_id'], x['owners']) for x in r['payload']['completed_races']],
                        r['payload']['timeout'],
                        r['payload']['salt'],
                        r['signature'],
                    )
                )
                self._notify(
                    f"`{snail['name']}` ({snail['stats']['experience']['level']} - {snail['stats']['experience']['remaining']}) joined mission LAST SPOT"
                )
            else:
                logger.error(r)
                self._notify(f'`{snail["name"]}` FAILED to join mission')
            # remove snail from queueable (as it is no longer available)
            queueable.remove(snail)

        if queueable:
            logger.info(f'{len(queueable)} without matching race')
            return
        return closest

    def _read_conf(self):
        try:
            with open(self.args.owner_file) as f:
                self.owner = f.read().strip()
        except FileNotFoundError:
            """ignore, optional config"""
        try:
            with open(self.args.web3_file) as f:
                self.web3provider = f.read().strip()
        except FileNotFoundError:
            """ignore, optional config"""
        try:
            with open(self.args.web3_wallet_key) as f:
                self.wallet_key = f.read().strip()
        except FileNotFoundError:
            """ignore, optional config"""

    def rename_snail(self):
        r = self.client.gql.name_change(self.args.name)
        if not r.get('status'):
            raise Exception(r)
        print(self.client.web3.set_snail_name(self.args.snail, self.args.name))

    def cmd_balance(self):
        print(f'Unclaimed SLIME: {self.client.web3.claimable_rewards()}')
        print(f'SLIME: {self.client.web3.balance_of_slime()}')
        print(f'SNAILS: {self.client.web3.balance_of_snails()}')
        print(f'AVAX: {self.client.web3.get_balance()}')

    def cmd_bot(self):
        if not (self.args.missions or self.args.races):
            logger.error('choose something...')
            return
        next_mission = None
        while True:
            try:
                if self.args.missions:
                    now = datetime.now(tz=timezone.utc)
                    if next_mission is None or next_mission < now:
                        next_mission = self.join_missions()
                        logger.info('next mission in at %s', next_mission)
                    if next_mission is not None:
                        w = (next_mission - now).total_seconds()

                if self.args.races:
                    # FIXME: refactor this "bot" mode...
                    # FIXME: loop all leagues, but save requests for now :)
                    _, races = self.find_races(client.LEAGUE_GOLD)
                    for race in races:
                        if race['id'] in self._notified_races:
                            # notify only once...
                            continue
                        if race['candidates'] and race['candidates'][0][0] > 1:
                            cands = [cand for cand in race['candidates'] if cand[0] > 1]
                            msg = f"Race {race['track']} ({race['id']}) found for {','.join(cand[1]['name'] for cand in cands)}"
                            logger.info(msg)
                            self._notify(msg)
                            self._notified_races.add(race['id'])
                    # override mission waiting
                    w = None

                if w is None or w <= 0:
                    w = self.args.wait
                logger.debug('waiting %d seconds', w)
                time.sleep(w)
            except HTTPError as e:
                if e.response.status_code == 502:
                    logger.error('site 502... waiting')
                else:
                    logger.exception('crash, waiting 2min')
                time.sleep(120)
            except Exception:
                logger.exception('crash, waiting 2min')
                time.sleep(120)

    def cmd_missions(self):
        self.list_missions()

    def cmd_snails(self):
        if self.args.females:
            self.find_female_snails()
        elif self.args.mine:
            self.list_owned_snails()

    def cmd_rename(self):
        self.rename_snail()

    def find_races(self, league):
        snails = list(self.client.iterate_my_snails_for_ranked(self.owner, league))
        if not snails:
            return [], []
        # sort with more adaptations first - for matching with races
        snails.sort(key=lambda x: len(x['adaptations']), reverse=True)
        races = []
        for x in self.client.iterate_onboarding_races(filters={'owner': self.owner, 'league': league}):
            candidates = []
            conditions = set(x['conditions'])
            for s in snails:
                score = len(conditions.intersection(s['adaptations']))
                if score:
                    candidates.append((score, s))
            candidates.sort(key=lambda x: x[0], reverse=True)
            x['candidates'] = candidates
            races.append(x)
        return snails, races

    def cmd_races(self):
        for league in (client.LEAGUE_GOLD, client.LEAGUE_PLATINUM):
            snails, races = self.find_races(league)
            logger.info(f"Snails for {league}: {[s['name'] for s in snails]}")
            if not snails:
                continue
            for x in races:
                if x['participation']:
                    color = Fore.LIGHTBLACK_EX
                else:
                    color = Fore.GREEN
                if self.args.verbose:
                    for k in ('__typename', 'starts_at', 'league'):
                        del x[k]
                    x_str = str(x)
                else:
                    x_str = f"{x['track']} (#{x['id']}): {x['distance']}m for {x['race_type']} entry"

                candidates = x['candidates']
                if candidates:
                    c = f' - candidates: {[(s[1]["name"]+"*"*s[0]) for s in candidates]}'
                else:
                    c = ''
                print(f'{color}{x_str}{Fore.RESET}{c}')

    def run(self):
        if self.args.cmd:
            getattr(self, f'cmd_{self.args.cmd}')()


def build_parser():
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument(
        '--owner-file', type=str, default='owner.conf', help='owner wallet (used for some filters/queries)'
    )
    parser.add_argument('--web3-file', type=str, default='web3provider.conf', help='file with web3 http endpoint')
    parser.add_argument('--web3-wallet-key', type=str, default='pkey.conf', help='file with wallet private key')
    parser.add_argument('--proxy', type=str, help='Use this mitmproxy instead of starting one')
    parser.add_argument('--notify', type=str, metavar='token', help='Enable notifications')
    parser.add_argument('--debug', action='store_true', help='Debug verbosity')

    subparsers = parser.add_subparsers(title='commands', dest='cmd')

    pm = subparsers.add_parser('missions')

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
    pm.add_argument('--no-adapt', action='store_true', help='If auto, ignore adaptations for boosted snails')
    pm.add_argument('-w', '--wait', type=int, default=30, help='Default wait time between checks')

    pm = subparsers.add_parser('snails')
    pm.add_argument('-m', '--mine', action='store_true', help='show owned')
    pm.add_argument('-f', '--females', action='store_true', help='breeders in marketplace')

    pm = subparsers.add_parser('rename')
    pm.add_argument('snail', type=int, help='snail')
    pm.add_argument('name', type=str, help='new name')

    subparsers.add_parser('balance')
    pm = subparsers.add_parser('races')
    pm.add_argument('-v', '--verbose', action='store_true', help='Verbosity')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.debug:
        logger.setLevel(logging.DEBUG)
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
