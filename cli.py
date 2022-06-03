from snail import proxy, client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_snails(client):
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


def _main(client):
    find_snails(client)


def main():
    logger.info('starting proxy')
    p = proxy.Proxy()
    p.start()
    logger.info('proxy ready on %s', p.url())
    try:
        _main(client.Client(proxy=p.url()))
    finally:
        p.stop()



if __name__ == '__main__':
    main()
