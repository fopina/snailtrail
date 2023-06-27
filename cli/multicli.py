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

    clis: list[cli.CLI]

    def __init__(
        self,
        wallets: List[cli.Wallet],
        proxy_url: str,
        args: argparse.Namespace,
    ):
        self.clis = []
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
        if self.args.tournament:
            # disable check in all accounts with repeated guilds
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
        if self.args.fee is not None and self.args.plan:
            snails = []
            for c in self.clis:
                _, ss = c.run()
                snails.extend((x1, x2, x3, c) for x1, x2, x3 in ss)
            print(f'\n{Fore.GREEN}== FULL PLAN =={Fore.RESET}')
            for fee, snail1, snail2, c in sorted(snails, key=lambda x: x[0]):
                print(
                    f'{c.name} - {cli.GENDER_COLORS[snail1.gender]}{snail1.name_id}{Fore.RESET} {snail1.family.gene} - {cli.GENDER_COLORS[snail2.gender]}{snail2.name_id}{Fore.RESET} {snail2.family.gene} for {Fore.RED}{fee}{Fore.RESET}'
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
            snails.sort(key=lambda x: x[0], reverse=True)
            for score, snail, c in snails:
                print(
                    f'{Fore.YELLOW}{score}{Fore.RESET} {snail.name} {Fore.YELLOW}{snail.purity_str}/{snail.level_str}{Fore.RESET} {snail.adaptations} {Fore.YELLOW}{c.name}{Fore.RESET} {c.profile_guild}'
                )

    def cmd_guild(self):
        if self.args.claim or self.args.unstake:
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
                    guilds[c.profile_guild]['members'].append((c.name, data['sink_reward']))

        for k, data in guilds.items():
            print(f'{Fore.CYAN}== Guild: {k} =={Fore.RESET}')
            print(f'Level: {data["level"]}')
            _ph = data["tomato_ph"]
            _m = f'Tomato: {data["tomato"]}'
            if _ph:
                _m += f' ({Fore.GREEN}{_ph} ph{Fore.RESET})'
            print(_m)
            print(f'Lettuce: {data["lettuce"]}')
            print(f'Members: {data["member_count"]} ({data["snail_count"]} snails)')
            for m in data['members']:
                _m = f' - {m[0]}'
                if m[1]:
                    _m += f' ({Fore.GREEN}{m[1]} TMT{Fore.RESET})'
                print(_m)

    def cmd_utils(self):
        """
        This is a multicli cmd only, not implmemented in cli ("per wallet")
        """
        m = getattr(self, f'cmd_utils_{self.args.util_cmd}')
        return m()

    def cmd_utils_accounts(self):
        for c in self.clis:
            print(c.name)

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
        if donor[0] - self.args.limit < total_transfer:
            print(f'Donor has not enough balance: {total_transfer} required but only {donor[0]} available')
            return
        for p in poor:
            print(f'{donor[1].name} to {p[2].name}: {p[1]}')
            if self.args.force:
                tx = donor[1].client.web3.transfer(p[2].owner, p[1])
                fee = tx['gasUsed'] * tx['effectiveGasPrice'] / cli.DECIMALS
                print(f'> fee: {fee}')

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
