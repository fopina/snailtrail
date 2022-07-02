#!/usr/bin/env python

import configargparse
import logging
import os
import time
from datetime import datetime, timezone

from colorama import Fore

from snail import client, proxy
from . import tgbot

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
        self.notifier = tgbot.Notifier(self.args.notify, self.args.bot_owner, self)
        if self.args.bot_owner:
            self.notifier.start_polling()
        self._notified_races = set()
        self._notify_mission_data = None
        self._next_mission = None

    @staticmethod
    def _now():
        return datetime.now(tz=timezone.utc)

    def _breed_status_str(self, status):
        if status >= 0:
            return f"{Fore.YELLOW}breed in {status:.2f}{Fore.RESET}"
        elif status == -1:
            return f"{Fore.GREEN}BREEDER{Fore.RESET}"
        elif status == -2:
            return f"{Fore.GREEN}NEW BREEDER{Fore.RESET}"
        else:
            return f"{Fore.RED}NO BREED?{Fore.RESET}"

    def find_market_snails(self, only_females=False, price_filter=2):
        all_snails = {}
        # include gender 0 as well - cycle end will be none if reset!
        genders = [0, 1]
        if not only_females:
            genders.append(2)
        for gender in genders:
            for snail in self.client.iterate_all_snails_marketplace(filters={'gender': gender}):
                if snail.market_price > price_filter:
                    break
                all_snails[snail.id] = snail
        logger.debug('Fetching details for %d snails', len(all_snails))
        keys = list(all_snails.keys())
        for i in range(0, len(keys), 20):
            for x in self.client.iterate_all_snails(filters={'id': keys[i : i + 20]}):
                all_snails[x.id].update(x)

        for snail_id, snail in all_snails.items():
            logger.info(
                f"{snail} - {self._breed_status_str(snail.breed_status)} - [https://www.snailtrail.art/snails/{snail_id}/about] for {Fore.LIGHTRED_EX}{snail.market_price}{Fore.RESET}"
            )

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

    def notify_mission(self, message):
        if self._notify_mission_data:
            passed = self._now() - self._notify_mission_data['start']

        # 3.5h = 12600 seconds, create new mission message after that
        if not self._notify_mission_data or passed.total_seconds() > 12600:
            msg = self.notifier.notify(message, silent=True)
            self._notify_mission_data = {'msg': msg, 'text': message, 'start': self._now()}
            return

        # `passed` is always defined here, due to first+second conditions being exclusive
        self._notify_mission_data['text'] += f'\n{message} `[+{str(passed).rsplit(".")[0]}]`'
        self.notifier.notify(self._notify_mission_data['text'], edit=self._notify_mission_data['msg'])

    def mission_queueable_snails(self):
        queueable = []

        closest = None
        for x in self.client.iterate_my_snails_for_missions(self.owner):
            if self.args.exclude and x['id'] in self.args.exclude:
                continue
            to_queue = x.queueable_at
            tleft = to_queue - self._now()
            if tleft.total_seconds() <= 0:
                queueable.append(x)
                logger.info(
                    f"{Fore.GREEN}{x['id']} : {x['name']} ({x['stats']['experience']['level']} - {x['stats']['experience']['remaining']}) : {x['adaptations']}{Fore.RESET}"
                )
            else:
                if closest is None or to_queue < closest:
                    closest = to_queue
                logger.info(
                    f"{Fore.YELLOW}{x['id']} : {x['name']} ({x['stats']['experience']['level']} - {x['stats']['experience']['remaining']}) : {tleft}{Fore.RESET}"
                )
        return queueable, closest

    def join_missions(self):
        queueable, closest = self.mission_queueable_snails()
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
                self.notify_mission(
                    f"🐌 `{snail['name']}` ({snail['stats']['experience']['level']} - {snail['stats']['experience']['remaining']}) joined mission",
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
                self.notify_mission(
                    f"🐌 `{snail['name']}` ({snail['stats']['experience']['level']} - {snail['stats']['experience']['remaining']}) joined mission LAST SPOT",
                )
            else:
                logger.error(r)
                self.notifier.notify(f'⛔ `{snail["name"]}` FAILED to join mission')
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

    def _balance(self):
        return f'''\
Unclaimed SLIME: {self.client.web3.claimable_rewards()}
SLIME: {self.client.web3.balance_of_slime()}
SNAILS: {self.client.web3.balance_of_snails()}
AVAX: {self.client.web3.get_balance()}
        '''

    def cmd_balance(self):
        print(self._balance())

    def cmd_bot(self):
        if not (self.args.missions or self.args.races):
            logger.error('choose something...')
            return
        self._next_mission = None
        while True:
            try:
                if self.args.missions:
                    now = datetime.now(tz=timezone.utc)
                    if self._next_mission is None or self._next_mission < now:
                        self._next_mission = self.join_missions()
                        logger.info('next mission in at %s', self._next_mission)
                    if self._next_mission is not None:
                        w = (self._next_mission - now).total_seconds()

                if self.args.races:
                    self.find_races()
                    # override mission waiting
                    w = None

                if w is None or w <= 0:
                    w = self.args.wait
                logger.debug('waiting %d seconds', w)
                time.sleep(w)
            except client.gqlclient.requests.exceptions.HTTPError as e:
                if e.response.status_code == 502:
                    logger.error('site 502... waiting')
                else:
                    logger.exception('crash, waiting 2min: %s', e)
                # too noisy
                # self.notifier.notify('bot gql error, check logs')
                time.sleep(120)
            except Exception as e:
                logger.exception('crash, waiting 2min: %s', e)
                self.notifier.notify('bot unknown error, check logs')
                time.sleep(120)

    def cmd_missions(self):
        self.list_missions()

    def cmd_snails(self):
        it = self.client.iterate_all_snails(filters={'owner': self.owner})
        if self.args.sort:
            it = list(it)
            if self.args.sort == 'breed':
                it.sort(key=lambda x: x.breed_status)
            elif self.args.sort == 'lvl':
                it.sort(key=lambda x: x.level)
        for snail in it:
            print(snail, self._breed_status_str(snail.breed_status))

    def cmd_market(self):
        self.find_market_snails(only_females=self.args.females, price_filter=self.args.price)

    def cmd_rename(self):
        self.rename_snail()

    def find_races_in_league(self, league):
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

    def find_races(self):
        # FIXME: loop all leagues, but save requests for now :)
        _, races = self.find_races_in_league(client.LEAGUE_GOLD)
        for race in races:
            if race['id'] in self._notified_races:
                # notify only once...
                continue
            if self.args.race_price and int(race['race_type']) > self.args.race_price:
                # too expensive! :D
                continue
            if race['candidates']:
                # report on just 1 match, but use only snails with 2 adaptations (stronger)
                cands = [
                    cand
                    for cand in race['candidates']
                    if cand[0] >= self.args.race_matches and len(cand[1]['adaptations']) > 1
                ]
                if not cands:
                    continue
                msg = f"🏎️  Race {race['track']} ({race['id']}) found for {','.join(cand[1]['name'] + (cand[0] * '⭐') for cand in cands)}: {race['race_type']} 🪙  {race['distance']}m"
                logger.info(msg)
                self.notifier.notify(msg)
                self._notified_races.add(race['id'])

    def _open_races(self):
        for league in (client.LEAGUE_GOLD, client.LEAGUE_PLATINUM):
            snails, races = self.find_races_in_league(league)
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

    def _finished_races(self):
        snails = {
            x.id: x
            for x in self.client.iterate_all_snails(filters={'owner': self.owner})
        }
        if not snails:
            return
        total_cr = 0
        total = 0
        for race in (
            race
            for league in (client.LEAGUE_GOLD, client.LEAGUE_PLATINUM)
            for race in self.client.iterate_finished_races(filters={'owner': self.owner, 'league': league}, own=True)
        ):
            for p, i in enumerate(race['results']):
                if i['token_id'] in snails:
                    break
            else:
                logger.error('no snail found, NOT POSSIBLE')
                continue
            snail = snails[i['token_id']]
            p += 1
            fee = int(race.prize_pool) / 9
            if p == 1:
                c = Fore.GREEN
                cr = fee * 4
            elif p == 2:
                c = Fore.YELLOW
                cr = fee * 1.5
            elif p == 3:
                c = Fore.LIGHTRED_EX
                cr = fee * 0.5
            else:
                c = Fore.RED
                cr = 0 - fee
            total_cr += cr
            print(f"{c}{snail.name} number {p} in {race.track}, for {race.distance}m - {cr}{Fore.RESET}")
            total += 1
            if self.args.limit and total >= self.args.limit:
                break
        print(f'\nTOTAL CR: {total_cr}')

    def _history_races(self, snail_id):
        total_cr = 0
        total = 0
        for race in (
            self.client.iterate_race_history(filters={'token_id': snail_id, 'league': league})
            for league in (client.LEAGUE_GOLD, client.LEAGUE_PLATINUM)
        ):
            for p, i in enumerate(race['results']):
                if i['token_id'] == snail_id:
                    break
            else:
                logger.error('no snail found, NOT POSSIBLE')
                continue
            p += 1
            fee = int(race.prize_pool) / 9
            if p == 1:
                c = Fore.GREEN
                cr = fee * 4
            elif p == 2:
                c = Fore.YELLOW
                cr = fee * 1.5
            elif p == 3:
                c = Fore.LIGHTRED_EX
                cr = fee * 0.5
            else:
                c = Fore.RED
                cr = 0 - fee
            total_cr += cr
            print(f"{c}#{snail_id} number {p} in {race.track}, for {race.distance}m - {cr}{Fore.RESET}")
            total += 1
            if self.args.limit and total >= self.args.limit:
                break
        print(f'\nTOTAL CR: {total_cr}')

    def cmd_races(self):
        if self.args.finished:
            return self._finished_races()
        if self.args.history:
            return self._history_races(self.args.history)
        return self._open_races()

    def cmd_incubate(self):
        # TODO: everything, just showing coefficient for now
        print(self.client.web3.get_current_coefficent())

    def run(self):
        if self.args.cmd:
            getattr(self, f'cmd_{self.args.cmd}')()


def build_parser():
    parser = configargparse.ArgParser(
        prog=__name__,
        auto_env_var_prefix='snailbot_',
        default_config_files=['./main.conf', '~/.snailbot.conf'],
        args_for_setting_config_path=['-c', '--config'],
    )
    parser.add_argument(
        '--owner-file', type=str, default='owner.conf', help='owner wallet (used for some filters/queries)'
    )
    parser.add_argument('--web3-file', type=str, default='web3provider.conf', help='file with web3 http endpoint')
    parser.add_argument('--web3-wallet-key', type=str, default='pkey.conf', help='file with wallet private key')
    parser.add_argument('--proxy', type=str, help='Use this mitmproxy instead of starting one')
    parser.add_argument('--notify', type=str, metavar='token', help='Enable notifications')
    parser.add_argument(
        '--bot-owner',
        type=int,
        metavar='CHAT_ID',
        help='Telegram Chat IDs to send notifications (and allowed to control the bot)',
    )
    parser.add_argument('--debug', action='store_true', help='Debug verbosity')

    subparsers = parser.add_subparsers(title='commands', dest='cmd')

    pm = subparsers.add_parser('missions')

    pm = subparsers.add_parser('bot', auto_env_var_prefix='snailbot_')
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
    pm.add_argument('--race-matches', type=int, default=1, help='Minimum adaptation matches to notify')
    pm.add_argument('--race-price', type=int, help='Maximum price for race')
    pm.add_argument('--no-adapt', action='store_true', help='If auto, ignore adaptations for boosted snails')
    pm.add_argument('-w', '--wait', type=int, default=30, help='Default wait time between checks')

    pm = subparsers.add_parser('snails')
    pm.add_argument('-s', '--sort', type=str, choices=['breed', 'lvl'], help='Sort snails by')

    pm = subparsers.add_parser('market')
    pm.add_argument('-f', '--females', action='store_true', help='breeders in marketplace')
    pm.add_argument('-p', '--price', type=float, default=1.5, help='price limit for search')

    pm = subparsers.add_parser('incubate')

    pm = subparsers.add_parser('rename')
    pm.add_argument('snail', type=int, help='snail')
    pm.add_argument('name', type=str, help='new name')

    subparsers.add_parser('balance')

    pm = subparsers.add_parser('races')
    pm.add_argument('-v', '--verbose', action='store_true', help='Verbosity')
    pm.add_argument('-f', '--finished', action='store_true', help='Get YOUR finished races')
    pm.add_argument('-l', '--limit', type=int, help='Limit to X races')
    pm.add_argument('--history', type=int, metavar='SNAIL_ID', help='Get race history for SNAIL_ID')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
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

    c = CLI(proxy_url, args)
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
