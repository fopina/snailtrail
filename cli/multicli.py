import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List

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

    def cmd_bot(self):
        for c in self.clis:
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

    def run(self):
        if not self.args.cmd:
            return
        m = getattr(self, f'cmd_{self.args.cmd}', None)
        if m is not None:
            return m()

        for c in self.clis:
            r = c.run()
            if r is False:
                # do not process any other clis
                return
