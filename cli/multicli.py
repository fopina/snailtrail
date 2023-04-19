import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List
from colorama import Fore

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
        for _ind, w in enumerate(wallets):
            c = cli.CLI(
                w, proxy_url, args, main_one=first_one, graphql_endpoint=args.graphql_endpoint, name=str(_ind + 1)
            )
            first_one = False
            args.notify.register_cli(c)
            self.clis.append(c)

        # get proper profile info
        profiles = [c.owner for c in self.clis]
        data = self.clis[0].client.gql.profile(profiles)
        for i, c in enumerate(self.clis):
            u = data[f'profile{i}']['username']
            if u[:5] != c.owner[:5]:
                c._name = str(i + 1) + ' ' + u

    @property
    def is_multi(self) -> bool:
        return len(self.clis) > 1

    def cmd_bot(self):
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

        for c in self.clis:
            cs = c.client.web3.claimable_slime()
            bs = c.client.web3.balance_of_slime()
            cw = c.client.web3.claimable_wavax()
            bw = c.client.web3.balance_of_wavax()
            ba = c.client.web3.get_balance()
            bn = c.client.web3.balance_of_snails()
            totals[0] += cs + bs
            totals[1] += cw + bw + ba
            totals[2] += bn
            print(f'{Fore.CYAN}== {c.name}{Fore.RESET} ==')
            print(
                f'''\
SLIME: {c.client.web3.claimable_slime()} / {c.client.web3.balance_of_slime():.3f}
WAVAX: {c.client.web3.claimable_wavax()} / {c.client.web3.balance_of_wavax()}
AVAX: {c.client.web3.get_balance():.3f} / SNAILS: {c.client.web3.balance_of_snails()}'''
            )
        print(f'{Fore.CYAN}== TOTAL{Fore.RESET} ==')
        print(
            f'''\
SLIME: {totals[0]:.3f}
AVAX: {totals[1]:.3f}
SNAILS: {totals[2]}'''
        )

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
