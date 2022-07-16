from collections import defaultdict
from dataclasses import dataclass
import time
from datetime import datetime, timezone
import logging
from colorama import Fore

from snail.gqltypes import Snail
from .decorators import cached_property_with_ttl
from snail import client, VERSION
from . import tgbot

logger = logging.getLogger(__name__)


@dataclass
class RaceJoin:
    snail_id: int
    race_id: int


@dataclass
class Wallet:
    address: str
    private_key: str


class CLI:
    owner = None

    def __init__(self, wallet: Wallet, proxy_url: str, args, main_one=False):
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
        self.notifier = args.notify
        self._notified_races = set()
        self._notified_races_over = set()
        self._notify_mission_data = None
        self._notify_marketplace = {}
        self._notify_coefficent = 99999
        self._next_mission = None
        self._bot_pause = False

    @staticmethod
    def _now():
        return datetime.now(tz=timezone.utc)

    def cached_snail_history(self, snail_id, price=None, limit=None):
        """
        Return snail race history plus a stats summary
        """
        # FIXME: make this prettier with a TTLed lru_cache
        if not hasattr(self, '_cached_snail_history'):
            setattr(self, '_cached_snail_history', {})

        key = (snail_id, price, limit)
        data, last_update = self._cached_snail_history.get(key, (None, 0))
        _now = time.time()
        # re-fetch only once per 30min
        # TODO: make configurable? update only once and use race notifications to keep it up to date?
        if _now - last_update < 1800:
            return data

        stats = defaultdict(lambda: [0, 0, 0, 0])
        races = []
        total = 0
        for race in (
            race
            for league in client.League
            for race in self.client.iterate_race_history(filters={'token_id': snail_id, 'league': league})
        ):
            if price and int(race.race_type) > price:
                continue
            for p, i in enumerate(race.results):
                if i['token_id'] == snail_id:
                    break
            else:
                logger.error('snail not found, NOT POSSIBLE')
                continue
            time_on_first = race.results[0]['time'] * 100 / race.results[p]['time']
            time_on_third = race.results[2]['time'] * 100 / race.results[p]['time']
            p += 1
            if p < 4:
                stats[race.distance][p - 1] += 1
            stats[race.distance][3] += 1
            races.append((race, p, time_on_first, time_on_third))
            total += 1
            if limit and total >= limit:
                break

        data = (races, stats)
        self._cached_snail_history[key] = (data, _now)
        return data

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

    def notify_mission(self, message):
        """helper method to group all the notify mission calls in a single telegram message (re-edit)"""
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
                r, _ = self.client.join_mission_races(
                    snail.id, race.id, self.owner, allow_last_spot=(snail.id in boosted)
                )
                msg = f"🐌 `{snail.name_id}` ({snail.level} - {snail.stats['experience']['remaining']}) joined mission"
                if r.get('status') == 0:
                    logger.info(f'{Fore.CYAN}{r["message"]}{Fore.RESET}')
                    self.notify_mission(msg)
                elif r.get('status') == 1:
                    logger.warning('requires transaction')
                    self.notify_mission(f'{msg} *LAST SPOT*')
            except client.ClientError as e:
                logger.exception('failed to join mission')
                self.notifier.notify(f'⛔ `{snail.name_id}` FAILED to join mission: {tgbot.escape_markdown(str(e))}')
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
            if not self._bot_pause:
                if self.args.missions:
                    now = datetime.now(tz=timezone.utc)
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

                if self.args.market and self.main_one:
                    self._bot_marketplace()

                if self.args.coefficent and self.main_one:
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
            logger.exception('re-join as last error')
            msg = str(e)
            if msg.startswith('This snail tried joining a mission as last, needs to rest '):
                return int(msg[58:].split(' ', 1)[0])
            logger.error('crash, waiting 2min (logged)')
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
                    logger.info(f'TEMPDEBUG: {rcpt.transactionHash.hex()} {rcpt.gasUsed} {r["payload"]["size"]} {r["payload"]["completed_races"]}')
                    logger.info(f'{c} - LASTSPOT (tx: {rcpt.transactionHash.hex()})')
            except client.ClientError as e:
                if e.args[0] == 'requires_transaction':
                    logger.error('only last spot available, use --last-spot')
                else:
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

    def find_races(self):
        if self.args.race_stats:
            _x = lambda snail, race: (
                '`'
                + '.'.join(map(str, self.cached_snail_history(snail.id, int(race.race_type))[1][race.distance]))
                + '`'
            )
        else:
            _x = lambda x, y: ''

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
                        f"{cand[1].name_id}{(cand[0] * '⭐')}{_x(cand[1], race)}" for cand in cands
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
        races, stats = self.cached_snail_history(snail.id, self.args.price, self.args.limit)
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
            return self._finished_races()
        if self.args.history is not None:
            if self.args.history == 0:
                for s in self.my_snails.values():
                    self._history_races(s)
            else:
                self._history_races(Snail({'id': self.args.history}))
            return
        if self.args.join:
            return self._join_race(self.args.join)
        return self._open_races()

    def cmd_incubate(self):
        # TODO: everything, just showing coefficient for now
        print(self.client.web3.get_current_coefficent())

    def run(self):
        if self.args.cmd:
            getattr(self, f'cmd_{self.args.cmd}')()
