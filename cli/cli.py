import argparse
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from functools import cached_property
from pathlib import Path
from typing import Optional, Union
from xmlrpc.client import Boolean

import requests
from colorama import Fore
from tqdm import tqdm

from snail import VERSION, client
from snail.gqltypes import Gender, Race, Snail, _parse_datetime
from snail.web3client import DECIMALS

from . import commands, tgbot
from .decorators import cached_property_with_ttl
from .helpers import SetQueue
from .types import RaceJoin, Wallet

logger = logging.getLogger(__name__)


GENDER_COLORS = {
    Gender.MALE: Fore.BLUE,
    Gender.FEMALE: Fore.MAGENTA,
    Gender.UNDEFINED: Fore.YELLOW,
}

UNDEF = object()


class CachedSnailHistory:
    def __init__(self, cli: 'CLI'):
        self.cli = cli
        self._cache = {}

    @staticmethod
    def race_stats(snail_id, race):
        for p, i in enumerate(race.results):
            if i['token_id'] == snail_id:
                break
        else:
            logger.error('snail not found, NOT POSSIBLE')
            return None, None, None
        time_on_first = race.results[0]['time'] * 100 / race.results[p]['time']
        time_on_third = race.results[2]['time'] * 100 / race.results[p]['time']
        p += 1
        return time_on_first, time_on_third, p

    def get(self, snail_id: Union[int, Snail], limit=None):
        """
        Return snail race history plus a stats summary
        """
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id
        # FIXME: make this prettier with a TTLed lru_cache
        key = (snail_id, limit)
        data, last_update = self._cache.get(key, (None, 0))
        _now = time.time()
        # re-fetch only once per 30min
        # TODO: make configurable? update only once and use race notifications to keep it up to date?
        if _now - last_update < 1800:
            return data

        races = []
        stats = defaultdict(lambda: [0, 0, 0, 0])
        total = 0

        for race in self.cli.client.iterate_race_history(filters={'token_id': snail_id, 'category': 3}):
            time_on_first, time_on_third, p = self.race_stats(snail_id, race)
            if time_on_first is None:
                continue
            if p < 4:
                stats[race.distance][p - 1] += 1
            stats[race.distance][3] += 1
            races.append((race, p, time_on_first, time_on_third))
            total += 1
            if limit and total >= limit:
                break

        data = (races, stats)
        self._cache[(snail_id, limit)] = (data, _now)
        return self._cache[key][0]

    def update(self, snail_id: Union[int, Snail], race: Race, limit=None):
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id

        key = (snail_id, limit)
        data, last_update = self._cache.get(key, (None, 0))
        _now = time.time()
        if _now - last_update >= 1800:
            # do not update anything as cache already expired
            return False

        time_on_first, time_on_third, p = self.race_stats(snail_id, race)
        if time_on_first is None:
            return False

        races, stats = data
        if p < 4:
            stats[race.distance][p - 1] += 1
        stats[race.distance][3] += 1
        races.append((race, p, time_on_first, time_on_third))
        return True


class CLI:
    owner = None

    def __init__(
        self,
        wallet: Wallet,
        proxy_url: str,
        args: argparse.Namespace,
        main_one: Optional[Boolean] = None,
        graphql_endpoint: Optional[str] = None,
        profile: dict = None,
    ):
        """
        :param wallet: Wallet of the owner, containing address and (optionally) private key
        :param proxy_url: URL of the proxy (mitmproxy or BURP) to use for GraphQL API calls
        :param args: original argparse Namespace
        :param main_one: flag to represent whether this is the only CLI instance (`None`) or if it is the `main` one (if there are more instances).
                         `main` one is the one used for actions that report the same information on any account (such as incubation coefficient)
        """
        self.args = args
        self.owner = wallet.address
        self.main_one = main_one
        self._profile = profile
        self.client = client.Client(
            proxy=proxy_url,
            wallet=self.owner,
            web3_account=wallet.account,
            web3_provider=args.web3_rpc,
            rate_limiter=args.rate_limit,
            gql_retry=args.retry if args.retry > 0 else None,
            web3_base_fee=args.web3_base_fee,
            web3_priority_fee=args.web3_priority_fee,
        )
        if graphql_endpoint:
            self.client.gql.url = graphql_endpoint
        self.notifier: tgbot.Notifier = args.notify
        self._notified_races = SetQueue(capacity=100)
        self._notified_races_over = SetQueue(capacity=100)
        self._notify_mission_data = None
        self._notify_marketplace = {}
        self._notify_coefficent = None
        self._notify_burn_coefficent = None
        self._notify_auto_claim = None
        self._notify_tournament = UNDEF
        self._next_mission = False, -1
        self._snail_mission_cooldown = {}
        self._snail_history = CachedSnailHistory(self)
        self._snail_levels = {}

    @staticmethod
    def _now():
        return datetime.now(tz=timezone.utc)

    @cached_property
    def guild_leader(self):
        if self._profile and self._profile['guild']:
            data = self.client.gql.guild_details(self._profile['guild']['id'], member=self.owner)
            return data['membership']['rank'] == 'LEADER'
        return False

    @cached_property
    def masked_wallet(self):
        if self.owner[:2] != '0x':
            return self.owner
        if len(self.owner) < 20:
            return self.owner
        return f'{self.owner[:5]}...{self.owner[-3:]}'

    @cached_property
    def name(self):
        if self._profile:
            _name = str(self._profile['_i'])
            u = self._profile['username']
            if u[:5] != self.owner[:5]:
                _name += f' {u}'
            return f'{_name} ({self.masked_wallet})'
        return self.masked_wallet

    @property
    def profile_guild(self):
        if self._profile['guild']:
            return self._profile['guild']['name']

    @property
    def report_as_main(self):
        return self.main_one is not False

    def load_bot_settings(self):
        settings_file = getattr(self.args, 'settings', None)
        if not settings_file:
            return
        try:
            settings = json.loads(settings_file.read_text())
        except FileNotFoundError:
            logger.warning('no initial settings found at %s', settings_file)
            return
        for k, v in settings.items():
            setattr(self.args, k, v)

    def save_bot_settings(self):
        settings_file = getattr(self.args, 'settings', None)
        if not settings_file:
            return
        if not self.notifier._settings_list:
            return
        data = {x.dest: getattr(self.args, x.dest) for x in self.notifier._settings_list}
        # FIXME: make this cleaner/more generic
        data['mission_chat_id'] = self.args.mission_chat_id
        settings_file.write_text(json.dumps(data))

    @cached_property_with_ttl(600)
    def my_snails(self):
        return {
            snail.id: snail for snail in self.client.iterate_all_snails(filters={'owner': self.owner}, more_stats=True)
        }

    def _breed_status_str(self, status):
        if status >= 0:
            if status >= 1:
                _s = f'{status:.2f}d'
            else:
                status *= 24
                if status >= 1:
                    _s = f'{status:.2f}h'
                else:
                    status *= 60
                    _s = f'{status:.2f}m'
            return f"{Fore.YELLOW}breed in {_s}{Fore.RESET}"
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

    def find_market_genes(self, price_filter=2):
        all_snails = {}
        for snail in self.client.iterate_all_genes_marketplace():
            if snail.gene_market_price > price_filter:
                break
            all_snails[snail.id] = snail
            if len(all_snails) == 20:
                break
        logger.debug('Fetching details for %d snails', len(all_snails))
        keys = list(all_snails.keys())
        for i in range(0, len(keys), 20):
            for x in self.client.iterate_all_snails(filters={'id': keys[i : i + 20]}):
                all_snails[x.id].update(x)

        for snail_id, snail in all_snails.items():
            logger.info(
                f"{snail} - {self._breed_status_str(snail.breed_status)} - [https://www.snailtrail.art/snails/{snail_id}/about] for {Fore.LIGHTRED_EX}{snail.gene_market_price}{Fore.RESET}"
            )

    def notify_mission(self, message):
        """helper method to group all the notify mission calls in a single telegram message (re-edit)"""
        if self._notify_mission_data:
            passed = self._now() - self._notify_mission_data['start']

        # 3.5h = 12600 seconds, create new (reset) mission message after that
        # or if existing message is near telegram message size limit (4096)
        if (
            not self._notify_mission_data
            or len(self._notify_mission_data['text'].encode()) > 4000
            or passed.total_seconds() > 12600
        ):
            msg = self.notifier.notify(message, silent=True, chat_id=self.args.mission_chat_id)
            self._notify_mission_data = {'msg': msg, 'text': message, 'start': self._now()}
            return

        # `passed` is always defined here, due to first+second conditions being exclusive
        self._notify_mission_data['text'] += f'\n{message} `[+{str(passed).rsplit(".")[0]}]`'
        self.notifier.notify(self._notify_mission_data['text'], edit=self._notify_mission_data['msg'])

    def mission_queueable_snails(self, race_conditions=None):
        queueable = []

        closest = None
        for x in self.client.iterate_my_snails_for_missions(self.owner, adaptations=race_conditions):
            if self.args.exclude and x.id in self.args.exclude:
                continue
            to_queue = x.queueable_at
            if x.id in self._snail_mission_cooldown and to_queue < self._snail_mission_cooldown[x.id]:
                to_queue = self._snail_mission_cooldown[x.id]
            tleft = to_queue - self._now()
            base_msg = f"{x.name_id} : ({x.level_str} - {x.stats['experience']['remaining']}) : "
            if tleft.total_seconds() <= 0:
                queueable.append(x)
                logger.info(f"{Fore.GREEN}{base_msg}{x.adaptations}{Fore.RESET}")
            else:
                if closest is None or to_queue < closest:
                    closest = to_queue
                logger.debug(f"{Fore.YELLOW}{base_msg}{tleft}{Fore.RESET}")
        return queueable, closest

    def _join_missions_compute_boosted(self, queueable):
        boosted = set(self.args.boost or [])
        if self.args.boost_wallet and self.owner in {w.address for w in self.args.boost_wallet}:
            # all snails are boosted
            boosted.update(snail.id for snail in queueable)
        if self.args.boost_pure:
            boosted.update(snail.id for snail in queueable if snail.purity >= self.args.boost_pure)
        if self.args.boost_to:
            # remove snails >= than this level
            for snail in queueable:
                if snail.level >= self.args.boost_to and snail.id in boosted:
                    self.notifier.notify(
                        f'{snail.name_id} has level {snail.level}, removed from boosted.', only_once=True
                    )
                    boosted.difference_update({snail.id})
        return boosted

    def _join_missions_race_snail(self, race, queueable, boosted):
        if race.participation:
            # already joined
            return None
        athletes = len(race.athletes)
        if athletes == 10:
            # race full
            return None

        candidates = self.find_candidates(race, queueable, include_zero=True)
        for score, _, _, snail in candidates:
            if athletes == 9:
                # don't queue non-boosted!
                if snail.id in boosted and (self.args.mission_matches <= score or self.args.no_adapt):
                    break
            else:
                # don't queue boosted here, so they wait for a last spot
                if snail.id not in boosted and self.args.mission_matches <= score:
                    break
        else:
            # no snail for this track
            return None

        return snail

    def join_missions(self) -> tuple[bool, datetime]:
        missions = list(self.client.iterate_mission_races(filters={'owner': self.owner}))
        missions.sort(key=lambda race: len(race.athletes), reverse=True)
        queueable, closest = self.mission_queueable_snails(race_conditions=[c.id for c in missions[0].conditions])
        if not queueable:
            return True, closest

        # level notifications
        if self.args.level_ups:
            for snail in queueable:
                pl = self._snail_levels.get(snail.id)
                self._snail_levels[snail.id] = snail.level
                if pl is not None and pl != snail.level:
                    self.notifier.notify(f'{snail.name_id} now has level {snail.level}.')

        boosted = self._join_missions_compute_boosted(queueable)
        if self.args.cheap and self.args.boost_not_cheap:
            not_cheap = boosted.copy()
        else:
            not_cheap = set()

        if self.args.fair:
            # add snails with few tickets to "boosted" to re-use logic
            for s in queueable:
                if s.stats['mission_tickets'] < self.args.minimum_tickets:
                    boosted.add(s.id)

        def _slow_snail(snail, seconds=90):
            # add snail to cooldown, use 90 for now - check future logs if they still get locked
            self._snail_mission_cooldown[snail.id] = self._now() + timedelta(seconds=seconds)
            # also remove from queueable (due to "continue")
            queueable.remove(snail)

        for race in missions:
            snail = self._join_missions_race_snail(race, queueable, boosted)
            if snail is None:
                continue
            logger.info(
                f'{Fore.CYAN}Joining {race.id} ({race.conditions}) with {snail.name_id} ({snail.adaptations}){Fore.RESET}'
            )

            tx = None

            # "boosted" includes explicitly boosted and the ones that need tickets
            # not_cheap will only include the explicitly boosted (and if --cheap is used)
            cheap_snail = snail.id in boosted and snail.id not in not_cheap
            try:
                if self.args.cheap and cheap_snail:
                    # join without allowing last spot to capture payload
                    try:
                        # if this succeeds, it was not a last spot - that should not happen...
                        r, _ = self.client.join_mission_races(snail.id, race.id, allow_last_spot=False)
                        logger.error('WTF? SHOULD HAVE FAILED TO JOIN AS LAST SPOT - but ok')
                    except client.RequiresTransactionClientError as e:
                        r = e.args[1]
                        if r['payload']['size'] == 0:
                            tx = self.client.rejoin_mission_races(r)
                        else:
                            _slow_snail(snail)
                            continue
                    except client.gqlclient.RaceAlreadyFullAPIError:
                        logger.error('TOO SLOW TO JOIN LAST - %s on %d', snail.name, race.id)
                        _slow_snail(snail)
                        continue
                else:
                    try:
                        r, tx = self.client.join_mission_races(snail.id, race.id, allow_last_spot=(snail.id in boosted))
                    except client.RequiresTransactionClientError as e:
                        logger.error('TOO SLOW TO JOIN NON-LAST - %s on %d', snail.name, race.id)
                        if not self.args.fair:
                            continue

                        r = e.args[1]
                        # join last spot anyway, even if not "boosted" (negative tickets)
                        if self.args.cheap and not r['payload']['size'] == 0:
                            continue

                        tx = self.client.rejoin_mission_races(r)
                        logger.info('Joined cheap last spot without need - %s on %d', snail.name, race.id)

                msg = (
                    f"🐌 `{snail.name_id}` ({snail.level_str} - {snail.stats['experience']['remaining']}) joined mission"
                )
                if r.get('status') == 0:
                    logger.info(f'{msg}')
                    self.notify_mission(msg)
                elif r.get('status') == 1:
                    fee = tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS
                    if tx['status'] == 1:
                        cheap_or_not = 'cheap' if r['payload']['size'] == 0 else 'normal'
                        logger.info(f'{msg} LAST SPOT ({cheap_or_not} -  tx: {tx.transactionHash.hex()} - fee: {fee}')
                        self.notify_mission(f'{msg} *LAST SPOT*')
                    else:
                        logger.error(f'Last spot transaction reverted - tx: {tx.transactionHash.hex()} - fee: {fee}')
                        _slow_snail(snail)
                        continue
            except client.ClientError as e:
                logger.exception('failed to join mission')
                self.notifier.notify(
                    f'⛔ `{snail.name_id}` FAILED to join mission: {tgbot.escape_markdown(str(e))}',
                    chat_id=self.args.mission_chat_id,
                )
            except client.gqlclient.NeedsToRestAPIError as e:
                # handle re-join timeout errors
                logger.exception('re-join as last error for %s', snail.name_id)
                _slow_snail(snail, seconds=e.seconds)
                continue
            except (client.gqlclient.RaceEntryFailedAPIError, client.gqlclient.RaceInnacurateRegistrantsAPIError):
                logger.exception('failed to join mission')
                continue
            except client.web3client.exceptions.ContractLogicError as e:
                # immediate contract errors, no fee paid
                if 'Race already submitted' in str(e):
                    logger.error('Too late for the race, try next one')
                    _slow_snail(snail)
                    continue
                raise

            # remove snail from queueable (as it is no longer available)
            queueable.remove(snail)

        if queueable:
            logger.info(f'{len(queueable)} without matching race')
            return False, len(queueable)
        return True, closest

    def _balance(self, data=None):
        if data is None:
            data = self.client.web3.multicall_balances([self.owner])[self.owner]
        r = {
            'SLIME': (self.client.web3.claimable_slime(), data[2]),
            'WAVAX': (self.client.web3.claimable_wavax(), data[1]),
            'AVAX': data[3],
            'SNAILS': data[0],
        }
        return r

    @commands.argument('-c', '--claim', action='store_true', help='Claim rewards')
    @commands.argument(
        '-s',
        '--send',
        type=commands.wallet_ext_or_int,
        metavar='account_or_address',
        help='Transfer slime to this account - if <account_or_address> starts with 0x it will be used as external address otherwise it will be used as a local account index',
    )
    @commands.command()
    def cmd_balance(self, data=None):
        """Check wallet balances for all the tokens"""
        if self.args.claim:
            try:
                r = self.client.web3.claim_rewards()
                if r.get('status') == 1:
                    bal = int(r['logs'][1]['data'], 16) / DECIMALS
                    print(f'claimed {bal}')
                else:
                    print('ERROR:', r)
            except client.web3client.exceptions.ContractLogicError as e:
                print(e)
        elif self.args.send is not None:
            return self.cmd_balance_transfer(self.args.send.address)
        else:
            r = self._balance(data=data)
            print(
                f'''\
SLIME: {r['SLIME'][0]} / {r['SLIME'][1]:.3f}
WAVAX: {r['WAVAX'][0]} / {r['SLIME'][1]}
AVAX: {r['AVAX']:.3f} / SNAILS: {r['SNAILS']}'''
            )
            return r

    def cmd_balance_transfer(self, target):
        if target == self.owner:
            return
        bal = self.client.web3.balance_of_slime(raw=True)
        if not bal:
            print('Nothing to send')
            return
        print(f'Sending {bal / DECIMALS} to {target}')
        r = self.client.web3.transfer_slime(target, bal)
        sent = int(r['logs'][0]['data'], 16) / DECIMALS
        print(f'{sent} SLIME sent')

    def _bot_marketplace(self):
        d = self.client.marketplace_stats()
        n = False
        txt = ['📉  Floors decreased']
        # do not notify on first run / less init spam
        if self._notify_marketplace:
            for k, v in d['prices'].items():
                ov = self._notify_marketplace.get(k, [99999])[0]
                if ov > v[0]:
                    n = True
                    txt.append(f"*{k}*: {' / '.join(map(str, v))} (previously `{ov}`)")
                else:
                    txt.append(f"*{k}*: {' / '.join(map(str, v))}")
        self._notify_marketplace = d['prices']
        if n:
            self.notifier.notify('\n'.join(txt))

    def _bot_coefficent(self):
        coef = self.client.web3.get_current_coefficent()
        if self._notify_coefficent is not None and coef < self._notify_coefficent:
            msg = f'🍆 Coefficent drop to *{coef:0.4f}* (from *{self._notify_coefficent}*)'
            self.notifier.notify(msg)
            logger.info(msg)
        self._notify_coefficent = coef

    def _bot_burn_coefficent(self):
        if self._notify_burn_coefficent is not None and self._notify_burn_coefficent[1] > datetime.now():
            # refresh only once every 2min
            return

        r = self._burn_coef()
        if r is None:
            logger.error('No snail available for burn coefficient')
            return
        coef = r['payload']['coef']
        if self._notify_burn_coefficent is not None and coef < self._notify_burn_coefficent[0]:
            msg = f'🔥 Coefficent drop to *{coef:0.4f}* (from *{self._notify_burn_coefficent[0]}*)'
            logger.info(msg)
            self.notifier.notify(msg)

        self._notify_burn_coefficent = (
            coef,
            datetime.now() + timedelta(minutes=120),
        )

    @commands.argument('-m', '--missions', action='store_true', help='Auto join daily missions (non-last/free)')
    @commands.argument(
        '--mission-chat-id', type=int, help='Notification chat id to be used only for mission join notifications'
    )
    @commands.argument('-x', '--exclude', type=int, action='append', help='If auto, ignore these snail ids')
    @commands.argument(
        '-b',
        '--boost',
        type=int,
        action='append',
        help='If auto, these snail ids should always take last spots for missions (boost)',
    )
    @commands.argument(
        '--boost-wallet',
        type=commands.wallet_ext_or_int,
        action='append',
        help='If auto, all snails in these wallets should always take last spots for missions (boost)',
    )
    @commands.argument(
        '--boost-pure',
        type=int,
        help='If auto, all snails with this purity or more should always take last spots for missions (boost)',
    )
    @commands.argument(
        '--boost-to',
        type=int,
        help='When using --boost, only consider snails under this level (excluded)',
    )
    @commands.argument(
        '--boost-not-cheap',
        action='store_true',
        help='For snails in --boost, --cheap is ignored (if enabled)',
    )
    @commands.argument(
        '--minimum-tickets',
        type=int,
        default=0,
        help='Any snail with less tickets than this will only join on last spots',
    )
    @commands.argument(
        '--settings', type=Path, help='File to save bot settings, most useful when changing settings via telegram'
    )
    @commands.argument(
        '-f',
        '--fair',
        action='store_true',
        help='Take last spots when negative mission tickets',
    )
    @commands.argument(
        '--cheap',
        action='store_true',
        help='Cheap mode - only take --fair/--boost last spots if they are low-fee races. Other cheap stuff to be added',
    )
    @commands.argument('--races', action='store_true', help='Monitor onboarding races for snails lv5+')
    @commands.argument(
        '--races-join',
        action='store_true',
        help='Auto-join every matched race - use race-matches and race-price to restrict them!',
    )
    @commands.argument(
        '--race-stats',
        action='store_true',
        help='Include similar race stats for the snail when notifying about a new race and for race over notifications (will generate extra queries)',
    )
    @commands.argument('--race-matches', type=int, default=1, help='Minimum adaptation matches to notify')
    @commands.argument('--race-price', type=int, help='Maximum price for race')
    @commands.argument(
        '-o',
        '--races-over',
        action='store_true',
        help='Monitor finished competitive races with participation and notify on position',
    )
    @commands.argument(
        '--missions-over',
        action='store_true',
        help='Monitor finished missions with participation and log position/earns (no notification sent)',
    )
    @commands.argument(
        '--first-run-over',
        action='store_true',
        help='Also trigger log/notify for first run (mostly for testing)',
    )
    @commands.argument(
        '--mission-matches',
        type=int,
        default=1,
        help='Minimum adaptation matches to join mission - 1 might be worthy, higher might be crazy',
    )
    @commands.argument('--market', action='store_true', help='Monitor marketplace stats')
    @commands.argument('-c', '--coefficent', action='store_true', help='Monitor incubation coefficent drops')
    @commands.argument('--burn', action='store_true', help='Monitor burn coefficent drops')
    @commands.argument('--tournament', action='store_true', help='Monitor tournament changes for own guild')
    @commands.argument('--no-adapt', action='store_true', help='If auto, ignore --mission-matches for boosted snails in missions')
    @commands.argument('-w', '--wait', type=int, default=30, help='Default wait time between checks')
    @commands.argument(
        '--paused', action='store_true', help='Start the bot paused (only useful for testing or with --tg-bot)'
    )
    @commands.argument('--auto-claim', action='store_true', help='Auto claim any guild rewards')
    @commands.argument('--level-ups', action='store_true', help='Notify when a snail levels up (during missions)')
    @commands.command()
    def cmd_bot(self):
        """
        THE THING!
        """
        self.load_bot_settings()
        self.cmd_bot_greet()
        self.args.notify.start_polling()
        try:
            while True:
                w = self.cmd_bot_tick()
                time.sleep(w)
        finally:
            self.args.notify.stop_polling()

    def cmd_bot_greet(self):
        msg = f'👋  Running *v{VERSION}*'
        if not self.args.tg_bot:
            msg += ' `(non-interactive)`'
        self.notifier.notify(msg)

    @commands.argument('-s', '--stats', action='store_true', help='Print only tournament stats')
    @commands.argument('-w', '--week', type=int, help='Week to check (default to current week)')
    @commands.command()
    def cmd_tournament(self, data=None):
        """Tournament info"""
        if data is None:
            data = self.client.gql.tournament(self.owner)
            print(f"Name: {data['name']}")
            print(f"Day: {data['current_day']}")
            print(f"Registered guilds: {data['guild_count']}")
            assert len(data['prize_pool']) == 1
            print(f"Prize: {data['prize_pool'][0]['amount']} {data['prize_pool'][0]['symbol']}")
            for week in data['weeks']:
                print(f"\nWeek {week['week']}")
                print(f"Conditions: {week['conditions']}")
                print(f"Distance: {week['distance']}")
                print(f"Registered guilds: {week['guild_count']}")
        if self.args.stats:
            # only print stats
            return False

        if self.args.week is None:
            week_pos = data['current_week']
        else:
            week_pos = self.args.week

        per_family = {}
        if week_pos == 0:
            print('No tournament this week')
        else:
            for week in data['weeks']:
                if week['week'] == week_pos:
                    break
            else:
                raise Exception(f'week {week_pos} not found')
            print(f'{Fore.GREEN}For week {week_pos}{Fore.RESET}')
            snails = list(self.client.iterate_all_snails(filters={'owner': self.owner}))
            candidates = self.find_candidates(Race(week), snails)
            for candidate in candidates:
                snail = candidate[3]
                if snail.family not in per_family:
                    per_family[snail.family] = []
                per_family[snail.family].append(candidate)

            for family, snails in per_family.items():
                print(f'{Fore.BLUE}{family}{Fore.RESET}')
                for candidate in snails:
                    score = candidate[0]
                    snail = candidate[3]
                    print(f'{score}: {snail.name} {snail.adaptations} {snail.purity_str} {snail.level_str}')
        return True, per_family, data

    def _bot_tournament(self):
        _n: datetime = self._now()
        if self._notify_tournament != UNDEF:
            _next, old_data, old_next = self._notify_tournament
            if _n < _next:
                # next race not yet started
                return
        else:
            _next, old_data, old_next = None, None, None

        tour_data = self.client.gql.tournament(self.owner)
        week = tour_data['current_week']
        if week == 0:
            # no races this week, jump to next week for "next race" date
            week = 1

        _previous = _next = None
        for day_i, day in enumerate(tour_data['weeks'][week - 1]['days']):
            _next = _parse_datetime(day['race_date'])
            if _next > _n:
                break
            _previous = _next
        if _previous == _next:
            # "previous" is last race of the week
            _next = None
            # adjust for the array access later on
            day_i += 1

        stats = self.client.gql.tournament_guild_stats(self.owner)
        data = stats['leaderboard']['my_guild']

        if self._notify_tournament != UNDEF:
            # if "previous" still ongoing (any entry with 0 points)
            for entry in tour_data['weeks'][week - 1]['days'][day_i - 1]['result']['entries']:
                if entry['points'] == 0:
                    # then DO NOTHING (check again in few seconds)
                    return

            if old_next is None and _next is not None:
                msg = f'{tour_data["name"]} week {week} starting!'
                logger.info(msg)
                self.notifier.notify(msg)

            if old_data != data:
                if data is None:
                    msg = 'Current tournament over!'
                elif old_data is None:
                    msg = 'Tournament starting!'
                else:
                    msg = f'`{self.profile_guild}` leaderboard:\n'

                    _k = 'order'
                    old_value = old_data[_k]
                    new_value = data[_k]
                    if old_value != new_value:
                        c = '🏆' if old_value > new_value else '💩'
                        msg += f"*position* {old_value}{c}{new_value}\n"
                    else:
                        msg += f"*position* {new_value}\n"

                    _k = 'points'
                    old_value = old_data[_k]
                    new_value = data[_k]
                    if old_value != new_value:
                        msg += f"*points* {old_value}📈{new_value}\n"
                    else:
                        msg += f"*points* {new_value}\n"
                logger.info(msg)
                self.notifier.notify(msg)

        old_next = _next
        if _next is None:
            # check again in 12h
            logger.error('NEXT tournament check is NONE, is this saturday or a break week?')
            _next = _n + timedelta(hours=12)
        self._notify_tournament = (_next, data, old_next)

    def _bot_autoclaim(self):
        if self._notify_auto_claim is not None and self._notify_auto_claim > datetime.now():
            # refresh only once every 24h
            return

        data = self._cmd_guild_data()
        if not data:
            return

        # FIXME: merge with self._cmd_guild_claim()
        if not data['rewards']:
            return

        msg = []
        for building, amount in data['rewards']:
            if building == 'SINK':
                try:
                    r = self.client.claim_tomato(self._profile['guild']['id'])['message']
                    msg.append(r)
                except client.gqlclient.APIError as e:
                    if 'claim once per hour' not in str(e):
                        raise
            else:
                try:
                    r = self.client.claim_building(self._profile['guild']['id'], building)
                except client.gqlclient.APIError as e:
                    if 'You have joined this guild after the current cycle start, wait for next cycle' in str(e):
                        continue
                    raise
                if 'changes' in r:
                    for c in r['changes']:
                        _a = int(c['_to']) - int(c['_from'])
                        if c["src_type"] == 'BUILDING':
                            msg.append(f'Claimed {_a} {c["name"]}')
                        else:
                            msg.append(f'Claimed {_a} {c["name"]} from {c["src_type"]}')
                else:
                    msg.append(f'Claimed {amount} from {building}')

        if msg:
            msg.insert(0, f'`💰 {self.name}` (`{self.profile_guild}`)')
            logger.info(msg)
            self.notifier.notify('\n'.join(msg))

        self._notify_auto_claim = datetime.now() + timedelta(hours=24)

    def cmd_bot_tick(self):
        try:
            w = self.args.wait
            if not self.args.paused:
                if self.args.missions:
                    now = self._now()
                    if self._next_mission[1] is None or self._next_mission[0] is False or self._next_mission[1] < now:
                        self._next_mission = self.join_missions()
                        if self._next_mission[0] is False:
                            msg = f'{self._next_mission[1]} pending'
                        elif self._next_mission[1] is None:
                            msg = f'no snails'
                        else:
                            msg = str(self._next_mission[1])
                        logger.info('next mission in at %s', msg)
                    if self._next_mission[0] and self._next_mission[1] is not None:
                        # if wait for next mission is lower than wait argument, use it
                        _w = (self._next_mission[1] - now).total_seconds()
                        if 0 < _w < w:
                            w = _w

                if self.args.races:
                    self.find_races()

                if self.args.races_over or self.args.missions_over:
                    self.find_races_over()

                if self.args.market and self.report_as_main:
                    self._bot_marketplace()

                if self.args.coefficent and self.report_as_main:
                    self._bot_coefficent()

                if self.args.burn and self.report_as_main:
                    self._bot_burn_coefficent()

                if self.args.tournament:
                    self._bot_tournament()

                if self.args.auto_claim:
                    self._bot_autoclaim()

            logger.debug('waiting %d seconds', w)
            return w
        except client.gqlclient.requests.exceptions.HTTPError as e:
            if e.response.status_code in (502, 504):
                # log stacktrace to check if specific calls cause this more frequently
                logger.exception('site %d... waiting', e.response.status_code)
                return 20

            if e.response.status_code == 429:
                # FIXME: handle retry-after header after checking it out
                # should not happen as requests retry adapter handles this?
                logger.exception(
                    'site %d... waiting: %s - %s',
                    e.response.status_code,
                    e.response.headers,
                    type(e.response.headers.get('retry-after')),
                )
                return 120

            logger.exception('crash, waiting 2min: %s', e)
            return 120
        except client.gqlclient.APIError as e:
            logger.exception('crash, waiting 2min (logged)')
            return 120
        except Exception as e:
            logger.exception('crash, waiting 2min: %s', e)
            self.notifier.notify(
                f'''bot unknown error, check logs
```
{tgbot.escape_markdown(str(e))}
```
'''
            )
            return 120

    @commands.argument('-j', '--join', action=commands.StoreRaceJoin, help='Join mission RACE_ID with SNAIL_ID')
    @commands.argument('--last-spot', action='store_true', help='Allow last spot (when --join)')
    @commands.argument('-l', '--limit', type=int, help='Limit history to X missions')
    @commands.argument(
        '--history', type=int, metavar='SNAIL_ID', help='Get mission history for SNAIL_ID (use 0 for ALL)'
    )
    @commands.argument('--agg', type=int, help='Aggregate history to X entries')
    @commands.command()
    def cmd_missions(self):
        """
        Mission stuff
        """
        if self.args.join:
            return self.cmd_missions_join()

        if self.args.history is not None:
            return self.cmd_missions_history()

        # list missions
        snails = None
        for x in self.client.iterate_mission_races(filters={'owner': self.owner}):
            athletes = len(x.athletes)
            if x.participation:
                color = Fore.LIGHTBLACK_EX
            elif athletes == 9:
                color = Fore.RED
            else:
                color = Fore.GREEN
            c = f'{color}{x} - {athletes}{Fore.RESET}'
            if snails is None:
                # delayed loading of snails to use first race adaptatios (we don't want to look like a bot!)
                snails = list(
                    self.client.iterate_my_snails_for_missions(self.owner, adaptations=[c.id for c in x.conditions])
                )
            candidates = self.find_candidates(x, snails)
            if candidates:
                c += f': {", ".join((s[3].name_id+"⭐"*s[0]) for s in candidates)}'
            print(c)

    def cmd_missions_join(self):
        """
        join mission
        """
        try:
            r, rcpt = self.client.join_mission_races(
                self.args.join.snail_id, self.args.join.race_id, allow_last_spot=self.args.last_spot
            )
            c = f'{Fore.CYAN}{r["message"]}{Fore.RESET}'
            if rcpt is None:
                logger.info(c)
            else:
                logger.info(f'{c} - LASTSPOT (tx: {rcpt.transactionHash.hex()})')
        except client.RequiresTransactionClientError:
            logger.error('only last spot available, use --last-spot')
        except client.ClientError:
            logger.exception('unexpected joinMission error')

    def cmd_missions_history(self):
        if self.args.history == 0:
            for s in tqdm(self.my_snails.values()):
                self._history_missions(s)
            return True
        else:
            s = list(self.client.iterate_all_snails(filters={'id': self.args.history}, more_stats=True))[0]
            self._history_missions(s)
            return False

    @commands.argument('-s', '--sort', choices=['breed', 'lvl', 'stats', 'pur'], help='Sort snails by')
    @commands.argument(
        '-t',
        '--transfer',
        action=commands.TransferParamsAction,
        # nargs='2+',
        help='Transfer 1 or more <snail_id> to <account_or_address> - if <account_or_address> starts with 0x it will be used as external address otherwise it will be used as a local account index',
    )
    @commands.argument(
        '-m',
        '--metadata',
        type=int,
        metavar='snail',
        help='Fetch snail metadata',
    )
    @commands.command()
    def cmd_snails(self):
        """
        Snail shit
        """
        if self.args.transfer is not None:
            return self.cmd_snails_transfer()

        if self.args.metadata is not None:
            return self._cmd_snails_metadata()

        if self.args.sort == 'stats':
            it = list(self.client.iterate_all_snails(filters={'owner': self.owner}, more_stats=True))
            for snail in it:
                stats = [None, None, None]
                if len(snail.more_stats) > 0:
                    for s in snail.more_stats[0]['data']:
                        if s['name'] == 'All':
                            for s2 in s['data']:
                                if s2['name'] == 'Dashboard':
                                    if s2['data'][0]['name'] == 'Races':
                                        stats[0] = s2['data'][0]['count']
                                    elif s2['data'][0]['name'] == 'Win':
                                        stats[1] = s2['data'][0]['count']
                                    elif s2['data'][0]['name'] == 'Top 3':
                                        stats[2] = s2['data'][0]['count']
                if all([x is not None for x in stats]):
                    snail['tmp_stat_top3'] = stats[2] * 100 / stats[0]
                    snail['tmp_stat_wins'] = stats[1] * 100 / stats[0]
                    snail['tmp_total_races'] = stats[0]
                else:
                    snail['tmp_stat_top3'] = -1
                    snail['tmp_stat_wins'] = -1
                    snail['tmp_total_races'] = -1
        else:
            it = list(self.my_snails.values())

        if self.args.sort:
            if self.args.sort == 'breed':
                it.sort(key=lambda x: x.breed_status)
            elif self.args.sort == 'lvl':
                it.sort(key=lambda x: x.level)
            elif self.args.sort == 'stats':
                it.sort(key=lambda x: x.tmp_stat_top3)
            elif self.args.sort == 'pur':
                it.sort(key=lambda x: x.purity)
        for snail in it:
            if self.args.sort == 'stats':
                print(
                    f'{snail} - {snail.stats["elo"]} - WIN: {snail.tmp_stat_wins:.2f} / TOP3: {snail.tmp_stat_top3:.2f} / TOTAL: {snail.tmp_total_races}'
                )
            else:
                print(snail, self._breed_status_str(snail.breed_status))
        print(f'==> {len(it)} snails')

    def cmd_snails_transfer(self):
        transfer_wallet: Wallet
        transfer_wallet, transfer_snails = self.args.transfer
        if not transfer_snails:
            print('No snails specified')
            return False

        matches = []
        for snail in self.client.iterate_all_snails(filters={'owner': self.owner}):
            if snail.id in transfer_snails:
                matches.append(snail)
                if len(matches) == len(transfer_snails):
                    # nothing else to look for, stop
                    break
        if not matches:
            print('snail not here')
            return

        if len(matches) == 1:
            print(f'Found: {matches[0]}')
        else:
            print('Found:')
            for m in matches:
                print(f' - {m}')

        if transfer_wallet.address == self.owner:
            print('Target is the same as owner')
            return False

        if len(matches) == 1:
            tx = self.client.web3.transfer_snail(self.owner, transfer_wallet.address, matches[0].id)
        else:
            tx = self.client.web3.approve_all_snails_for_bulk()
            if tx:
                fee = tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS
                print(f'Approved bulkTransfer for {fee} AVAX')
            tx = self.client.web3.bulk_transfer_snails(
                transfer_wallet.address,
                [m.id for m in matches],
            )
        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS
        print(f'Transferred for {fee} AVAX')
        for m in matches:
            transfer_snails.remove(m.id)
        return len(transfer_snails) > 0

    def _cmd_snails_metadata(self):
        url = self.client.web3.snail_metadata(self.args.metadata)
        print(f'URL: {url}')
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        print(f'Name: {data["name"]}')
        print(f'Image: {data["image"]}')
        for attr in data['attributes']:
            print(f'{attr["trait_type"]}: {attr["value"]}')
        return False

    @commands.argument('--ids', action='store_true', help='Print item IDs')
    @commands.command()
    def cmd_inventory(self, verbose=True):
        """
        Inventory shit
        """
        type_group = defaultdict(list)
        for item in self.client.iterate_inventory(self.owner):
            type_group[item.type_id].append(item)
        for _, v in type_group.items():
            f = v[0]
            for f2 in v[1:]:
                assert f.name == f2.name
            if verbose:
                if self.args.ids:
                    print(f'{f.name}: {len(v)} - {[f2.id for f2 in v]}')
                else:
                    print(f'{f.name}: {len(v)}')
        return type_group

    @commands.argument('-f', '--females', action='store_true', help='breeders in marketplace')
    @commands.argument('-g', '--genes', action='store_true', help='search genes marketplace')
    @commands.argument('-p', '--price', type=float, default=1, help='price limit for search')
    @commands.argument('--stats', action='store_true', help='marketplace stats')
    @commands.command()
    def cmd_market(self):
        """
        Find bargains and matches in the market
        """
        if self.args.stats:
            d = self.client.marketplace_stats()
            print(f"Volume: {d['volume']}")
            for k, v in d['prices'].items():
                print(f"{k}: {v}")
        elif self.args.genes:
            self.find_market_genes(price_filter=self.args.price)
        else:
            self.find_market_snails(only_females=self.args.females, price_filter=self.args.price)
        return False

    @commands.argument('--snail', type=int, help='rename this snail')
    @commands.argument('--acc', type=commands.wallet_ext_or_int, help='rename this account')
    @commands.argument('name', help='new name')
    @commands.command()
    def cmd_rename(self):
        """Rename stuff: snails, accounts, etc"""
        if self.args.snail:
            return self.cmd_rename_snail()
        if self.args.acc:
            return self.cmd_rename_account()
        print('Nothing to rename?')
        return False

    def cmd_rename_account(self):
        if self.args.acc.address != self.owner:
            # not this one, next
            return

        print(f'Renaming {self._profile.get("username", "(unk)")} to {self.args.name}')
        self.client.rename_account(self.args.name)
        return False

    def cmd_rename_snail(self):
        r = self.client.gql.name_change(self.args.name)
        if not r.get('status'):
            raise Exception(r)
        print(self.client.web3.set_snail_name(self.args.snail, self.args.name))

    def _cmd_guild_data(self, guild_id=None):
        if guild_id is None and not self.profile_guild:
            return
        if guild_id is None:
            guild_id = self._profile['guild']['id']
        data = self.client.gql.guild_details(guild_id, member=self.owner)
        cleaned_data = {
            'rewards': [],
            'next_rewards': [],
            'name': data['name'],
        }
        for b in data['research']['buildings']:
            if b['reward']:
                if b['reward']['has_reward']:
                    cleaned_data['rewards'].append((b['type'], b['reward']['amount']))
                if b['reward']['next_reward_at']:
                    cleaned_data['next_rewards'].append((b['type'], b['reward']['next_reward_at']))
        for b in data['treasury']['resources']:
            if b['id'] == 'PRIMARY':
                cleaned_data['tomato'] = b['amount']
            elif b['id'] == 'SECONDARY':
                cleaned_data['lettuce'] = b['amount']
        cleaned_data.update(data['research']['stats'])
        cleaned_data.update(data['stats'])
        return cleaned_data

    @commands.argument(
        '--unstake',
        action='store_true',
        help='Unstake all the snails',
    )
    @commands.argument(
        '--stake',
        action='store_true',
        help='Stake all the snails',
    )
    @commands.argument(
        '-c',
        '--claim',
        action='store_true',
        help='Claim guild rewards (only tomato for now)',
    )
    @commands.argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Display details for every account (otherwise just overall summary)',
    )
    @commands.argument(
        '--other',
        type=int,
        help='Details for a guild other than yours',
    )
    @commands.command()
    def cmd_guild(self):
        """Guilds overview"""
        if self.args.unstake:
            return self.cmd_guild_unstake()

        if self.args.stake:
            return self.cmd_guild_stake()

        if self.args.other:
            data = self._cmd_guild_data(guild_id=self.args.other)
            print(f'Guild: {data["name"]} - lv {data["level"]}')
            print(f'Tomato: {data["tomato"]} ({data["tomato_ph"]} ph)')
            print(f'Lettuce: {data["lettuce"]}')
            print(f'Members: {data["member_count"]} ({data["snail_count"]} snails)')
            data = self.client.gql.guild_roster(self.args.other)
            for member in data['roster']['members']['users']:
                p = member['profile']
                print(f"- {p['username']} ({p['address']}): {member['stats']['workers']} workers")
            return False

        data = self._cmd_guild_data()
        if not data:
            if self.args.verbose or self.main_one is None:
                print('No guild')
            return

        if self.args.claim:
            return self.cmd_guild_claim(data)

        if self.args.verbose or self.main_one is None:
            print(f'Guild: {data["name"]} - lv {data["level"]}')
            print(f'Tomato: {data["tomato"]} ({data["tomato_ph"]} ph)')
            print(f'Lettuce: {data["lettuce"]}')
            print(f'Members: {data["member_count"]} ({data["snail_count"]} snails)')
            if data['next_rewards']:
                print('Next rewards:')
                for r1, r2 in data['next_rewards']:
                    print(f' - {r1}: {r2}')
            if data['rewards']:
                print(f"Rewards:")
                for r1, r2 in data['rewards']:
                    print(f' - {r1}: {r2}')
        return True, data

    def cmd_guild_claim(self, data):
        if not data['rewards']:
            return
        for building, _ in data['rewards']:
            if building == 'SINK':
                try:
                    print(self.client.claim_tomato(self._profile['guild']['id'])['message'])
                except client.gqlclient.APIError as e:
                    if 'claim once per hour' not in str(e):
                        raise
                    logger.warn(str(e))
            else:
                print(self.client.claim_building(self._profile['guild']['id'], building))

    def cmd_guild_stake(self):
        if not self.profile_guild:
            print('No guild')
            return
        snails = list(self.client.iterate_my_snails(self.owner))
        if not snails:
            print('No one available to work')
            return
        snail_ids = [s.id for s in snails]
        tx = self.client.stake_snails(self._profile['guild']['id'], snail_ids)
        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS
        print(f'{len(snails)} snails staked for {fee} AVAX')

    def cmd_guild_unstake(self):
        if not self.profile_guild:
            print('No guild')
            return
        snails = list(self.client.iterate_my_snails(self.owner, filters={'status': 5}))
        if not snails:
            print('No workers')
            return
        snail_ids = [s.id for s in snails]
        tx = self.client.web3.unstake_snails(snail_ids)
        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / DECIMALS
        print(f'{len(snails)} snails unstaked for {fee} AVAX')

    def find_candidates_sorting(self, candidates):
        candidates.sort(key=lambda x: x[:3], reverse=True)

    def find_candidates(self, race, snails, include_zero=False):
        candidates = []
        conditions = set(race.conditions)
        for s in snails:
            score = len(conditions.intersection(s.adaptations))
            if score or include_zero:
                candidates.append((score, len(s.adaptations), s.purity, s))
        self.find_candidates_sorting(candidates)
        return candidates

    def find_races_in_league(self, league):
        snails = list(self.client.iterate_my_snails_for_ranked(self.owner, league))
        if not snails:
            return [], []
        # sort with more adaptations first - for matching with races
        snails.sort(key=lambda x: len(x.adaptations), reverse=True)
        races = []
        for x in self.client.iterate_onboarding_races(filters={'owner': self.owner, 'league': league}):
            candidates = self.find_candidates(x, snails)
            x['candidates'] = candidates
            races.append(x)
        return snails, races

    def race_stats_text(self, snail, race):
        if not self.args.race_stats:
            return ''
        return '`' + '.'.join(map(str, self._snail_history.get(snail)[1][race.distance])) + '`'

    def find_races(self, check_notified=True):
        first_run = not self._notified_races and not self.args.first_run_over
        for league in client.League:
            _, races = self.find_races_in_league(league)
            for race in races:
                if check_notified and race.id in self._notified_races:
                    # notify only once...
                    continue
                if self.args.race_price and int(race.race_type) > self.args.race_price:
                    # too expensive! :D
                    continue
                if race.participation:
                    # already joined
                    continue
                if race['candidates']:
                    if not first_run:
                        # report on just required minimum matches, but use only snails with 2 adaptations (stronger)
                        cands = [
                            cand for cand in race['candidates'] if cand[0] >= self.args.race_matches and cand[1] > 1
                        ]
                        if not cands:
                            continue
                        candidate_list = ','.join(
                            f"{cand[1].name_id}{(cand[0] * '⭐')}{self.race_stats_text(cand[3], race)}" for cand in cands
                        )
                        msg = f"🏎️  Race {race} matched {candidate_list}"
                        if self.args.races_join:
                            join_actions = None
                            try:
                                self.client.join_competitive_races(cands[0][3].id, race.id, self.owner)
                                msg += '\nJOINED ✅'
                            except Exception:
                                logger.exception('failed to join race')
                                msg += '\nFAILED to join ❌'
                        else:
                            # TODO: reformat join message race
                            # * stats on different line
                            # * on top of stats for the race distance, show overall stats as well (on any distance)
                            # * date from last stat
                            # * use more_stats endpoint from server instead of getting all history?
                            #   * can we have stats per distance on that endpoint?
                            # ----
                            # (if this code is ever used again - competitives suck!)
                            join_actions = [
                                (
                                    f'✅ Join with {cand[3].name_id} {cand[0] * "⭐"}',
                                    f'joinrace {self.owner} {cand[3].id} {race.id}',
                                )
                                for cand in cands
                            ] + [
                                ('🏳️ Skip', 'joinrace'),
                            ]
                        logger.info(msg)
                        self.notifier.notify(msg, actions=join_actions)
                    self._notified_races.add(race['id'])

    def find_races_over(self):
        first_run = not self._notified_races_over and not self.args.first_run_over
        for race in self.client.iterate_finished_races(filters={'owner': self.owner}, own=True, max_calls=1):
            if race['id'] in self._notified_races_over:
                # notify only once...
                continue
            self._notified_races_over.add(race['id'])

            if first_run:
                # do not log or notify anything on "first run"
                # avoid restart spam with "pre-existing" finished races
                continue
            if race.is_mission and not self.args.missions_over:
                continue
            if not race.is_mission and not self.args.races_over:
                continue

            found = False
            for p, i in enumerate(race['results']):
                if i['token_id'] in self.my_snails:
                    found = True
                    snail = self.my_snails[i['token_id']]
                    if race.is_tournament:
                        msg = f"🥅 {snail.name_id} ({self.profile_guild}) in {race.track}, for {race.distance}, time {i['time']:.2f}s"
                    else:
                        p += 1
                        if p > 3:
                            e = '💩'
                        else:
                            e = '🥇🥈🥉'[p - 1]
                        if len(race.rewards['final_distribution']) >= p:
                            reward = race.rewards['final_distribution'][p - 1]
                        else:
                            reward = 0
                        msg = f"{e} {snail.name_id} number {p} in {race.track}, for {race.distance}, reward {reward}"
                    if race.is_competitive and self.args.race_stats:
                        self._snail_history.update(snail, race)
                        msg += ' ' + self.race_stats_text(snail, race)
                    logger.info(msg)
                    if not race.is_mission:
                        self.notifier.notify(msg)
                    if not race.is_mega:
                        # no point looking for more snails
                        break

            if not found:
                snail = Snail({'id': 0, 'name': 'UNKNOWN SNAIL'})
                msg = f"⁉️ {snail.name_id} in {race.track}, for {race.distance}"
                logger.info(msg)
                self.notifier.notify(msg)
        if first_run and not self._notified_races_over:
            # HACK ALERT: add random value just to make sure next run is not "first_run"
            self._notified_races_over.add(1)

    def _open_races(self):
        for league in client.League:
            snails, races = self.find_races_in_league(league)
            logger.info(f"Snails for {league}: {', '.join([s.name_id for s in snails])}")
            if not snails:
                continue
            for race in races:
                if self.args.price and int(race.race_type) > self.args.price:
                    continue
                if race.participation:
                    color = Fore.LIGHTBLACK_EX
                else:
                    color = Fore.GREEN
                if self.args.verbose:
                    for k in ('__typename', 'starts_at', 'league'):
                        del race[k]
                    x_str = str(race)
                else:
                    x_str = f"{race.track} (#{race.id}): {race.distance}m for {race.race_type} entry"

                candidates = race['candidates']
                if candidates:
                    c = f' - candidates: {", ".join((s[3].name_id+"⭐"*s[0]) for s in candidates)}'
                else:
                    c = ''
                print(f'{color}{x_str}{Fore.RESET}{c}')

    def _open_races(self):
        for league in client.League:
            snails, races = self.find_races_in_league(league)
            logger.info(f"Snails for {league}: {', '.join([s.name_id for s in snails])}")
            if not snails:
                continue
            for race in races:
                if self.args.price and int(race.race_type) > self.args.price:
                    continue
                if race.participation:
                    color = Fore.LIGHTBLACK_EX
                else:
                    color = Fore.GREEN
                if self.args.verbose:
                    for k in ('__typename', 'starts_at', 'league'):
                        del race[k]
                    x_str = str(race)
                else:
                    x_str = f"{race.track} (#{race.id}): {race.distance}m for {race.race_type} entry"

                candidates = race['candidates']
                if candidates:
                    c = f' - candidates: {", ".join((s[3].name_id+"⭐"*s[0]) for s in candidates)}'
                else:
                    c = ''
                print(f'{color}{x_str}{Fore.RESET}{c}')

    def _finished_races(self):
        total_cr = 0
        total = 0
        for race in (
            race
            for league in client.League
            for race in self.client.iterate_finished_races(filters={'owner': self.owner, 'league': league}, own=True)
        ):
            if self.args.price and race.is_competitive and int(race.race_type) > self.args.price:
                continue
            for p, i in enumerate(race['results']):
                if i['token_id'] in self.my_snails:
                    snail = self.my_snails[i['token_id']]
                    time_taken = i['time']
                    break
            else:
                snail = Snail({'id': 0, 'name': 'UNKNOWN SNAIL'})
                time_taken = -1
            p += 1
            if race.is_tournament:
                c = Fore.LIGHTYELLOW_EX
                cr = 0
                print(f"{c}{snail.name_id} in {race.track}, for {race.distance}m - {time_taken:.2f}s{Fore.RESET}")
            else:
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
                print(f"{c}{snail.name_id} number {p} in {race.track}, for {race.distance}m - {cr}{Fore.RESET}")
            total_cr += cr
            total += 1
            if self.args.limit and total >= self.args.limit:
                break
        print(f'\nRaces #: {total}')
        print(f'TOTAL CR: {total_cr}')

    def _history_races(self, snail):
        total_cr = 0
        total = 0
        races, stats = self._snail_history.get(snail, self.args.limit)
        for race_data in races:
            race, p, time_on_first, time_on_third = race_data
            fee = int(race.prize_pool) / 9
            if p < 4:
                c = [Fore.GREEN, Fore.YELLOW, Fore.LIGHTRED_EX][p - 1]
                m = [4, 1.5, 0.5][p - 1]
                cr = fee * m
            else:
                c = Fore.RED
                cr = 0 - fee
            total_cr += cr

            print(
                f"{c}{snail.name_id} number {p} in {race.track}, for {race.distance}m (on 1st: {time_on_first:0.2f}%, on 3rd: {time_on_third:0.2f}%) - {cr}{Fore.RESET}"
            )
            total += 1
        if total:
            print(f'\nRaces #: {total}')
            print(f'TOTAL CR: {total_cr}')
            print(
                'Stats (1/2/3/Total):',
                ' | '.join(
                    f'{Fore.CYAN}{k}{Fore.RESET}: {Fore.GREEN}{v[:3]}{Fore.RESET} ({v[3]})' for k, v in stats.items()
                ),
            )
        else:
            logger.warning(f'Nothing for {snail.name_id}')

    def _history_missions(self, snail):
        total = 0
        races = []
        with tqdm(
            self.client.iterate_race_history(filters={'token_id': snail.id, 'category': 2}),
            desc=str(snail),
            leave=False,
        ) as pb:
            for race in pb:
                time_on_first, time_on_third, p = CachedSnailHistory.race_stats(snail.id, race)
                if time_on_first is None:
                    continue
                reward = race.rewards['final_distribution'][p - 1]
                # FIXME: this might change
                if p <= 4:
                    reward_no_boost = [15, 12, 9, 6][p - 1]
                else:
                    reward_no_boost = 3
                races.append((race, p, time_on_first, time_on_third, reward, reward_no_boost))
                total += 1
                if self.args.limit and total >= self.args.limit:
                    break

            agg = '.'
            if self.args.agg and self.args.agg < len(races):
                aggs = []
                for i in range(0, len(races), self.args.agg):
                    w = races[i : i + self.args.agg]
                    aggs.append(sum(x[4] for x in w) / len(w))
                aggs_c = []
                for i in range(len(aggs) - 1):
                    if aggs[i] > aggs[i + 1]:
                        c = Fore.GREEN
                    elif aggs[i] < aggs[i + 1]:
                        c = Fore.RED
                    else:
                        c = ''
                    aggs_c.append(f'{c}{aggs[i]}{Fore.RESET}')
                aggs_c.append(str(aggs[-1]))
                agg = f': {"/".join(aggs_c)}'

            total_rewards = sum(x[4] for x in races)
            total_rewards_nb = sum(x[5] for x in races)
            if self.args.limit and len(races) == self.args.limit:
                c = Fore.GREEN
            else:
                c = Fore.YELLOW

            rate = total_rewards / len(races)
            text_nb = ''
            if total_rewards_nb != total_rewards:
                rate_nb = total_rewards_nb / len(races)
                text_nb = f' ({c}{rate_nb:.2f}{Fore.RESET})'

            rate_all = '-'
            total_missions = 0
            for stat in snail.more_stats[0]['data']:
                if stat['name'] == 'Mission':
                    for istat in stat['data']:
                        if istat['name'] == 'Race Type':
                            total_missions = istat['data'][0]['count']
                            rate_all = f"{snail.stats['earned_token'] / total_missions:.2f}"
                            break
                    break
            pb.write(
                f"{snail} - {len(races)} total missions, average {c}{rate:.2f}{Fore.RESET}{text_nb} reward (overall {rate_all} in {total_missions} missions){agg}"
            )

    def _join_race(self, join_arg: RaceJoin):
        try:
            r, rcpt = self.client.join_competitive_races(join_arg.snail_id, join_arg.race_id, self.owner)
            # FIXME: effectiveGasPrice * gasUsed = WEI used (AVAX 10^-18) - also print hexstring, not bytes...
            logger.info(f'{Fore.CYAN}{r["message"]}{Fore.RESET} - (tx: {rcpt.transactionHash.hex()})')
        except client.ClientError:
            logger.exception('unexpected joinRace error')

    @commands.argument('-v', '--verbose', action='store_true', help='Verbosity')
    @commands.argument('-f', '--finished', action='store_true', help='Get YOUR finished races')
    @commands.argument('-l', '--limit', type=int, help='Limit to X races')
    @commands.argument('--history', type=int, metavar='SNAIL_ID', help='Get race history for SNAIL_ID (use 0 for ALL)')
    @commands.argument('-p', '--price', type=int, help='Filter for less or equal to PRICE')
    @commands.argument(
        '-j', '--join', action=commands.StoreRaceJoin, help='Join competitive race RACE_ID with SNAIL_ID'
    )
    @commands.argument('--pending', action='store_true', help='Get YOUR pending races (joined but not yet started)')
    @commands.command()
    def cmd_races(self):
        """Race details (not missions)"""
        if self.args.finished:
            self._finished_races()
            return
        if self.args.pending:
            for r in self.client.iterate_onboarding_races(own=True, filters={'owner': self.owner}):
                print(f'{r.track} (#{r.id}): {len(r.athletes)} athletes scheduled for {r.schedules_at}')
            return
        if self.args.history is not None:
            if self.args.history == 0:
                for s in self.my_snails.values():
                    self._history_races(s)
            else:
                self._history_races(Snail({'id': self.args.history}))
            return
        if self.args.join:
            try:
                self._join_race(self.args.join)
                return False
            except client.gqlclient.APIError as e:
                if str(e) != 'Racer is not the active holder of the snail.':
                    raise
            return
        self._open_races()

    @commands.argument(
        '-f',
        '--fee',
        metavar='SNAIL_ID',
        type=int,
        nargs='*',
        help='if not SNAIL_ID is specified, all owned snails will be crossed. If one is, that will be compared against owned snails. If two are specified, only those 2 are used.',
    )
    @commands.argument(
        '-s',
        '--sim',
        metavar='SNAIL_ID',
        type=int,
        nargs='*',
        help='if not SNAIL_ID is specified, all owned snails will be crossed. If one is, that will be compared against owned snails. If two are specified, only those 2 are used.',
    )
    @commands.argument(
        '--external-wallet',
        type=commands.wallet_ext_or_int,
        metavar='account_or_address',
        help='Test snail against snails from this external account',
    )
    @commands.argument(
        '-g', '--genes', type=int, help='search genes marketplace (value is the number of gene search results to fetch)'
    )
    @commands.argument('-G', '--gene-family', type=int, help='filter gene market by this family (5 is Atlantis)')
    @commands.argument('-b', '--breeders', action='store_true', help='use only snails that are able to breed NOW')
    @commands.argument(
        '--plan', action='store_true', help='Lazy (suboptimal) planning for cheapest breeds (only for `-bf`)'
    )
    @commands.argument(
        '-x',
        '--execute',
        type=Path,
        help='Execute breeding plan from saved file',
    )
    @commands.command()
    def cmd_incubate(self):
        """
        Incubation fees and breed planning
        """
        if self.args.execute is not None:
            return self.cmd_incubate_execute()
        if self.args.fee is not None:
            return self.cmd_incubate_fee()
        if self.args.sim is not None:
            return self.cmd_incubate_sim()
        print(self.client.web3.get_current_coefficent())
        return False

    def cmd_incubate_execute(self):
        raise Exception('implemented only in multicli')

    def cmd_incubate_fee_lazy_plan(self, snail_fees):
        # lazy planning, only useful with many-to-many snails
        final_pairs = []
        sorted_pairs = sorted(snail_fees, key=lambda x: x[0])
        used = set()
        while True:
            # pick a male
            s_count = {}
            male = None

            def _s(s):
                if s not in used:
                    s_count[s] = s_count.get(s, 0) + 1
                    if s_count[s] > 2:
                        return True

            for _, snail1, snail2 in sorted_pairs:
                if _s(snail1):
                    male = snail1
                    break
                if _s(snail2):
                    male = snail2
                    break
            if male is None:
                # no male found
                break
            used.add(male)
            # find 3 pairs
            p = 0
            for fee, snail1, snail2 in sorted_pairs:
                if snail1 == male:
                    female = snail2
                elif snail2 == male:
                    female = snail1
                else:
                    continue
                if female in used:
                    continue
                p += 1
                used.add(female)
                final_pairs.append((fee, male, female))
                if p >= 3:
                    break
        return final_pairs

    def cmd_incubate_fee(self):
        pc = self.client.web3.get_current_coefficent()
        argc = len(self.args.fee)
        if argc == 2:
            snails = list(self.client.iterate_all_snails(filters={'id': self.args.fee}))
            assert len(snails) == 2
            print(snails[0].incubation_fee(snails[1], pc=pc))
            return False
        elif argc == 1:
            snails = list(self.client.iterate_all_snails(filters={'id': self.args.fee}))
            assert len(snails) == 1
            main_snail = snails

        snail_fees = []
        snails = list(self.client.iterate_all_snails(filters={'owner': self.owner}))
        if self.args.breeders:
            snails = [x for x in snails if x.breed_status < 0]

        if self.args.genes:
            male_snails = {}
            for snail in self.client.iterate_all_genes_marketplace():
                male_snails[snail.id] = snail
                if len(male_snails) == self.args.genes:
                    break
            keys = list(male_snails.keys())
            for i in range(0, len(keys), 20):
                for x in self.client.iterate_all_snails(filters={'id': keys[i : i + 20]}):
                    male_snails[x.id].update(x)

            if argc == 1:
                snails = main_snail
            for s1 in snails:
                for s2 in male_snails.values():
                    fee = s1.incubation_fee(s2, pc=pc)
                    snail_fees.append((fee + s2.gene_market_price, s1, s2))
        else:
            if argc == 1:
                for si2 in snails:
                    if main_snail == si2:
                        continue
                    fee = main_snail[0].incubation_fee(si2, pc=pc)
                    snail_fees.append((fee, main_snail[0], si2))
            else:
                for si1 in range(len(snails)):
                    for si2 in range(si1 + 1, len(snails)):
                        fee = snails[si1].incubation_fee(snails[si2], pc=pc)
                        snail_fees.append((fee, snails[si1], snails[si2]))

        if self.args.plan:
            # lazy planning, only useful with many-to-many snails
            snails = self.cmd_incubate_fee_lazy_plan(snail_fees)
            for fee, snail1, snail2 in snails:
                print(
                    f'{snail1.id}:{snail2.id} - '
                    f'{GENDER_COLORS[snail1.gender]}{snail1.name_id}{self._incubate_locked_gender(snail1)}{self._incubate_breed_limit(snail1)}{Fore.RESET} P{snail1.purity} {snail1.family.gene} - '
                    f'{GENDER_COLORS[snail2.gender]}{snail2.name_id}{self._incubate_locked_gender(snail2)}{self._incubate_breed_limit(snail2)}{Fore.RESET} P{snail2.purity} {snail2.family.gene} for {Fore.RED}{fee}{Fore.RESET}'
                )
            return True, snails
        else:
            for fee, snail1, snail2 in sorted(snail_fees, key=lambda x: x[0]):
                print(
                    f'{GENDER_COLORS[snail1.gender]}{snail1.name_id}{self._incubate_locked_gender(snail1)}{self._incubate_breed_limit(snail1)}{Fore.RESET} P{snail1.purity} {snail1.family.gene} - '
                    f'{GENDER_COLORS[snail2.gender]}{snail2.name_id}{self._incubate_locked_gender(snail2)}{self._incubate_breed_limit(snail2)}{Fore.RESET} P{snail2.purity} {snail2.family.gene} for {Fore.RED}{fee}{Fore.RESET}'
                )
        return True

    def cmd_incubate_sim_report(self, results, indent=0):
        families, purities, total = results
        family_odds = ' / '.join(
            f'{Fore.GREEN}{f[0]} {Fore.YELLOW}{f[1]*100/total:0.2f}%{Fore.RESET}' for f in families[::-1]
        )
        top_odds = ' / '.join(
            f'{Fore.GREEN}{f[0][0]}{f[0][1]} {Fore.YELLOW}{f[1]*100/total:0.2f}%{Fore.RESET}'
            for f in purities[-1:-5:-1]
        )
        top_purities = ' / '.join(
            f'{Fore.GREEN}{f[0][0]}{f[0][1]} {Fore.YELLOW}{f[1]*100/total:0.2f}%{Fore.RESET}'
            for f in sorted(purities, key=lambda x: x[0][1], reverse=True)[:5]
        )
        indent_str = ' ' * indent
        return f'\n{indent_str}'.join([family_odds, top_odds, top_purities])

    def _incubate_locked_gender(self, snail: Snail):
        return '' if snail.can_change_gender else '🔒'

    def _incubate_breed_limit(self, snail: Snail):
        if snail.breed_status < 0:
            return f' ({snail.monthly_breed_available}/{snail.monthly_breed_limit})'
        return ''

    def cmd_incubate_sim(self):
        pc = self.client.web3.get_current_coefficent()
        argc = len(self.args.sim)
        if argc == 2:
            snails = list(self.client.iterate_all_snails(filters={'id': self.args.sim}))
            assert len(snails) == 2
            print(self.cmd_incubate_sim_report(snails[0].incubation_simulation(snails[1])))
            return False

        if argc == 1:
            snails = list(self.client.iterate_all_snails(filters={'id': self.args.sim}))
            assert len(snails) == 1
            main_snail = snails

        ret = True
        snail_fees: list[tuple[int, Snail, Snail, float]] = []
        if self.args.external_wallet:
            if argc != 1:
                raise Exception(
                    '--external-wallet currently can only be used with a specific snail, not all snails from the current account'
                )
            snails = list(self.client.iterate_all_snails(filters={'owner': self.args.external_wallet.address}))
        else:
            snails = list(self.client.iterate_all_snails(filters={'owner': self.owner}))
        if self.args.breeders:
            snails = [x for x in snails if x.breed_status < 0]

        if self.args.genes:
            male_snails = {}
            filters = {}
            if self.args.gene_family:
                filters = {'family': self.args.gene_family}
            for snail in self.client.iterate_all_genes_marketplace(filters=filters):
                male_snails[snail.id] = snail
                if len(male_snails) == self.args.genes:
                    break
            keys = list(male_snails.keys())
            for i in range(0, len(keys), 20):
                for x in self.client.iterate_all_snails(filters={'id': keys[i : i + 20]}):
                    male_snails[x.id].update(x)

            if argc == 1:
                snails = main_snail
                ret = False
            for s1 in tqdm(snails):
                for s2 in tqdm(male_snails.values(), leave=False):
                    sim = s1.incubation_simulation(s2)
                    fee = s1.incubation_fee(s2, pc=pc)
                    snail_fees.append((sim, s1, s2, fee + s2.gene_market_price))
        else:
            if argc == 1:
                with tqdm(snails) as pbar:
                    for si2 in pbar:
                        pbar.set_description(si2.name)
                        if main_snail[0].id == si2.id:
                            continue
                        sim = main_snail[0].incubation_simulation(si2)
                        fee = main_snail[0].incubation_fee(si2, pc=pc)
                        snail_fees.append((sim, main_snail[0], si2, fee))
            else:
                with tqdm(range(len(snails))) as pb1:
                    for si1 in pb1:
                        pb1.set_description(snails[si1].name)
                        with tqdm(range(si1 + 1, len(snails)), leave=False) as pb2:
                            for si2 in pb2:
                                pb2.set_description(snails[si2].name)
                                sim = snails[si1].incubation_simulation(snails[si2])
                                fee = snails[si1].incubation_fee(snails[si2], pc=pc)
                                snail_fees.append((sim, snails[si1], snails[si2], fee))

        colors = {
            Gender.MALE: Fore.BLUE,
            Gender.FEMALE: Fore.MAGENTA,
            Gender.UNDEFINED: Fore.YELLOW,
        }
        # use GENE_FEES to "weight" family (but reversed)
        for sim, snail1, snail2, fee in sorted(
            snail_fees, key=lambda x: (1 / Snail.GENE_FEES[x[0][0][0][0]], x[0][0][0][1])
        ):
            prefix = (
                f'{colors[snail1.gender]}{snail1.name_id}{self._incubate_locked_gender(snail1)}{self._incubate_breed_limit(snail1)}{Fore.RESET}'
                ' - '
                f'{colors[snail2.gender]}{snail2.name_id}{self._incubate_locked_gender(snail2)}{self._incubate_breed_limit(snail2)}{Fore.RESET} for {Fore.RED}{fee:0.2f}{Fore.RESET}: '
            )
            # remove 30 for the coloring bytes
            indent = len(prefix) - 30
            print(f'{prefix}{self.cmd_incubate_sim_report(sim, indent=indent)}')
        return ret

    def _burn_coef(self):
        # pick random snail to simulate and get the coefficient
        for s in self.my_snails:
            try:
                return self.client.microwave_snails_preview([s])
            except client.gqlclient.APIError as e:
                if 'You have recently used this action' not in str(e):
                    raise

    @commands.command()
    def cmd_burn(self):
        """
        Burn fees
        """
        r = self._burn_coef()
        if r is None:
            # no snail available? just let it roll to another account
            return
        print(r['payload']['coef'])
        return False

    def _header(self):
        if self.main_one is not None:
            print(f'{Fore.CYAN}== {self.name} =={Fore.RESET}')

    def run(self):
        if not self.args.cmd:
            return
        self._header()
        return getattr(self, f'cmd_{self.args.cmd}')()
