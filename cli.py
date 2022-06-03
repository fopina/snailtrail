import logging
import os
from urllib.parse import uses_fragment
from snail import proxy, client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OWNER = '0x76e83242f3294E1EB64D7F4b8645C50b63bd767e'


def find_female_snails(client):
    all_snails = []
    for snail in client.iterate_all_snails():
        if snail['market']['price'] > 2:
            break
        all_snails.append(snail)

    cycle_end = []
    for snail in all_snails:
        if snail['gender']['id'] == 1:
            if snail['breeding']['breed_status']['cycle_remaining'] > 0:
                print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'])
            else:
                cycle_end.append(snail)

    cycle_end.sort(key=lambda snail:snail['breeding']['breed_status']['cycle_end'])

    for snail in cycle_end:
        print(f'https://www.snailtrail.art/snails/{snail["id"]}/snail', snail['market']['price'], snail['breeding']['breed_status']['cycle_end'])


def list_missions(client):
    for x in client.iterate_mission_races(filters={'owner': OWNER}):
        print(x)


def _main(client):
    # find_female_snails(client)
    list_missions(client)


def main():
    logger.info('starting proxy')
    use_upstream_proxy = os.getenv('http_proxy') or os.getenv('https_proxy')
    if use_upstream_proxy:
        use_upstream_proxy = use_upstream_proxy.split('://')[-1]
        logger.warning('(upstream proxy %s)', use_upstream_proxy)
    p = proxy.Proxy(upstream_proxy=use_upstream_proxy)
    p.start()
    logger.info('proxy ready on %s', p.url())
    try:
        _main(client.Client(proxy=p.url()))
    finally:
        p.stop()


if __name__ == '__main__':
    main()
