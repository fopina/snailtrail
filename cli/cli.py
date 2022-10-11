import argparse
from collections import defaultdict
from functools import cached_property
import json
import time
from datetime import datetime, timedelta, timezone
import logging
from typing import Optional, Union
from xmlrpc.client import Boolean
from colorama import Fore

from snail.gqltypes import Race, Snail, Gender
from .decorators import cached_property_with_ttl
from snail import client, VERSION
from .types import RaceJoin, Wallet
from .helpers import SetQueue
from . import tgbot

logger = logging.getLogger(__name__)


class CachedSnailHistory:
    def __init__(self, cli: 'CLI'):
        self.cli = cli
        self._cache = {}

    def __race_stats(self, snail_id, race):
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

    def get_all(self, snail_id: Union[int, Snail], limit=None):
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id
        # trigger any caching
        self.get(snail_id, 50, limit=limit)
        races = []
        stats = defaultdict(lambda: [0, 0, 0, 0])
        for k, v in self._cache.items():
            if (k[0], k[2]) != (snail_id, limit):
                continue
            r, s = v[0]
            races.extend(r)
            for k1, v1 in s.items():
                for i in range(4):
                    stats[k1][i] += v1[i]
        return races, stats

    def get(self, snail_id: Union[int, Snail], price: Union[int, Race], limit=None):
        """
        Return snail race history plus a stats summary
        """
        if isinstance(price, Race):
            price = int(price.race_type)
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id
        # FIXME: make this prettier with a TTLed lru_cache
        key = (snail_id, price, limit)
        data, last_update = self._cache.get(key, (None, 0))
        _now = time.time()
        # re-fetch only once per 30min
        # TODO: make configurable? update only once and use race notifications to keep it up to date?
        if _now - last_update < 1800:
            return data

        races_per_price = {
            50: [],
            100: [],
            200: [],
            500: [],
        }

        for race in (
            race
            for league in client.League
            for race in self.cli.client.iterate_race_history(filters={'token_id': snail_id, 'league': league})
        ):
            races_per_price[int(race.race_type)].append(race)

        for race_type, history_races in races_per_price.items():
            stats = defaultdict(lambda: [0, 0, 0, 0])
            races = []
            total = 0
            for race in history_races:
                time_on_first, time_on_third, p = self.__race_stats(snail_id, race)
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
            self._cache[(snail_id, race_type, limit)] = (data, _now)
        return self._cache[key][0]

    def update(self, snail_id: Union[int, Snail], race: Race, limit=None):
        price = int(race.race_type)
        if isinstance(snail_id, Snail):
            snail_id = snail_id.id

        key = (snail_id, price, limit)
        data, last_update = self._cache.get(key, (None, 0))
        _now = time.time()
        if _now - last_update >= 1800:
            # do not update anything as cache already expired
            return False

        time_on_first, time_on_third, p = self.__race_stats(snail_id, race)
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

    def __init__(self, wallet: Wallet, proxy_url: str, args: argparse.Namespace, main_one: Optional[Boolean] = None):
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
        self.client = client.Client(
            proxy=proxy_url,
            wallet=self.owner,
            private_key=wallet.private_key,
            web3_provider=args.web3_rpc,
            rate_limiter=args.rate_limit,
            gql_retry=args.retry if args.retry > 0 else None,
        )
        self.notifier: tgbot.Notifier = args.notify
        self._notified_races = SetQueue(capacity=100)
        self._notified_races_over = SetQueue(capacity=100)
        self._notify_mission_data = None
        self._notify_marketplace = {}
        self._notify_coefficent = 99999
        self._next_mission = None
        self._snail_mission_cooldown = {}
        self._snail_history = CachedSnailHistory(self)

    @staticmethod
    def _now():
        return datetime.now(tz=timezone.utc)

    @cached_property
    def masked_wallet(self):
        if self.owner[:2] != '0x':
            return self.owner
        if len(self.owner) < 20:
            return self.owner
        return f'{self.owner[:5]}...{self.owner[-3:]}'

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
        settings_file.write_text(json.dumps(data))

    @cached_property_with_ttl(600)
    def my_snails(self):
        return {snail.id: snail for snail in self.client.iterate_all_snails(filters={'owner': self.owner})}

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
            if self.args.exclude and x.id in self.args.exclude:
                continue
            to_queue = x.queueable_at
            if x.id in self._snail_mission_cooldown and to_queue < self._snail_mission_cooldown[x.id]:
                to_queue = self._snail_mission_cooldown[x.id]
            tleft = to_queue - self._now()
            base_msg = f"{x.name_id} : ({x.level} - {x.stats['experience']['remaining']}) : "
            if tleft.total_seconds() <= 0:
                queueable.append(x)
                logger.info(f"{Fore.GREEN}{base_msg}{x.adaptations}{Fore.RESET}")
            else:
                if closest is None or to_queue < closest:
                    closest = to_queue
                logger.info(f"{Fore.YELLOW}{base_msg}{tleft}{Fore.RESET}")
        return queueable, closest

    def join_missions(self):
        queueable, closest = self.mission_queueable_snails()
        if not queueable:
            return closest

        boosted = set(self.args.boost or [])
        if self.args.fair:
            # add snails with negative tickets to "boosted" to re-use logic
            for s in queueable:
                if s.stats['mission_tickets'] < 0:
                    boosted.add(s.id)

        for race in self.client.iterate_mission_races(filters={'owner': self.owner}):
            if race.participation:
                # already joined
                continue
            athletes = len(race.athletes)
            if athletes == 10:
                # race full
                continue
            for snail in queueable:
                # FIXME: update for multiple adaptations
                if athletes == 9:
                    # don't queue non-boosted!
                    if snail.id in boosted and ((snail.adaptations[0] in race.conditions) or self.args.no_adapt):
                        break
                else:
                    # don't queue boosted here, so they wait for a last spot
                    if snail.id not in boosted and (snail.adaptations[0] in race.conditions):
                        break
            else:
                # no snail for this track
                continue
            logger.info(
                f'{Fore.CYAN}Joining {race.id} ({race.conditions}) with {snail.name_id} ({snail.adaptations}){Fore.RESET}'
            )
            try:
                if self.args.cheap and snail.id in boosted:
                    # join without allowing last spot to capture payload
                    try:
                        # if this succeeds, it was not a last spot - that should not happen...
                        r, rcpt = self.client.join_mission_races(snail.id, race.id, self.owner, allow_last_spot=False)
                        logger.error('WTF? SHOULD HAVE FAILED TO JOIN AS LAST SPOT - but ok')
                    except client.RequiresTransactionClientError as e:
                        r = e.args[1]
                        if r['payload']['size'] == 0:
                            rcpt = self.client.rejoin_mission_races(r)
                        else:
                            try:
                                estimated_gas = self.client.rejoin_mission_races(r, estimate_only=True)
                            except:
                                # ignore any errors estimating
                                estimated_gas = '-'
                            # TODO: add snail to cooldown, is 150 too much? check future logs
                            self._snail_mission_cooldown[snail.id] = self._now() + timedelta(seconds=150)
                            # also remove from queueable (due to "continue")
                            queueable.remove(snail)
                            continue
                else:
                    try:
                        r, rcpt = self.client.join_mission_races(
                            snail.id, race.id, self.owner, allow_last_spot=(snail.id in boosted)
                        )
                    except client.RequiresTransactionClientError as e:
                        logger.error('TOO SLOW TO JOIN NON-LAST - %s on %d', snail.name, race.id)
                        if not self.args.fair:
                            raise

                        r = e.args[1]
                        # join last spot anyway, even if not "boosted" (negative tickets)
                        if self.args.cheap and not r['payload']['size'] == 0:
                            raise

                        rcpt = self.client.rejoin_mission_races(r)

                msg = f"🐌 `{snail.name_id}` ({snail.level} - {snail.stats['experience']['remaining']}) joined mission"
                if r.get('status') == 0:
                    logger.info(f'{msg} - {r["message"]}')
                    self.notify_mission(msg)
                elif r.get('status') == 1:
                    logger.info(f'{msg} LAST SPOT - {r["message"]}')
                    self.notify_mission(f'{msg} *LAST SPOT*')
            except client.ClientError as e:
                logger.exception('failed to join mission')
                self.notifier.notify(f'⛔ `{snail.name_id}` FAILED to join mission: {tgbot.escape_markdown(str(e))}')
            except client.gqlclient.APIError as e:
                # handle re-join timeout errors
                msg = str(e)
                if not msg.startswith('This snail tried joining a mission as last, needs to rest '):
                    raise
                logger.exception('re-join as last error for %s', snail.name_id)
                self._snail_mission_cooldown[snail.id] = self._now() + timedelta(seconds=int(msg[58:].split(' ', 1)[0]))
            except client.web3client.exceptions.ContractLogicError as e:
                if 'Race already submitted' in str(e):
                    logger.error('Too late for the race, try next one')
                    # continue loop to next race *without* removing snail from queueable
                    continue
                raise

            # remove snail from queueable (as it is no longer available)
            queueable.remove(snail)

        if queueable:
            logger.info(f'{len(queueable)} without matching race')
            return
        return closest

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
        if self.args.claim:
            try:
                r = self.client.web3.claim_rewards()
                if r.get('status') == 1:
                    bal = int(r['logs'][1]['data'], 16) / 1000000000000000000
                    print(f'claimed {bal}')
                else:
                    print('ERROR:', r)
            except client.web3client.exceptions.ContractLogicError as e:
                print(e)
        elif self.args.send is not None:
            target = self.args.wallet[self.args.send].address
            if target == self.owner:
                return
            bal = self.client.web3.balance_of_slime(raw=True)
            if not bal:
                print('Nothing to send')
                return
            print(f'Sending {bal / 1000000000000000000} to {target}')
            r = self.client.web3.transfer_slime(target, bal)
            sent = int(r['logs'][0]['data'], 16) / 1000000000000000000
            print(f'{sent} SLIME sent')
        else:
            print(self._balance())

    def _bot_marketplace(self):
        d = self.client.marketplace_stats()
        n = False
        txt = ['📉  Floors decreased']
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
        if coef < self._notify_coefficent:
            msg = f'Coefficent drop to *{coef:0.4f}* (from *{self._notify_coefficent}*)'
            self.notifier.notify(msg)
            logger.info(msg)
        self._notify_coefficent = coef

    def cmd_bot(self):
        self.cmd_bot_greet()
        while True:
            w = self.cmd_bot_tick()
            time.sleep(w)

    def cmd_bot_greet(self):
        msg = f'👋  Running *v{VERSION}*'
        if not self.args.tg_bot:
            msg += ' `(non-interactive)`'
        self.notifier.notify(msg)

    def cmd_bot_tick(self):
        try:
            w = self.args.wait
            if not self.args.paused:
                if self.args.missions:
                    now = self._now()
                    if self._next_mission is None or self._next_mission < now:
                        self._next_mission = self.join_missions()
                        logger.info('next mission in at %s', self._next_mission)
                    if self._next_mission is not None:
                        # if wait for next mission is lower than wait argument, use it
                        _w = (self._next_mission - now).total_seconds()
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

            logger.debug('waiting %d seconds', w)
            return w
        except client.gqlclient.requests.exceptions.HTTPError as e:
            if e.response.status_code in (502, 504):
                # log stacktrace to check if specific calls cause this more frequently
                logger.exception('site %d... waiting', e.response.status_code)
                return 20

            if e.response.status_code == 429:
                # FIXME: handle retry-after header after checking it out
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

    def cmd_missions(self):
        if self.args.join:
            # join mission
            try:
                r, rcpt = self.client.join_mission_races(
                    self.args.join.snail_id, self.args.join.race_id, self.owner, allow_last_spot=self.args.last_spot
                )
                c = f'{Fore.CYAN}{r["message"]}{Fore.RESET}'
                if rcpt is None:
                    logger.info(c)
                else:
                    logger.info(f'{c} - LASTSPOT (tx: {rcpt.transactionHash.hex()})')
            except client.RequiresTransactionClientError:
                logger.error('only last spot available, use --last-spot')
            except client.ClientError as e:
                logger.exception('unexpected joinMission error')
        else:
            # list missions
            snails = list(self.client.iterate_my_snails_for_missions(self.owner))
            for x in self.client.iterate_mission_races(filters={'owner': self.owner}):
                athletes = len(x.athletes)
                if x.participation:
                    color = Fore.LIGHTBLACK_EX
                elif athletes == 9:
                    color = Fore.RED
                else:
                    color = Fore.GREEN
                c = f'{color}{x} - {athletes}{Fore.RESET}'
                candidates = self.find_candidates(x, snails)
                if candidates:
                    c += f': {", ".join((s[1].name_id+"⭐"*s[0]) for s in candidates)}'
                print(c)

    def cmd_snails(self):
        it = list(self.my_snails.values())
        if self.args.sort:
            if self.args.sort == 'breed':
                it.sort(key=lambda x: x.breed_status)
            elif self.args.sort == 'lvl':
                it.sort(key=lambda x: x.level)
        for snail in it:
            print(snail, self._breed_status_str(snail.breed_status))

    def cmd_market(self):
        if self.args.stats:
            d = self.client.marketplace_stats()
            print(f"Volume: {d['volume']}")
            for k, v in d['prices'].items():
                print(f"{k}: {v}")
        elif self.args.genes:
            self.find_market_genes(price_filter=self.args.price)
        else:
            self.find_market_snails(only_females=self.args.females, price_filter=self.args.price)

    def cmd_rename(self):
        self.rename_snail()

    def find_candidates(self, race, snails):
        candidates = []
        conditions = set(race.conditions)
        for s in snails:
            score = len(conditions.intersection(s.adaptations))
            if score:
                candidates.append((score, s))
        candidates.sort(key=lambda x: x[0], reverse=True)
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
        return '`' + '.'.join(map(str, self._snail_history.get_all(snail)[1][race.distance])) + '`'

    def find_races(self):
        for league in client.League:
            _, races = self.find_races_in_league(league)
            for race in races:
                if race.id in self._notified_races:
                    # notify only once...
                    continue
                if self.args.race_price and int(race.race_type) > self.args.race_price:
                    # too expensive! :D
                    continue
                if race.participation:
                    # already joined
                    continue
                if race['candidates']:
                    # report on just 1 match, but use only snails with 2 adaptations (stronger)
                    cands = [
                        cand
                        for cand in race['candidates']
                        if cand[0] >= self.args.race_matches and len(cand[1].adaptations) > 1
                    ]
                    if not cands:
                        continue
                    candidate_list = ','.join(
                        f"{cand[1].name_id}{(cand[0] * '⭐')}{self.race_stats_text(cand[1], race)}" for cand in cands
                    )
                    msg = f"🏎️  Race {race} matched {candidate_list}"
                    if self.args.races_join:
                        join_actions = None
                        try:
                            self.client.join_competitive_races(cands[0][1].id, race.id, self.owner)
                            msg += '\nJOINED ✅'
                        except Exception:
                            logger.exception('failed to join race')
                            msg += '\nFAILED to join ❌'
                    else:
                        join_actions = [
                            (
                                f'✅ Join with {cand[1].name_id} {cand[0] * "⭐"}',
                                f'joinrace {self.owner} {cand[1].id} {race.id}',
                            )
                            for cand in cands
                        ] + [
                            ('🏳️ Skip', 'joinrace'),
                        ]
                    logger.info(msg)
                    self.notifier.notify(msg, actions=join_actions)
                    self._notified_races.add(race['id'])

    def find_races_over(self):
        for race in self.client.iterate_finished_races(filters={'owner': self.owner}, own=True, max_calls=1):
            if race['id'] in self._notified_races_over:
                # notify only once...
                continue
            self._notified_races_over.add(race['id'])

            if race.is_mission and not self.args.missions_over:
                continue
            if not race.is_mission and not self.args.races_over:
                continue

            for p, i in enumerate(race['results']):
                if i['token_id'] in self.my_snails:
                    snail = self.my_snails[i['token_id']]
                    break
            else:
                snail = Snail({'id': 0, 'name': 'UNKNOWN SNAIL'})
            p += 1
            if p > 3:
                e = '💩'
                if race.is_mission:
                    continue
            else:
                e = '🥇🥈🥉'[p - 1]

            msg = f"{e} {snail.name_id} number {p} in {race.track}, for {race.distance}"
            if not race.is_mission and self.args.race_stats:
                self._snail_history.update(snail, race)
                msg += ' ' + self.race_stats_text(snail, race)
            logger.info(msg)
            self.notifier.notify(msg, silent=True)

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
                    c = f' - candidates: {", ".join((s[1].name_id+"⭐"*s[0]) for s in candidates)}'
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
            if self.args.price and int(race.race_type) > self.args.price:
                continue
            for p, i in enumerate(race['results']):
                if i['token_id'] in self.my_snails:
                    snail = self.my_snails[i['token_id']]
                    break
            else:
                snail = Snail({'id': 0, 'name': 'UNKNOWN SNAIL'})
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
            print(f"{c}{snail.name_id} number {p} in {race.track}, for {race.distance}m - {cr}{Fore.RESET}")
            total += 1
            if self.args.limit and total >= self.args.limit:
                break
        print(f'\nRaces #: {total}')
        print(f'TOTAL CR: {total_cr}')

    def _history_races(self, snail):
        total_cr = 0
        total = 0
        races, stats = self._snail_history.get(snail, self.args.price, self.args.limit)
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

    def _join_race(self, join_arg: RaceJoin):
        try:
            r, rcpt = self.client.join_competitive_races(join_arg.snail_id, join_arg.race_id, self.owner)
            # FIXME: effectiveGasPrice * gasUsed = WEI used (AVAX 10^-18) - also print hexstring, not bytes...
            logger.info(f'{Fore.CYAN}{r["message"]}{Fore.RESET} - (tx: {rcpt["transactionHash"]})')
        except client.ClientError:
            logger.exception('unexpected joinRace error')

    def cmd_races(self):
        if self.args.finished:
            self._finished_races()
            return
        if self.args.history is not None:
            if self.args.history == 0:
                for s in self.my_snails.values():
                    self._history_races(s)
            else:
                self._history_races(Snail({'id': self.args.history}))
            return
        if self.args.join:
            self._join_race(self.args.join)
            return
        self._open_races()

    def cmd_incubate(self):
        if self.args.fee is not None:
            return self.cmd_incubate_fee()
        if self.args.sim is not None:
            return self.cmd_incubate_sim()
        print(self.client.web3.get_current_coefficent())
        return False

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

        colors = {
            Gender.MALE: Fore.BLUE,
            Gender.FEMALE: Fore.MAGENTA,
            Gender.UNDEFINED: Fore.YELLOW,
        }
        for fee, snail1, snail2 in sorted(snail_fees, key=lambda x: x[0]):
            print(
                f'{colors[snail1.gender]}{snail1.name_id}{Fore.RESET} - {colors[snail2.gender]}{snail2.name_id}{Fore.RESET} for {Fore.RED}{fee}{Fore.RESET}'
            )
        return True

    def cmd_incubate_sim_report(self, results):
        families, purities, total = results
        return ' --- '.join(
            [
                ' / '.join(
                    f'{Fore.GREEN}{f[0]} {Fore.YELLOW}{f[1]*100/total:0.2f}%{Fore.RESET}' for f in families[::-1]
                ),
                ' / '.join(
                    f'{Fore.GREEN}{f[0][0]}{f[0][1]} {Fore.YELLOW}{f[1]*100/total:0.2f}%{Fore.RESET}'
                    for f in purities[-1:-5:-1]
                ),
            ]
        )

    def cmd_incubate_sim(self):
        pc = self.client.web3.get_current_coefficent()
        argc = len(self.args.sim)
        if argc == 2:
            snails = list(self.client.iterate_all_snails(filters={'id': self.args.sim}))
            assert len(snails) == 2
            print(self.cmd_incubate_sim_report(snails[0].incubation_simulation(snails[1])))
            return False
        elif argc == 1:
            snails = list(self.client.iterate_all_snails(filters={'id': self.args.sim}))
            assert len(snails) == 1
            main_snail = snails

        ret = True
        snail_fees = []
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
            for s1 in snails:
                for s2 in male_snails.values():
                    sim = s1.incubation_simulation(s2)
                    fee = s1.incubation_fee(s2, pc=pc)
                    snail_fees.append((sim, s1, s2, fee + s2.gene_market_price))
        else:
            if argc == 1:
                for si2 in snails:
                    if main_snail[0].id == si2.id:
                        continue
                    sim = main_snail[0].incubation_simulation(si2)
                    fee = main_snail[0].incubation_fee(si2, pc=pc)
                    snail_fees.append((sim, main_snail[0], si2, fee))
            else:
                for si1 in range(len(snails)):
                    for si2 in range(si1 + 1, len(snails)):
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
            print(
                f'{colors[snail1.gender]}{snail1.name_id}{Fore.RESET} - {colors[snail2.gender]}{snail2.name_id}{Fore.RESET} for {Fore.RED}{fee:0.2f}{Fore.RESET}: {self.cmd_incubate_sim_report(sim)}'
            )
        return ret

    def run(self):
        if not self.args.cmd:
            return
        if self.main_one is not None:
            print(f'{Fore.CYAN}== {self.masked_wallet}{Fore.RESET} ==')
        return getattr(self, f'cmd_{self.args.cmd}')()
