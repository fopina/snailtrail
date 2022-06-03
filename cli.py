import logging
from operator import sub
import os
import argparse
from snail import proxy, client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CLI:
    client = None
    owner = None

    def __init__(self, client):
        self.client = client

    def find_female_snails(self):
        all_snails = []
        for snail in self.client.iterate_all_snails_marketplace():
            if snail['market']['price'] > 2:
                break
            all_snails.append(snail)

        cycle_end = []
        for snail in all_snails:
            if snail['gender']['id'] == 1:
                if snail['breeding']['breed_status'] and snail['breeding']['breed_status']['cycle_remaining'] > 0:
                    print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'])
                else:
                    cycle_end.append(snail)

        cycle_end.sort(key=lambda snail:snail['breeding']['breed_status']['cycle_end'])

        for snail in cycle_end:
            print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'], snail['breeding']['breed_status']['cycle_end'])
    
    def list_owned_snails(self):
        for snail in self.client.iterate_all_snails(filters={'owner': self.owner}):
            print(snail)

    def list_missions(self):
        for x in self.client.iterate_mission_races(filters={'owner': self.owner}):
            if not x:
                # TODO: remove this after fixing "own" / check if "participation" means own...?
                continue
            del x['__typename']
            del x['distance']
            x['athletes'] = len(x['athletes'])
            print(x)

    def _read_conf(self):
        with open('owner.conf') as f:
            return f.read().strip()

    def run(self, args):
        self.owner = args.owner or self._read_conf()
        if args.cmd == 'missions':
            self.list_missions()
        elif args.cmd == 'snails':
            if args.females:
                self.find_female_snails()
            elif args.mine:
                self.list_owned_snails()


def build_parser():
    parser = argparse.ArgumentParser(prog=__name__)
    parser.add_argument('--owner', type=str, help='owner wallet (used for some filters/queries)')
    subparsers = parser.add_subparsers(title='commands', dest='cmd')
    subparsers.add_parser('missions')
    p = subparsers.add_parser('snails')
    p.add_argument('-m', '--mine', action='store_true', help='show owned')
    p.add_argument('-f', '--females', action='store_true', help='breeders in marketplace')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    logger.info('starting proxy')
    use_upstream_proxy = os.getenv('http_proxy') or os.getenv('https_proxy')
    if use_upstream_proxy:
        use_upstream_proxy = use_upstream_proxy.split('://')[-1]
        logger.warning('(upstream proxy %s)', use_upstream_proxy)
    p = proxy.Proxy(upstream_proxy=use_upstream_proxy)
    p.start()
    logger.info('proxy ready on %s', p.url())
    try:
        CLI(client.Client(proxy=p.url())).run((args))
    finally:
        p.stop()


if __name__ == '__main__':
    main()
