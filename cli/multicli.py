import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import List
from colorama import Fore
from tqdm import tqdm

from . import cli

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
            c = cli.CLI(w, proxy_url, args, main_one=first_one, graphql_endpoint=args.graphql_endpoint)
            first_one = False
            args.notify.register_cli(c)
            self.clis.append(c)

        # get original indices (so they remain constant in the name)
        # as "active" wallets might be restricted using -a flag
        wallet_indices = {w.address: i + 1 for i, w in enumerate(self.args.wallet)}

        # get proper profile info
        profiles = [c.owner for c in self.clis]
        data = self.clis[0].client.gql.profile(profiles)
        for i, c in enumerate(self.clis):
            c._profile = data[f'profile{i}']
            c._profile['_i'] = wallet_indices[c.owner]

    @property
    def is_multi(self) -> bool:
        return len(self.clis) > 1

    @property
    def main_cli(self) -> cli.CLI:
        return self.clis[0]

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
                if snail not in done:
                    tx = c.client.web3.set_snail_gender(snail, gender.value)
                    if tx:
                        fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                        print(f'{snail} changed gender to {gender} for {fee}')
                    done.add(snail)

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
                c = self.clis[acc - 1]
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
                        if not 'Protocol coefficent changed' in str(e):
                            raise
                        time.sleep(1)
                        _r = e
                raise _r

            last_client = None
            for acc, acc_plan in new_plan.items():
                c = self.clis[acc - 1]
                if last_client is not None and last_client != c:
                    last_client.cmd_balance_transfer(c.owner)
                last_client = c
                for ms, fs, *rest in acc_plan:
                    if rest:
                        print(f'Skipping {ms, fs}')
                        continue
                    # transgender
                    _transgender(c, ms, cli.Gender.MALE)
                    _transgender(c, fs, cli.Gender.FEMALE)
                    print(f'breeding {ms, fs}...')
                    tx = retriable_breed(c, fs, ms)
                    fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                    print(f'bred {ms, fs} for {fee}')
            return
        if self.args.fee is not None and self.args.plan:
            snails = []
            for c in self.clis:
                _, ss = c.run()
                snails.extend((x1, x2, x3, c) for x1, x2, x3 in ss)
            print(f'\n{Fore.GREEN}== FULL PLAN =={Fore.RESET}')
            for fee, snail1, snail2, c in sorted(snails, key=lambda x: x[0]):
                print(
                    f'{c._profile["_i"]}:{snail1.id}:{snail2.id} - {c.name} - {cli.GENDER_COLORS[snail1.gender]}{snail1.name_id}{Fore.RESET} {snail1.family.gene} - {cli.GENDER_COLORS[snail2.gender]}{snail2.name_id}{Fore.RESET} {snail2.family.gene} for {Fore.RED}{fee}{Fore.RESET}'
                )
            return
        return False

    def cmd_tournament(self):
        if self.args.stats:
            return False
        all_snails = defaultdict(list)
        data = None
        for c in self.clis:
            c._header()
            _, res, data = c.cmd_tournament(data=data)
            for family, snails in res.items():
                for score, snail in snails:
                    all_snails[family].append((score, snail, c))

        print(f'\n{Fore.GREEN}Summary for all{Fore.RESET}')
        for family, snails in all_snails.items():
            print(f'{Fore.BLUE}{family}{Fore.RESET}')
            # sort according to https://docs.snailtrail.art/racing/speed/
            snails.sort(key=lambda x: (x[0], int(x[1].purity), int(x[1].level)), reverse=True)
            for score, snail, c in snails:
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

    def cmd_utils_accounts(self):
        for c in self.clis:
            print(f'{c.name} - {c.owner}')

    def cmd_utils_duplicates(self):
        sa = defaultdict(list)
        for c in self.clis:
            for _, snail in c.my_snails.items():
                k = tuple(sorted(x.id for x in snail.adaptations))
                sa[k].append((c, snail))
        ordered = sorted(((k, len(v)) for k, v in sa.items()), key=lambda x: x[1])
        for k, _ in ordered:
            v = sa[k]
            if len(k) != 3 and not self.args.all:
                continue
            if len(v) == 1 and not self.args.all:
                continue
            adapt = v[0][1].adaptations
            print(f'{adapt} ({len(v)}):')
            for c, snail in v:
                print(f'  {snail.name} {c.name}')

    def cmd_utils_balance_balance(self):
        if self.args.limit <= self.args.stop:
            raise Exception('stop must be lower than limit')
        balances = []
        for c in self.clis:
            balances.append((c.client.web3.get_balance(), c))
        balances.sort(key=lambda x: x[0], reverse=True)
        donor: tuple[float, cli.CLI] = balances[0]
        poor: list[tuple[float, cli.CLI]] = [(x, self.args.limit - x, z) for (x, z) in balances if x < self.args.stop]
        total_transfer = sum(y for _, y, _ in poor)
        total_fees = 0
        if donor[0] - self.args.limit < total_transfer:
            print(f'Donor has not enough balance: {total_transfer} required but only {donor[0]} available')
            return
        for p in poor:
            print(f'{donor[1].name} to {p[2].name}: {p[1]}')
            if self.args.force:
                tx = donor[1].client.web3.transfer(p[2].owner, p[1])
                fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                total_fees += fee
                print(f'> fee: {fee}')
        print(f'> Total transfer: {total_transfer}')
        if total_fees:
            print(f'> Total fees: {total_fees}')

    def cmd_utils_bruteforce_test(self):
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

    def cmd_utils_css(self):
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

    def cmd_utils_boost_snail(self):
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

        if self.is_multi:
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
