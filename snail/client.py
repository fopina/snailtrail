from enum import Enum
from typing import Generator

from . import gqlclient, gqltypes, web3client


class League(int, Enum):
    GOLD = 5
    PLATINUM = 6
    TOURNAMENT = 10


class ClientError(Exception):
    """Client raised error"""

    def __str__(self) -> str:
        return super().__str__()


class RequiresTransactionClientError(ClientError):
    """
    Client raised error when action requires transaction

    >>> e = RequiresTransactionClientError('requires_transaction')
    >>> str(e)
    'requires_transaction'
    >>> e = RequiresTransactionClientError('requires_transaction', {'x': 1})
    >>> str(e)
    'requires_transaction (size: ?)'
    >>> e = RequiresTransactionClientError('requires_transaction', {'payload': {'size': 2}})
    >>> str(e)
    'requires_transaction (size: 2)'
    """

    def __str__(self) -> str:
        if len(self.args) > 1:
            size = self.args[1].get('payload', {}).get('size', '?')
            return f'{self.args[0]} (size: {size})'
        return self.args[0]


class Client:
    def __init__(
        self,
        http_token=None,
        proxy=None,
        wallet=None,
        private_key=None,
        web3_provider=None,
        web3_provider_class=None,
        rate_limiter=None,
        gql_retry=None,
    ):
        self.gql = gqlclient.Client(http_token=http_token, proxy=proxy, rate_limiter=rate_limiter, retry=gql_retry)
        if wallet and private_key and web3_provider:
            self.web3 = web3client.Client(wallet, private_key, web3_provider, web3_provider_class=web3_provider_class)

    def _iterate_pages(self, method, key, klass=None, args=None, kwargs=None, max_calls=None):
        args = args or []
        kwargs = kwargs or {}
        c = 0
        calls = 0
        while True:
            kwargs['offset'] = c
            objs = method(*args, **kwargs)
            if not objs[key]:
                break
            total = objs.get('count')
            _r = map(klass, objs[key]) if klass else objs[key]
            yield from _r
            c += len(objs[key])
            if total is not None and c >= total:
                break
            calls += 1
            if max_calls and calls >= max_calls:
                break

    def iterate_all_genes_marketplace(self, filters={}) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_all_genes_marketplace, 'snails', klass=gqltypes.Snail, kwargs={'filters': filters}
        )

    def iterate_all_snails_marketplace(self, filters={}) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_all_snails_marketplace, 'snails', klass=gqltypes.Snail, kwargs={'filters': filters}
        )

    def iterate_all_snails(self, filters={}, more_stats=False) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_all_snails,
            'snails',
            klass=gqltypes.Snail,
            kwargs={'filters': filters, 'more_stats': more_stats},
        )

    def iterate_my_snails_for_missions(self, owner, adaptations=None) -> Generator[gqltypes.Snail, None, None]:
        yield from self._iterate_pages(
            self.gql.get_my_snails_for_missions,
            'snails',
            klass=gqltypes.Snail,
            args=[owner],
            kwargs={'adaptations': adaptations},
        )

    def iterate_my_snails_for_ranked(self, owner, league):
        yield from self._iterate_pages(
            self.gql.get_my_snails_for_ranked, 'snails', klass=gqltypes.Snail, args=[owner, league]
        )

    def iterate_inventory(self, address, adaptations=None) -> Generator[gqltypes.InventoryItem, None, None]:
        yield from self._iterate_pages(
            self.gql.get_inventory,
            'items',
            klass=gqltypes.InventoryItem,
            args=[address],
        )

    def iterate_mission_races(self, filters={}, max_calls=None) -> Generator[gqltypes.Race, None, None]:
        yield from self._iterate_pages(
            self.gql.get_mission_races,
            'all',
            klass=gqltypes.Race,
            kwargs={'filters': filters},
            max_calls=max_calls,
        )

    def iterate_onboarding_races(self, own=False, filters={}) -> Generator[gqltypes.Race, None, None]:
        k = 'own' if own else 'all'
        yield from self._iterate_pages(
            self.gql.get_onboarding_races, k, klass=gqltypes.Race, kwargs={'filters': filters}
        )

    def iterate_finished_races(self, filters={}, own=False, max_calls=None) -> Generator[gqltypes.Race, None, None]:
        k = 'own' if own else 'all'
        yield from self._iterate_pages(
            self.gql.get_finished_races,
            k,
            klass=gqltypes.Race,
            kwargs={'filters': filters, 'own': own},
            max_calls=max_calls,
        )

    def iterate_race_history(self, filters={}) -> Generator[gqltypes.Race, None, None]:
        yield from self._iterate_pages(
            self.gql.get_race_history, 'races', klass=gqltypes.Race, kwargs={'filters': filters}
        )

    def rejoin_mission_races(self, gql_payload, **kwargs):
        return self.web3.join_daily_mission(
            (
                gql_payload['payload']['race_id'],
                gql_payload['payload']['token_id'],
                gql_payload['payload']['address'],
            ),
            gql_payload['payload']['size'],
            [
                (x['race_id'], x['race_type'], x['owners'], list(map(int, x['rewards_wei'])))
                for x in gql_payload['payload']['completed_races']
            ],
            gql_payload['payload']['timeout'],
            gql_payload['payload']['salt'],
            gql_payload['signature'],
            **kwargs,
        )

    def join_mission_races(self, snail_id: int, race_id: int, allow_last_spot=False):
        """join mission race - signature is generated by `sign_race_join`"""
        signature = self.web3.sign_race_join(snail_id, race_id)
        r = self.gql.join_mission_races(snail_id, race_id, self.web3.wallet, signature)
        if r.get('status') == 0:
            return r, None
        elif r.get('status') == 1:
            if allow_last_spot:
                return r, self.rejoin_mission_races(r)
            else:
                raise RequiresTransactionClientError('requires_transaction', r)
        else:
            raise ClientError('unknown status', r)

    def join_competitive_races(self, snail_id: int, race_id: int, address: str):
        """join mission race - signature is generated by `sign_race_join`"""
        signature = self.web3.sign_race_join(address, snail_id, race_id)
        r = self.gql.join_competitive_races(snail_id, race_id, address, signature)
        if r.get('status') != 1:
            raise ClientError('unknown status', r)

        m = [
            (x['race_id'], x['race_type'], x['owners'], list(map(int, x['rewards_wei'])))
            for x in r['payload']['completed_races']
        ]
        return r, self.web3.join_competitive_race(
            (
                r['payload']['race_id'],
                r['payload']['token_id'],
                r['payload']['address'],
                int(r['payload']['entry_fee_wei']),
                r['payload']['size'],
            ),
            m[0],
            r['payload']['timeout'],
            r['payload']['salt'],
            r['signature'],
        )

    def marketplace_stats(self, market=1):
        d = self.gql.marketplace_stats(market=market)
        r = {
            'volume': d['volume'],
            'prices': {},
        }
        for l in d['floors']:
            r['prices'][l['name']] = [l['value'], None]
        for l in d['highs']:
            r['prices'][l['name']][1] = l['value']
        return r
