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

from snail.gqltypes import Adaptation, Snail

from . import cli, commands, utils

logger = logging.getLogger(__name__)


class MultiCLI:
    """
    Wrapper of CLI objects to control multiple wallets
    """

    def __init__(
        self,
        wallets: List[cli.Wallet],
        proxy_url: str,
        args: argparse.Namespace,
    ):
        self.clis: list[cli.CLI] = []
        self.args = args

        first_one = True if len(wallets) > 1 else None
        for w in wallets:
            if w is None:
                continue
            c = cli.CLI(w, proxy_url, args, main_one=first_one, graphql_endpoint=args.graphql_endpoint)
            first_one = False
            args.notify.register_cli(c)
            self.clis.append(c)

        # get original indices (so they remain constant in the name)
        # as "active" wallets might be restricted using -a flag
        wallet_indices = {w.address: i + 1 for i, w in enumerate(self.args.wallet) if w is not None}

        # get proper profile info
        if self.main_cli:
            profiles = [c.owner for c in self.clis]
            data = self.main_cli.client.gql.profile(profiles)
            for i, c in enumerate(self.clis):
                c._profile = data[f'profile{i}']
                c._profile['_i'] = wallet_indices[c.owner]

    @property
    def is_multi(self) -> bool:
        return len(self.clis) > 1

    @property
    def main_cli(self) -> cli.CLI:
        if self.clis:
            return self.clis[0]
        return None

    def cmd_bot(self):
        # disable tournament check in all accounts with repeated guilds
        # no need to notify wins for the same guild :D
        guilds = set()
        for c in self.clis:
            if c.profile_guild and c.profile_guild in guilds:
                c._bot_tournament = lambda: None
            guilds.add(c.profile_guild)

        c = self.clis[0]
        c.load_bot_settings()

        # this cmd is special as it should loop infinitely
        self.args.notify.start_polling()

        cli_waits = {}
        try:
            self.clis[0].cmd_bot_greet()
            while True:
                now = datetime.now(tz=timezone.utc)
                for c in self.clis:
                    if c.owner in cli_waits and now < cli_waits[c.owner]:
                        continue
                    w = c.cmd_bot_tick()
                    cli_waits[c.owner] = now + timedelta(seconds=w)
                wf = min(list(cli_waits.values()))
                time.sleep((wf - now).total_seconds())
        except KeyboardInterrupt:
            logger.info('Stopping...')
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
            # validate
            plan = [list(map(int, l.split(' ')[0].split(':'))) for l in self.args.execute.read_text().splitlines()]

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
            if fail:
                raise Exception('incomplete plan')
            for k, v in females.items():
                if v != 1:
                    print(f'female {k} has {v} breeds')
                    fail = True
            if fail:
                raise Exception('incomplete plan')

            # transgender plan
            done = set()

            def _transgender(c, snail, gender):
                fee = 0
                if snail not in done:
                    tx = c.client.web3.set_snail_gender(snail, gender.value)
                    if tx:
                        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                        print(f'{snail} changed gender to {gender} for {fee}')
                    done.add(snail)
                return fee

            acc_indices = {c._profile['_i']: _i for _i, c in enumerate(self.clis)}
            # regroup per account
            new_plan = {}
            # reversed would be more profitable (more expensive first) but if it runs out of funds
            # the cheapest are not processed...
            for p in plan:
                if p[0] not in new_plan:
                    new_plan[p[0]] = []
                new_plan[p[0]].append(p[1:])

            # approve incubator
            for acc in tqdm(new_plan, desc='Approve incubator'):
                c = self.clis[acc_indices[acc]]
                tx = c.client.web3.approve_slime_for_incubator()
                if tx:
                    fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                    print(f'{c.name} approved incubator for {fee}')

            def retriable_breed(c, fs, ms):
                _r = None
                for _ in range(60):
                    try:
                        return c.client.breed_snails(fs, ms)
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

            try:
                for acc, acc_plan in new_plan.items():
                    c = self.clis[acc_indices[acc]]
                    if last_client is not None and last_client != c:
                        last_client.cmd_balance_transfer(c.owner)
                    last_client = c
                    for ms, fs, *rest in acc_plan:
                        if rest:
                            print(f'Skipping {ms, fs}')
                            continue
                        # transgender
                        fee = _transgender(c, ms, cli.Gender.MALE)
                        gender_fees += fee
                        fee = _transgender(c, fs, cli.Gender.FEMALE)
                        gender_fees += fee
                        # get coefficient just for displaying
                        coef = c.client.web3.get_current_coefficent()
                        print(f'breeding {ms, fs} (with coeff {coef})...')
                        tx = retriable_breed(c, fs, ms)
                        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                        breed_fees += fee
                        print(f'bred {ms, fs} for {fee}')
            finally:
                print(
                    f'''
== Fees summary ==
Transgender: {gender_fees}
Breed: {breed_fees}
Total: {breed_fees + gender_fees}
'''
                )
            return
        if self.args.fee is not None and self.args.plan:
            snails = []
            for c in self.clis:
                _, ss = c.run()
                snails.extend((x1, x2, x3, c) for x1, x2, x3 in ss)
            print(f'\n{Fore.GREEN}== FULL PLAN =={Fore.RESET}')
            for fee, snail1, snail2, c in sorted(snails, key=lambda x: x[0]):
                print(
                    f'{c._profile["_i"]}:{snail1.id}:{snail2.id} - {c.name} - {cli.GENDER_COLORS[snail1.gender]}{snail1.name_id}{Fore.RESET} P{snail1.purity} {snail1.family.gene} - {cli.GENDER_COLORS[snail2.gender]}{snail2.name_id}{Fore.RESET} P{snail2.purity} {snail2.family.gene} for {Fore.RED}{fee}{Fore.RESET}'
                )
            return
        return False

    def cmd_tournament(self):
        if self.args.stats or self.args.preview:
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
                    f'{Fore.YELLOW}{score}{Fore.RESET} {snail.name} {Fore.YELLOW}{snail.purity_str}/{snail.level_str}{Fore.RESET} {snail.adaptations} {Fore.YELLOW}{c.name}{Fore.RESET} {c.profile_guild}'
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
                        ]
                    )

    @commands.util_command()
    def cmd_utils_gas_price(self):
        """Print out median gas price"""
        median = self.main_cli.client.gas_price() / 1000000000
        print(f'Configured base fee: {self.args.web3_base_fee}')
        print(f'Current median fee: {median}')
        pct = median * 100 / self.args.web3_base_fee
        print(f'Median is {pct:.2f}% of your base fee')

    @commands.util_command()
    def cmd_utils_all_adapts(self):
        """Print out all possible adaptation combinations"""
        adapt_types = [[], [], []]

        for x in Adaptation:
            if x.is_landscape():
                adapt_types[0].append(x)
            elif x.is_weather():
                adapt_types[1].append(x)
            else:
                adapt_types[2].append(x)

        for a in adapt_types[0]:
            for b in adapt_types[1]:
                for c in adapt_types[2]:
                    x = ', '.join(map(str, [a, b, c]))
                    print(x)

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
                print(snail)

            vlw = pairs[1][0].get((str(snail.family), snail.ordered_adaptations[0], snail.ordered_adaptations[2]), [])
            if len(vlw) == pairs[1][4]:
                print(snail)

            vlw = pairs[2][0].get((str(snail.family), snail.ordered_adaptations[1], snail.ordered_adaptations[2]), [])
            if len(vlw) == pairs[2][4]:
                print(snail)

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
                        fee = r['gasUsed'] * r['effectiveGasPrice'] / cli.DECIMALS
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
                        fee = r['gasUsed'] * r['effectiveGasPrice'] / cli.DECIMALS
                        total_fees += fee
                        print(f'Sent {bal} from {c.name} for {fee}')
                except cli.client.web3client.exceptions.ContractLogicError as e:
                    pass

        balance = final_c.client.web3.balance_of_slime(raw=True)
        out_min = final_c.client.web3.swap_slime_avax(amount_in=balance, preview=True)
        print(f'Swapping {balance / cli.DECIMALS} SLIME for (at least) {out_min / cli.DECIMALS} AVAX')

        tx = final_c.client.web3.swap_slime_avax(amount_in=balance, amount_out=out_min)
        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
        total_fees += fee
        print(f'Swapped for {fee}')
        print(f'Total fees: {total_fees}')

    @commands.argument('snail', type=int, help='Snail ID')
    @commands.util_command()
    def cmd_utils_boost_snail(self):
        """
        Apply all slime boosts to this snail (transferring snail around)
        """
        owner_c = None
        snail = None

        for c in tqdm(self.clis, desc='Searching snail'):
            if self.args.snail in c.my_snails:
                owner_c = c
                snail = c.my_snails[self.args.snail]
                break
        else:
            print('Snail not found')
            return
        print(f'Found snail in {c.name}')

        totals = defaultdict(lambda: 0)
        for c in tqdm(self.clis, desc='Loading inventory'):
            for _, v in c.cmd_inventory(verbose=False).items():
                if v[0].name.startswith('Slime Boost '):
                    totals[c] = v

        prev_c = owner_c
        while totals:
            c = list(totals.keys())[0] if owner_c not in totals else owner_c
            if prev_c != c:
                tx = prev_c.client.web3.transfer_snail(prev_c.owner, c.owner, self.args.snail)
                fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                print(f'{snail} transferred from {prev_c.name} to {c.name} for {fee}')

            for v in totals[c]:
                # try a few times
                for _ in range(15):
                    try:
                        r = c.client.apply_pressure(self.args.snail, v.id)
                        if not 'changes' in r:
                            raise Exception('Unexpected reply', r)
                        for chg in r['changes']:
                            print(f'{snail} slime boost changed from {chg["_from"]} to {chg["_to"]}')
                        break
                    except cli.client.gqlclient.APIError as e:
                        if 'You are not the holder of Snail' not in str(e):
                            raise
                        print('Retrying...')
                        time.sleep(0.5)
                else:
                    raise Exception('too many retries, not the holder?!')

            del totals[c]
            prev_c = c

    def run(self):
        if not self.args.cmd:
            return

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
