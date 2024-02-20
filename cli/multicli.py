import argparse
import itertools
import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from colorama import Fore
from tqdm import tqdm

from snail import VERSION
from snail.gqlclient.types import Adaptation, Family, Snail
from snail.web3client import DECIMALS

from . import cli, commands, utils
from .database import GlobalDB, MissionLoop

logger = logging.getLogger(__name__)


class MultiCLI:
    """
    Wrapper of CLI objects to control multiple wallets
    """

    def __init__(
        self,
        wallets: List['cli.Wallet'],
        proxy_url: str,
        args: argparse.Namespace,
    ):
        self.clis: list[cli.CLI] = []
        self.args = args
        # --bot specific in global init... ugly...
        bot_data_dir = getattr(args, 'data_dir', None)
        if bot_data_dir:
            self.database = GlobalDB.load_from_file(self.args.data_dir / 'db.json')
        else:
            self.database = GlobalDB()

        first_one = True if len(wallets) > 1 else None
        for w in wallets:
            if w is None:
                continue
            wallet_db = self.database.add_wallet(w.address)
            c = cli.CLI(
                w,
                proxy_url,
                args,
                main_one=first_one,
                graphql_endpoint=args.graphql_endpoint,
                multicli=self,
                database=wallet_db,
            )
            first_one = False
            args.notify.register_cli(c)
            self.clis.append(c)

        self.load_profiles()

    @property
    def is_multi(self) -> bool:
        return len(self.clis) > 1

    @property
    def main_cli(self) -> 'cli.CLI':
        if self.clis:
            return self.clis[0]
        return None

    def load_profiles(self):
        """get proper profile info"""
        if not self.main_cli:
            return

        # get original indices (so they remain constant in the name)
        # as "active" wallets might be restricted using -a flag
        wallet_indices = {w.address: i + 1 for i, w in enumerate(self.args.wallet) if w is not None}

        profiles = [c.owner for c in self.clis]
        data = self.main_cli.client.gql.profile(profiles)
        for i, c in enumerate(self.clis):
            c._profile = data[f'profile{i}']
            c._profile['_i'] = wallet_indices[c.owner]

    def cmd_bot(self):
        logger.info('Running bot %s', VERSION)
        # disable tournament check in all accounts with repeated guilds
        # no need to notify wins for the same guild :D
        guilds = set()
        for c in self.clis:
            if c.profile_guild and c.profile_guild in guilds:
                c._bot_tournament = lambda: None
            guilds.add(c.profile_guild)

        self.main_cli.load_bot_settings()

        # this cmd is special as it should loop infinitely
        self.args.notify.start_polling()

        _past = self.main_cli._now()
        cli_waits = defaultdict(lambda: _past)
        cli_waits_other = defaultdict(lambda: _past)
        try:
            self.main_cli.cmd_bot_greet()
            while True:
                now = self.main_cli._now()
                snail_balance = self.main_cli.client.web3.multicall_balances(
                    [c.owner for c in self.clis], _all=False, snails=True
                )
                # do all missions in a row, first (but skip wallets with 0 snails)
                for c in self.clis:
                    if snail_balance[c.owner].snails == 0:
                        c.database.mission_loop.status = MissionLoop.Status.NO_SNAILS
                        continue
                    if now < cli_waits[c.owner]:
                        continue
                    _start = self.main_cli._now()
                    w = c._cmd_bot_tick_exception_handler(c._cmd_bot_tick_missions)
                    if w:
                        cli_waits[c.owner] = now + timedelta(seconds=w)
                    duration = (self.main_cli._now() - _start).total_seconds()
                    if duration > 1:
                        c.logger.info(
                            'Tick-mission processed in %s (%d seconds)', self.main_cli._now() - _start, duration
                        )
                # then the others
                for c in self.clis:
                    if now < cli_waits_other[c.owner]:
                        continue
                    _start = self.main_cli._now()
                    w = c._cmd_bot_tick_exception_handler(c._cmd_bot_tick_other)
                    if w:
                        cli_waits_other[c.owner] = now + timedelta(seconds=w)
                    duration = (self.main_cli._now() - _start).total_seconds()
                    if duration > 1:
                        c.logger.info(
                            'Tick-other processed in %s (%d seconds)', self.main_cli._now() - _start, duration
                        )
                time.sleep(1)
        finally:
            self.args.notify.stop_polling()

    def cmd_balance(self):
        if self.args.claim or self.args.send is not None:
            return False
        totals = [0, 0, 0]

        cache = self.main_cli.client.web3.multicall_balances([c.owner for c in self.clis])

        for c in self.clis:
            c._header()
            data = c.cmd_balance(data=cache[c.owner])
            totals[0] += sum(data['SLIME'])
            totals[1] += sum(data['WAVAX']) + data['AVAX']
            totals[2] += data['SNAILS']
        print(f'{Fore.CYAN}== TOTAL{Fore.RESET} ==')
        print(
            f'''\
SLIME: {totals[0]:.3f}
AVAX: {totals[1]:.3f}
SNAILS: {totals[2]}'''
        )

    def cmd_inventory(self):
        totals = defaultdict(lambda: 0)
        for c in self.clis:
            c._header()
            for _, v in c.cmd_inventory().items():
                totals[v[0].name] += len(v)

        print(f'{Fore.CYAN}== TOTAL{Fore.RESET} ==')
        for k, v in totals.items():
            print(f'{k}: {v}')

    def cmd_incubate(self):
        if self.args.execute:
            return self._cmd_incubate_execute()
        if self.args.fee is not None and self.args.plan:
            return self._cmd_incubate_plan()
        return False

    def _cli_by_address(self, address):
        for cli in self.clis:
            if cli.owner[-40:].lower() == address[-40:].lower():
                return cli

    def _wait_api_transfer(self, cli: cli.CLI, *snails: int, sleep=0.5) -> list[Snail]:
        """wait for API to refresh after snail transfers"""
        for _ in range(60):
            _snails = list(cli.client.iterate_all_snails(filters={'id': snails}))
            if len(_snails) == len(snails) and {x.owner for x in _snails} == {cli.owner}:
                print('API updated')
                return _snails
            print('.', end='', flush=True)
            time.sleep(sleep)
        raise Exception('too many retries, not the holder?!')

    def _cmd_incubate_execute(self):
        # validate
        plan = [list(map(int, l.split(' ')[0].split(':'))) for l in self.args.execute.read_text().splitlines() if l]

        # any incomplete breed cycle?
        males = defaultdict(lambda: 0)
        females = defaultdict(lambda: 0)
        for p in plan:
            males[p[1]] += 1
            females[p[2]] += 1
        fail = False
        for k, v in males.items():
            if v < 3:
                print(f'male {k} only has {v} breeds')
                fail = True
        if fail and not self.args.execute_force:
            raise Exception('incomplete plan')
        for k, v in females.items():
            if v != 1:
                print(f'female {k} has {v} breeds')
                fail = True
        if fail and not self.args.execute_force:
            raise Exception('incomplete plan')

        # transgender plan
        done = set()

        def _transgender(c, snail, gender):
            fee = 0
            if snail not in done:
                tx = c.client.web3.set_snail_gender(snail, gender.value)
                if tx:
                    fee = utils.tx_fee(tx)
                    print(f'{snail} changed gender to {gender} for {fee}')
                done.add(snail)
            return fee

        acc_indices = {c._profile['_i']: _i for _i, c in enumerate(self.clis)}
        # regroup per account
        new_plan: dict[int, list[int]] = defaultdict(list)
        # reversed would be more profitable (more expensive first) but if it runs out of funds
        # the cheapest are not processed...
        for p in plan:
            new_plan[p[0]].append(p[1:])

        # approve incubator
        for acc in tqdm(new_plan, desc='Approve incubator'):
            c = self.clis[acc_indices[acc]]
            tx = c.client.web3.approve_slime_for_incubator()
            if tx:
                fee = utils.tx_fee(tx)
                print(f'{c.name} approved incubator for {fee}')

        def retriable_breed(c, fs, ms, use_scroll=False):
            _r = None
            for _ in range(60):
                try:
                    return c.client.breed_snails(fs, ms, use_scroll=use_scroll)
                except cli.client.gqlclient.APIError as e:
                    if 'Please provide a' not in str(e):
                        raise
                    _r = e
                    time.sleep(0.5)
                except cli.client.web3client.exceptions.ContractLogicError as e:
                    if 'Protocol coefficent changed' not in str(e):
                        raise
                    time.sleep(1)
                    _r = e
            raise _r

        last_client = None
        gender_fees = 0
        breed_fees = 0
        transfer_fees = 0
        scrolls: dict[cli.CLI, int] = defaultdict(lambda: 0)
        if self.args.execute_scroll:
            for c in tqdm(self.clis, desc='Loading inventory'):
                for _, v in c.cmd_inventory(verbose=False).items():
                    if v[0].name.startswith('Breeding Scroll'):
                        scrolls[c] += 1

        try:
            for acc, acc_plan in new_plan.items():
                c = self.clis[acc_indices[acc]]
                if not self.args.execute_scroll and last_client is not None and last_client != c:
                    last_client.cmd_balance_transfer_slime(c.owner)
                last_client = c
                for ms, fs, *rest in acc_plan:
                    if rest:
                        print(f'Skipping {ms, fs}')
                        continue

                    if self.args.execute_scroll and scrolls[c] < 1:
                        # use another cli with scroll
                        for nc, nv in scrolls.items():
                            if nv > 0 and nc not in new_plan:
                                break
                        else:
                            raise Exception('no useable scrolls found')
                        scrolls[nc] -= 1
                        owners = c.client.snail_owners(ms, fs)
                        if owners[ms] == owners[fs]:
                            oc = self._cli_by_address(owners[ms])
                            if oc != nc:
                                ap_tx, tx = oc.client.transfer_snails(nc.owner, ms, fs)
                                if ap_tx:
                                    fee = utils.tx_fee(ap_tx)
                                    print(f'Approved bulkTransfer for {fee} AVAX')
                                fee = utils.tx_fee(tx)
                                print(f'bulkTransfer to {nc} for {fee} AVAX')
                                transfer_fees += fee
                        else:
                            for _s in (ms, fs):
                                oc = self._cli_by_address(owners[_s])
                                if oc != nc:
                                    _, tx = oc.client.transfer_snails(nc.owner, _s)
                                    fee = utils.tx_fee(tx)
                                    print(f'transfer to {nc} for {fee} AVAX')
                                    transfer_fees += fee
                        c = nc
                        self._wait_api_transfer(c, ms, fs)

                    # transgender
                    fee = _transgender(c, ms, cli.Gender.MALE)
                    gender_fees += fee
                    fee = _transgender(c, fs, cli.Gender.FEMALE)
                    gender_fees += fee

                    # get coefficient just for displaying
                    coef = c.client.web3.get_current_coefficent()
                    print(f'breeding {ms, fs} (with coeff {coef})...')
                    new_snail_id, tx = retriable_breed(c, fs, ms, use_scroll=self.args.execute_scroll)
                    new_snail = self._wait_api_transfer(c, new_snail_id)[0]
                    fee = utils.tx_fee(tx)
                    breed_fees += fee
                    print(f'bred {new_snail} from {ms, fs} for {fee}')
        finally:
            print(
                f'''
== Fees summary ==
Transfers: {transfer_fees}
Transgender: {gender_fees}
Breed: {breed_fees}
Total: {breed_fees + gender_fees + transfer_fees}
'''
            )
        return

    def _cmd_incubate_plan(self):
        snails = []
        for c in tqdm(self.clis):
            _, ss = c.cmd_incubate_fee(verbose=False)
            snails.extend((x1, x2, x3, c) for x1, x2, x3 in ss)
        print(f'\n{Fore.GREEN}== FULL PLAN =={Fore.RESET}')
        base_pc = self.main_cli.client.web3.get_current_coefficent()
        last_pc = base_pc
        total_slime = 0
        for fee, snail1, snail2, c in sorted(snails, key=lambda x: x[0]):
            new_fee = fee / base_pc * last_pc
            total_slime += fee
            print(
                f'{c._profile["_i"]}:{snail1.id}:{snail2.id} - {c.name} - {cli.GENDER_COLORS[snail1.gender]}{snail1.name_id}{Fore.RESET} P{snail1.purity} {snail1.family.gene} - {cli.GENDER_COLORS[snail2.gender]}{snail2.name_id}{Fore.RESET} P{snail2.purity} {snail2.family.gene} for {Fore.RED}{fee} / {new_fee} / {total_slime}{Fore.RESET}'
            )
            last_pc += 0.2
        return

    def cmd_tournament(self):
        if self.args.stats or self.args.preview or self.args.market:
            return False
        all_snails = defaultdict(list)
        data = None
        for c in self.clis:
            c._header()
            _, res, data = c.cmd_tournament(data=data)
            for family, snails in res.items():
                for cand in snails:
                    all_snails[family].append(cand + (c,))

        print(f'\n{Fore.GREEN}Summary for all{Fore.RESET}')
        for family, snails in all_snails.items():
            print(f'{Fore.BLUE}{family}{Fore.RESET}')
            self.main_cli.find_candidates_sorting(snails)
            for score, _, _, snail, c in snails:
                print(
                    f'{Fore.YELLOW}{score}{Fore.RESET} {snail.name_id} {Fore.YELLOW}{snail.purity_str}/{snail.level_str}{Fore.RESET} {snail.adaptations} {Fore.YELLOW}{c.name}{Fore.RESET} {c.profile_guild}'
                )

    def cmd_guild(self):
        if self.args.claim or self.args.unstake or self.args.other:
            return False
        guilds = {}
        with tqdm(self.clis, disable=self.args.verbose) as pbar:
            for c in pbar:
                if self.args.verbose:
                    c._header()
                else:
                    pbar.set_description(c.name)
                data = c.cmd_guild()
                if data:
                    data = data[1]
                    if c.profile_guild not in guilds:
                        guilds[c.profile_guild] = data
                        guilds[c.profile_guild]['members'] = []
                    if not guilds[c.profile_guild]['next_rewards'] and data['next_rewards']:
                        # in case first member did not have next_rewards but the others do :shrug:
                        guilds[c.profile_guild]['next_rewards'] = data['next_rewards']
                    guilds[c.profile_guild]['members'].append((c.name, data['rewards']))

        for k, data in guilds.items():
            print(f'{Fore.CYAN}== Guild: {k} =={Fore.RESET}')
            print(f'Level: {data["level"]}')
            _ph = data["tomato_ph"]
            _m = f'Tomato: {data["tomato"]}'
            if _ph:
                _m += f' ({Fore.GREEN}{_ph} ph{Fore.RESET})'
            print(_m)
            print(f'Lettuce: {data["lettuce"]}')
            if data['next_rewards']:
                print('Next rewards:')
                for r1, r2 in data['next_rewards']:
                    print(f' - {r1}: {r2}')
            print(f'Members: {data["member_count"]} ({data["snail_count"]} snails)')
            for m in data['members']:
                _m = f' - {m[0]}'
                if m[1]:
                    _m += f' ({Fore.GREEN}{m[1]}{Fore.RESET})'
                print(_m)

    def cmd_utils(self):
        """
        This is a multicli cmd only, not implmemented in cli ("per wallet")
        """
        m = getattr(self, f'cmd_utils_{self.args.util_cmd}')
        return m()

    @commands.util_command()
    def cmd_utils_accounts(self):
        """Just list accounts, quick function"""
        for c in self.clis:
            print(f'{c.name} - {c.profile_guild} - {c.owner}')

    @commands.argument(
        '--all',
        action='store_true',
        help='Also display duplicates with less than 3 adaptations and/or just one snail (not duplicated)',
    )
    @commands.argument(
        '--family',
        action='store_true',
        help='Compare per family (useful for guild races)',
    )
    @commands.argument(
        '--purity',
        type=int,
        help='Minimum purity to consider',
    )
    @commands.argument(
        '--same-wallet',
        action='store_true',
        help='Only report those in same wallet (useful to transfer out these conflicting ones)',
    )
    @commands.util_command()
    def cmd_utils_duplicates(self):
        """Find snails with same adaptations"""
        sa = defaultdict(list)
        for c in tqdm(self.clis):
            for _, snail in c.my_snails.items():
                if self.args.purity and snail.purity < self.args.purity:
                    continue
                k = tuple(sorted(x.id for x in snail.adaptations))
                if self.args.family:
                    k = (snail.family, k)
                sa[k].append((c, snail))

        ordered = sorted(
            ((k, len(v)) for k, v in sa.items()), key=lambda x: (x[0][0].id, x[1]) if self.args.family else x[1]
        )
        for k, _ in ordered:
            v = sa[k]
            if not self.args.family and len(k) != 3 and not self.args.all:
                continue
            if self.args.family and len(k[1]) != 3 and not self.args.all:
                continue
            if len(v) == 1 and not self.args.all:
                continue
            adapt = v[0][1].adaptations
            if self.args.same_wallet and len(set(c for c, _ in v)) == len(v):
                # none in same wallet
                continue
            if self.args.family:
                print(f'[{k[0]}] {adapt} ({len(v)}):')
            else:
                print(f'{adapt} ({len(v)}):')
            for c, snail in v:
                print(f'  {snail} ({c.name})')

    @commands.argument(
        '-f',
        '--force',
        action='store_true',
        help='Do it (only simulates without this flag)',
    )
    @commands.argument('stop', type=float, help='Stop amount that triggers transfer')
    @commands.argument('limit', type=float, help='Final balance every triggered account should have')
    @commands.util_command()
    def cmd_utils_balance_balance(self):
        """Take from the rich and give to the poor - balance wallet balances"""

        def _cb(msg):
            print(msg)

        utils.balance_balance(self.clis, self.args.limit, self.args.stop, _cb, force=self.args.force)

    @commands.argument('file', type=Path, help='CSV filename')
    @commands.util_command()
    def cmd_utils_dump_csv(self):
        """Dump all snails to CSV"""
        import csv

        with self.args.file.open('w') as _f:
            csvf = csv.writer(_f)
            csvf.writerow(
                [
                    'Snail',
                    'Family',
                    'Level',
                    'Purity',
                    'Adapt Landscape',
                    'Adapt Weather',
                    'Adapt Athletics',
                    'SB',
                    'WB',
                    'Status',
                ]
            )
            for c in self.clis:
                for snail in itertools.chain(
                    c.my_snails.values(), c.client.iterate_my_snails(c.owner, filters={'status': 5})
                ):
                    print(snail)
                    ads = snail.ordered_adaptations
                    csvf.writerow(
                        [
                            snail.name_id,
                            snail.family,
                            snail.level,
                            snail.purity,
                            ads[0],
                            ads[1],
                            ads[2],
                            snail.slime_boost,
                            snail.work_boost,
                            snail.status,
                        ]
                    )

    @commands.util_command()
    def cmd_utils_gas_price(self):
        """Print out median gas price"""
        median = self.main_cli.client.gas_price()
        print(f'Configured max fee: {self.main_cli.client.max_fee}')
        print(f'Current median fee: {median}')
        pct = median * 100 / self.main_cli.client.max_fee
        print(f'Median is {pct:.2f}% of your base fee')

    @commands.util_command()
    def cmd_utils_tour_races(self):
        """List races of ALL tournaments"""

        def _deets(data):
            print(f"Name: {data.name}")
            print(f"Registered guilds: {data.guild_count}")
            for week in data.weeks:
                print(f"Week {week.week}: {week.ordered_conditions} {week.distance}m ({week.guild_count} guilds)")

        data = self.main_cli.client.tournament(self.main_cli.owner)
        _deets(data)
        last_id = data['id']

        for nid in range(last_id - 1, 0, -1):
            data = self.main_cli.client.tournament(self.main_cli.owner, tournament_id=nid)
            _deets(data)

    @commands.util_command()
    def cmd_utils_all_adapts(self):
        """Print out all possible adaptation combinations"""
        for triplet in Adaptation.all():
            print(', '.join(map(str, triplet)))

    @commands.argument('snails', type=Path, help='file with snails list')
    @commands.argument('adapts', type=Path, help='file with adaptations summary')
    @commands.util_command()
    def cmd_utils_tmp_snails_to_boost(self):
        """Print out best snails to boost"""
        stats = [0, 0, 0, 0, 0]
        adapts = self.args.adapts.read_text().splitlines()
        ad = {}
        for adapt in adapts[1:]:
            a = adapt.split('\t')
            k, *v = a[:6]
            k = tuple(x.strip() for x in k.split(','))
            ad[k] = list(map(int, v))

        famind = ['Atlantis', 'Agate', 'Helix', 'Milk', 'Garden']

        data = self.args.snails.read_text().splitlines()
        for s in data[1:]:
            s = s.split('\t')
            if not s[0]:
                continue
            stats[0] += 1
            snail, family, lvl, purity, a1, a2, a3, *_ = s
            lvl = int(lvl)
            if lvl >= 15:
                stats[1] += 1
                continue
            if lvl < 5:
                stats[2] += 1
                continue
            stats[3] += 1
            purity = int(purity)
            find = famind.index(family)
            for ak, av in ad.items():
                ak1, ak2, ak3 = ak
                if (not a1 or a1 == ak1) and (not a2 or a2 == ak2) and (not a3 or a3 == ak3):
                    if not av[find]:
                        print(f'{snail} L{lvl} P{purity}')
                        stats[4] += 1
                        break
        print(
            f'''
Stats:
- {stats[0]} snails in file
- {stats[1]} 15+, ignored
- {stats[2]} <5, ignored
- {stats[3]} tested
- {stats[4]} printed out to boost
'''
        )

    @commands.argument('adapts', type=Path, help='file with adaptations summary')
    @commands.util_command()
    def cmd_utils_tmp_market_adapts(self):
        """Convert missing adapts TSV from excel to use after with utils_market_adapts"""
        adapts = self.args.adapts.read_text().splitlines()
        famind = ['Atlantis', 'Agate', 'Helix', 'Milk', 'Garden']

        for adapt in adapts[1:]:
            a = adapt.split('\t')
            k, *v = a[:6]
            k = k.replace(' ', '')
            for vi, vv in enumerate(v):
                if vv == '0':
                    print(f'{k},{famind[vi]}')

    @commands.util_command()
    def cmd_utils_dkron(self):
        """Print out dkron balances command"""
        for cli in self.clis:
            print(cli.owner)
        print('--hass')
        for cli in self.clis:
            print(
                f"https://hass.pis.sf/api/states/sensor.balance_snailtrail{cli._profile['_i'] if cli._profile['_i'] != 1 else ''}"
            )
        print('--hass-token "%hass token dkron jobs"')

    @commands.argument('--file', type=Path, help='Cache filename')
    @commands.argument('--save', action='store_true', help='If --file is specified, fetch snails and update it')
    @commands.util_command()
    def cmd_utils_burn_candidates(self):
        """Print out good candidates for burning based on adaptations not needed"""

        if self.args.save and not self.args.file:
            raise Exception('--save requires --file')

        snails: list[Snail] = []
        if self.args.save or not self.args.file:
            if self.args.save:
                fd = self.args.file.open('w')
            for c in tqdm(self.clis, desc='Gather all snails'):
                for snail in tqdm(
                    itertools.chain(
                        c.my_snails.values(),
                        c.client.iterate_my_snails(c.owner, filters={'status': 5}),
                    ),
                    leave=False,
                ):
                    if self.args.save:
                        fd.write(json.dumps(snail))
                        fd.write('\n')
                    snails.append(snail)
            if self.args.save:
                fd.close()
        else:
            with self.args.file.open('r') as f:
                for l in f:
                    snails.append(Snail(json.loads(l)))

        tadapts = set()

        for snail in snails:
            if snail.level < 15:
                continue
            ads = tuple([snail.family] + snail.ordered_adaptations)
            tadapts.add(ads)

        pairs = [
            (defaultdict(set), 1, 2, 3, 4),
            (defaultdict(set), 1, 3, 2, 6),
            (defaultdict(set), 2, 3, 1, 6),
        ]

        for pset, px1, px2, px3, _ in pairs:
            for x in tadapts:
                pset[str(x[0]), x[px1], x[px2]].add(x[px3])

        print('== Unique adapt pairs')

        for pset, _, _, _, pl in pairs:
            for k, v in pset.items():
                if len(v) == pl:
                    print(k)

        print('== Burn candidates based')

        for snail in snails:
            if snail.level >= 15:
                continue

            vlw = pairs[0][0].get((str(snail.family), snail.ordered_adaptations[0], snail.ordered_adaptations[1]), [])
            if len(vlw) == pairs[0][4]:
                print(f"{snail} (ticlets {snail.stats['mission_tickets']})")

            vlw = pairs[1][0].get((str(snail.family), snail.ordered_adaptations[0], snail.ordered_adaptations[2]), [])
            if len(vlw) == pairs[1][4]:
                print(f"{snail} (ticlets {snail.stats['mission_tickets']})")

            vlw = pairs[2][0].get((str(snail.family), snail.ordered_adaptations[1], snail.ordered_adaptations[2]), [])
            if len(vlw) == pairs[2][4]:
                print(f"{snail} (ticlets {snail.stats['mission_tickets']})")

    @commands.argument('snail', nargs='+', type=int, help='snail id to burn')
    @commands.util_command()
    def cmd_utils_burn_snails(self):
        """Burn these snails using scrolls (and transfers)"""
        snail_owners = {}
        owners = self.main_cli.client.snail_owners(*self.args.snail)
        for s, v in owners.items():
            c = self._cli_by_address(v)
            ss = c.my_snails[s]
            print(f'Found {ss} (🎫{ss.stats["mission_tickets"]}) in {c.name}')
            snail_owners[s] = (ss, c)

        if len(snail_owners) != len(self.args.snail):
            print('Some snails not found')
            print('Missing:', set(self.args.snail) - set(snail_owners.keys()))
            return

        totals = defaultdict(lambda: 0)
        for c in tqdm(self.clis, desc='Loading inventory'):
            for _, v in c.cmd_inventory(verbose=False).items():
                if v[0].name.startswith('Microwave Scroll'):
                    totals[c] = v

        while snail_owners:
            snail = None
            for _snail, owner in snail_owners.values():
                if owner in totals:
                    snail = _snail
                    owner = owner
                    new_owner = owner
                    break
            if snail is None:
                snail, owner = list(snail_owners.values())[0]
                new_owner = list(totals.keys())[0]

            if owner != new_owner:
                tx = owner.client.web3.transfer_snail(owner.owner, new_owner.owner, snail.id)
                fee = utils.tx_fee(tx)
                print(f'{snail} transferred from {owner.name} to {new_owner.name} for {fee}')

            tx = new_owner.client.web3.approve_all_snails_for_lab()
            if tx:
                fee = utils.tx_fee(tx)
                print(f'{c.name} approved lab for {fee}')

            self._wait_api_transfer(new_owner, snail.id)
            tx = new_owner.client.microwave_snails([snail.id], use_scroll=True)
            fee = utils.tx_fee(tx)
            print(f'{snail} burnt for {fee}')
            del snail_owners[snail.id]
            del totals[new_owner]

    @commands.argument('snail', type=int, help='Snail ID')
    @commands.util_command()
    def cmd_utils_bruteforce_test(self):
        """test bruteforce apply inventory item"""
        for c in self.clis:
            if self.args.snail in c.my_snails:
                print(f'Found in {c.name}')
                owned_scrolls = set()
                for v in c.cmd_inventory(verbose=False).values():
                    for v1 in v:
                        owned_scrolls.add(v1.id)
                for i in range(10000):
                    if i in owned_scrolls:
                        # do not use own scrolls!
                        continue
                    print(f'Testing {i}')
                    try:
                        print(c.client.apply_pressure(self.args.snail, i))
                    except cli.client.gqlclient.APIError as e:
                        print(f'fail with {e}')
                break
        return True

    @commands.argument(
        'account_id', type=commands.wallet_ext_or_int, help='Target account (to send ALL slime and to swap in)'
    )
    @commands.argument('--skip-claim', action='store_true', help='Do not claim')
    @commands.argument('--skip-transfer', action='store_true', help='Do not transfer')
    @commands.util_command()
    def cmd_utils_css(self):
        """Claim, send and swap ALL SLIME for AVAX"""
        final_c = None

        for c in self.clis:
            if c.owner == self.args.account_id.address:
                final_c = c
                break
        else:
            raise Exception('not found')

        total_fees = 0.0

        if not self.args.skip_claim:
            # claim all
            hash_queue = []
            for c in self.clis:
                h = c.client.web3.claim_rewards(wait_for_transaction_receipt=False)
                hash_queue.append((c, h))
            for c, hash in hash_queue:
                try:
                    r = c.client.web3.web3.eth.wait_for_transaction_receipt(hash, timeout=120)
                    if r.get('status') == 1:
                        bal = int(r['logs'][1]['data'], 16) / cli.DECIMALS
                        fee = utils.tx_fee(r)
                        total_fees += fee
                        print(f'Claimed {bal} on {c.name} for {fee}')
                except cli.client.web3client.exceptions.ContractLogicError as e:
                    pass

        if not self.args.skip_transfer:
            # send all to swap account
            hash_queue = []
            for c in self.clis:
                if c.owner == final_c.owner:
                    continue
                bal = c.client.web3.balance_of_slime(raw=True)
                if bal:
                    h = c.client.web3.transfer_slime(final_c.owner, bal, wait_for_transaction_receipt=False)
                    hash_queue.append((c, h))
            for c, hash in hash_queue:
                try:
                    r = c.client.web3.web3.eth.wait_for_transaction_receipt(hash, timeout=120)
                    if r.get('status') == 1:
                        if len(r['logs']) > 1:
                            logger.error('weird tx data: %s', r)
                            bal = 0
                        else:
                            bal = int(r['logs'][0]['data'], 16) / cli.DECIMALS
                        fee = utils.tx_fee(r)
                        total_fees += fee
                        print(f'Sent {bal} from {c.name} for {fee}')
                except cli.client.web3client.exceptions.ContractLogicError as e:
                    pass

        balance = final_c.client.web3.balance_of_slime(raw=True)
        out_min = final_c.client.web3.swap_slime_avax(amount_in=balance, preview=True)
        print(f'Swapping {balance / cli.DECIMALS} SLIME for (at least) {out_min / cli.DECIMALS} AVAX')

        tx = final_c.client.web3.swap_slime_avax(amount_in=balance, amount_out=out_min)
        fee = utils.tx_fee(tx)
        total_fees += fee
        print(f'Swapped for {fee}')
        print(f'Total fees: {total_fees}')

    @commands.argument('snail', type=int, help='Snail ID')
    @commands.argument('--exclude', type=float, action='append', help='Exclude scrolls with these coefs')
    @commands.argument('--include', type=float, action='append', help='Only include scrolls with these coefs')
    @commands.util_command()
    def cmd_utils_boost_snail(self):
        """
        Apply all slime boosts to this snail (transferring snail around)
        """
        owner_c = None
        snail = None
        owners = self.main_cli.client.snail_owners(self.args.snail)
        if not owners:
            print('Snail not found')
            return

        owner_c = self._cli_by_address(owners[self.args.snail])
        snail = owner_c.my_snails[self.args.snail]
        print(f'Found snail in {owner_c.name}')

        totals = defaultdict(lambda: 0)
        for c in tqdm(self.clis, desc='Loading inventory'):
            for _, v in c.cmd_inventory(verbose=False).items():
                if v[0].name.startswith('Slime Boost '):
                    if self.args.exclude and v[0].coef in self.args.exclude:
                        continue
                    if self.args.include and v[0].coef not in self.args.include:
                        continue
                    totals[c] = v

        prev_c = owner_c
        while totals:
            c = list(totals.keys())[0] if owner_c not in totals else owner_c
            if prev_c != c:
                tx = prev_c.client.web3.transfer_snail(prev_c.owner, c.owner, self.args.snail)
                fee = utils.tx_fee(tx)
                print(f'{snail} transferred from {prev_c.name} to {c.name} for {fee}')

            for v in totals[c]:
                # try a few times
                for _ in range(30):
                    try:
                        r = c.client.apply_pressure(self.args.snail, v.id)
                        if not 'changes' in r:
                            raise Exception('Unexpected reply', r)
                        for chg in r['changes']:
                            print(f'{snail} slime boost changed to {chg["_from"]}')
                        break
                    except cli.client.gqlclient.APIError as e:
                        if 'You are not the holder of Snail' not in str(e):
                            raise
                        print('.', end='', flush=True)
                        time.sleep(0.5)
                else:
                    raise Exception('too many retries, not the holder?!')

            del totals[c]
            prev_c = c

    @commands.argument('snail', type=int, help='Snail ID')
    @commands.util_command()
    def cmd_utils_xpboost_snail(self):
        """
        Apply one double XP boost scroll to this snail (transferring snail, if needed)
        """
        owner_c = None
        snail = None
        owners = self.main_cli.client.snail_owners(self.args.snail)
        if not owners:
            print('Snail not found')
            return

        owner_c = self._cli_by_address(owners[self.args.snail])
        snail = owner_c.my_snails[self.args.snail]
        print(f'Found snail in {owner_c.name}')

        items = owner_c.cmd_inventory(verbose=False).values()
        found = None
        for v in items:
            if v[0].name.startswith('Double XP Boost'):
                found = owner_c
                break

        if not found:
            for c in tqdm(self.clis, desc='Loading inventory'):
                for v in c.cmd_inventory(verbose=False).values():
                    if v[0].name.startswith('Double XP Boost'):
                        found = c
                        break
                if found:
                    break

        if found != owner_c:
            tx = owner_c.client.web3.transfer_snail(owner_c.owner, found.owner, self.args.snail)
            fee = utils.tx_fee(tx)
            print(f'{snail} transferred from {owner_c.name} to {found.name} for {fee}')

        # try a few times
        for _ in range(30):
            try:
                r = found.client.apply_pressure(self.args.snail, v[0].id)
                if not 'changes' in r:
                    raise Exception('Unexpected reply', r)
                for chg in r['changes']:
                    print(f'{snail} xp boost applied: {chg}')
                break
            except cli.client.gqlclient.APIError as e:
                if 'You are not the holder of Snail' not in str(e):
                    raise
                print('.', end='', flush=True)
                time.sleep(0.5)
        else:
            raise Exception('too many retries, not the holder?!')

        if found != owner_c:
            tx = found.client.web3.transfer_snail(found.owner, owner_c.owner, self.args.snail)
            fee = utils.tx_fee(tx)
            print(f'{snail} transferred from {found.name} to {owner_c.name} for {fee}')

    @commands.argument('-t', '--tournament', action='store_true', help='Also include tournament adapts to search for')
    @commands.argument(
        '-m',
        '--missing',
        action='store_true',
        help='Also include adaptation triplets that do not exist in these wallets/accounts',
    )
    @commands.argument(
        '--file',
        action='store_true',
        help='Read adaptations from file instead of argv',
    )
    @commands.argument(
        'adaptations',
        nargs='*',
        help='Adaptation combo to look for, comma-separated: Desert,Hot,Slide. Optionally, add family: Desert,Hot,Slide,Garden',
    )
    @commands.util_command()
    def cmd_utils_market_adapts(self):
        """
        Search market for snails that match these adaptations
        """
        conditions = {}

        if self.args.tournament:
            data = self.main_cli.client.tournament(self.main_cli.owner)
            for week in data.weeks:
                conditions[tuple(week.ordered_conditions)] = ('t', week.week)

        if self.args.missing:
            all_adapts = {x for x in Adaptation.all()}
            owned_adapts = defaultdict(lambda: set())
            for c in tqdm(self.clis, desc='Loading snails'):
                for snail in itertools.chain(
                    c.my_snails.values(), c.client.iterate_my_snails(c.owner, filters={'status': 5})
                ):
                    if snail.level < 15:
                        continue
                    owned_adapts[snail.family].add(tuple(snail.ordered_adaptations))
            family_condition = defaultdict(lambda: set())
            for family, adapts in owned_adapts.items():
                missing = all_adapts - adapts
                for adapt in missing:
                    family_condition[adapt].add(family)
            for adapt, families in family_condition.items():
                if adapt in conditions:
                    print('TRIPLET OVERLAP', adapt)
                    return
                conditions[adapt] = ('f', families)

        if self.args.file:
            adapt_list = Path(self.args.adaptations[0]).read_text().splitlines()
        else:
            adapt_list = self.args.adaptations

        fam_included = adapt_list[0].count(',') > 2
        if fam_included:
            family_condition = defaultdict(lambda: set())
            for adapt in adapt_list:
                c = tuple(adapt.split(','))
                k1 = c[:3]
                k2 = Family.from_str(c[3])
                family_condition[tuple(k1)].add(k2)
            for adapt, families in family_condition.items():
                if adapt in conditions:
                    print('TRIPLET OVERLAP', adapt)
                    return
                conditions[adapt] = ('f', families)
        else:
            for adapt in adapt_list:
                c = tuple(adapt.split(','))
                if c in conditions:
                    print('TRIPLET OVERLAP', c)
                    return
                conditions[c] = ('m',)

        if not conditions:
            print('Please specify SOME adaptations (or one of the flags)')
            return

        for snail, score, w in self.main_cli._bot_tournament_market_search(conditions):
            place = '🥇🥈🥉'[score - 1]
            if w[0] == 'm':
                print(f'{place} {snail} {snail.ordered_adaptations} - {snail.market_price} 🔺')
            elif w[0] == 't':
                print(f'{place} Week {w[1]} - {snail} - {snail.market_price} 🔺')
            elif w[0] == 'f':
                if snail.family in w[1]:
                    print(f'{place} {snail} {snail.ordered_adaptations} - {snail.market_price} 🔺')
            else:
                print(f'{place} UNK - {snail} - {snail.market_price} 🔺')

    def cmd_snails(self):
        """re-implement to handle transfers more efficiently"""
        if self.args.transfer is None:
            return False
        transfer_wallet, transfer_snails = self.args.transfer
        owners = self.main_cli.client.snail_owners(*transfer_snails)
        done = set()
        r = True
        for _, v in owners.items():
            if v in done:
                continue
            done.add(v)
            cli = self._cli_by_address(v)
            cli._header()
            r = cli.cmd_snails_transfer()

        # only wait for snails if ALL were transferred...
        if not r:
            cli = self._cli_by_address(transfer_wallet.address)
            if cli is not None:
                self._wait_api_transfer(cli, *owners.keys())

    def run(self):
        if not self.args.cmd:
            return

        try:
            if self.is_multi or not hasattr(cli.CLI, f'cmd_{self.args.cmd}'):
                m = getattr(self, f'cmd_{self.args.cmd}', None)
                if m is not None:
                    r = m()
                    if r is not False:
                        return r

            for c in self.clis:
                r = c.run()
                if r is False:
                    # do not process any other clis
                    return
        except KeyboardInterrupt:
            logger.info('Stopping...')
